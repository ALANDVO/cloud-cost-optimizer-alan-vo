# GCP Cost Analysis Service
from datetime import datetime, timedelta
from typing import List, Dict, Any
from backend.app.models.analysis import RecommendationType


class GCPService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self._compute = None
        self._billing = None

    @property
    def compute(self):
        if self._compute is None:
            from google.cloud import compute_v1
            self._compute = compute_v1.InstancesClient()
        return self._compute

    def _estimate_gcp_cost(self, machine_type: str) -> float:
        """Estimate monthly cost for GCP machine type (on-demand)."""
        base_costs = {
            "e2-micro": 6.1, "e2-small": 12.1, "e2-medium": 24.3, "e2-standard-2": 48.6,
            "n1-standard-1": 24.7, "n1-standard-2": 49.3, "n1-standard-4": 98.6, "n1-standard-8": 197.1,
            "n1-highmem-2": 39.4, "n1-highmem-4": 78.8, "n1-highmem-8": 157.7,
            "n2-standard-2": 58.4, "n2-standard-4": 116.8, "n2-standard-8": 233.6,
        }
        # Extract base type from full machine type URL
        mt = machine_type.split("/")[-1]
        return base_costs.get(mt, 50.0)

    def detect_idle_instances(self, cpu_threshold: float = 5.0, days: int = 14) -> List[Dict[str, Any]]:
        """Detect idle GCP Compute Engine instances."""
        findings = []
        try:
            from google.cloud import compute_v1, monitoring_v3
            from google.api_core.exceptions import GoogleAPICallError

            client = compute_v1.InstancesClient()
            request = compute_v1.AggregatedListInstancesRequest(project=self.project_id)
            agg_list = client.aggregated_list(request=request)

            monitoring_client = monitoring_v3.MetricServiceClient()
            project_name = f"projects/{self.project_id}"
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            for zone, scope in agg_list:
                if scope.instances:
                    for instance in scope.instances:
                        if instance.status != "RUNNING":
                            continue

                        instance_name = instance.name
                        machine_type = instance.machine_type
                        zone_name = zone.split("/")[-1] if zone else "unknown"

                        # Get CPU metrics from Cloud Monitoring
                        try:
                            filter_str = f'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.label.instance_id="{instance.id}"'
                            results = monitoring_client.list_time_series(
                                name=project_name,
                                filter=filter_str,
                                interval={"end_time": end_time, "start_time": start_time},
                                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                            )

                            cpu_values = []
                            for ts in results:
                                for point in ts.points:
                                    cpu_values.append(point.value.double_value)

                            if cpu_values:
                                avg_cpu = sum(cpu_values) / len(cpu_values) * 100
                                max_cpu = max(cpu_values) * 100

                                if avg_cpu < cpu_threshold and max_cpu < cpu_threshold * 2:
                                    monthly_cost = self._estimate_gcp_cost(machine_type)
                                    findings.append({
                                        "type": RecommendationType.IDLE_INSTANCE.value,
                                        "resource_id": instance_name,
                                        "resource_type": f"GCE:{machine_type.split('/')[-1]}",
                                        "region": zone_name,
                                        "current_cost_monthly": monthly_cost,
                                        "recommended_action": f"Stop idle instance {instance_name} (avg CPU: {avg_cpu:.1f}%)",
                                        "estimated_savings_monthly": monthly_cost,
                                        "confidence": 0.85,
                                        "details": {
                                            "machine_type": machine_type,
                                            "avg_cpu_percent": round(avg_cpu, 2),
                                            "max_cpu_percent": round(max_cpu, 2),
                                            "zone": zone_name,
                                            "analysis_days": days,
                                        },
                                    })
                        except GoogleAPICallError:
                            pass  # Skip if metrics unavailable

        except Exception as e:
            raise RuntimeError(f"GCP API error: {e}")

        return findings

    def find_unattached_disks(self) -> List[Dict[str, Any]]:
        """Find unattached persistent disks."""
        findings = []
        try:
            from google.cloud import compute_v1
            from google.api_core.exceptions import GoogleAPICallError

            client = compute_v1.DisksClient()
            request = compute_v1.AggregatedListDisksRequest(project=self.project_id)
            agg_list = client.aggregated_list(request=request)

            for zone, scope in agg_list:
                if scope.disks:
                    for disk in scope.disks:
                        if not disk.users:  # Unattached disk
                            disk_name = disk.name
                            size_gb = disk.size_gb
                            disk_type = disk.type.split("/")[-1] if disk.type else "pd-standard"
                            zone_name = zone.split("/")[-1] if zone else "unknown"

                            cost_per_gb = {"pd-standard": 0.04, "pd-balanced": 0.10, "pd-ssd": 0.17, "pd-extreme": 0.60}.get(disk_type, 0.04)
                            monthly_cost = round(size_gb * cost_per_gb, 2)

                            findings.append({
                                "type": RecommendationType.UNATTACHED_VOLUME.value,
                                "resource_id": disk_name,
                                "resource_type": f"PD:{disk_type}",
                                "region": zone_name,
                                "current_cost_monthly": monthly_cost,
                                "recommended_action": f"Delete unattached disk {disk_name} ({size_gb} GiB, {disk_type})",
                                "estimated_savings_monthly": monthly_cost,
                                "confidence": 0.95,
                                "details": {
                                    "size_gb": size_gb,
                                    "disk_type": disk_type,
                                    "zone": zone_name,
                                },
                            })

        except Exception as e:
            raise RuntimeError(f"GCP API error: {e}")

        return findings

    def find_orphaned_ips(self) -> List[Dict[str, Any]]:
        """Find unassigned static external IPs."""
        findings = []
        try:
            from google.cloud import compute_v1
            from google.api_core.exceptions import GoogleAPICallError

            client = compute_v1.AddressesClient()
            request = compute_v1.AggregatedListAddressesRequest(project=self.project_id)
            agg_list = client.aggregated_list(request=request)

            for region, scope in agg_list:
                if scope.addresses:
                    for addr in scope.addresses:
                        if not addr.users:  # Unassigned static IP
                            addr_name = addr.name
                            ip_address = addr.address
                            region_name = region.split("/")[-1] if region else "global"
                            # Static IP cost: ~$7.30/month when not attached
                            monthly_cost = 7.30

                            findings.append({
                                "type": RecommendationType.ORPHANED_IP.value,
                                "resource_id": addr_name,
                                "resource_type": "Static IP",
                                "region": region_name,
                                "current_cost_monthly": monthly_cost,
                                "recommended_action": f"Release unassigned static IP {ip_address} ({addr_name})",
                                "estimated_savings_monthly": monthly_cost,
                                "confidence": 1.0,
                                "details": {"ip_address": ip_address, "region": region_name},
                            })

        except Exception as e:
            raise RuntimeError(f"GCP API error: {e}")

        return findings

    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary from Cloud Billing (requires BigQuery export)."""
        # This would require BigQuery billing export setup
        return {
            "total_monthly_cost": 0.0,
            "by_service": {},
            "period_days": days,
            "note": "Requires Cloud Billing export to BigQuery",
        }


def create_gcp_service(project_id: str) -> GCPService:
    return GCPService(project_id)