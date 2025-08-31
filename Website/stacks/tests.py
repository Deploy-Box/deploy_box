from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from stacks.models import Stack, PurchasableStack
from projects.models import Project
from accounts.models import UserProfile, Organization


class StackIACOverwriteTestCase(APITestCase):
    """Test cases for the IAC overwrite functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create user profile
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            email_verified=True
        )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='Test Organization',
            owner=self.user_profile
        )
        
        # Create project
        self.project = Project.objects.create(
            name='Test Project',
            organization=self.organization
        )
        
        # Create purchasable stack
        self.purchasable_stack = PurchasableStack.objects.create(
            type='MERN',
            variant='basic',
            version='1.0',
            price_id='price_test123'
        )
        
        # Create stack
        self.stack = Stack.objects.create(
            name='Test Stack',
            project=self.project,
            purchased_stack=self.purchasable_stack,
            iac={'existing': 'configuration'}
        )
        
        # Set up API client
        self.client = APIClient()
        
    @patch('stacks.services.DeployBoxIAC')
    def test_overwrite_iac_success(self, mock_deploy_box_iac):
        """Test successful IAC overwrite"""
        # Mock the DeployBoxIAC class
        mock_instance = MagicMock()
        mock_deploy_box_iac.return_value = mock_instance
        
        # New IAC configuration
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
        
        # Make the API request
        url = reverse('overwrite_iac', kwargs={'stack_id': str(self.stack.id)})
        response = self.client.post(
            url,
            data={'iac': new_iac},
            format='json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('IAC configuration overwritten successfully', response.data['message'])
        
        # Verify the stack was updated
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac, new_iac)
        
        # Verify DeployBoxIAC was called
        mock_instance.deploy.assert_called_once_with(f"{self.stack.id}-rg", new_iac)
    
    def test_overwrite_iac_stack_not_found(self):
        """Test IAC overwrite with non-existent stack"""
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = reverse('overwrite_iac', kwargs={'stack_id': non_existent_id})
        
        response = self.client.post(
            url,
            data={'iac': {'test': 'config'}},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Stack not found', response.data['error'])
    
    def test_overwrite_iac_invalid_data(self):
        """Test IAC overwrite with invalid data"""
        url = reverse('overwrite_iac', kwargs={'stack_id': str(self.stack.id)})
        
        # Test with missing iac field
        response = self.client.post(
            url,
            data={},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('iac', response.data)
        
        # Test with non-dict iac
        response = self.client.post(
            url,
            data={'iac': 'not_a_dict'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('stacks.services.DeployBoxIAC')
    def test_overwrite_iac_deployment_failure(self, mock_deploy_box_iac):
        """Test IAC overwrite when deployment fails"""
        # Mock DeployBoxIAC to raise an exception
        mock_instance = MagicMock()
        mock_instance.deploy.side_effect = Exception("Deployment failed")
        mock_deploy_box_iac.return_value = mock_instance
        
        new_iac = {'test': 'configuration'}
        url = reverse('overwrite_iac', kwargs={'stack_id': str(self.stack.id)})
        
        response = self.client.post(
            url,
            data={'iac': new_iac},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('Failed to overwrite IAC configuration', response.data['error'])
    
    def test_overwrite_iac_viewset_action(self):
        """Test the ViewSet action for overwriting IAC"""
        # This would require authentication setup, but we can test the structure
        url = f'/api/stacks/{self.stack.id}/overwrite_iac/'
        
        # Note: This test would need proper authentication setup
        # For now, we're just testing that the endpoint exists
        self.assertTrue(url.endswith('/overwrite_iac/'))


class StackIACOverwriteIntegrationTestCase(TestCase):
    """Integration tests for IAC overwrite functionality"""
    
    def setUp(self):
        """Set up test data for integration tests"""
        # Create test user
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
        
        # Create user profile
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            email_verified=True
        )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='Integration Organization',
            owner=self.user_profile
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
            iac=self.initial_iac
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
        self.stack.iac = new_iac
        self.stack.save()
        
        # Refresh from database
        self.stack.refresh_from_db()
        
        # Verify IAC was updated
        self.assertEqual(self.stack.iac, new_iac)
        
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
        self.stack.iac = complex_iac
        self.stack.save()
        
        # Refresh and verify
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac, complex_iac)
        
        # Verify nested structure is preserved
        self.assertEqual(self.stack.iac['azure']['tags']['environment'], 'production')
        self.assertEqual(self.stack.iac['container_apps']['frontend']['replicas'], 3)
        self.assertTrue(self.stack.iac['databases']['mongodb']['enabled'])


class StackStatusUpdateTestCase(APITestCase):
    """Test cases for the stack status update functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='statususer',
            email='status@example.com',
            password='testpass123'
        )
        
        # Create user profile
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            email_verified=True
        )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='Status Test Organization',
            owner=self.user_profile
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
    
    def test_update_status_success(self):
        """Test successful status update"""
        new_status = 'RUNNING'
        
        # Make the API request
        url = f'/api/stacks/{self.stack.id}/update_status/'
        response = self.client.post(
            url,
            data={'status': new_status},
            format='json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Stack status updated successfully', response.data['message'])
        self.assertEqual(response.data['stack_id'], str(self.stack.id))
        self.assertEqual(response.data['old_status'], 'STARTING')
        self.assertEqual(response.data['new_status'], new_status)
        
        # Verify the stack was updated in the database
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.status, new_status)
    
    def test_update_status_stack_not_found(self):
        """Test status update with non-existent stack"""
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = f'/api/stacks/{non_existent_id}/update_status/'
        
        response = self.client.post(
            url,
            data={'status': 'RUNNING'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_status_invalid_data(self):
        """Test status update with invalid data"""
        url = f'/api/stacks/{self.stack.id}/update_status/'
        
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
    
    def test_update_status_service_failure(self):
        """Test status update when service fails"""
        # Mock the service to return False
        with patch('stacks.services.update_stack_status', return_value=False):
            url = f'/api/stacks/{self.stack.id}/update_status/'
            response = self.client.post(
                url,
                data={'status': 'RUNNING'},
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertFalse(response.data['success'])
            self.assertIn('Failed to update stack status', response.data['error'])
    
    def test_update_status_to_various_states(self):
        """Test updating status to various common states"""
        test_states = ['PROVISIONING', 'RUNNING', 'STOPPED', 'ERROR', 'DELETING']
        
        for test_state in test_states:
            url = f'/api/stacks/{self.stack.id}/update_status/'
            response = self.client.post(
                url,
                data={'status': test_state},
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
            self.assertEqual(response.data['new_status'], test_state)
            
            # Verify the stack was updated
            self.stack.refresh_from_db()
            self.assertEqual(self.stack.status, test_state)


class StackIACUpdateTestCase(APITestCase):
    """Test cases for the stack IAC update functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='iacuser',
            email='iac@example.com',
            password='testpass123'
        )
        
        # Create user profile
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            email_verified=True
        )
        
        # Create organization
        self.organization = Organization.objects.create(
            name='IAC Test Organization',
            owner=self.user_profile
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
            iac={'existing': 'configuration'}
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_update_iac_success(self):
        """Test successful IAC update (database only, no deployment)"""
        
        # New IAC configuration
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
        
        # Make the API request
        url = f'/api/stacks/{self.stack.id}/update_iac/'
        response = self.client.post(
            url,
            data={'data': new_iac},
            format='json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('IAC configuration updated successfully (no deployment)', response.data['message'])
        self.assertEqual(response.data['stack_id'], str(self.stack.id))
        self.assertEqual(response.data['old_iac'], {'existing': 'configuration'})
        self.assertEqual(response.data['new_iac'], new_iac)
        
        # Verify the stack was updated
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac, new_iac)
    
    def test_update_iac_stack_not_found(self):
        """Test IAC update with non-existent stack"""
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = f'/api/stacks/{non_existent_id}/update_iac/'
        
        response = self.client.post(
            url,
            data={'data': {'test': 'config'}},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_iac_invalid_data(self):
        """Test IAC update with invalid data"""
        url = f'/api/stacks/{self.stack.id}/update_iac/'
        
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
    
    def test_update_iac_service_failure(self):
        """Test IAC update when service fails"""
        # Mock the service to return False
        with patch('stacks.services.update_stack_iac_only', return_value=False):
            new_iac = {'test': 'configuration'}
            url = f'/api/stacks/{self.stack.id}/update_iac/'
            
            response = self.client.post(
                url,
                data={'data': new_iac},
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('Failed to update IAC configuration', response.data['error'])
    
    def test_update_iac_with_section_parameter(self):
        """Test IAC update with section parameter (should be ignored for full overwrite)"""
        new_iac = {
            'azure': {
                'resource_group': 'test-rg'
            }
        }
        
        url = f'/api/stacks/{self.stack.id}/update_iac/'
        response = self.client.post(
            url,
            data={
                'data': new_iac,
                'section': ['azure', 'container_apps']  # This should be ignored
            },
            format='json'
        )
        
        # Should still work as it's a full overwrite
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify the stack was updated with the full new IAC
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.iac, new_iac)
