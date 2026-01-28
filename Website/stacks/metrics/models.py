from django.db import models
from stacks.models import Stack

class MetricDefinition(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit_name = models.CharField(max_length=50) # e.g., "Bytes", "Requests", "Seconds"
    record_frequency_cron = models.CharField(max_length=100, default="0 * * * *")  # e.g., "0 * * * *" for hourly recording
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("name", "unit_name")

    def __str__(self):
        return self.name

class MetricUsageRecord(models.Model):
    metric_definition = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, related_name="usage_records")
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name="metric_usage_records")
    resource = models.CharField(max_length=255)  # e.g., specific resource identifier within the stack
    amount_used = models.DecimalField(max_digits=18, decimal_places=6)
    usage_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("metric_definition", "stack", "resource", "usage_date")

    def __str__(self):
        return f"{self.metric_definition} usage for {self.stack} on {self.usage_date} (Resource: {self.resource}) - Amount Used: {self.amount_used}"