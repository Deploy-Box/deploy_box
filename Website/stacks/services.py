import logging
import json
import requests
from django.http import JsonResponse
from django.db import transaction
from stacks.models import (
    Stack,
    PurchasableStack,
)
from django.conf import settings
from projects.models import Project
from accounts.models import UserProfile
import os
from django.views.decorators.csrf import csrf_exempt
from .service_helpers import ServiceHelper

logger = logging.getLogger(__name__)

def send_to_azure_function(message_data: dict, function_url: str | None = None) -> bool:
    """
    Sends a message to Azure Function via HTTP trigger.
    
    Args:
        message_data (dict): The data to send as a message
        function_url (str): The URL of the Azure Function HTTP trigger
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    function_url = function_url or os.environ.get('AZURE_FUNCTION_URL')

    if not function_url:
        logger.error("Azure Function URL is not configured.")
        return False

    try:
        # Send HTTP POST request to Azure Function
        response = requests.post(
            function_url,
            json=message_data,
            headers={'Content-Type': 'application/json'},
            timeout=30  # 30 second timeout
        )
        
        # Check if the request was successful
        if response.status_code in [200, 202]:
            logger.info(f"Successfully sent message to Azure Function: {function_url}")
            return True
        else:
            logger.error(f"Azure Function returned status code {response.status_code}: {response.text}")
            return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to Azure Function: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message to Azure Function: {str(e)}")
        return False
    

def add_stack(**kwargs) -> Stack:
    name = kwargs.get("name")
    project_id = kwargs.get("project_id")
    purchasable_stack_id = kwargs.get("purchasable_stack_id")

    project = Project.objects.get(pk=project_id)
    purchasable_stack = PurchasableStack.objects.get(pk=purchasable_stack_id)

    with transaction.atomic():

        print(f"Variant: {purchasable_stack.variant}")

        stack = Stack.objects.create(
            name=name, project=project, purchased_stack=purchasable_stack, status="PROVISIONING"
        )

        

        # Put request on Azure Service Bus
        message_data = {
            "request_type": "iac.create",
            "source": os.environ.get("HOST"),          
            "data": {
                "stack_id": str(stack.id),
                "project_id": str(project.id),
                "org_id": str(project.organization.id),
                "purchasable_stack_type": purchasable_stack.type.upper(),
                "purchasable_stack_variant": purchasable_stack.variant.upper(),
                "purchasable_stack_version": purchasable_stack.version,
            }
        }

        # Send message to Azure Function (non-blocking)
        try:
            send_to_azure_function(message_data)
        except Exception as e:
            logger.warning(f"Failed to send message to Azure Function: {str(e)}")

    return stack

# project = Project.objects.all()[0]
# purchasable_stack = PurchasableStack.objects.all()[0]
# add_stack(name="test", project_id=project.id, purchasable_stack_id=purchasable_stack.id)


def update_stack(**kwargs) -> Stack:
    stack_id = kwargs.get("stack_id")
    stack_iac = kwargs.get("stack_iac", {})
    source_code_path = kwargs.get("source_code_path", "")


    with transaction.atomic():

        stack = Stack.objects.get(pk=stack_id)

        if not stack_iac:
            stack_iac = stack.iac

        # Put request on Azure Service Bus
        message_data = {
            "request_type": "iac.update",
            "source": os.environ.get("HOST"),
            "data": {
                "stack_id": str(stack.id),
                "source_code_path": str(source_code_path),
                "iac": stack_iac,
            }
        }

        # Send message to Azure Function (non-blocking)
        try:
            send_to_azure_function(message_data)
        except Exception as e:
            logger.warning(f"Failed to send message to Azure Function: {str(e)}")

    return stack


def get_stacks(user: UserProfile) -> list[Stack]:
    projects = Project.objects.filter(projectmember__user=user)

    return list(Stack.objects.filter(project__in=projects).order_by("-created_at"))


def post_purchasable_stack(
    type: str, variant: str, version: str, price_id: str
) -> JsonResponse:
    try:
        with transaction.atomic():
            PurchasableStack.objects.create(
                type=type, variant=variant, version=version, price_id=price_id
            )
            return JsonResponse(
                {"message": "Purchasable stack created successfully."}, status=201
            )
    except Exception as e:
        logger.error(f"Failed to create purchasable stack: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to create purchasable stack: {str(e)}"}, status=500
        )


def update_stack_iac_state_only(stack: Stack, new_iac_state: dict) -> bool:
    """
    Updates only the IAC state field in the database without triggering cloud deployment.

    Args:
        stack (Stack): The stack object to update.
        new_iac_state (dict): The complete new IAC state configuration to replace the existing one.

    Returns:
        bool: True if the IAC state was updated successfully, False otherwise.
    """
    try:
        logger.info(f"Updating IAC state field only for stack {stack.id}")
        
        # Store the old IAC state for logging purposes
        old_iac_state = stack.iac_state
        logger.info(f"Old IAC state configuration: {old_iac_state}")
        logger.info(f"New IAC state configuration: {new_iac_state}")
        
        # Validate that the new IAC state is a valid dictionary
        if not isinstance(new_iac_state, dict):
            logger.error(f"Invalid IAC state configuration type for stack {stack.id}: {type(new_iac_state)}")
            return False
        
        # Overwrite the IAC state configuration in the database only
        stack.iac_state = new_iac_state
        stack.save()
        
        logger.info(f"Successfully updated IAC state field for stack {stack.id} (no deployment)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update IAC state field for stack {stack.id}: {str(e)}")
        return False


# TODO: show loading indicator
def post_stack_env(
    stack_id: str, selected_frameworks, selected_locations, env_dict
):
    """
    Sets environment variables as secrets and environment variables
    in the corresponding Azure Container App using AzureDeployBoxIAC.
    """
    # Determine resource group and app name
    if selected_locations == "none":
        app_name = f"{selected_frameworks}-{stack_id}"
    else:
        app_name = f"{selected_frameworks}-{selected_locations}-{stack_id}"

    resource_group_name = stack_id + "-rg"  # Or derive dynamically if needed

    stack = Stack.objects.get(id=stack_id)
    if not stack:
        return JsonResponse(
            {"status": "error", "message": "Stack not found."}, status=404
        )

    iac = stack.iac
    # Add secrets and environment variables to the Azure Container App
    cloud = AzureDeployBoxIAC()
    result = cloud.add_container_app_envs_as_secrets(
        iac, app_name, env_dict, "testing-mern"
    )

    if result is None:
        return JsonResponse(
            {"status": "error", "message": "Failed to update secrets."}, status=500
        )

    # Update the stack with the new IAC
    stack.iac = iac

    main(resource_group_name, iac)

    stack.save()

    return JsonResponse({"status": "success"})

@csrf_exempt
def update_stack_databases_usages(data) -> bool:
    """
    Updates the usage of multiple stack databases.

    Args:
        data (dict): Dictionary containing the data with stack database updates

    Returns:
        bool: True if all updates were successful
    """

    try:
        data = json.loads(data)
        print("Data: ", data)
        for stack_id, usage in data.items():
            stack_id = stack_id.strip('-rg')  # Remove '-rg' suffix if present
            try:
                stack_database = Stack.objects.get(pk=stack_id)
                stack_database.instance_usage = usage
                stack_database.save()
            except Stack.DoesNotExist:
                logger.error(f"Stack with ID {stack_id} does not exist.")
                continue
        return True
    except Exception as e:
        logger.error(f"Failed to update stack databases usages: {str(e)}")
        return False
    
def update_stack_information(stack_id: str, stack_information: dict) -> JsonResponse:
    """
    Updates the stack information for a given stack.
    """
    try:
        print(f"Updating stack information for stack: {stack_id}")
        print(f"Stack information: {stack_information}")
        stack = Stack.objects.get(pk=stack_id)
        stack.stack_information = stack_information
        stack.save()
        return JsonResponse({
            "success": True,
            "message": "Stack information updated successfully.",
            "stack_id": stack_id
        }, status=200)
    except Stack.DoesNotExist:
        logger.error(f"Stack with ID {stack_id} does not exist.")
        return JsonResponse({"error": "Stack not found."}, status=404)
    except Exception as e:
        logger.error(f"Failed to update stack information: {str(e)}")
        return JsonResponse({"error": f"Failed to update stack information. {str(e)}"}, status=500)

def update_iac(stack_id: str, new_iac: dict) -> JsonResponse:
    """
    Completely overwrites the IAC configuration for a given stack.

    Args:
        stack_id (str): The ID of the stack to update.
        new_iac (dict): The complete new IAC configuration to replace the existing one.

    Returns:
        JsonResponse: Success or error response.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
        logger.info(f"Overwriting IAC for stack: {stack_id}")
        
        # Store the old IAC for logging purposes
        old_iac = stack.iac
        logger.info(f"Old IAC configuration: {old_iac}")
        logger.info(f"New IAC configuration: {new_iac}")
        
        # Validate that the new IAC is a valid dictionary
        if not isinstance(new_iac, dict):
            return JsonResponse({"error": "IAC configuration must be a valid JSON object."}, status=400)
        
        # Overwrite the IAC configuration
        stack.iac = new_iac
        stack.save()
        
        # Deploy the new IAC configuration
        resource_group_name = f"{stack_id}-rg"
        cloud = DeployBoxIAC()
        cloud.deploy(resource_group_name, new_iac)
        
        logger.info(f"Successfully overwrote IAC for stack: {stack_id}")
        return JsonResponse({
            "success": True, 
            "message": "IAC configuration overwritten successfully.",
            "stack_id": stack_id,
            "old_iac": old_iac,
            "new_iac": new_iac
        }, status=200)

    except Stack.DoesNotExist:
        logger.error(f"Stack with ID {stack_id} does not exist.")
        return JsonResponse({"error": "Stack not found."}, status=404)
    except Exception as e:
        logger.error(f"Failed to overwrite IAC for stack {stack_id}: {str(e)}")
        return JsonResponse({"error": f"Failed to overwrite IAC configuration. {str(e)}"}, status=500)


