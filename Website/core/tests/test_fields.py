from django.test import TestCase
from django.db import models

from core.fields import ShortUUIDField


class _PlainModel(models.Model):
    """Unmanaged model for testing ShortUUIDField without a DB table."""
    id = ShortUUIDField(primary_key=True)

    class Meta:
        app_label = "core"
        managed = False


class _PrefixedModel(models.Model):
    """Unmanaged model for testing ShortUUIDField with a prefix."""
    id = ShortUUIDField(primary_key=True, prefix="org")

    class Meta:
        app_label = "core"
        managed = False


class ShortUUIDFieldTest(TestCase):

    def test_pre_save_generates_value_on_add(self):
        field = _PlainModel._meta.get_field("id")
        instance = _PlainModel()
        value = field.pre_save(instance, add=True)
        self.assertEqual(len(value), 16)
        self.assertEqual(instance.id, value)

    def test_pre_save_does_not_overwrite_existing_value(self):
        field = _PlainModel._meta.get_field("id")
        instance = _PlainModel(id="existing_1234567")
        value = field.pre_save(instance, add=True)
        self.assertEqual(value, "existing_1234567")

    def test_pre_save_noop_when_not_adding(self):
        field = _PlainModel._meta.get_field("id")
        instance = _PlainModel(id="existing_1234567")
        value = field.pre_save(instance, add=False)
        self.assertEqual(value, "existing_1234567")

    def test_prefix_is_prepended(self):
        field = _PrefixedModel._meta.get_field("id")
        instance = _PrefixedModel()
        value = field.pre_save(instance, add=True)
        self.assertTrue(value.startswith("org_"))
        self.assertEqual(len(value), 16)

    def test_field_attributes(self):
        field = _PlainModel._meta.get_field("id")
        self.assertEqual(field.max_length, 16)
        self.assertTrue(field.unique)
        self.assertFalse(field.editable)
