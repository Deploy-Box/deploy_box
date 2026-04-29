from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from stacks.models import Stack, PurchasableStack
from stacks.resources.resources_manager import ResourcesManager, RESOURCE_MANAGER_MAPPING
from stacks.resources.resource import Resource, ResourceDependency
from stacks.resources.type_registry import ResourceTypeRegistry
from projects.models import Project
from organizations.models import Organization, OrganizationMember
from django.contrib.auth import get_user_model

UserProfile = get_user_model()


class _StackTestMixin:
    """Shared setUp for custom-stack tests."""

    def _create_base_objects(self):
        self.user = UserProfile.objects.create_user(
            username="customuser",
            email="custom@example.com",
            password="testpass123",
        )
        self.organization = Organization.objects.create(name="Test Org")
        OrganizationMember.objects.create(
            user=self.user,
            organization=self.organization,
            role="admin",
        )
        self.project = Project.objects.create(
            name="Test Project",
            organization=self.organization,
        )
        self.purchasable_stack = PurchasableStack.objects.create(
            type="CUSTOM",
            variant="CUSTOM",
            version="1.0",
            price_id="",
            name="Custom Stack",
            description="Build your own stack.",
            stack_infrastructure=[],
        )
        self.stack = Stack.objects.create(
            name="My Custom Stack",
            project=self.project,
            purchased_stack=self.purchasable_stack,
            status="DRAFT",
        )


