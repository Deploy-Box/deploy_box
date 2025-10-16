import json
from django.db import models
from django.db.models import UniqueConstraint
from projects.models import Project

from core.fields import ShortUUIDField


class PurchasableStack(models.Model):
    id = ShortUUIDField(primary_key=True)
    type = models.CharField(max_length=10)
    variant = models.CharField(max_length=10)
    version = models.CharField(max_length=10)
    price_id = models.CharField(max_length=50)
    description = models.CharField(default="check out this stack", max_length=512)
    name = models.CharField(default="this is a stack", max_length=128)
    prebuilt_quantity = models.PositiveIntegerField(default=0, help_text="Number of prebuilt stacks available for immediate use")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.type


class Stack(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    purchased_stack = models.ForeignKey(PurchasableStack, on_delete=models.DO_NOTHING)
    root_directory = models.CharField(max_length=100, default="")
    instance_usage = models.FloatField(default=0)
    instance_usage_bill_amount = models.FloatField(default=0)
    status = models.CharField(max_length=100, default="STARTING")
    iac = models.JSONField(default=dict)
    iac_state = models.JSONField(default=dict)
    stack_information = models.JSONField(default=dict)
    parent_stack = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_stacks')
    environment_type = models.CharField(max_length=50, default="DEV")
    environment_name = models.CharField(max_length=50, default="Development")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # MERN
    @property
    def mern_frontend_url(self):
        return "https://" + self.stack_information.get("azurerm_container_app-1-endpoint", {}).get("value", "")

    @property
    def mern_backend_url(self):
        return "https://" + self.stack_information.get("azurerm_container_app-0-endpoint", {}).get("value", "")
    
    @property
    def mern_mongodb_uri(self):
        user = self.iac.get("mongodbatlas_database_user", {}).get("user-1", {})
        return user.get("username", "") + ":" + user.get("password", "") + "@cluster0.yjaoi.mongodb.net/" + user.get("roles", [{}])[0].get("database_name", "")
    

    # Django
    @property
    def django_url(self):
        return f'https://{self.get_attributes_from_resource("azurerm_container_app-1").get("ingress", [{}])[0].get("fqdn", "")}'
    
    @property
    def django_port(self):
        return self.get_attributes_from_resource("azurerm_container_app-1").get("ingress", [{}])[0].get("target_port", "")

    @property
    def django_postgres_host(self):
        return self.get_attributes_from_resource("neon_project-1").get("database_host", "")
    
    @property
    def django_postgres_database(self):
        return self.get_attributes_from_resource("neon_project-1").get("database_name", "")

    def get_attributes_from_resource(self, value) -> dict: 
        key = "name"
        resource_list = self.iac_state.get("resources", [])
        for resource in resource_list:
            if resource.get(key) == value:
                return resource.get("instances", [{}])[0].get("attributes", {})
        return {}

    @classmethod
    def get_service(cls, **kwargs):
        import stacks.services as stack_services


    @classmethod
    def post_service(cls, **kwargs):
        import stacks.services as stack_services

        return stack_services.add_stack(**kwargs)

    def __str__(self):
        return self.project.name + " - " + self.name


class PrebuiltStack(models.Model):
    id = ShortUUIDField(primary_key=True)
    purchasable_stack = models.ForeignKey(PurchasableStack, on_delete=models.CASCADE, related_name="prebuilt_stacks")
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PrebuiltStack {self.id} for PurchasableStack {self.purchasable_stack.id}"

class StackFrontend(models.Model):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    url = models.URLField()
    root_directory = models.CharField(max_length=100, default="")
    image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.url


class StackBackend(models.Model):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    url = models.URLField()
    root_directory = models.CharField(max_length=100, default="")
    image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.url


class StackDatabase(models.Model):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_usage = models.IntegerField(default=0)
    pending_billed = models.IntegerField(default=0)

    def __str__(self):
        return self.uri


class StackState(models.TextChoices):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    DELETING = "DELETING"
    UPDATING = "UPDATING"
    ERROR = "ERROR"

