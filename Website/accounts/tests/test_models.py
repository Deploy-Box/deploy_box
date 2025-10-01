from django.test import TestCase
from ..models import UserProfile
from django.contrib.auth import get_user_model

UserProfile = get_user_model()


class UserProfileTest(TestCase):
    def test_id_len_and_autofill(self):
        user = UserProfile.objects.create_user(username="kaleb", password="test")
        self.assertIsInstance(user.id, str)
        self.assertEqual(len(user.id), 22)
    
    def test_str(self):
        user = UserProfile.objects.create_user(username="jacob", password="test")
        self.assertEqual(str(user), "jacob")

    def test_related_names_exist(self):
        user = UserProfile.objects.create_user(username="hamza", password="test")
        groups_field = user._meta.get_field("groups")
        perms_field = user._meta.get_field("user_permissions")
        self.assertEqual(groups_field.remote_field.related_name, "userprofile_set")
        self.assertEqual(perms_field.remote_field.related_name, "userprofile_set")