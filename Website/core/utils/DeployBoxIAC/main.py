import json
import subprocess
import tempfile
import os
import shutil
from azure.storage.blob import BlobServiceClient

from core.utils.DeployBoxIAC.AzureDeployBoxIAC import AzureDeployBoxIAC
from core.utils.DeployBoxIAC.MongoDBAtlas import MongoDBAtlasDeployBoxIAC
from dotenv import load_dotenv
import shutil

load_dotenv()

class DeployBoxIAC:
    def __init__(self):
        self.azure_storage_connection_string = os.environ.get(
            "AZURE_STORAGE_CONNECTION_STRING"
        )
        self.container_name = os.environ.get("CONTAINER_NAME")

    def run_terraform_cmd(self, command, cwd):
        """Run terraform command and return result"""
        # exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_program.exe")
        result = subprocess.run(
            ["terraform"] + command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(f"\nterraform {' '.join(command)}")
        print("STDOUT:\n", result.stdout)
        if result.stderr:
            print("STDERR:\n", result.stderr)
        return result

    def upload_directory_to_blob(self, local_dir, blob_prefix="terraform"):
        """Upload directory contents to Azure Blob Storage"""
        assert self.azure_storage_connection_string is not None
        assert self.container_name is not None
        blob_service = BlobServiceClient.from_connection_string(
            self.azure_storage_connection_string
        )
        container_client = blob_service.get_container_client(self.container_name)

        # Ensure container exists
        try:
            container_client.create_container()
        except Exception:
            pass

        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_dir)
                blob_path = f"{blob_prefix}/{relative_path}".replace("\\", "/")
                print(f"Uploading: {local_path} -> {blob_path}")
                with open(local_path, "rb") as data:
                    container_client.upload_blob(blob_path, data, overwrite=True)

    def download_directory_from_blob(self, blob_prefix, local_dir):
        """Download directory contents from Azure Blob Storage"""
        assert self.azure_storage_connection_string is not None
        assert self.container_name is not None
        blob_service = BlobServiceClient.from_connection_string(
            self.azure_storage_connection_string
        )
        container_client = blob_service.get_container_client(self.container_name)

        blobs = container_client.list_blobs(name_starts_with=blob_prefix)
        for blob in blobs:
            blob_name = blob.name
            relative_path = os.path.relpath(blob_name, blob_prefix)
            local_path = os.path.join(local_dir, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            print(f"Downloading: {blob_name} -> {local_path}")
            with open(local_path, "wb") as file:
                blob_data = container_client.download_blob(blob_name)
                file.write(blob_data.readall())

    def deploy(self, resource_group_name, iac):
        """Main deployment logic - moved from main function"""
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Debugging temp dir: {temp_dir}")

            # Optionally download from Azure Blob (if restoring from prior state)
            self.download_directory_from_blob(resource_group_name, temp_dir)

            # Create state file if it does not exist
            state_file = os.path.join(temp_dir, "state.json")

            state = {}
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    state = json.load(f)

            tf_file = os.path.join(temp_dir, "main.tf.json")
            tf_plan_file = os.path.join(temp_dir, "plan.tfplan")

            # Generate TF JSON config
            azure_deploy_box_iac = AzureDeployBoxIAC()
            mongodb_atlas_deploy_box_iac = MongoDBAtlasDeployBoxIAC()

            terraform = azure_deploy_box_iac.plan({}, iac, state)
            terraform = mongodb_atlas_deploy_box_iac.plan(terraform, iac, state)

            if not terraform.get("resource"):
                del terraform["resource"]

            with open(tf_file, "w") as f:
                json.dump(terraform, f, indent=2)

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            print(f"Generated Terraform file: {json.dumps(terraform, indent=2)}")
            print(f"Generated state file: {json.dumps(state, indent=2)}")

            # Run Terraform commands
            self.run_terraform_cmd(["init"], temp_dir)
            self.run_terraform_cmd(["plan", f"--out={tf_plan_file}"], temp_dir)
            self.run_terraform_cmd(["apply", "-auto-approve", tf_plan_file], temp_dir)

            # Delete the tf_file file
            os.remove(tf_file)

            # Delete the tf_plan_file file
            os.remove(tf_plan_file)

            # Remove the .terraform directory
            shutil.rmtree(os.path.join(temp_dir, ".terraform"), ignore_errors=True)

            # Upload results (including .tfstate) to blob storage
            self.upload_directory_to_blob(temp_dir, blob_prefix=resource_group_name)

    def get_billing_info(self):
        """Update billing info"""

        azure_deploy_box_iac = AzureDeployBoxIAC()
        # mongodb_atlas_deploy_box_iac = MongoDBAtlasDeployBoxIAC()

        billing_info = {}
        billing_info = azure_deploy_box_iac.get_billing_info(billing_info)

        print(f"Billing info: {billing_info}")

        return billing_info



# Legacy function for backward compatibility
def main(resource_group_name, iac):
    """Legacy main function - now delegates to DeployBoxIAC class"""
    deploy_box = DeployBoxIAC()
    return deploy_box.deploy(resource_group_name, iac)
