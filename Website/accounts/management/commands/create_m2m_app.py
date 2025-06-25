from django.core.management.base import BaseCommand
from django.conf import settings
from oauth2_provider.models import Application
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an OAuth2 application for machine-to-machine authentication'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Name of the OAuth application'
        )
        parser.add_argument(
            '--client-type',
            type=str,
            choices=['confidential', 'public'],
            default='confidential',
            help='Client type (confidential or public)'
        )
        parser.add_argument(
            '--authorization-grant-type',
            type=str,
            choices=['client-credentials', 'password', 'authorization-code'],
            default='client-credentials',
            help='Authorization grant type'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of the user who will own this application'
        )
        parser.add_argument(
            '--skip-authorization',
            action='store_true',
            help='Skip authorization step for this application'
        )

    def handle(self, *args, **options):
        name = options['name']
        client_type = options['client_type']
        authorization_grant_type = options['authorization_grant_type']
        username = options['user']
        skip_authorization = options['skip_authorization']

        # Get or create a user for the application
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" does not exist')
                )
                return
        else:
            # Create a system user for M2M applications
            user, created = User.objects.get_or_create(
                username='system',
                defaults={
                    'email': 'system@deploy-box.com',
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created system user for M2M applications')
                )

        # Create the OAuth application
        try:
            application = Application.objects.create(
                name=name,
                user=user,
                client_type=client_type,
                authorization_grant_type=authorization_grant_type,
                skip_authorization=skip_authorization,
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created OAuth application "{name}"'
                )
            )
            self.stdout.write(f'Client ID: {application.client_id}')
            self.stdout.write(f'Client Secret: {application.client_secret}')
            self.stdout.write(f'Client Type: {application.client_type}')
            self.stdout.write(f'Grant Type: {application.authorization_grant_type}')
            self.stdout.write(f'Skip Authorization: {application.skip_authorization}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create OAuth application: {str(e)}')
            ) 