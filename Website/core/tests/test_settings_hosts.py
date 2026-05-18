import os
from unittest.mock import patch

from django.test import SimpleTestCase

from core.settings.base import _append_env_host


class AppendEnvHostTest(SimpleTestCase):
    def test_appends_app_service_hostname_from_environment(self):
        allowed_hosts = ["deploy-box.com"]

        with patch.dict(os.environ, {"WEBSITE_HOSTNAME": "deploy-box-dev.azurewebsites.net"}):
            _append_env_host(allowed_hosts, "WEBSITE_HOSTNAME")

        self.assertIn("deploy-box-dev.azurewebsites.net", allowed_hosts)

    def test_does_not_duplicate_existing_hostname(self):
        allowed_hosts = ["deploy-box-dev.azurewebsites.net"]

        with patch.dict(os.environ, {"WEBSITE_HOSTNAME": "deploy-box-dev.azurewebsites.net"}):
            _append_env_host(allowed_hosts, "WEBSITE_HOSTNAME")

        self.assertEqual(allowed_hosts, ["deploy-box-dev.azurewebsites.net"])
