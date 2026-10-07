#!/usr/bin/env python3
# cloud-cost-optimizer — AI-powered cloud cost analysis for AWS, GCP, and Azure — finds waste, right-sizes instances, analyzes spend trends, and generates optimization plans with estimated savings.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
import json, os, re, sys, time, statistics
from datetime import datetime, timedelta

def _get_aws_client(service):
    try:
        import boto3
        session = boto3.Session()
        return session.client(service)
    except ImportError:
        raise SystemExit("boto3 not installed. Run: pip install boto3")

def _get_gcp_service(service_name):
    try:
        if service_name == "billing":
            from google.cloud import billing_v1
            return billing_v1.BillingAccountServiceClient()
        elif service_name == "compute":
            from google.cloud import compute_v1
            return compute_v1.InstancesClient()
    except ImportError:
        raise SystemExit("GCP SDK not installed. Run: pip install google-cloud-billing google-cloud-compute")

def _get_azure_client(service_name):
    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        if service_name == "billing":
            from azure.mgmt.consumption import ConsumptionManagementClient
            return ConsumptionManagementClient(cred)
        elif service_name == "compute":
            from azure.mgmt.compute import ComputeManagementClient
            return ComputeManagementClient(cred)
    except ImportError:
        raise SystemExit("Azure SDK not installed. Run: pip install azure-identity azure-mgmt-consumption azure-mgmt-compute")

def _detect_idle_instances_aws(region):
    ec2 = _get_aws_client("ec2")
    findings = []
    try:
        resp = ec2.describe_instances(Filters=[
            {"Name": "instance-state-name", "Values": ["running"]},
        ], MaxResults=100)
        for res in resp.get("Reservations", []):
            for inst in res.get("Instances", []):
                iid = inst.get("InstanceId")
                itype = inst.get("InstanceType")
                launch = inst.get("LaunchTime")
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                name = tags.get("Name", iid)
                try:
                    metrics = _get_aws_client("cloudwatch").get_metric_statistics(
                        Namespace="AWS/EC2", MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": iid}],
                        StartTime=datetime.utcnow() - timedelta(hours=24),
                        EndTime=datetime.utcnow(), Period=3600, Statistics=["Average"]
                    )
                    avg_cpu = statistics.mean(d["Average"] for d in metrics.get("Datapoints", []))
                except Exception:
                    avg_cpu = -1
                if avg_cpu >= 0 and avg_cpu < 5:
                    findings.append({"id": iid, "name": name, "type": itype, "avg_cpu_24h": round(avg_cpu, 1),
                                     "est_monthly_usd": _estimate_ec2_cost(itype, region), "reason": "CPU < 5% for 24h"})
    except Exception as e:
        print(f"  [warn] EC2 scan: {e}")
    return findings

def _estimate_ec2_cost(itype, region):
    base = {"t3.micro": 6.1, "t3.small": 24.5, "t3.medium": 49, "t3.large": 98, "t3.xlarge": 196,
            "t3.2xlarge": 392, "m5.large": 78.4, "m5.xlarge": 156.8, "m5.2xlarge": 313.6,
            "m5.4xlarge": 627.2, "m5.8xlarge": 1254.4, "c5.large": 75.2, "c5.xlarge": 150.4,
            "c5.2xlarge": 300.8, "c5.4xlarge": 601.6, "r5.large": 102.4, "r5.xlarge": 204.8}
    return round(base.get(itype, 100), 2)

def _find_unattached_ebs(region):
    ec2 = _get_aws_client("ec2")
    findings = []
    try:
        vols = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
        for v in vols.get("Volumes", []):
            size = v.get("Size", 0)
            vol_id = v.get("VolumeId")
            findings.append({"id": vol_id, "size_gb": size, "est_monthly_usd": round(size * 0.10, 2),
                             "reason": "Unattached EBS volume"})
    except Exception as e:
        print(f"  [warn] EBS scan: {e}")
    return findings

