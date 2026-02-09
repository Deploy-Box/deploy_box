from django.db import models
from stacks.models import Stack
from croniter import croniter, CroniterBadCronError

class MetricDefinition(models.Model):
    name = models.CharField(max_length=255)
    applicable_resources = models.JSONField()  # e.g., ["stacks_azurermstoragecontainer"]
    description = models.TextField(blank=True)
    unit_name = models.CharField(max_length=50) # e.g., "Bytes", "Requests", "Seconds"
    record_frequency_cron = models.CharField(max_length=100)  # e.g., "0 * * * *" for hourly recording
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("name", "unit_name")

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Ensure that the record_frequency_cron is a valid cron expression
        try:
            croniter(self.record_frequency_cron)
        except CroniterBadCronError:
            raise ValueError(f"Invalid cron expression: {self.record_frequency_cron}")
        
        super().save(*args, **kwargs)

class MetricUsageRecord(models.Model):
    metric_definition = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, related_name="usage_records")
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name="metric_usage_records")
    resource = models.CharField(max_length=255)  # e.g., specific resource identifier within the stack
    amount_used = models.DecimalField(max_digits=18, decimal_places=6)
    usage_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("metric_definition", "stack", "resource", "usage_datetime")

    def __str__(self):
        return f"{self.metric_definition} usage for {self.stack} on {self.usage_datetime} (Resource: {self.resource}) - Amount Used: {self.amount_used}"