def update_stack_status(stack: Stack, new_status: str) -> bool:
    """
    Updates the status of a given stack.

    Args:
        stack (Stack): The stack object to update.
        new_status (str): The new status to set.

    Returns:
        bool: True if the status was updated successfully, False otherwise.
    """
    try:
        logger.info(f"Updating status for stack {stack.id} from '{stack.status}' to '{new_status}'")
        
        # Update the stack status
        stack.status = new_status

        if new_status == "DELETED":
            stack.delete()

        else:
            stack.save()
        
        logger.info(f"Successfully updated status for stack {stack.id} to '{new_status}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update status for stack {stack.id}: {str(e)}")
        return False


def update_stack_iac(stack: Stack, data: dict, section: list[str]) -> bool:
    """
    Updates the IAC for a given stack based on the provided data.

    Args:
        stack (Stack): The stack object to update.
        data (dict): The new IAC data to apply.
        section (list[str]): The top-level sections of the IAC to target.

    Returns:
        bool: True if the IAC was updated successfully, False otherwise.
    """
    try:
        logger.info(f"Updating IAC for stack {stack.id}")
        logger.info(f"Stack info: {stack.stack_information}")
        
        old_iac = stack.iac
        logger.info(f"Old IAC: {old_iac}")

        for item in section:
            iac_section = ServiceHelper().find_nested_value(old_iac, item)
            logger.info(f"Processing section: {item}")
            logger.info(f"Section content: {iac_section}")
            
            for key, value in data.items():
                try:
                    ServiceHelper().update_nested_value(iac_section, key, value)
                    if key in stack.stack_information:
                        stack.stack_information[key] = value
                    else:
                        continue
                except Exception as e:
                    logger.warning(f"Failed to update nested value {key}: {str(e)}")
                    continue

            # Reassign back just in case it's not by reference
            ServiceHelper().update_nested_value(old_iac, item, iac_section)

        stack.iac = old_iac
        stack.save()

        # Deploy the updated IAC
        resource_group_name = f"{stack.id}-rg"
        cloud = DeployBoxIAC()
        cloud.deploy(resource_group_name, old_iac)
        
        logger.info(f"Successfully updated IAC for stack {stack.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update IAC for stack {stack.id}: {str(e)}")
        return False