def _find_orphaned_ips(region):
    ec2 = _get_aws_client("ec2")
    findings = []
    try:
        addrs = ec2.describe_addresses(MaxResults=50)
        for a in addrs.get("Addresses", []):
            if not a.get("InstanceId"):
                findings.append({"id": a.get("PublicIp"), "est_monthly_usd": 4.0, "reason": "Unattached Elastic IP"})
    except Exception as e:
        print(f"  [warn] EIP scan: {e}")
    return findings

def _gcp_idle_instances():
    findings = []
    try:
        client = _get_gcp_service("compute")
        for zone in ["us-central1-a", "us-east1-b", "us-west1-a"]:
            try:
                instances = client.list(project="auto", zone=zone)
                for inst in instances:
                    if inst.status == "RUNNING":
                        findings.append({"id": inst.name, "zone": zone, "machine_type": inst.machine_type.split("/")[-1],
                                         "est_monthly_usd": _estimate_gcp_cost(inst.machine_type.split("/")[-1]),
                                         "reason": "Running instance (check utilization)"})
            except Exception:
                continue
    except Exception as e:
        print(f"  [warn] GCP scan: {e}")
    return findings

def _estimate_gcp_cost(mtype):
    base = {"e2-micro": 10.0, "e2-small": 20.0, "e2-medium": 40.0, "n1-standard-1": 30.0,
            "n1-standard-2": 60.0, "n1-standard-4": 120.0, "n1-highmem-2": 96.0, "n1-highmem-4": 192.0}
    return round(base.get(mtype, 50), 2)

def _azure_idle_vms():
    findings = []
    try:
        client = _get_azure_client("compute")
        vms = client.virtual_machines.list_all()
        for vm in vms:
            if vm.power_state and "deallocated" in str(vm.power_state).lower():
                pass
            else:
                findings.append({"id": vm.name, "sku": vm.hardware_profile.vm_size,
                                 "est_monthly_usd": _estimate_azure_cost(vm.hardware_profile.vm_size),
                                 "reason": "Running VM (check utilization)"})
    except Exception as e:
        print(f"  [warn] Azure scan: {e}")
    return findings

def _estimate_azure_cost(vsize):
    base = {"Standard_B1s": 15.0, "Standard_B2s": 60.0, "Standard_DS1_v2": 25.0, "Standard_DS2_v2": 50.0,
            "Standard_D2_v3": 72.0, "Standard_D4_v3": 144.0, "Standard_E2_v3": 96.0, "Standard_E4_v3": 192.0}
    return round(base.get(vsize, 50), 2)

