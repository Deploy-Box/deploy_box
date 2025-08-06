from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from stacks.models import Stack, PurchasableStack
from projects.models import Project
from organizations.models import Organization, OrganizationMember
from accounts.models import UserProfile

User = UserProfile


class Command(BaseCommand):
    help = 'Create three test stacks for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testuser',
            help='Username for the test user (default: testuser)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='test@example.com',
            help='Email for the test user (default: test@example.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='testpass123',
            help='Password for the test user (default: testpass123)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        # Create or get test user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_active': True,
            }
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created test user: {username}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Test user already exists: {username}')
            )

        # UserProfile is the user model itself, so we don't need to create a separate profile
        user_profile = user

        # Create or get test organization
        org, created = Organization.objects.get_or_create(
            name='Test Organization',
            defaults={
                'email': email,
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created test organization: Test Organization')
            )

        # Add user to organization
        org_member, created = OrganizationMember.objects.get_or_create(
            organization=org,
            user=user_profile,
            defaults={
                'role': 'admin',
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Added {username} to Test Organization as admin')
            )

        # Create or get test project
        project, created = Project.objects.get_or_create(
            name='Test Project',
            organization=org,
            defaults={
                'description': 'A test project for creating stacks',
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created test project: Test Project')
            )

        # Create purchasable stacks if they don't exist
        purchasable_stacks_data = [
            {
                'type': 'MERN',
                'variant': 'BASIC',
                'version': '1.0',
                'price_id': 'price_mern_basic',
                'description': 'MERN Stack Basic Plan - MongoDB, Express, React, Node.js',
                'name': 'MERN Stack Basic',
            },
            {
                'type': 'MERN',
                'variant': 'PREMIUM',
                'version': '1.0',
                'price_id': 'price_mern_premium',
                'description': 'MERN Stack Premium Plan - MongoDB, Express, React, Node.js',
                'name': 'MERN Stack Premium',
            },
            {
                'type': 'DJANGO',
                'variant': 'BASIC',
                'version': '1.0',
                'price_id': 'price_django_basic',
                'description': 'Django Stack Basic Plan - Django, PostgreSQL',
                'name': 'Django Stack Basic',
            },
        ]

        purchasable_stacks = []
        for stack_data in purchasable_stacks_data:
            purchasable_stack, created = PurchasableStack.objects.get_or_create(
                type=stack_data['type'],
                variant=stack_data['variant'],
                version=stack_data['version'],
                defaults=stack_data
            )
            purchasable_stacks.append(purchasable_stack)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created purchasable stack: {stack_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Purchasable stack already exists: {stack_data["name"]}')
                )

        # Create three test stacks
        test_stacks_data = [
            {
                'name': 'Test MERN Basic Stack',
                'purchasable_stack': purchasable_stacks[0],
                'status': 'STARTING',
            },
            {
                'name': 'Test MERN Premium Stack',
                'purchasable_stack': purchasable_stacks[1],
                'status': 'RUNNING',
            },
            {
                'name': 'Test Django Basic Stack',
                'purchasable_stack': purchasable_stacks[2],
                'status': 'STOPPED',
            },
        ]

        created_stacks = []
        for stack_data in test_stacks_data:
            stack, created = Stack.objects.get_or_create(
                name=stack_data['name'],
                project=project,
                defaults={
                    'purchased_stack': stack_data['purchasable_stack'],
                    'status': stack_data['status'],
                    'root_directory': '/app',
                    'instance_usage': 0.0,
                    'instance_usage_bill_amount': 0.0,
                    'iac': {
                        'project_id': 'test-project-123',
                        'region': 'us-central1',
                        'environment': 'test',
                    },
                    'stack_information': {
                        'frontend_url': 'https://test-frontend.example.com',
                        'backend_url': 'https://test-backend.example.com',
                        'database_uri': 'mongodb://test-db.example.com:27017',
                    },
                }
            )
            created_stacks.append(stack)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created test stack: {stack_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Test stack already exists: {stack_data["name"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {len(created_stacks)} test stacks:\n'
                f'- User: {username}\n'
                f'- Organization: Test Organization\n'
                f'- Project: Test Project\n'
                f'- Stacks: {", ".join([stack.name for stack in created_stacks])}'
            )
        ) 