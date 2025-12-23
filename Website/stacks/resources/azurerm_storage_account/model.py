from django.db import models

from core.fields import ShortUUIDField

TYPE_CHOICES = [
    ('RESOURCE', 'Resource'),
    ('DATA', 'Data'),
]

CLASS_PREFIX = "res002"

class AzurermStorageAccount(models.Model):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
    name = models.CharField(max_length=255)
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Resource specific fields
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='RESOURCE')
    azurerm_id = models.CharField(max_length=255)
    azurerm_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, default='eastus')
    tags = models.JSONField(default=dict, blank=True)
    access_tier = models.CharField(max_length=50, default='Hot')
    account_kind = models.CharField(max_length=50, default='StorageV2')
    account_replication_type = models.CharField(max_length=50, default='LRS')
    account_tier = models.CharField(max_length=50, default='Standard')
    allow_nested_items_to_be_public = models.BooleanField(default=False)
    allowed_copy_scope = models.CharField(max_length=255, blank=True, default='')
    cross_tenant_replication_enabled = models.BooleanField(default=False)
    default_to_oauth_authentication = models.BooleanField(default=False)
    dns_endpoint_type = models.CharField(max_length=50, default='Standard')
    edge_zone = models.CharField(max_length=255, blank=True, default='')
    https_traffic_only_enabled = models.BooleanField(default=True)
    infrastructure_encryption_enabled = models.BooleanField(default=False)
    is_hns_enabled = models.BooleanField(default=False)
    large_file_share_enabled = models.BooleanField(default=True)
    local_user_enabled = models.BooleanField(default=True)
    min_tls_version = models.CharField(max_length=50, default='TLS1_2')
    nfsv3_enabled = models.BooleanField(default=False)
    primary_access_key = models.CharField(max_length=255, blank=True, default='')
    primary_blob_connection_string = models.TextField(blank=True, default='')
    primary_connection_string = models.TextField(blank=True, default='')
    provisioned_billing_model_version = models.CharField(max_length=50, blank=True, default='')
    public_network_access_enabled = models.BooleanField(default=True)
    queue_encryption_key_type = models.CharField(max_length=50, default='Service')
    resource_group_name = models.CharField(max_length=255)
    secondary_access_key = models.CharField(max_length=255, blank=True, default='')
    secondary_blob_connection_string = models.TextField(blank=True, default='')
    secondary_connection_string = models.TextField(blank=True, default='')
    sftp_enabled = models.BooleanField(default=False)
    shared_access_key_enabled = models.BooleanField(default=True)
    table_encryption_key_type = models.CharField(max_length=50, default='Service')

    # Blob Properties
    blob_change_feed_enabled = models.BooleanField(default=False)
    blob_change_feed_retention_in_days = models.IntegerField(default=0)
    blob_default_service_version = models.CharField(max_length=50, blank=True, default='')
    blob_last_access_time_enabled = models.BooleanField(default=False)
    blob_versioning_enabled = models.BooleanField(default=False)
    
    # Container Delete Retention Policy
    blob_container_delete_retention_days = models.IntegerField(default=7)
    
    # Delete Retention Policy
    blob_delete_retention_days = models.IntegerField(default=7)
    blob_delete_retention_permanent_delete_enabled = models.BooleanField(default=False)

    # Share Properties
    share_retention_policy_days = models.IntegerField(default=7)

    def __str__(self):
        return self.name