def cmd_analyze(args):
    llm = LLM()
    cloud = args.cloud.lower()
    days = args.days
    print(f"{'='*60}")
    print(f"CLOUD COST ANALYSIS — {cloud.upper()} — last {days} days")
    print(f"{'='*60}\n")
    print("Collecting cost data...")
    if cloud == "aws":
        findings = []
        findings += _detect_idle_instances_aws(args.region)
        findings += _find_unattached_ebs(args.region)
        findings += _find_orphaned_ips(args.region)
        print(f"  Found {len(findings)} potential waste items")
        total_waste = sum(f["est_monthly_usd"] for f in findings)
        print(f"  Estimated monthly waste: ${total_waste:.2f}")
    elif cloud == "gcp":
        findings = _gcp_idle_instances()
        print(f"  Found {len(findings)} running instances")
        total_waste = sum(f["est_monthly_usd"] for f in findings)
        print(f"  Estimated monthly cost of running instances: ${total_waste:.2f}")
    elif cloud == "azure":
        findings = _azure_idle_vms()
        print(f"  Found {len(findings)} running VMs")
        total_waste = sum(f["est_monthly_usd"] for f in findings)
        print(f"  Estimated monthly cost: ${total_waste:.2f}")
    else:
        raise SystemExit(f"Unsupported cloud: {cloud}")
    print(f"\n{'='*60}")
    print(f"TOTAL POTENTIAL SAVINGS: ${total_waste:.2f}/month (${total_waste * 12:.2f}/year)")
    print(f"{'='*60}\n")
    top5 = sorted(findings, key=lambda x: x["est_monthly_usd"], reverse=True)[:5]
    print("TOP 5 WASTE ITEMS:")
    for f in top5:
        print(f"  {f['id']:<30} ${f['est_monthly_usd']:>8.2f}/mo  {f['reason']}")
    if args.output:
        report = {"cloud": cloud, "region": args.region, "days": days, "findings": findings,
                  "total_monthly_waste": total_waste, "analyzed_at": datetime.utcnow().isoformat()}
        with open(args.output, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nReport saved to {args.output}")

def cmd_waste(args):
    llm = LLM()
    cloud = args.cloud.lower()
    print(f"{'='*60}")
    print(f"WASTE DETECTION — {cloud.upper()}")
    print(f"{'='*60}\n")
    findings = []
    if cloud == "aws":
        findings += _detect_idle_instances_aws(args.region)
        findings += _find_unattached_ebs(args.region)
        findings += _find_orphaned_ips(args.region)
    elif cloud == "gcp":
        findings = _gcp_idle_instances()
    elif cloud == "azure":
        findings = _azure_idle_vms()
    total = sum(f["est_monthly_usd"] for f in findings)
    print(f"Total waste items: {len(findings)}")
    print(f"Total monthly waste: ${total:.2f}")
    print(f"Total yearly waste: ${total * 12:.2f}\n")
    for f in sorted(findings, key=lambda x: x["est_monthly_usd"], reverse=True):
        print(f"  ${f['est_monthly_usd']:>8.2f}/mo  {f['id']:<35} {f['reason']}")
    if findings:
        prompt = f"You are a FinOps engineer. Here are {len(findings)} waste items found in a {cloud} account:\n" + json.dumps(findings, indent=2) + "\n\nGenerate a prioritized action plan to eliminate this waste. For each item, give: 1) the exact CLI/API command to fix it, 2) estimated savings, 3) risk level (low/med/high), 4) recommended timeline."
        plan = llm.generate(prompt)
        print(f"\n{'='*60}")
        print("AI ACTION PLAN:")
        print(f"{'='*60}")
        print(plan)

def cmd_rightsize(args):
    llm = LLM()
    print(f"Right-sizing analysis for {args.instance}")
    cloud = args.cloud.lower()
    if cloud == "aws":
        try:
            cw = _get_aws_client("cloudwatch")
            for metric in ["CPUUtilization", "MemoryUsedPercent", "NetworkIn", "NetworkOut"]:
                try:
                    resp = cw.get_metric_statistics(Namespace="AWS/EC2", MetricName=metric,
                        Dimensions=[{"Name": "InstanceId", "Value": args.instance}],
                        StartTime=datetime.utcnow() - timedelta(days=7),
                        EndTime=datetime.utcnow(), Period=3600, Statistics=["Average", "Maximum", "p95"])
                    dp = resp.get("Datapoints", [])
                    if dp:
                        avg = statistics.mean(d.get("Average", 0) for d in dp)
                        mx = max(d.get("Maximum", 0) for d in dp)
                        p95 = max(d.get("p95", 0) for d in dp)
                        print(f"  {metric:<20} avg={avg:.1f}  max={mx:.1f}  p95={p95:.1f}")
                except Exception:
                    pass
        except Exception as e:
            print(f"  [warn] CloudWatch: {e}")
    prompt = f"Instance: {args.instance}, Cloud: {cloud}. Based on typical utilization patterns, recommend a right-sized instance type. Consider: if CPU < 20% sustained, recommend smaller compute-optimized; if memory-bound, recommend r-series; if balanced, m-series. Give 2-3 options with cost comparison."
    rec = llm.generate(prompt)
    print(f"\nRIGHT-SIZING RECOMMENDATION:\n{rec}")

def cmd_ask(args):
    llm = LLM()
    question = args.question
    cloud = args.cloud.lower()
    print(f"{'='*60}")
    print(f"COST Q&A — {cloud.upper()}")
    print(f"{'='*60}")
    print(f"Q: {question}\n")
    findings = []
    if cloud == "aws":
        findings = _detect_idle_instances_aws(args.region) + _find_unattached_ebs(args.region) + _find_orphaned_ips(args.region)
    elif cloud == "gcp":
        findings = _gcp_idle_instances()
    elif cloud == "azure":
        findings = _azure_idle_vms()
    context = json.dumps(findings[:20], indent=2) if findings else "No specific findings collected."
    prompt = f"You are a cloud cost expert. Answer this question using the provided account data when relevant:\n\nAccount data ({cloud}):\n{context}\n\nQuestion: {question}\n\nBe specific with numbers, service names, and actionable recommendations. If data is insufficient, explain what additional data would help."
    answer = llm.generate(prompt)
    print(answer)

def cmd_plan(args):
    llm = LLM()
    cloud = args.cloud.lower()
    target = args.target_savings or 0
    print(f"Generating optimization plan targeting ${target}/month savings...\n")
    findings = []
    if cloud == "aws":
        findings = _detect_idle_instances_aws(args.region) + _find_unattached_ebs(args.region) + _find_orphaned_ips(args.region)
    elif cloud == "gcp":
        findings = _gcp_idle_instances()
    elif cloud == "azure":
        findings = _azure_idle_vms()
    total = sum(f["est_monthly_usd"] for f in findings)
    print(f"Current detected waste: ${total:.2f}/month")
    prompt = f"Generate a 90-day cloud cost optimization plan for a {cloud} account.\n\nTarget: save ${target}/month (currently {round(target/total*100,1) if total else 0}% of detected waste).\n\nCurrent waste items:\n{json.dumps(findings[:30], indent=2)}\n\nInclude: Phase 1 (week 1-2: quick wins), Phase 2 (week 3-6: structural changes), Phase 3 (week 7-12: optimization programs). For each phase list specific actions, expected savings, and success metrics. Also recommend reserved instance / committed use coverage strategy."
    plan = llm.generate(prompt)
    print(f"\n{'='*60}")
    print("90-DAY COST OPTIMIZATION PLAN")
    print(f"{'='*60}\n")
    print(plan)

def main():
    import argparse
    p = argparse.ArgumentParser(prog="cloud-cost-optimizer", description="AI-powered cloud cost analysis and optimization")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="Full cost analysis with waste detection")
    a.add_argument("--cloud", required=True, choices=["aws", "gcp", "azure"]); a.add_argument("--region", default="us-east-1")
    a.add_argument("--days", type=int, default=30); a.add_argument("--output", default=None)
    a.set_defaults(fn=cmd_analyze)

    w = sub.add_parser("waste", help="Detect waste with AI action plan")
    w.add_argument("--cloud", required=True, choices=["aws", "gcp", "azure"]); w.add_argument("--region", default="us-east-1")
    w.set_defaults(fn=cmd_waste)

    r = sub.add_parser("rightsize", help="Right-size a specific instance")
    r.add_argument("--cloud", default="aws", choices=["aws", "gcp", "azure"]); r.add_argument("--instance", required=True)
    r.add_argument("--region", default="us-east-1")
    r.set_defaults(fn=cmd_rightsize)

    q = sub.add_parser("ask", help="Ask a natural language cost question")
    q.add_argument("--question", required=True); q.add_argument("--cloud", default="aws", choices=["aws", "gcp", "azure"])
    q.add_argument("--region", default="us-east-1")
    q.set_defaults(fn=cmd_ask)

    pl = sub.add_parser("plan", help="Generate 90-day optimization plan")
    pl.add_argument("--cloud", default="aws", choices=["aws", "gcp", "azure"]); pl.add_argument("--target-savings", type=float, default=0)
    pl.add_argument("--region", default="us-east-1")
    pl.set_defaults(fn=cmd_plan)

    args = p.parse_args()
    args.fn(args)

if __name__ == '__main__':
    main()
