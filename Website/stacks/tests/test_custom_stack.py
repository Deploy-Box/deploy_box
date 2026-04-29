from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from stacks.models import Stack, PurchasableStack
from stacks.resources.resources_manager import ResourcesManager, RESOURCE_MANAGER_MAPPING
from projects.models import Project
from organizations.models import Organization
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
