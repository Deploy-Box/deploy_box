from django.db import models
from django.db.models import UniqueConstraint
from projects.models import Project

from core.fields import ShortUUIDField
from core.models.requestable_model import RequestableModel


class PurchasableStack(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    type = models.CharField(max_length=10)
    variant = models.CharField(max_length=10)
    version = models.CharField(max_length=10)
    price_id = models.CharField(max_length=50)
    description = models.CharField(default="check out this stack", max_length=512)
    name = models.CharField(default="this is a stack", max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.type


class Stack(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    purchased_stack = models.ForeignKey(PurchasableStack, on_delete=models.DO_NOTHING)
    root_directory = models.CharField(max_length=100, default="")
    instance_usage = models.FloatField(default=0)
    instance_usage_bill_amount = models.FloatField(default=0)
    iac = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_service(cls, **kwargs):
        import stacks.services as stack_services


    @classmethod
    def post_service(cls, **kwargs):
        import stacks.services as stack_services

        return stack_services.add_stack(**kwargs)

    # class Meta:
    #     constraints = [
    #         UniqueConstraint(
    #             fields=["project", "name"], name="unique_stack_name_per_project"
    #         )
    #     ]

    def __str__(self):
        return self.project.name + " - " + self.name


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


class StackGoogleCloudRun(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    url = models.URLField()
    image_url = models.URLField()
    state = models.CharField(
        max_length=100, default="STARTING", choices=StackState.choices
    )
    build_status_url = models.URLField(default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class StackMongoDB(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.uri


class StackRedis(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.uri


class StackPostgreSQL(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.uri


class GoogleCloudBucket(RequestableModel):
    id = ShortUUIDField(primary_key=True)
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
