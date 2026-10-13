# Azure Cost Analysis Service
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.app.models.analysis import RecommendationType


class AzureService:
    def __init__(self, subscription_id: str):
        self.subscription_id = subscription_id
        self._compute_client = None
        self._consumption_client = None
        self._authorization_client = None

    def _get_credential(self):
        from azure.identity import DefaultAzureCredential
        return DefaultAzureCredential()

    def _estimate_azure_cost(self, vm_size: str) -> float:
        """Estimate monthly cost for Azure VM size (on-demand, Linux)."""
        base_costs = {
            "Standard_B1s": 7.3, "Standard_B2s": 29.2, "Standard_B4ms": 58.4,
            "Standard_D2s_v3": 57.8, "Standard_D4s_v3": 115.6, "Standard_D8s_v3": 231.2,
            "Standard_E2s_v3": 77.1, "Standard_E4s_v3": 154.2, "Standard_E8s_v3": 308.4,
            "Standard_F2s_v2": 52.6, "Standard_F4s_v2": 105.1, "Standard_F8s_v2": 210.2,
        }
        return base_costs.get(vm_size, 50.0)

    def detect_idle_vms(self, cpu_threshold: float = 5.0, days: int = 14) -> List[Dict[str, Any]]:
        """Detect idle Azure Virtual Machines."""
        findings = []
        try:
            from azure.mgmt.compute import ComputeManagementClient
            from azure.mgmt.monitor import MonitorManagementClient
            from azure.identity import DefaultAzureCredential

            credential = self._get_credential()
            compute_client = ComputeManagementClient(credential, self.subscription_id)
            monitor_client = MonitorManagementClient(credential, self.subscription_id)

            vms = compute_client.virtual_machines.list_all()
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            for vm in vms:
                # Get instance view to check power state
                instance_view = compute_client.virtual_machines.instance_view(
                    vm.id.split("/")[4], vm.name  # resource group, vm name
                )
                power_state = "unknown"
                for status in instance_view.statuses:
                    if status.code.startswith("PowerState/"):
                        power_state = status.code.split("/")[-1]
                        break

                if power_state != "running":
                    continue

                vm_size = vm.hardware_profile.vm_size
                resource_group = vm.id.split("/")[4]
                location = vm.location

                # Get CPU metrics
                try:
                    metrics = monitor_client.metrics.list(
                        vm.id,
                        timespan=f"{start_time.isoformat()}Z/{end_time.isoformat()}Z",
                        interval=timedelta(hours=1),
                        metricnames="Percentage CPU",
                        aggregation="Average,Maximum",
                    )

                    cpu_values = []
                    for metric in metrics.value:
                        for ts in metric.timeseries:
                            for point in ts.data:
                                if point.average is not None:
                                    cpu_values.append(point.average)
                                if point.maximum is not None:
                                    cpu_values.append(point.maximum)

                    if cpu_values:
                        avg_cpu = sum(cpu_values) / len(cpu_values)
                        max_cpu = max(cpu_values)

                        if avg_cpu < cpu_threshold and max_cpu < cpu_threshold * 2:
                            monthly_cost = self._estimate_azure_cost(vm_size)
                            findings.append({
                                "type": RecommendationType.IDLE_INSTANCE.value,
                                "resource_id": vm.name,
                                "resource_type": f"VM:{vm_size}",
                                "region": location,
                                "current_cost_monthly": monthly_cost,
                                "recommended_action": f"Deallocate idle VM {vm.name} (avg CPU: {avg_cpu:.1f}%)",
                                "estimated_savings_monthly": monthly_cost,
                                "confidence": 0.85,
                                "details": {
                                    "vm_size": vm_size,
                                    "avg_cpu_percent": round(avg_cpu, 2),
                                    "max_cpu_percent": round(max_cpu, 2),
                                    "resource_group": resource_group,
                                    "analysis_days": days,
                                },
                            })
                except Exception:
                    pass  # Skip if metrics unavailable

        except Exception as e:
            raise RuntimeError(f"Azure API error: {e}")

        return findings

    def find_unattached_disks(self) -> List[Dict[str, Any]]:
        """Find unattached managed disks."""
        findings = []
        try:
            from azure.mgmt.compute import ComputeManagementClient
            from azure.identity import DefaultAzureCredential

            credential = self._get_credential()
            compute_client = ComputeManagementClient(credential, self.subscription_id)

            disks = compute_client.disks.list()
            for disk in disks:
                if disk.managed_by is None:  # Unattached
                    disk_name = disk.name
                    size_gb = disk.disk_size_gb
                    sku = disk.sku.name if disk.sku else "Standard_LRS"
                    location = disk.location
                    resource_group = disk.id.split("/")[4]

                    cost_per_gb = {
                        "Standard_LRS": 0.045, "StandardSSD_LRS": 0.075,
                        "Premium_LRS": 0.15, "Ultra_LRS": 0.25,
                    }.get(sku, 0.045)
                    monthly_cost = round(size_gb * cost_per_gb, 2)

                    findings.append({
                        "type": RecommendationType.UNATTACHED_VOLUME.value,
                        "resource_id": disk_name,
                        "resource_type": f"Disk:{sku}",
                        "region": location,
                        "current_cost_monthly": monthly_cost,
                        "recommended_action": f"Delete unattached disk {disk_name} ({size_gb} GiB, {sku})",
                        "estimated_savings_monthly": monthly_cost,
                        "confidence": 0.95,
                        "details": {
                            "size_gb": size_gb,
                            "sku": sku,
                            "location": location,
                            "resource_group": resource_group,
                        },
                    })

        except Exception as e:
            raise RuntimeError(f"Azure API error: {e}")

        return findings

    def find_orphaned_public_ips(self) -> List[Dict[str, Any]]:
        """Find unassociated public IP addresses."""
        findings = []
        try:
            from azure.mgmt.network import NetworkManagementClient
            from azure.identity import DefaultAzureCredential

            credential = self._get_credential()
            network_client = NetworkManagementClient(credential, self.subscription_id)

            public_ips = network_client.public_ip_addresses.list_all()
            for pip in public_ips:
                if pip.ip_configuration is None:  # Unassociated
                    pip_name = pip.name
                    ip_address = pip.ip_address or "unknown"
                    location = pip.location
                    resource_group = pip.id.split("/")[4]
                    sku = pip.sku.name if pip.sku else "Basic"
                    # Static public IP cost: ~$3.65/month (Basic) or $5.50 (Standard) when not attached
                    monthly_cost = 5.50 if sku == "Standard" else 3.65

                    findings.append({
                        "type": RecommendationType.ORPHANED_IP.value,
                        "resource_id": pip_name,
                        "resource_type": f"PublicIP:{sku}",
                        "region": location,
                        "current_cost_monthly": monthly_cost,
                        "recommended_action": f"Delete unassociated public IP {ip_address} ({pip_name})",
                        "estimated_savings_monthly": monthly_cost,
                        "confidence": 1.0,
                        "details": {"ip_address": ip_address, "sku": sku, "resource_group": resource_group},
                    })

        except Exception as e:
            raise RuntimeError(f"Azure API error: {e}")

        return findings

    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary from Azure Cost Management."""
        try:
            from azure.mgmt.consumption import ConsumptionManagementClient
            from azure.identity import DefaultAzureCredential

            credential = self._get_credential()
            consumption_client = ConsumptionManagementClient(credential, self.subscription_id)

            # This is simplified - real usage would query usage details
            return {
                "total_monthly_cost": 0.0,
                "by_service": {},
                "period_days": days,
                "note": "Requires Cost Management API configuration",
            }
        except Exception:
            return {
                "total_monthly_cost": 0.0,
                "by_service": {},
                "period_days": days,
                "note": "Cost data unavailable",
            }


def create_azure_service(subscription_id: str) -> AzureService:
    return AzureService(subscription_id)