def update_stack_iac_only(stack: Stack, new_iac: dict) -> bool:
    """
    Updates only the IAC field in the database without triggering cloud deployment.

    Args:
        stack (Stack): The stack object to update.
        new_iac (dict): The complete new IAC configuration to replace the existing one.

    Returns:
        bool: True if the IAC was updated successfully, False otherwise.
    """
    try:
        logger.info(f"Updating IAC field only for stack {stack.id}")
        
        # Store the old IAC for logging purposes
        old_iac = stack.iac
        logger.info(f"Old IAC configuration: {old_iac}")
        logger.info(f"New IAC configuration: {new_iac}")
        
        # Validate that the new IAC is a valid dictionary
        if not isinstance(new_iac, dict):
            logger.error(f"Invalid IAC configuration type for stack {stack.id}: {type(new_iac)}")
            return False
        
        # Overwrite the IAC configuration in the database only
        stack.iac = new_iac
        stack.save()
        
        logger.info(f"Successfully updated IAC field for stack {stack.id} (no deployment)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update IAC field for stack {stack.id}: {str(e)}")
        return False



def delete_stack(stack: Stack) -> bool:
    """
    Deletes a given stack.
    """
    print(f"Deleting stack {stack.id}")
    try:
        stack.status = "DELETING"
        stack.save()
        send_to_azure_function(
            {
                "request_type": "iac.delete",
                "source": os.environ.get("HOST"),
                "data": {
                    "stack_id": stack.id,
                    "iac": stack.iac
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to delete stack {stack.id}: {str(e)}")
        return False