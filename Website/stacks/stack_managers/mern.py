import os
from django.db import transaction
from stacks.stack_managers.stack_manager import StackManager
from stacks.models import StackIACAttribute

class MERNStackManager(StackManager):
    @staticmethod
    def get_purchasable_stack_info():
        return {
            "name": "MERN",
            "type": "MERN",
            "variant": "STARTER",
            "version": "1.0",
            "description": "A full-stack MERN application with MongoDB Atlas database and React frontend deployed on Azure Container Apps.",
            "price_id": "TEST",
            "features": [
                "Azure Container Apps hosting for backend and frontend",
                "MongoDB Atlas database integration",
                "Express.js backend API",
                "React frontend application",
                "Auto-scaling from 0 to 1 replica per container",
                "Pre-configured environment variables and database connection"
            ]
        }
    
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
        backend_attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, attribute_name="azurerm_container_app.azurerm_container_app-1.template.min_replicas").first()
        frontend_attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, attribute_name="azurerm_container_app.azurerm_container_app-2.template.min_replicas").first()

        if backend_attribute and frontend_attribute:
            return backend_attribute.attribute_value == "1" and frontend_attribute.attribute_value == "1"
        return False

    def set_is_persistent(self, is_persistent: bool) -> None:
        with transaction.atomic():
            backend_attributes = StackIACAttribute.objects.filter(stack_id=self.stack.id, attribute_name="azurerm_container_app.azurerm_container_app-1.template.min_replicas")
            assert backend_attributes.exists(), "Backend attribute not found"
            backend_attribute = backend_attributes.first()
            assert backend_attribute is not None, "Backend attribute not found"

            frontend_attributes = StackIACAttribute.objects.filter(stack_id=self.stack.id, attribute_name="azurerm_container_app.azurerm_container_app-2.template.min_replicas")
            assert frontend_attributes.exists(), "Frontend attribute not found"
            frontend_attribute = frontend_attributes.first()
            assert frontend_attribute is not None, "Frontend attribute not found"

            if is_persistent:
                backend_attribute.attribute_value = "1"
                frontend_attribute.attribute_value = "1"
            else:
                backend_attribute.attribute_value = "0"
                frontend_attribute.attribute_value = "0"

            backend_attribute.save()
            frontend_attribute.save()
