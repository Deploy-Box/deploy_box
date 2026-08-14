from django.test import SimpleTestCase
from django.urls import reverse


class DeveloperTemplateTests(SimpleTestCase):
    def test_home_renders(self):
        response = self.client.get(reverse("developer:home"))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content.decode()), 0)
        self.assertContains(response, "Find developers, build trust, ship faster.")

    def test_detail_renders_username(self):
        response = self.client.get(reverse("developer:detail", kwargs={"username": "alice"}))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content.decode()), 0)
        self.assertContains(response, "@alice")

    def test_showcase_renders_username(self):
        response = self.client.get(reverse("developer:showcase", kwargs={"username": "alice"}))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content.decode()), 0)
        self.assertContains(response, "@alice's work")

    def test_kaleb_showcase_renders_featured_projects(self):
        response = self.client.get(reverse("developer:showcase", kwargs={"username": "kalebwbishop"}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="navbar"')
        self.assertContains(response, "@kalebwbishop's work")
        self.assertContains(response, '/media/dental.png')
        self.assertContains(response, "finishingtouchdentallab.z13.web.core.windows.net")
        self.assertContains(response, "heitmeyerconcrete.z13.web.core.windows.net")
        self.assertContains(response, "johnbreitigamhomeimpro.z13.web.core.windows.net")
        self.assertContains(response, "powellmemorialprod.z20.web.core.windows.net")
        self.assertContains(response, "deploy-box.com")
        self.assertContains(response, "Image placeholder", count=4)
