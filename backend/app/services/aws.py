# AWS Cost Analysis Service
import boto3
import botocore
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.app.models.analysis import RecommendationType


class AWSService:
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._ec2 = None
        self._ce = None
        self._cloudwatch = None

    @property
    def ec2(self):
        if self._ec2 is None:
            self._ec2 = boto3.client("ec2", region_name=self.region)
        return self._ec2

    @property
    def ce(self):
        if self._ce is None:
            self._ce = boto3.client("ce", region_name="us-east-1")  # Cost Explorer is global
        return self._ce

    @property
    def cloudwatch(self):
        if self._cloudwatch is None:
            self._cloudwatch = boto3.client("cloudwatch", region_name=self.region)
        return self._cloudwatch

    def _estimate_ec2_cost(self, instance_type: str) -> float:
        """Estimate monthly cost for EC2 instance type (on-demand, Linux)."""
        base_costs = {
            "t3.nano": 3.8, "t3.micro": 7.6, "t3.small": 15.2, "t3.medium": 30.4,
            "t3.large": 60.8, "t3.xlarge": 121.6, "t3.2xlarge": 243.2,
            "t4g.nano": 3.0, "t4g.micro": 6.1, "t4g.small": 12.1, "t4g.medium": 24.3,
            "m5.large": 70.1, "m5.xlarge": 140.2, "m5.2xlarge": 280.3, "m5.4xlarge": 560.6,
            "c5.large": 62.1, "c5.xlarge": 124.1, "c5.2xlarge": 248.2, "c5.4xlarge": 496.4,
            "r5.large": 94.6, "r5.xlarge": 189.2, "r5.2xlarge": 378.4, "r5.4xlarge": 756.8,
        }
        return base_costs.get(instance_type, 50.0)

    def detect_idle_instances(self, cpu_threshold: float = 5.0, days: int = 14) -> List[Dict[str, Any]]:
        """Detect EC2 instances with low CPU utilization."""
        findings = []
        try:
            paginator = self.ec2.get_paginator("describe_instances")
            for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
                for reservation in page["Reservations"]:
                    for instance in reservation["Instances"]:
                        instance_id = instance["InstanceId"]
                        instance_type = instance["InstanceType"]
                        launch_time = instance["LaunchTime"]

                        # Get CPU utilization from CloudWatch
                        end_time = datetime.utcnow()
                        start_time = end_time - timedelta(days=days)

                        try:
                            metrics = self.cloudwatch.get_metric_statistics(
                                Namespace="AWS/EC2",
                                MetricName="CPUUtilization",
                                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=3600,
                                Statistics=["Average", "Maximum"],
                            )

                            if metrics["Datapoints"]:
                                avg_cpu = sum(d["Average"] for d in metrics["Datapoints"]) / len(metrics["Datapoints"])
                                max_cpu = max(d["Maximum"] for d in metrics["Datapoints"])

                                if avg_cpu < cpu_threshold and max_cpu < cpu_threshold * 2:
                                    monthly_cost = self._estimate_ec2_cost(instance_type)
                                    findings.append({
                                        "type": RecommendationType.IDLE_INSTANCE.value,
                                        "resource_id": instance_id,
                                        "resource_type": f"EC2:{instance_type}",
                                        "region": self.region,
                                        "current_cost_monthly": monthly_cost,
                                        "recommended_action": f"Stop or terminate idle instance {instance_id} (avg CPU: {avg_cpu:.1f}%, max: {max_cpu:.1f}%)",
                                        "estimated_savings_monthly": monthly_cost,
                                        "confidence": 0.85,
                                        "details": {
                                            "instance_type": instance_type,
                                            "avg_cpu_percent": round(avg_cpu, 2),
                                            "max_cpu_percent": round(max_cpu, 2),
                                            "launch_time": launch_time.isoformat(),
                                            "analysis_days": days,
                                        },
                                    })
                        except botocore.exceptions.ClientError:
                            pass  # Skip instances without metrics
        except botocore.exceptions.ClientError as e:
            raise RuntimeError(f"AWS API error: {e}")

        return findings

    def find_unattached_volumes(self) -> List[Dict[str, Any]]:
        """Find unattached EBS volumes."""
        findings = []
        try:
            paginator = self.ec2.get_paginator("describe_volumes")
            for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
                for volume in page["Volumes"]:
                    volume_id = volume["VolumeId"]
                    size_gb = volume["Size"]
                    volume_type = volume["VolumeType"]

                    # Rough monthly cost estimation
                    cost_per_gb = {"gp2": 0.10, "gp3": 0.08, "io1": 0.125, "io2": 0.125, "st1": 0.045, "sc1": 0.025}.get(volume_type, 0.10)
                    monthly_cost = round(size_gb * cost_per_gb, 2)

                    findings.append({
                        "type": RecommendationType.UNATTACHED_VOLUME.value,
                        "resource_id": volume_id,
                        "resource_type": f"EBS:{volume_type}",
                        "region": self.region,
                        "current_cost_monthly": monthly_cost,
                        "recommended_action": f"Delete unattached {volume_type} volume {volume_id} ({size_gb} GiB)",
                        "estimated_savings_monthly": monthly_cost,
                        "confidence": 0.95,
                        "details": {
                            "size_gb": size_gb,
                            "volume_type": volume_type,
                            "create_time": volume["CreateTime"].isoformat() if volume.get("CreateTime") else None,
                        },
                    })
        except botocore.exceptions.ClientError as e:
            raise RuntimeError(f"AWS API error: {e}")

        return findings

    def find_orphaned_elastic_ips(self) -> List[Dict[str, Any]]:
        """Find unassociated Elastic IPs."""
        findings = []
        try:
            addresses = self.ec2.describe_addresses()["Addresses"]
            for addr in addresses:
                if "AssociationId" not in addr:
                    allocation_id = addr["AllocationId"]
                    public_ip = addr.get("PublicIp", "unknown")
                    # EIP cost: ~$3.65/month when not attached
                    monthly_cost = 3.65
                    findings.append({
                        "type": RecommendationType.ORPHANED_IP.value,
                        "resource_id": allocation_id,
                        "resource_type": "EIP",
                        "region": self.region,
                        "current_cost_monthly": monthly_cost,
                        "recommended_action": f"Release unassociated Elastic IP {public_ip} ({allocation_id})",
                        "estimated_savings_monthly": monthly_cost,
                        "confidence": 1.0,
                        "details": {"public_ip": public_ip, "domain": addr.get("Domain", "vpc")},
                    })
        except botocore.exceptions.ClientError as e:
            raise RuntimeError(f"AWS API error: {e}")

        return findings

    def get_rightsize_recommendations(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get right-sizing recommendations for a specific instance."""
        findings = []
        try:
            # Get instance details
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            if not response["Reservations"]:
                return findings

            instance = response["Reservations"][0]["Instances"][0]
            instance_type = instance["InstanceType"]

            # Get CPU/memory metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=14)

            cpu_metrics = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average", "Maximum"],
            )

            if not cpu_metrics["Datapoints"]:
                return findings

            avg_cpu = sum(d["Average"] for d in cpu_metrics["Datapoints"]) / len(cpu_metrics["Datapoints"])
            max_cpu = max(d["Maximum"] for d in cpu_metrics["Datapoints"])

            current_cost = self._estimate_ec2_cost(instance_type)

            # Simple right-sizing logic: if avg CPU < 20%, suggest one size down
            if avg_cpu < 20:
                smaller_types = {
                    "t3.large": "t3.medium", "t3.xlarge": "t3.large", "t3.2xlarge": "t3.xlarge",
                    "m5.xlarge": "m5.large", "m5.2xlarge": "m5.xlarge", "m5.4xlarge": "m5.2xlarge",
                    "c5.xlarge": "c5.large", "c5.2xlarge": "c5.xlarge", "c5.4xlarge": "c5.2xlarge",
                    "r5.xlarge": "r5.large", "r5.2xlarge": "r5.xlarge", "r5.4xlarge": "r5.2xlarge",
                }
                if instance_type in smaller_types:
                    recommended_type = smaller_types[instance_type]
                    new_cost = self._estimate_ec2_cost(recommended_type)
                    savings = current_cost - new_cost
                    findings.append({
                        "type": RecommendationType.RIGHTSIZE.value,
                        "resource_id": instance_id,
                        "resource_type": f"EC2:{instance_type}",
                        "region": self.region,
                        "current_cost_monthly": current_cost,
                        "recommended_action": f"Downsize {instance_id} from {instance_type} to {recommended_type} (avg CPU: {avg_cpu:.1f}%)",
                        "estimated_savings_monthly": round(savings, 2),
                        "confidence": 0.75,
                        "details": {
                            "current_type": instance_type,
                            "recommended_type": recommended_type,
                            "avg_cpu_percent": round(avg_cpu, 2),
                            "max_cpu_percent": round(max_cpu, 2),
                        },
                    })

        except botocore.exceptions.ClientError as e:
            raise RuntimeError(f"AWS API error: {e}")

        return findings

    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary from Cost Explorer."""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)

            response = self.ce.get_cost_and_usage(
                TimePeriod={"Start": start_date.isoformat(), "End": end_date.isoformat()},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            total_cost = 0.0
            by_service = {}
            for result in response["ResultsByTime"]:
                for group in result["Groups"]:
                    service = group["Keys"][0]
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    by_service[service] = by_service.get(service, 0) + amount
                    total_cost += amount

            return {
                "total_monthly_cost": round(total_cost, 2),
                "by_service": {k: round(v, 2) for k, v in sorted(by_service.items(), key=lambda x: -x[1])},
                "period_days": days,
            }
        except botocore.exceptions.ClientError as e:
            raise RuntimeError(f"AWS Cost Explorer error: {e}")

    def check_ri_coverage(self) -> Dict[str, Any]:
        """Check Reserved Instance coverage."""
        try:
            # Get RI utilization
            response = self.ce.get_reservation_utilization(
                TimePeriod={
                    "Start": (datetime.utcnow().date() - timedelta(days=30)).isoformat(),
                    "End": datetime.utcnow().date().isoformat(),
                }
            )

            total_ri_cost = 0.0
            total_on_demand_equivalent = 0.0

            for util in response["UtilizationsByTime"]:
                total_ri_cost += float(util.get("TotalActualHours", 0)) * 0.0  # Simplified
                total_on_demand_equivalent += float(util.get("TotalRunningHours", 0)) * 0.0

            return {
                "coverage_percent": 0.0,  # Would need more detailed calculation
                "recommendation": "Run detailed RI analysis with AWS Compute Optimizer",
            }
        except botocore.exceptions.ClientError:
            return {"coverage_percent": 0.0, "recommendation": "RI data unavailable"}


def create_aws_service(region: str = "us-east-1") -> AWSService:
    """Factory function for AWS service."""
    return AWSService(region)