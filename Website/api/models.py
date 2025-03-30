from django.db import models
from django.contrib.auth.models import User


class AvailableStacks(models.Model):
    type = models.CharField(max_length=10)
    variant = models.CharField(max_length=10)
    version = models.CharField(max_length=10)
    price_id = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.type


class Stacks(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    purchased_stack = models.ForeignKey(AvailableStacks, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username + " - " + self.name


class StackFrontends(models.Model):
    stack = models.ForeignKey(Stacks, on_delete=models.CASCADE)
    url = models.URLField()
    image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url


class StackBackends(models.Model):
    stack = models.ForeignKey(Stacks, on_delete=models.CASCADE)
    url = models.URLField()
    image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url


class StackDatabases(models.Model):
    stack = models.ForeignKey(Stacks, on_delete=models.CASCADE)
    uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    current_usage = models.IntegerField(default=0)
    pending_billed = models.IntegerField(default=0)

    def __str__(self):
        return self.url
