import os
import hashlib
from django.db import transaction
from stacks.stack_managers.stack_manager import StackManager
from stacks.models import StackIACAttribute

class DjangoStackManager(StackManager):
    def get_starter_stack_iac_attributes(self):
        secret_key = hashlib.sha256(os.urandom(64)).hexdigest()

        return {
            "neon_project.neon_project-1": "{}",
            "azurerm_resource_group.azurerm_resource_group-1": "{}",
            "azurerm_container_app.azurerm_container_app-1.name": f"django-contapp-{self.stack.id}",
            "azurerm_container_app.azurerm_container_app-1.secret": "[]",
            "azurerm_container_app.azurerm_container_app-1.ingress.target_port": "8080",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].name": "django-container",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].image": "${deploy_box_iac.acr_name}.azurecr.io/django:latest",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DJANGO_ALLOWED_HOSTS": "*",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DJANGO_SECRET_KEY": secret_key,
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DB_NAME": "${neon_project.neon_project-1.database_name}",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DB_USER": "${neon_project.neon_project-1.database_user}",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DB_PASSWORD": "${neon_project.neon_project-1.database_password}",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DB_HOST": "${neon_project.neon_project-1.database_host}",
            "azurerm_container_app.azurerm_container_app-1.template.container[0].env.value?name=DB_PORT": "5432",
            "azurerm_container_app.azurerm_container_app-1.template.min_replicas": "0",
            "azurerm_container_app.azurerm_container_app-1.template.max_replicas": "1",
        }
    
    def set_source_code_upload(self) -> None:
        with transaction.atomic():
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
                    attribute_value=self.stack.root_directory or "."
                )

            attribute.save()

    def get_is_persistent(self) -> bool:
        print("Getting is_persistent value")
        print(type(self.stack))
        attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, attribute_name="azurerm_container_app.azurerm_container_app-1.template.min_replicas").first()
        return attribute.attribute_value == "1" if attribute else False

    def set_is_persistent(self, is_persistent: bool) -> None:
        attribute = StackIACAttribute.objects.filter(stack_id=self.stack.id, attribute_name="azurerm_container_app.azurerm_container_app-1.template.min_replicas").first()

        if is_persistent:
            attribute.attribute_value = "1"
        else:
            attribute.attribute_value = "0"

        attribute.save()