from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from stacks.models import Stack, PurchasableStack
from projects.models import Project
from organizations.models import Organization
from django.contrib.auth import get_user_model

UserProfile = get_user_model()


class StackIACOverwriteIntegrationTestCase(TestCase):
    """Integration tests for IAC model-level operations"""
    
    def setUp(self):
        """Set up test data for integration tests"""
        # Create test user
        self.user_profile = UserProfile.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
        
        # # Create user profile
        # self.user_profile = UserProfile.objects.create(
        #     user=self.user,
        #     email_verified=True
        # )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='Integration Organization',
        )
        
        # Create project
        self.project = Project.objects.create(
            name='Integration Project',
            organization=self.organization
        )
        
        # Create purchasable stack
        self.purchasable_stack = PurchasableStack.objects.create(
            type='DJANGO',
            variant='premium',
            version='2.0',
            price_id='price_integration123'
        )
        
        # Create stack with initial IAC
        self.initial_iac = {
            'azure': {
                'resource_group': 'initial-rg',
                'location': 'westus'
            }
        }
        
        self.stack = Stack.objects.create(
            name='Integration Stack',
            project=self.project,
            purchased_stack=self.purchasable_stack,
            iac_state=self.initial_iac
        )
    
    def test_iac_overwrite_preserves_other_fields(self):
        """Test that overwriting IAC doesn't affect other stack fields"""
        new_iac = {
            'azure': {
                'resource_group': 'new-rg',
                'location': 'eastus'
            },
            'new_service': {
                'enabled': True
            }
        }
        
        # Store original values
        original_name = self.stack.name
        original_project = self.stack.project
        original_purchased_stack = self.stack.purchased_stack
        original_created_at = self.stack.created_at
        
        # Overwrite IAC
        self.stack.iac_state = new_iac
        self.stack.save()
        
        # Refresh from database
        self.stack.refresh_from_db()
        
        # Verify IAC was updated
        self.assertEqual(self.stack.iac_state, new_iac)
        
        # Verify other fields remain unchanged
        self.assertEqual(self.stack.name, original_name)
        self.assertEqual(self.stack.project, original_project)
        self.assertEqual(self.stack.purchased_stack, original_purchased_stack)
        self.assertEqual(self.stack.created_at, original_created_at)
    
    def test_iac_overwrite_with_complex_configuration(self):
        """Test overwriting IAC with a complex configuration"""
        complex_iac = {
            'azure': {
                'resource_group': 'complex-rg',
                'location': 'centralus',
                'tags': {
                    'environment': 'production',
                    'project': 'test-project'
                }
            },
            'container_apps': {
                'frontend': {
                    'name': 'frontend-app',
                    'image': 'nginx:alpine',
                    'replicas': 3,
                    'resources': {
                        'cpu': '0.5',
                        'memory': '1Gi'
                    }
                },
                'backend': {
                    'name': 'backend-app',
                    'image': 'node:18-alpine',
                    'replicas': 2,
                    'resources': {
                        'cpu': '1.0',
                        'memory': '2Gi'
                    },
                    'environment_variables': {
                        'NODE_ENV': 'production',
                        'PORT': '3000'
                    }
                }
            },
            'databases': {
                'mongodb': {
                    'enabled': True,
                    'version': '6.0',
                    'storage_gb': 10
                },
                'redis': {
                    'enabled': True,
                    'version': '7.0',
                    'memory_mb': 512
                }
            }
        }
        
        # Overwrite IAC
        self.stack.iac_state = complex_iac
        self.stack.save()
        
        # Refresh and verify
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac_state, complex_iac)
        
        # Verify nested structure is preserved
        self.assertEqual(self.stack.iac_state['azure']['tags']['environment'], 'production')
        self.assertEqual(self.stack.iac_state['container_apps']['frontend']['replicas'], 3)
        self.assertTrue(self.stack.iac_state['databases']['mongodb']['enabled'])