# ---------------------------------------------------------------------------
# Unit tests — ResourcesManager
# ---------------------------------------------------------------------------
class ResourcesManagerAddRemoveTestCase(_StackTestMixin, TestCase):
    def setUp(self):
        self._create_base_objects()

    def test_add_resource_creates_instance(self):
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        self.assertIsNotNone(resource)
        self.assertEqual(resource.stack_id, self.stack.pk)
        self.assertTrue(resource.pk.startswith("res007"))

    def test_add_resource_increments_index(self):
        r1 = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        r2 = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        self.assertEqual(r1.index, 0)
        self.assertEqual(r2.index, 1)

    def test_add_resource_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            ResourcesManager.add_resource(self.stack, "NONEXISTENT_RESOURCE")

    def test_remove_resource_deletes(self):
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        resource_id = resource.pk
        self.assertTrue(ResourcesManager.remove_resource(resource_id))
        self.assertIsNone(ResourcesManager.read(resource_id))

    def test_remove_resource_not_found(self):
        self.assertFalse(ResourcesManager.remove_resource("res007_nonexistent"))

    def test_add_resource_with_config(self):
        resource = ResourcesManager.add_resource(
            self.stack,
            "AZURERM_CONTAINER_APP",
            config={"name": "my-backend"},
        )
        # The model's save() generates the name from resource type + index,
        # overriding any config-provided name.
        self.assertEqual(resource.name, "azurerm_container_app_0")

    def test_get_available_resource_types(self):
        types = ResourcesManager.get_available_resource_types()
        self.assertIsInstance(types, list)
        self.assertTrue(len(types) > 0)
        keys = {t["resource_type"] for t in types}
        self.assertIn("AZURERM_CONTAINER_APP", keys)
        self.assertIn("AZURERM_LINUX_VIRTUAL_MACHINE", keys)
        for t in types:
            self.assertIn("display_name", t)
            self.assertIn("category", t)

    def test_add_and_list_from_stack(self):
        ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        ResourcesManager.add_resource(self.stack, "AZURERM_LINUX_VIRTUAL_MACHINE")
        resources = ResourcesManager.get_from_stack(self.stack)
        self.assertEqual(len(resources), 2)


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------
class CustomStackServiceTestCase(_StackTestMixin, TestCase):
    def setUp(self):
        self._create_base_objects()

    @patch("payments.services.organization_has_payment_method", return_value=True)
    def test_create_custom_stack(self, _mock_payment):
        self.organization.has_reached_free_stack_limit = lambda: False
        from stacks.services import create_custom_stack
        data = create_custom_stack(project_id=str(self.project.pk))
        self.assertIn("id", data)
        stack = Stack.objects.get(pk=data["id"])
        self.assertEqual(stack.status, "DRAFT")
        self.assertEqual(stack.purchased_stack.type, "CUSTOM")

    def test_create_custom_stack_missing_project(self):
        from stacks.services import create_custom_stack, ValidationError
        with self.assertRaises(ValidationError):
            create_custom_stack(project_id="")

    def test_add_resource_to_stack_service(self):
        from stacks.services import add_resource_to_stack
        result = add_resource_to_stack(
            stack_id=str(self.stack.pk),
            resource_type="AZURERM_CONTAINER_APP",
        )
        self.assertIsNotNone(result)
        self.assertIn("id", result)

    def test_add_resource_to_nonexistent_stack(self):
        from stacks.services import add_resource_to_stack, NotFoundError
        with self.assertRaises(NotFoundError):
            add_resource_to_stack(stack_id="nonexistent", resource_type="AZURERM_CONTAINER_APP")

    def test_add_resource_bad_type(self):
        from stacks.services import add_resource_to_stack, ValidationError
        with self.assertRaises(ValidationError):
            add_resource_to_stack(stack_id=str(self.stack.pk), resource_type="BAD_TYPE")

    def test_remove_resource_from_stack_service(self):
        from stacks.services import add_resource_to_stack, remove_resource_from_stack
        result = add_resource_to_stack(
            stack_id=str(self.stack.pk),
            resource_type="AZURERM_CONTAINER_APP",
        )
        remove_resource_from_stack(
            stack_id=str(self.stack.pk),
            resource_id=result["id"],
        )
        resources = ResourcesManager.get_from_stack(self.stack)
        self.assertEqual(len(resources), 0)

    def test_remove_resource_wrong_stack(self):
        from stacks.services import add_resource_to_stack, remove_resource_from_stack, ValidationError
        result = add_resource_to_stack(
            stack_id=str(self.stack.pk),
            resource_type="AZURERM_CONTAINER_APP",
        )
        other_stack = Stack.objects.create(
            name="Other Stack",
            project=self.project,
            purchased_stack=self.purchasable_stack,
        )
        with self.assertRaises(ValidationError):
            remove_resource_from_stack(
                stack_id=str(other_stack.pk),
                resource_id=result["id"],
            )

    def test_list_stack_resources_service(self):
        from stacks.services import add_resource_to_stack, list_stack_resources
        add_resource_to_stack(stack_id=str(self.stack.pk), resource_type="AZURERM_CONTAINER_APP")
        add_resource_to_stack(stack_id=str(self.stack.pk), resource_type="AZURERM_PUBLIC_IP")
        resources = list_stack_resources(stack_id=str(self.stack.pk))
        self.assertEqual(len(resources), 2)

    def test_list_available_resource_types_service(self):
        from stacks.services import list_available_resource_types
        types = list_available_resource_types()
        self.assertEqual(len(types), len(RESOURCE_MANAGER_MAPPING))


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
class CustomStackAPITestCase(_StackTestMixin, APITestCase):
    def setUp(self):
        self._create_base_objects()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("payments.services.organization_has_payment_method", return_value=True)
    def test_create_custom_stack_endpoint(self, _mock_payment):
        self.organization.has_reached_free_stack_limit = lambda: False
        url = reverse("stacks:stack-create_custom")
        response = self.client.post(url, data={"project_id": str(self.project.pk)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

    def test_add_resource_endpoint(self):
        url = reverse("stacks:stack-add_resource", kwargs={"pk": str(self.stack.pk)})
        response = self.client.post(
            url,
            data={"resource_type": "AZURERM_CONTAINER_APP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

    def test_add_resource_invalid_type(self):
        url = reverse("stacks:stack-add_resource", kwargs={"pk": str(self.stack.pk)})
        response = self.client.post(
            url,
            data={"resource_type": "INVALID"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_resource_endpoint(self):
        # First add a resource
        add_url = reverse("stacks:stack-add_resource", kwargs={"pk": str(self.stack.pk)})
        add_resp = self.client.post(
            add_url,
            data={"resource_type": "AZURERM_CONTAINER_APP"},
            format="json",
        )
        resource_id = add_resp.data["id"]

        # Then remove it
        remove_url = reverse("stacks:stack-remove_resource", kwargs={"pk": str(self.stack.pk)})
        response = self.client.post(
            remove_url,
            data={"resource_id": resource_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_resources_endpoint(self):
        ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        url = reverse("stacks:stack-list_resources", kwargs={"pk": str(self.stack.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_available_resource_types_endpoint(self):
        url = reverse("stacks:stack-available_resource_types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        types = {t["resource_type"] for t in response.data}
        self.assertIn("AZURERM_CONTAINER_APP", types)
        self.assertIn("AZURERM_LINUX_VIRTUAL_MACHINE", types)

    @patch("stacks.services.send_to_queue", return_value=True)
    def test_add_resource_with_auto_deploy(self, mock_queue):
        url = reverse("stacks:stack-add_resource", kwargs={"pk": str(self.stack.pk)})
        response = self.client.post(
            url,
            data={"resource_type": "AZURERM_CONTAINER_APP", "auto_deploy": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_queue.assert_called_once()

    @patch("stacks.services.send_to_queue", return_value=True)
    def test_remove_resource_with_auto_deploy(self, mock_queue):
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        url = reverse("stacks:stack-remove_resource", kwargs={"pk": str(self.stack.pk)})
        response = self.client.post(
            url,
            data={"resource_id": resource.pk, "auto_deploy": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_queue.assert_called_once()

    def test_unauthenticated_add_resource_rejected(self):
        self.client.logout()
        url = reverse("stacks:stack-add_resource", kwargs={"pk": str(self.stack.pk)})
        response = self.client.post(
            url,
            data={"resource_type": "AZURERM_CONTAINER_APP"},
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ---------------------------------------------------------------------------
# Unified Resource model tests (Phase 1)
# ---------------------------------------------------------------------------
class ResourceTypeRegistryTestCase(TestCase):
    """Tests for the ResourceTypeRegistry utility."""

    def test_get_by_type_returns_definition(self):
        defn = ResourceTypeRegistry.get_by_type("azurerm_container_app")
        self.assertIsNotNone(defn)
        self.assertEqual(defn.prefix, "res007")
        self.assertEqual(defn.resource_type, "azurerm_container_app")

    def test_get_by_prefix_returns_definition(self):
        defn = ResourceTypeRegistry.get_by_prefix("res000")
        self.assertIsNotNone(defn)
        self.assertEqual(defn.resource_type, "azurerm_resource_group")

    def test_get_by_type_unknown_returns_none(self):
        defn = ResourceTypeRegistry.get_by_type("not_a_real_type")
        self.assertIsNone(defn)

    def test_get_by_prefix_unknown_returns_none(self):
        defn = ResourceTypeRegistry.get_by_prefix("res999")
        self.assertIsNone(defn)

    def test_all_17_types_registered(self):
        # Should have all resource types from RESOURCE_MANAGER_MAPPING
        for key in RESOURCE_MANAGER_MAPPING.keys():
            defn = ResourceTypeRegistry.get_by_type(key.lower())
            self.assertIsNotNone(defn, f"Missing type registry entry for {key}")

    def test_get_defaults(self):
        defaults = ResourceTypeRegistry.get_defaults("azurerm_container_app")
        self.assertIsInstance(defaults, dict)

    def test_get_display_name(self):
        name = ResourceTypeRegistry.get_display_name("azurerm_container_app")
        self.assertIsNotNone(name)
        self.assertIn("Container App", name)

    def test_get_category(self):
        category = ResourceTypeRegistry.get_category("azurerm_container_app")
        self.assertEqual(category.lower(), "compute")

    def test_get_parent_type(self):
        parent = ResourceTypeRegistry.get_parent_type("azurerm_container_app")
        self.assertEqual(parent, "azurerm_container_app_environment")

    def test_resource_group_has_no_parent(self):
        parent = ResourceTypeRegistry.get_parent_type("azurerm_resource_group")
        self.assertIsNone(parent)


class UnifiedResourceDualWriteTestCase(_StackTestMixin, TestCase):
    """Tests that dual-write creates Resource rows when using old ResourcesManager."""

    def setUp(self):
        self._create_base_objects()

    def test_add_resource_creates_unified_row(self):
        """Adding via ResourcesManager should also create a Resource row."""
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        unified = Resource.objects.filter(pk=resource.pk).first()
        self.assertIsNotNone(unified)
        self.assertEqual(unified.resource_type, "azurerm_container_app")
        self.assertEqual(unified.prefix, "res007")
        self.assertEqual(unified.stack, self.stack)

    def test_add_multiple_resources_creates_unified_rows(self):
        """Adding multiple resources creates multiple Resource rows."""
        r1 = ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        r2 = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        self.assertEqual(Resource.objects.filter(stack=self.stack).count(), 2)
        self.assertEqual(
            Resource.objects.get(pk=r1.pk).resource_type,
            "azurerm_resource_group",
        )
        self.assertEqual(
            Resource.objects.get(pk=r2.pk).resource_type,
            "azurerm_container_app",
        )

    def test_remove_resource_deletes_unified_row(self):
        """Removing via ResourcesManager should also delete the Resource row."""
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        self.assertTrue(Resource.objects.filter(pk=resource.pk).exists())
        ResourcesManager.remove_resource(resource.pk)
        self.assertFalse(Resource.objects.filter(pk=resource.pk).exists())

    def test_delete_stack_resources_clears_unified(self):
        """Deleting all resources for a stack clears Resource table too."""
        ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        self.assertEqual(Resource.objects.filter(stack=self.stack).count(), 2)
        ResourcesManager.delete(self.stack)
        self.assertEqual(Resource.objects.filter(stack=self.stack).count(), 0)

    def test_unified_resource_index_matches_old(self):
        """Resource index in unified model matches the old model."""
        r1 = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        r2 = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")
        u1 = Resource.objects.get(pk=r1.pk)
        u2 = Resource.objects.get(pk=r2.pk)
        self.assertEqual(u1.index, r1.index)
        self.assertEqual(u2.index, r2.index)

    def test_parent_inferred_for_child_resource(self):
        """Child resources should get parent set when parent already exists."""
        rg = ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        # Container App Environment's parent type is resource_group
        env = ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP_ENVIRONMENT")
        unified_env = Resource.objects.get(pk=env.pk)
        unified_rg = Resource.objects.get(pk=rg.pk)
        self.assertEqual(unified_env.parent, unified_rg)


class UnifiedResourceModelTestCase(_StackTestMixin, TestCase):
    """Tests for the Resource model itself."""

    def setUp(self):
        self._create_base_objects()

    def test_resource_str(self):
        resource = Resource.objects.create(
            stack=self.stack,
            index=0,
            name="test-rg",
            resource_type="azurerm_resource_group",
            prefix="res000",
        )
        self.assertIn("azurerm_resource_group", str(resource))
        self.assertIn("test-rg", str(resource))

    def test_unique_constraint_stack_type_index(self):
        """Cannot create two resources with the same stack + type + index."""
        Resource.objects.create(
            stack=self.stack, index=0, name="rg1",
            resource_type="azurerm_resource_group", prefix="res000",
        )
        with self.assertRaises(Exception):
            Resource.objects.create(
                stack=self.stack, index=0, name="rg2",
                resource_type="azurerm_resource_group", prefix="res000",
            )

    def test_different_types_same_index_allowed(self):
        """Different resource types CAN share the same index."""
        Resource.objects.create(
            stack=self.stack, index=0, name="rg",
            resource_type="azurerm_resource_group", prefix="res000",
        )
        Resource.objects.create(
            stack=self.stack, index=0, name="app",
            resource_type="azurerm_container_app", prefix="res007",
        )
        self.assertEqual(Resource.objects.filter(stack=self.stack).count(), 2)

    def test_resource_dependency_creation(self):
        """ResourceDependency links two resources."""
        r1 = Resource.objects.create(
            stack=self.stack, index=0, name="vault",
            resource_type="azurerm_key_vault", prefix="res00B",
        )
        r2 = Resource.objects.create(
            stack=self.stack, index=0, name="app",
            resource_type="azurerm_container_app", prefix="res007",
        )
        dep = ResourceDependency.objects.create(
            resource=r2, depends_on=r1, dependency_type="secret_access",
        )
        self.assertEqual(r2.dependencies.count(), 1)
        self.assertEqual(r2.dependencies.first().depends_on, r1)

    def test_cascade_delete_on_stack(self):
        """Deleting a stack cascades to Resource rows."""
        Resource.objects.create(
            stack=self.stack, index=0, name="rg",
            resource_type="azurerm_resource_group", prefix="res000",
        )
        stack_pk = self.stack.pk
        self.stack.delete()
        self.assertEqual(Resource.objects.filter(stack_id=stack_pk).count(), 0)

    def test_attributes_json_field(self):
        """Attributes JSONField stores arbitrary data."""
        resource = Resource.objects.create(
            stack=self.stack, index=0, name="app",
            resource_type="azurerm_container_app", prefix="res007",
            attributes={"cpu": 0.5, "memory": "1Gi", "min_replicas": 0},
        )
        resource.refresh_from_db()
        self.assertEqual(resource.attributes["cpu"], 0.5)
        self.assertEqual(resource.attributes["memory"], "1Gi")


class ResourceTreeViewTestCase(_StackTestMixin, APITestCase):
    """Tests for the resource-tree API endpoint."""

    def setUp(self):
        self._create_base_objects()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_resource_tree_empty_stack(self):
        url = reverse("stacks:resource-tree", kwargs={"stack_id": str(self.stack.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resource_tree"], [])

    def test_resource_tree_with_resources(self):
        Resource.objects.create(
            stack=self.stack, index=0, name="rg",
            resource_type="azurerm_resource_group", prefix="res000",
        )
        Resource.objects.create(
            stack=self.stack, index=0, name="app",
            resource_type="azurerm_container_app", prefix="res007",
        )
        url = reverse("stacks:resource-tree", kwargs={"stack_id": str(self.stack.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_resource_tree_unauthorized(self):
        self.client.logout()
        url = reverse("stacks:resource-tree", kwargs={"stack_id": str(self.stack.pk)})
        response = self.client.get(url)
        self.assertIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# Phase 2 — Unified read-path tests
# ---------------------------------------------------------------------------
class UnifiedReadPathTestCase(_StackTestMixin, TestCase):
    """Tests that the unified read path (USE_UNIFIED_RESOURCE_READS=True)
    produces correct output matching legacy format."""

    def setUp(self):
        self._create_base_objects()

    @patch("stacks.resources.resources_manager.django_settings")
    def test_get_from_stack_returns_resource_instances(self, mock_settings):
        """When flag is on, get_from_stack returns Resource instances."""
        mock_settings.USE_UNIFIED_RESOURCE_READS = True
        # Create via legacy path (dual-writes to unified)
        ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")

        resources = ResourcesManager.get_from_stack(self.stack)
        self.assertEqual(len(resources), 2)
        for r in resources:
            self.assertIsInstance(r, Resource)

    @patch("stacks.resources.resources_manager.django_settings")
    def test_get_from_stack_flag_off_returns_legacy_instances(self, mock_settings):
        """When flag is off, get_from_stack returns old model instances."""
        mock_settings.USE_UNIFIED_RESOURCE_READS = False
        ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")

        resources = ResourcesManager.get_from_stack(self.stack)
        self.assertEqual(len(resources), 1)
        self.assertNotIsInstance(resources[0], Resource)

    @patch("stacks.resources.resources_manager.django_settings")
    def test_serialize_unified_produces_legacy_format(self, mock_settings):
        """Serializing via unified path produces the same keys as legacy."""
        mock_settings.USE_UNIFIED_RESOURCE_READS = True
        ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")

        resources = ResourcesManager.get_from_stack(self.stack)
        serialized = ResourcesManager.serialize(resources)

        self.assertEqual(len(serialized), 1)
        data = serialized[0]
        # Must have legacy base fields
        self.assertIn("id", data)
        self.assertIn("index", data)
        self.assertIn("name", data)
        self.assertIn("type", data)
        self.assertEqual(data["type"], "RESOURCE")
        self.assertIn("stack", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)
        # Must have azurerm provider fields under original names
        self.assertIn("azurerm_id", data)
        self.assertIn("azurerm_name", data)
        # Must have tags
        self.assertIn("tags", data)

    @patch("stacks.resources.resources_manager.django_settings")
    def test_serialize_unified_container_app_has_attributes(self, mock_settings):
        """Container app attributes are flattened to top-level."""
        mock_settings.USE_UNIFIED_RESOURCE_READS = True
        ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")

        resources = ResourcesManager.get_from_stack(self.stack)
        serialized = ResourcesManager.serialize(resources)
        data = serialized[0]

        # Container app should have type-specific fields at top level
        self.assertIn("azurerm_id", data)
        self.assertIn("azurerm_name", data)
        self.assertEqual(data["type"], "RESOURCE")

    @patch("stacks.resources.resources_manager.django_settings")
    def test_parity_resource_group_legacy_vs_unified(self, mock_settings):
        """Legacy and unified serialization produce same keys for resource group."""
        # Create resource (dual-write active)
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")

        # Serialize via legacy path
        mock_settings.USE_UNIFIED_RESOURCE_READS = False
        legacy_resources = ResourcesManager.get_from_stack(self.stack)
        legacy_serialized = ResourcesManager.serialize(legacy_resources)

        # Serialize via unified path
        mock_settings.USE_UNIFIED_RESOURCE_READS = True
        unified_resources = ResourcesManager.get_from_stack(self.stack)
        unified_serialized = ResourcesManager.serialize(unified_resources)

        self.assertEqual(len(legacy_serialized), len(unified_serialized))
        legacy_data = legacy_serialized[0]
        unified_data = unified_serialized[0]

        # Key fields must match
        self.assertEqual(legacy_data["id"], unified_data["id"])
        self.assertEqual(legacy_data["index"], unified_data["index"])
        self.assertEqual(legacy_data["name"], unified_data["name"])
        self.assertEqual(legacy_data["type"], unified_data["type"])

    @patch("stacks.resources.resources_manager.django_settings")
    def test_unified_get_from_stack_single_query(self, mock_settings):
        """Unified path should use fewer queries than legacy (1 vs 17)."""
        mock_settings.USE_UNIFIED_RESOURCE_READS = True
        ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        ResourcesManager.add_resource(self.stack, "AZURERM_CONTAINER_APP")

        from django.test.utils import override_settings
        from django.db import connection, reset_queries
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            resources = ResourcesManager.get_from_stack(self.stack)

        # Should be 1 query (SELECT from stacks_resource WHERE stack_id=...)
        self.assertLessEqual(len(ctx), 2)  # 1 main + possibly 1 for parent join


class UnifiedRemoveResourceTestCase(_StackTestMixin, TestCase):
    """Tests that remove operations delete from both tables atomically."""

    def setUp(self):
        self._create_base_objects()

    def test_remove_resource_from_stack_deletes_both(self):
        """remove_resource_from_stack deletes from legacy AND unified tables."""
        from stacks.services import remove_resource_from_stack
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        resource_pk = resource.pk

        # Verify exists in both
        self.assertTrue(Resource.objects.filter(pk=resource_pk).exists())
        from stacks.resources.azurerm_resource_group.model import AzurermResourceGroup
        self.assertTrue(AzurermResourceGroup.objects.filter(pk=resource_pk).exists())

        # Remove
        remove_resource_from_stack(str(self.stack.pk), resource_pk)

        # Verify deleted from both
        self.assertFalse(Resource.objects.filter(pk=resource_pk).exists())
        self.assertFalse(AzurermResourceGroup.objects.filter(pk=resource_pk).exists())


class UnifiedBulkUpdateTestCase(_StackTestMixin, TestCase):
    """Tests that bulk_update_resources writes atomically to both tables."""

    def setUp(self):
        self._create_base_objects()

    def test_bulk_update_syncs_to_unified(self):
        """bulk_update_resources updates both old and unified tables."""
        from stacks.services import bulk_update_resources
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        resource_pk = resource.pk

        bulk_update_resources([{
            "id": resource_pk,
            "location": "westus2",
        }])

        # Verify unified model was updated
        unified = Resource.objects.get(pk=resource_pk)
        self.assertEqual(unified.location, "westus2")

    def test_bulk_update_with_provider_id(self):
        """bulk_update with azurerm_id updates unified provider_id."""
        from stacks.services import bulk_update_resources
        resource = ResourcesManager.add_resource(self.stack, "AZURERM_RESOURCE_GROUP")
        resource_pk = resource.pk

        bulk_update_resources([{
            "id": resource_pk,
            "azurerm_id": "/subscriptions/123/resourceGroups/my-rg",
        }])

        unified = Resource.objects.get(pk=resource_pk)
        self.assertEqual(unified.provider_id, "/subscriptions/123/resourceGroups/my-rg")
        # provider_name is auto-generated by the model's custom save(),
        # so just verify it's non-empty (sync happened)
        self.assertTrue(len(unified.provider_name) > 0)


class CompatSerializerTestCase(_StackTestMixin, TestCase):
    """Tests for the compatibility serializer directly."""

    def setUp(self):
        self._create_base_objects()

    def test_serialize_resource_group(self):
        """Resource group serializes with azurerm_id/azurerm_name fields."""
        from stacks.resources.compat_serializer import serialize_resource_compat
        resource = Resource.objects.create(
            stack=self.stack, index=0, name="test-rg",
            resource_type="azurerm_resource_group", prefix="res000",
            provider_id="/subscriptions/123/resourceGroups/test-rg",
            provider_name="test-rg",
            location="eastus",
            tags={"env": "dev"},
            attributes={"resource_group_name": "test-rg"},
        )
        data = serialize_resource_compat(resource)
        self.assertEqual(data["azurerm_id"], "/subscriptions/123/resourceGroups/test-rg")
        self.assertEqual(data["azurerm_name"], "test-rg")
        self.assertEqual(data["location"], "eastus")
        self.assertEqual(data["tags"], {"env": "dev"})
        self.assertEqual(data["type"], "RESOURCE")
        self.assertEqual(data["resource_group_name"], "test-rg")

    def test_serialize_postgres_database(self):
        """Postgres database serializes with deploybox_database_id field."""
        from stacks.resources.compat_serializer import serialize_resource_compat
        resource = Resource.objects.create(
            stack=self.stack, index=0, name="my-db",
            resource_type="deployboxrm_postgres_database", prefix="res00E",
            provider_id="db-12345",
            attributes={"db_host": "example.com", "db_port": 5432, "sslmode": "require"},
        )
        data = serialize_resource_compat(resource)
        self.assertEqual(data["deploybox_database_id"], "db-12345")
        self.assertNotIn("azurerm_id", data)
        self.assertEqual(data["db_host"], "example.com")
        self.assertEqual(data["db_port"], 5432)

    def test_serialize_workos_integration(self):
        """WorkOS integration has no provider_id fields."""
        from stacks.resources.compat_serializer import serialize_resource_compat
        resource = Resource.objects.create(
            stack=self.stack, index=0, name="workos",
            resource_type="deployboxrm_workos_integration", prefix="res008",
            attributes={"api_key": "wk_123", "client_id": "client_abc"},
        )
        data = serialize_resource_compat(resource)
        self.assertNotIn("azurerm_id", data)
        self.assertNotIn("thenilerm_id", data)
        self.assertNotIn("deploybox_database_id", data)
        self.assertEqual(data["api_key"], "wk_123")
        self.assertEqual(data["client_id"], "client_abc")

    def test_serialize_thenilerm_database(self):
        """Nile database serializes with thenilerm_id/thenilerm_name."""
        from stacks.resources.compat_serializer import serialize_resource_compat
        resource = Resource.objects.create(
            stack=self.stack, index=0, name="nile-db",
            resource_type="thenilerm_database", prefix="res009",
            provider_id="nile-id-123",
            provider_name="nile-db-name",
            tags={},
            attributes={"region": "AZURE_EASTUS", "sharded": True},
        )
        data = serialize_resource_compat(resource)
        self.assertEqual(data["thenilerm_id"], "nile-id-123")
        self.assertEqual(data["thenilerm_name"], "nile-db-name")
        self.assertEqual(data["region"], "AZURE_EASTUS")
        self.assertEqual(data["sharded"], True)
        self.assertIn("tags", data)
