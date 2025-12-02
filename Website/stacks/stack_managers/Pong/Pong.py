import os
import hashlib
from django.db import transaction
from stacks.stack_managers.stack_manager import StackManager
from stacks.models import StackIACAttribute
import base64

class PongStackManager(StackManager):
    @staticmethod
    def get_purchasable_stack_info():
        return {
            "name": "Pong",
            "type": "PONG",
            "variant": "STARTER",
            "version": "1.0",
            "description": "A simple Pong game stack deployed on Azure Virtual Machine.",
            "price_id": "TEST",
            "features": [
                "Azure Virtual Machine hosting Pong game",
                "Pre-configured environment for quick deployment",
                "Basic monitoring and logging setup"
            ]
        }
    
    @staticmethod
    def get_infrastructure_diagram_data() -> tuple[list[dict], list[dict], list[dict]]:
        wrappers = [
            {
                "id": "vm",
                "label": "Virtual Machine",
                "x": 330,
                "y": 150,
                "width": 500,
                "height": 200,
                "color": "rgba(139, 92, 246, 0.1)",
                "borderColor": "#8b5cf6",
                "nodeIds": ["frontend", "backend"]
            }
        ]

        nodes = [
            {
                "id": "public_ip",
                "label": "Public IP",
                "sublabel": "Network",
                "x": -100,
                "y": 225,
                "width": 150,
                "height": 80,
                "color": "#f59e0b",
                "icon": "🌍"
            },
            {
                "id": "proxy",
                "label": "Deploy Box Proxy",
                "sublabel": "Load Balancer",
                "x": 110,
                "y": 210,
                "width": 140,
                "height": 110,
                "color": "#ec4899",
                "icon": "🔀"
            },
            {
                "id": "frontend",
                "label": "Pong Web App",
                "sublabel": "Frontend",
                "x": 380,
                "y": 200,
                "width": 150,
                "height": 100,
                "color": "#10b981",
                "icon": "🌐"
            },
            {
                "id": "backend",
                "label": "PostgreSQL",
                "sublabel": "Database",
                "x": 630,
                "y": 200,
                "width": 150,
                "height": 100,
                "color": "#3b82f6",
                "icon": "🗄️"
            },
            {
                "id": "disk",
                "label": "Persistent Disk",
                "sublabel": "Storage",
                "x": 950,
                "y": 200,
                "width": 180,
                "height": 100,
                "color": "#64748b",
                "icon": "💾"
            }
        ]

        connections = [
            {"from": "public_ip", "to": "proxy", "label": "Internet"},
            {"from": "proxy", "to": "vm", "label": "Forwarded"},
            {"from": "frontend", "to": "backend", "label": "Data Connection"},
            {"from": "vm", "to": "disk", "label": "Mounted"}
        ]

        return wrappers, nodes, connections
    
    def get_starter_stack_iac_attributes(self):
        user_data = open(os.path.join(os.path.dirname(__file__), 'user_data.bash'), 'r').read()
        user_data = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')

        return {
            "azurerm_resource_group.azurerm_resource_group-1.name": f"{self.stack.id}-rg",
            "azurerm_resource_group.azurerm_resource_group-1.location": "eastus",
            "azurerm_resource_group.azurerm_resource_group-1.tags.org": self.stack.project.organization.id,
            "azurerm_resource_group.azurerm_resource_group-1.tags.project": self.stack.project.id,
            "azurerm_public_ip.azurerm_public_ip-1.allocation_method": "Static",
            "azurerm_public_ip.azurerm_public_ip-1.ddos_protection_mode": "VirtualNetworkInherited",
            "azurerm_public_ip.azurerm_public_ip-1.idle_timeout_in_minutes": "4",
            "azurerm_public_ip.azurerm_public_ip-1.ip_tags": "{}",
            "azurerm_public_ip.azurerm_public_ip-1.ip_version": "IPv4",
            "azurerm_public_ip.azurerm_public_ip-1.location": "${azurerm_resource_group.azurerm_resource_group-1.location}",
            "azurerm_public_ip.azurerm_public_ip-1.name": f"pong-vm-ip-{self.stack.id}",
            "azurerm_public_ip.azurerm_public_ip-1.resource_group_name": "${azurerm_resource_group.azurerm_resource_group-1.name}",
            "azurerm_public_ip.azurerm_public_ip-1.sku": "Standard",
            "azurerm_public_ip.azurerm_public_ip-1.sku_tier": "Regional",
            "azurerm_public_ip.azurerm_public_ip-1.tags": "{}",
            "azurerm_network_interface.azurerm_network_interface-1.accelerated_networking_enabled": "false",
            "azurerm_network_interface.azurerm_network_interface-1.dns_servers": "[]",
            "azurerm_network_interface.azurerm_network_interface-1.ip_forwarding_enabled": "false",
            "azurerm_network_interface.azurerm_network_interface-1.location": "${azurerm_resource_group.azurerm_resource_group-1.location}",
            "azurerm_network_interface.azurerm_network_interface-1.name": f"pong-vm-nic-{self.stack.id}",
            "azurerm_network_interface.azurerm_network_interface-1.resource_group_name": "${azurerm_resource_group.azurerm_resource_group-1.name}",
            "azurerm_network_interface.azurerm_network_interface-1.tags": "{}",
            "azurerm_network_interface.azurerm_network_interface-1.ip_configuration.name": "ipconfig1",
            "azurerm_network_interface.azurerm_network_interface-1.ip_configuration.primary": "true",
            "azurerm_network_interface.azurerm_network_interface-1.ip_configuration.private_ip_address_allocation": "Dynamic",
            "azurerm_network_interface.azurerm_network_interface-1.ip_configuration.private_ip_address_version": "IPv4",
            "azurerm_network_interface.azurerm_network_interface-1.ip_configuration.subnet_id": "/subscriptions/3106bb2d-2f28-445e-ab1e-79d93bd15979/resourceGroups/testing_rg/providers/Microsoft.Network/virtualNetworks/vnet-eastus/subnets/snet-eastus-2",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.admin_password": "password123!",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.admin_username": "kalebwbishop",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.user_data": user_data,
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.allow_extension_operations": "true",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.bypass_platform_safety_checks_on_user_schedule_enabled": "false",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.computer_name": f"pong-vm-{self.stack.id}",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.disable_password_authentication": "false",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.disk_controller_type": "SCSI",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.encryption_at_host_enabled": "false",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.extensions_time_budget": "PT1H30M",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.location": "${azurerm_resource_group.azurerm_resource_group-1.location}",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.max_bid_price": "-1",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.name": f"pong-vm-{self.stack.id}",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.network_interface_ids": ["${azurerm_network_interface.azurerm_network_interface-1.id}"],
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.patch_assessment_mode": "ImageDefault",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.patch_mode": "ImageDefault",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.priority": "Regular",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.provision_vm_agent": "true",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.resource_group_name": "${azurerm_resource_group.azurerm_resource_group-1.name}",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.secure_boot_enabled": "true",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.size": "Standard_B1s",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.tags": "{}",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.vtpm_enabled": "true",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.additional_capabilities.hibernation_enabled": "false",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.additional_capabilities.ultra_ssd_enabled": "false",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.os_disk.caching": "ReadWrite",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.os_disk.disk_size_gb": "8",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.os_disk.name": f"pong-vm-osdisk-{self.stack.id}",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.os_disk.storage_account_type": "StandardSSD_LRS",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.os_disk.write_accelerator_enabled": "false",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.source_image_reference.offer": "azure-linux-3",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.source_image_reference.publisher": "microsoftcblmariner",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.source_image_reference.sku": "azure-linux-3-kernel-hwe",
            "azurerm_linux_virtual_machine.azurerm_linux_virtual_machine-1.source_image_reference.version": "latest",
        }
    
    def get_is_persistent(self):
        pass

    def set_is_persistent(self, is_persistent: bool) -> None:
        pass
    