# from django.db import models  # type: ignore
# from django.db.models import UniqueConstraint  # type: ignore
# from projects.models import Project
# from core.fields import ShortUUIDField


# class AvailableStack(models.Model):
#     id = ShortUUIDField(primary_key=True)
#     type = models.CharField(max_length=10)
#     variant = models.CharField(max_length=10)
#     version = models.CharField(max_length=10)
#     price_id = models.CharField(max_length=50)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.type


# # class Stack(models.Model):
# #     id = ShortUUIDField(primary_key=True)
# #     name = models.CharField(max_length=100)
# #     project = models.ForeignKey(Project, on_delete=models.CASCADE)
# #     purchased_stack = models.ForeignKey(AvailableStack, on_delete=models.DO_NOTHING)
# #     instance_usage = models.FloatField(default=0)
# #     instance_usage_bill_amount = models.FloatField(default=0)
# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)

# #     class Meta:
# #         constraints = [
# #             UniqueConstraint(
# #                 fields=["project", "name"], name="unique_stack_name_per_project"
# #             )
# #         ]

# #     def __str__(self):
# #         return self.project.name + " - " + self.name


# class StackFrontend(models.Model):
#     id = ShortUUIDField(primary_key=True)
#     stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
#     url = models.URLField()
#     image_url = models.URLField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.url


# class StackBackend(models.Model):
#     id = ShortUUIDField(primary_key=True)
#     stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
#     url = models.URLField()
#     image_url = models.URLField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.url


# class StackDatabase(models.Model):
#     id = ShortUUIDField(primary_key=True)
#     stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
#     uri = models.URLField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     current_usage = models.IntegerField(default=0)
#     pending_billed = models.IntegerField(default=0)

#     def __str__(self):
#         return self.uri
