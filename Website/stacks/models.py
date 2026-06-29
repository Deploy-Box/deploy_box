import json
from django.db import models
from django.db.models import UniqueConstraint
from projects.models import Project

from core.fields import ShortUUIDField
from stacks.resources import *

class PurchasableStack(models.Model):
    id = ShortUUIDField(primary_key=True)
    type = models.CharField(max_length=10)
    variant = models.CharField(max_length=10)
    version = models.CharField(max_length=10)
    price_id = models.CharField(max_length=50)
    features = models.JSONField(default=list, blank=True)
    description = models.CharField(default="check out this stack", max_length=512)
    name = models.CharField(default="this is a stack", max_length=128)
    prebuilt_quantity = models.PositiveIntegerField(default=0, help_text="Number of prebuilt stacks available for immediate use")
    stack_infrastructure = models.JSONField(default=dict, blank=True)
    source_code_location = models.CharField(max_length=255, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["type", "variant", "version"], name="unique_purchasable_stack")
        ]

    def __str__(self):
        return self.type


class StackStatus(models.TextChoices):
    STARTING = "STARTING", "Starting"
    DRAFT = "DRAFT", "Draft"
    PROVISIONING = "PROVISIONING", "Provisioning"
    READY = "READY", "Ready"
    RUNNING = "RUNNING", "Running"
    PAUSED = "PAUSED", "Paused"
    STOPPED = "STOPPED", "Stopped"
    ERROR = "ERROR", "Error"
    DELETING = "DELETING", "Deleting"
    DELETED = "DELETED", "Deleted"
    FAILED = "FAILED", "Failed"


class Stack(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    purchased_stack = models.ForeignKey(PurchasableStack, on_delete=models.PROTECT)
    root_directory = models.CharField(max_length=100, default="", blank=True)
    instance_usage = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    instance_usage_bill_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=StackStatus.choices, default=StackStatus.STARTING)
    error_message = models.TextField(default="", blank=True)
    iac_state = models.JSONField(default=dict)
    parent_stack = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_stacks')
    environment_type = models.CharField(max_length=50, default="DEV")
    environment_name = models.CharField(max_length=50, default="Development")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_persistent(self):
        attribute = StackIACAttribute.objects.filter(
            stack_id=self.id,
            attribute_name="azurerm_container_app.azurerm_container_app-1.template.min_replicas"
        ).first()
        if attribute is None:
            return False
        return attribute.attribute_value == "1"

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

class StackIACAttribute(models.Model):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name="iac_attributes")
    attribute_name = models.CharField(max_length=200)
    attribute_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['stack', 'attribute_name'], name='unique_stack_attribute')
        ]

    def __str__(self):
        return f"IAC Attribute {self.attribute_name} in Stack {self.stack.id}"

class DeploymentLog(models.Model):
    OPERATION_CHOICES = [
        ('APPLY', 'Apply'),
        ('DELETE', 'Delete'),
        ('PAUSE', 'Pause'),
        ('RESUME', 'Resume'),
    ]
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='deployment_logs')
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING')
    log_text = models.TextField(default='', blank=True)
    line_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['stack', '-started_at']),
        ]

    def __str__(self):
        return f"DeploymentLog {self.id} ({self.operation}) for Stack {self.stack_id}"


class PrebuiltStack(models.Model):
    id = ShortUUIDField(primary_key=True)
    purchasable_stack = models.ForeignKey(PurchasableStack, on_delete=models.CASCADE, related_name="prebuilt_stacks")
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PrebuiltStack {self.id} for PurchasableStack {self.purchasable_stack.id}"


class Operation(models.Model):
    """Tracks an IaC operation (apply/destroy/pause/resume) through its lifecycle.

    Created by Django before sending the Service Bus message. Claimed and
    completed by the IaC job via HMAC-authenticated API calls.
    """

    OPERATION_CHOICES = [
        ('APPLY', 'Apply'),
        ('DELETE', 'Delete'),
        ('PAUSE', 'Pause'),
        ('RESUME', 'Resume'),
        ('DEPLOY', 'Deploy'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCEEDED', 'Succeeded'),
        ('FAILED', 'Failed'),
        ('TIMED_OUT', 'Timed Out'),
    ]

    # Maps operation_type + success → stack status
    SUCCESS_STATUS_MAP = {
        'APPLY': StackStatus.READY,
        'DELETE': StackStatus.DELETED,
        'PAUSE': StackStatus.PAUSED,
        'RESUME': StackStatus.READY,
        'DEPLOY': StackStatus.READY,
    }

    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='operations')
    operation_type = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(default='', blank=True)
    attempt_id = models.CharField(
        max_length=64, default='', blank=True,
        help_text="Unique token set by the claiming worker to prove ownership.",
    )
    lease_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="If RUNNING and this time is passed, the operation is considered stuck.",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stack', '-created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    @property
    def is_terminal(self) -> bool:
        return self.status in ('SUCCEEDED', 'FAILED', 'TIMED_OUT')

    def __str__(self):
        return f"Operation {self.id} ({self.operation_type} / {self.status}) for Stack {self.stack_id}"

