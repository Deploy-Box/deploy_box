"""Unified Resource model — replaces 17 individual resource tables.

All resource types share this single table. Type-specific configuration
lives in the `attributes` JSONField. Relationships are captured via
`parent` (ownership tree) and `ResourceDependency` (cross-cutting deps).
"""

import os
import uuid

from django.db import models

from core.fields import ShortUUIDField


class Resource(models.Model):
    """Single polymorphic model for all stack resources."""

    id = ShortUUIDField(primary_key=True, prefix="res")
    stack = models.ForeignKey(
        "stacks.Stack",
        on_delete=models.CASCADE,
        related_name="unified_resources",
    )
    index = models.IntegerField(default=0)
    name = models.CharField(max_length=255, blank=True, default="")
    resource_type = models.CharField(max_length=100, db_index=True)
    prefix = models.CharField(max_length=10, db_index=True)

    # Tree structure: ownership hierarchy for UI display
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    # Common provider fields (promoted from type-specific for fast filtering)
    provider_id = models.CharField(max_length=512, blank=True, default="")
    provider_name = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=50, blank=True, default="")
    tags = models.JSONField(default=dict, blank=True)

    # Type-specific attributes (all other fields from the original models)
    attributes = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["index"]
        indexes = [
            models.Index(fields=["stack", "resource_type"], name="idx_resource_stack_type"),
            models.Index(fields=["stack", "prefix"], name="idx_resource_stack_prefix"),
            models.Index(fields=["parent"], name="idx_resource_parent"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["stack", "resource_type", "index"],
                name="unique_resource_per_stack_type",
            ),
        ]

    def __str__(self):
        return f"{self.resource_type}:{self.name}" if self.name else self.resource_type

    def save(self, *args, **kwargs):
        # Generate ID using the resource-type prefix (e.g. res000, res002) so
        # that id.split('_')[0] gives the IaC ResourceManager prefix.
        if not self.pk and self.prefix:
            suffix = uuid.uuid4().hex[:16 - len(self.prefix) - 1]
            self.pk = f"{self.prefix}_{suffix}"

        # Auto-generate provider_name if not set (mirrors old save() logic)
        if not self.provider_name and self.stack_id:
            from .type_registry import ResourceTypeRegistry

            defn = ResourceTypeRegistry.get_by_type(self.resource_type)
            if defn and defn.generate_provider_name:
                self.provider_name = defn.generate_provider_name(
                    self.stack, self.index, self.prefix
                )

        # Auto-generate name if not set
        if not self.name:
            self.name = f"{self.resource_type}_{self.index}"

        super().save(*args, **kwargs)


class ResourceDependency(models.Model):
    """Cross-cutting dependency between resources (not ownership).

    Example: ContainerApp depends_on KeyVault for secrets,
    but the KeyVault is not a child of the ContainerApp.
    """

    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="dependencies"
    )
    depends_on = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="dependents"
    )
    dependency_type = models.CharField(
        max_length=50,
        blank=True,
        default="requires",
        help_text="e.g. requires, reads_from, writes_to, routes_to",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "depends_on"],
                name="unique_resource_dependency",
            ),
        ]

    def __str__(self):
        return f"{self.resource} → {self.depends_on} ({self.dependency_type})"