@patch('stacks.views.verify_iac_webhook_signature')
class StackStatusUpdateTestCase(APITestCase):
    """Test cases for the stack status update functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user_profile = UserProfile.objects.create_user(
            username='statususer',
            email='status@example.com',
            password='testpass123'
        )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='Status Test Organization',
        )
        
        # Create project
        self.project = Project.objects.create(
            name='Status Test Project',
            organization=self.organization
        )
        
        # Create purchasable stack
        self.purchasable_stack = PurchasableStack.objects.create(
            type='MERN',
            variant='basic',
            version='1.0',
            price_id='price_status123'
        )
        
        # Create stack with initial status
        self.stack = Stack.objects.create(
            name='Status Test Stack',
            project=self.project,
            purchased_stack=self.purchasable_stack,
            status='STARTING'
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_update_status_success(self, mock_verify):
        """Test successful status update"""
        new_status = 'RUNNING'
        
        url = f'/api/v1/stacks/{self.stack.id}/update_status/'
        response = self.client.post(
            url,
            data={'status': new_status},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Stack status updated successfully', response.data['message'])
        self.assertEqual(response.data['stack_id'], str(self.stack.id))
        self.assertEqual(response.data['old_status'], 'STARTING')
        self.assertEqual(response.data['new_status'], new_status)
        
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.status, new_status)
    
    def test_update_status_stack_not_found(self, mock_verify):
        """Test status update with non-existent stack"""
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = f'/api/v1/stacks/{non_existent_id}/update_status/'
        
        response = self.client.post(
            url,
            data={'status': 'RUNNING'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_status_invalid_data(self, mock_verify):
        """Test status update with invalid data"""
        url = f'/api/v1/stacks/{self.stack.id}/update_status/'
        
        # Test with missing status field
        response = self.client.post(
            url,
            data={},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        
        # Test with empty status
        response = self.client.post(
            url,
            data={'status': ''},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status is required', response.data['error'])
    
    def test_update_status_service_failure(self, mock_verify):
        """Test status update when service fails"""
        with patch('stacks.services.update_stack_status', return_value=False):
            url = f'/api/v1/stacks/{self.stack.id}/update_status/'
            response = self.client.post(
                url,
                data={'status': 'RUNNING'},
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertFalse(response.data['success'])
            self.assertIn('Failed to update stack status', response.data['error'])
    
    def test_update_status_to_various_states(self, mock_verify):
        """Test updating status to various common states"""
        test_states = ['PROVISIONING', 'RUNNING', 'STOPPED', 'ERROR', 'DELETING']
        
        for test_state in test_states:
            url = f'/api/v1/stacks/{self.stack.id}/update_status/'
            response = self.client.post(
                url,
                data={'status': test_state},
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
            self.assertEqual(response.data['new_status'], test_state)
            
            self.stack.refresh_from_db()
            self.assertEqual(self.stack.status, test_state)


@patch('stacks.views.verify_iac_webhook_signature')
class StackIACUpdateTestCase(APITestCase):
    """Test cases for the stack IAC update functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user_profile = UserProfile.objects.create_user(
            username='iacuser',
            email='iac@example.com',
            password='testpass123'
        )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='IAC Test Organization',
        )
        
        # Create project
        self.project = Project.objects.create(
            name='IAC Test Project',
            organization=self.organization
        )
        
        # Create purchasable stack
        self.purchasable_stack = PurchasableStack.objects.create(
            type='MERN',
            variant='basic',
            version='1.0',
            price_id='price_iac123'
        )
        
        # Create stack with initial IAC
        self.stack = Stack.objects.create(
            name='IAC Test Stack',
            project=self.project,
            purchased_stack=self.purchasable_stack,
            iac_state={'existing': 'configuration'}
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_update_iac_success(self, mock_verify):
        """Test successful IAC update (database only, no deployment)"""
        
        new_iac = {
            'azure': {
                'resource_group': 'test-rg',
                'location': 'eastus'
            },
            'container_apps': {
                'frontend': {
                    'name': 'frontend-app',
                    'image': 'nginx:latest'
                },
                'backend': {
                    'name': 'backend-app',
                    'image': 'node:16'
                }
            }
        }
        
        url = f'/api/v1/stacks/{self.stack.id}/update_iac/'
        response = self.client.post(
            url,
            data={'data': new_iac},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('IAC configuration updated successfully (no deployment)', response.data['message'])
        self.assertEqual(response.data['stack_id'], str(self.stack.id))
        self.assertEqual(response.data['old_iac'], {'existing': 'configuration'})
        self.assertEqual(response.data['new_iac'], new_iac)
        
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac_state, new_iac)
    
    def test_update_iac_stack_not_found(self, mock_verify):
        """Test IAC update with non-existent stack"""
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = f'/api/v1/stacks/{non_existent_id}/update_iac/'
        
        response = self.client.post(
            url,
            data={'data': {'test': 'config'}},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_iac_invalid_data(self, mock_verify):
        """Test IAC update with invalid data"""
        url = f'/api/v1/stacks/{self.stack.id}/update_iac/'
        
        # Test with missing data field
        response = self.client.post(
            url,
            data={},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data', response.data)
        
        # Test with empty data
        response = self.client.post(
            url,
            data={'data': {}},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('IAC configuration is required', response.data['error'])
        
        # Test with non-dict data
        response = self.client.post(
            url,
            data={'data': 'not_a_dict'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('IAC configuration must be a valid JSON object', response.data['error'])
    
    def test_update_iac_service_failure(self, mock_verify):
        """Test IAC update when service fails"""
        with patch('stacks.services.update_stack_iac_only', return_value=False):
            new_iac = {'test': 'configuration'}
            url = f'/api/v1/stacks/{self.stack.id}/update_iac/'
            
            response = self.client.post(
                url,
                data={'data': new_iac},
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('Failed to update IAC configuration', response.data['error'])
    
    def test_update_iac_with_section_parameter(self, mock_verify):
        """Test IAC update with section parameter (should be ignored for full overwrite)"""
        new_iac = {
            'azure': {
                'resource_group': 'test-rg'
            }
        }
        
        url = f'/api/v1/stacks/{self.stack.id}/update_iac/'
        response = self.client.post(
            url,
            data={
                'data': new_iac,
                'section': ['azure', 'container_apps']  # This should be ignored
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac_state, new_iac)
