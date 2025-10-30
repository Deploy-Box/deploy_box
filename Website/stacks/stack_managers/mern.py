import os
import hashlib
from django.db import transaction
from stacks.stack_managers.stack_manager import StackManager
from stacks.models import StackIACAttribute

class MERNStackManager(StackManager):
    def get_starter_stack_iac_attributes(self):
        return {
            "mongodbatlas_database_user.user-1": "{}",
            "azurerm_resource_group.rg-1": "{}",
            "azurerm_container_app.azurerm_container_app-1.name": f"mern-backend-contapp-{self.stack.id}",
            "azurerm_container_app.azurerm_container_app-1.secret": "[]",
            "azurerm_container_app.azurerm_container_app-1.ingress.target_port": "5000",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].image": "${deploy_box_iac.acr_name}.azurecr.io/mern-backend:latest",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=MONGO_URI": "${format(\"mongodb+srv://%s:%s@${deploy_box_iac.mongo_db_host}/%s\", mongodbatlas_database_user.user-1.username, mongodbatlas_database_user.user-1.password, one([for r in mongodbatlas_database_user.user-1.roles : r.database_name]))}",
            "azurerm_container_app.azurerm_container_app-2.name": f"mern-frontend-contapp-{self.stack.id}",
            "azurerm_container_app.azurerm_container_app-2.secret": "[]",
            "azurerm_container_app.azurerm_container_app-2.ingress.target_port": "8080",
            "azurerm_container_app.azurerm_container_app-2.template.container[0].image": "${deploy_box_iac.acr_name}.azurecr.io/mern-frontend:latest",
            "azurerm_container_app.azurerm_container_app-2.template.container[0].env.value?name=REACT_APP_BACKEND_URL": "https://${azurerm_container_app.azurerm_container_app-1.ingress[0].fqdn}",
        }
    
    def set_source_code_upload(self) -> None:
        with transaction.atomic():
            root_directory = self.stack.root_directory or "."
            if root_directory.endswith("/"):
                root_directory = root_directory[:-1]

            # Backend
            attribute = StackIACAttribute.objects.filter(
                stack_id=self.stack.id,
                attribute_name="azurerm_container_app.azurerm_container_app-1.template.container[0].image"
            ).first()
            if attribute:
                attribute.delete()

            attribute = StackIACAttribute.objects.filter(
                stack_id=self.stack.id,
                attribute_name="azurerm_container_app.azurerm_container_app-1.template.container[0].build_context"
            ).first()
            if not attribute:
                attribute = StackIACAttribute(
                    stack_id=self.stack.id,
                    attribute_name="azurerm_container_app.azurerm_container_app-1.template.container[0].build_context",
                    attribute_value=root_directory
                )

            attribute.save()

             # Frontend
            attribute = StackIACAttribute.objects.filter(
                stack_id=self.stack.id,
                attribute_name="azurerm_container_app.azurerm_container_app-2.template.container[0].image"
            ).first()
            if attribute:
                attribute.delete()

            attribute = StackIACAttribute.objects.filter(
                stack_id=self.stack.id,
                attribute_name="azurerm_container_app.azurerm_container_app-2.template.container[0].build_context"
            ).first()
            if not attribute:
                attribute = StackIACAttribute(
                    stack_id=self.stack.id,
                    attribute_name="azurerm_container_app.azurerm_container_app-2.template.container[0].build_context",
                    attribute_value=root_directory
                )

            attribute.save()

    def get_is_persistent(self) -> bool:
        backend_attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, key="azurerm_container_app.azurerm_container_app-1.template.min_replicas").first()
        frontend_attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, key="azurerm_container_app.azurerm_container_app-2.template.min_replicas").first()

        if backend_attribute and frontend_attribute:
            return backend_attribute.attribute_value == "1" and frontend_attribute.attribute_value == "1"
        return False

    def set_is_persistent(self, is_persistent: bool) -> None:
        with transaction.atomic():
            backend_attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, key="azurerm_container_app.azurerm_container_app-1.template.min_replicas").first()
            frontend_attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, key="azurerm_container_app.azurerm_container_app-2.template.min_replicas").first()

            if is_persistent:
                backend_attribute.attribute_value = "1"
                frontend_attribute.attribute_value = "1"
            else:
                backend_attribute.attribute_value = "0"
                frontend_attribute.attribute_value = "0"

            backend_attribute.save()
            frontend_attribute.save()

def get_iac():
    return {
        "mongodbatlas_database_user": {
            "user-1": {}
        },
        "azurerm_resource_group": {
            "rg-1": {}
        },
        "azurerm_container_app": {
            "azurerm_container_app-1": {
                "secret": [],
                "ingress": {
                    "target_port": 5000
                },
                "template": {
                    "container": [
                        {
                            "image": f"{os.environ.get('acr-name')}.azurecr.io/mern-backend:latest",
                            "env": [
                                {
                                    "name": "MONGO_URI",
                                    "value": "${format(\"mongodb+srv://%s:%s@" + os.environ.get('mongodb-host') + "/%s\", mongodbatlas_database_user.user-1.username, mongodbatlas_database_user.user-1.password, one([for r in mongodbatlas_database_user.user-1.roles : r.database_name]))}"
                                }
                            ],
                        }
                    ],
                },
            },
            "azurerm_container_app-2": {
                "secret": [],
                "ingress": {
                    "target_port": 8080
                },
                "template": {
                    "container": [
                        {
                            "image": f"{os.environ.get('acr-name')}.azurecr.io/mern-frontend:latest",
                            "env": [
                                {
                                    "name": "REACT_APP_BACKEND_URL",
                                    "value": f"https://${{azurerm_container_app.azurerm_container_app-1.ingress[0].fqdn}}",
                                }
                            ],
                        }
                    ]
                },
            },
        },
    }
