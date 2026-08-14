"""
Management command: create an e2e test user + Django session.

Outputs the session key so Playwright can inject it as a cookie.
Usage:
    python manage.py setup_e2e
    python manage.py setup_e2e --create-org   # also creates an org + project
"""

from django.core.management.base import BaseCommand
from django.contrib.sessions.backends.db import SessionStore

from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Create an e2e test user and print a valid session cookie value."

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-org",
            action="store_true",
            help="Also create a test organization, project, and purchasable stacks.",
        )

    def handle(self, *args, **options):
        user, created = UserProfile.objects.get_or_create(
            username="e2e_test_user",
            defaults={
                "email": "e2e@test.deploy-box.com",
                "workos_user_id": "workos_e2e_dummy_id",
                "auth_provider": "workos",
            },
        )
        if created:
            self.stderr.write(self.style.SUCCESS("Created e2e test user"))
        else:
            self.stderr.write("e2e test user already exists")

        if options["create_org"]:
            self._create_org_and_project(user)

        # Build a session that WorkOSSessionMiddleware will recognise
        session = SessionStore()
        session["_workos_user_id"] = str(user.pk)
        session.create()

        # Print the session key with a unique marker so it can be extracted
        # even if Django prints other things to stdout (e.g. "HOST set to ...")
        self.stdout.write(f"E2E_SESSION_KEY={session.session_key}")

    def _create_org_and_project(self, user):
        from organizations.models import Organization, OrganizationMember
        from projects.models import Project, ProjectMember

        org, org_created = Organization.objects.get_or_create(
            name="E2E Test Org",
            defaults={"email": "e2e-org@test.deploy-box.com"},
        )
        if org_created:
            self.stderr.write(self.style.SUCCESS("Created e2e test organization"))

        OrganizationMember.objects.get_or_create(
            user=user,
            organization=org,
            defaults={"role": "admin"},
        )

        project, proj_created = Project.objects.get_or_create(
            name="E2E Test Project",
            defaults={
                "organization": org,
                "description": "Project for e2e testing",
            },
        )
        if proj_created:
            self.stderr.write(self.style.SUCCESS("Created e2e test project"))

        ProjectMember.objects.get_or_create(
            user=user,
            project=project,
            defaults={"role": "admin"},
        )

        # Print org and project IDs to stderr for debugging
        self.stderr.write(f"org_id={org.id}  project_id={project.id}")
