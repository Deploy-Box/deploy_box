from google.cloud import run_v2, artifactregistry_v1
from google.iam.v1 import policy_pb2
from google.iam.v1 import iam_policy_pb2
from google.protobuf.duration_pb2 import Duration
from google.cloud import storage
from google.oauth2 import service_account
from google.cloud import iam_admin_v1
import os
import time
from django.conf import settings
from google.cloud import monitoring_v3

# Set paths and credentials
current_working_dir = os.getcwd()
GCP_KEY_PATH = settings.GCP.get("KEY_PATH")
PROJECT_ID = "deploy-box"
REGION = "us-central1"
name = f"projects/{PROJECT_ID}"
parent = f"{name}/locations/{REGION}"


# Helper function to load credentials
def get_credentials():
    return service_account.Credentials.from_service_account_file(GCP_KEY_PATH)


# Helper function to initialize IAM client
def get_iam_client():
    return iam_admin_v1.IAMClient(credentials=get_credentials())


# Helper function to initialize Artifact Registry client
def get_artifact_registry_client():
    return artifactregistry_v1.ArtifactRegistryClient(credentials=get_credentials())


# Helper function to initialize storage client
def get_storage_client():
    return storage.Client(project=PROJECT_ID, credentials=get_credentials())


# Helper function to initialize services client
def get_services_client():
    return run_v2.ServicesClient(credentials=get_credentials())

def get_monitoring_client():
    return monitoring_v3.MetricServiceClient(credentials=get_credentials())


# Helper to determine when the service account is ready
def service_account_ready(service_account_name):
    attempts = 50
    while attempts > 0:
        attempts -= 1
        client = get_iam_client()
        service_accounts = client.list_service_accounts(name=name)
        for account in service_accounts:
            if service_account_name in account.name:
                return True
        time.sleep(2)
    return False


# Function to create service account key
def create_service_account_key(project_id, service_account_name, key_file_path):
    client = get_iam_client()
    service_account_email = (
        f"{service_account_name}@{project_id}.iam.gserviceaccount.com"
    )
    service_account_resource = (
        f"projects/{project_id}/serviceAccounts/{service_account_email}"
    )

    response = client.create_service_account_key(
        name=service_account_resource,
        private_key_type="TYPE_GOOGLE_CREDENTIALS_FILE",
        key_algorithm="KEY_ALG_RSA_2048",
    )

    with open(key_file_path, "wb") as key_file:
        key_file.write(response.private_key_data)
    print(f"Service account key created and saved to {key_file_path}.")


# Function to create Google Cloud bucket
def create_bucket(bucket_name, location):
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    bucket.create(location=location)
    print(f"Bucket '{bucket_name}' created in location '{location}'.")


# Function to add IAM policy binding to the bucket
def add_iam_policy_binding_to_bucket(bucket_name, service_account_name, role):
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    policy = bucket.get_iam_policy()

    policy.bindings.append(
        {
            "role": role,
            "members": [
                f"serviceAccount:{service_account_name}@{PROJECT_ID}.iam.gserviceaccount.com"
            ],
        }
    )

    bucket.set_iam_policy(policy)
    print(
        f"IAM policy binding added for {service_account_name} with role {role} on bucket {bucket_name}."
    )


# Function to create service account and related resources (bucket, repository, etc.)
def create_service_account_and_resources(deployment_id: str):
    try:
        service_account_name = f"deploy-box-sa-{deployment_id}"
        role = "projects/deploy-box/roles/deployBoxArtifactRegistryReadWriteRole"
        location = "us-central1"
        service_account_key_path = os.path.join(
            current_working_dir, "api", "utils", f"{service_account_name}-key.json"
        )

        # Initialize IAM client
        client = get_iam_client()

        # Check if service account exists
        service_accounts = client.list_service_accounts(name=name)
        for account in service_accounts:
            if service_account_name in account.name:
                print(f"Service account {service_account_name} already exists.")
                return

        # Create service account
        request = iam_admin_v1.CreateServiceAccountRequest(
            name=name,
            account_id=service_account_name,
            service_account=iam_admin_v1.ServiceAccount(
                display_name="Deploy Box Service Account",
                description="Service account for deploy box",
            ),
        )
        response = client.create_service_account(request=request)
        print(f"Service account created: {response.name}")

        # Create Artifact Registry repository
        artifact_registry_client = get_artifact_registry_client()
        repository_name = f"deploy-box-repo-{deployment_id}"
        request = artifactregistry_v1.CreateRepositoryRequest(
            parent=parent,
            repository_id=repository_name,
            repository=artifactregistry_v1.Repository(
                format_=artifactregistry_v1.Repository.Format.DOCKER,
                description="Docker repository for Deploy Box",
            ),
        )
        operation = artifact_registry_client.create_repository(request=request)
        response = operation.result()
        print(f"Repository created: {response.name}")

        # Check if service account is ready
        if not service_account_ready(service_account_name):
            print("Service account not ready.")

        # Add IAM policy binding to Artifact Registry repository
        repository_resource = response.name
        policy_request = iam_policy_pb2.GetIamPolicyRequest(
            resource=repository_resource
        )
        policy = artifact_registry_client.get_iam_policy(request=policy_request)
        binding = policy_pb2.Binding(role=role)
        binding.members.append(
            f"serviceAccount:{service_account_name}@{PROJECT_ID}.iam.gserviceaccount.com"
        )
        policy.bindings.append(binding)
        set_policy_request = iam_policy_pb2.SetIamPolicyRequest(
            resource=repository_resource, policy=policy
        )
        artifact_registry_client.set_iam_policy(request=set_policy_request)

        # Create Google Cloud Storage bucket
        bucket_name = f"deploy-box-bucket-{deployment_id}"
        create_bucket(bucket_name, location)

        # Check if service account is ready
        if not service_account_ready(service_account_name):
            print("Service account not ready.")

        # Add IAM policy binding to the bucket
        add_iam_policy_binding_to_bucket(bucket_name, service_account_name, role)

        # Create service account key and return it
        create_service_account_key(
            PROJECT_ID, service_account_name, service_account_key_path
        )
        with open(service_account_key_path, "r") as file:
            key_data = file.read()

        # Clean up the key file
        os.remove(service_account_key_path)
        return key_data

    except Exception as e:
        print(f"Error: {e}")
        return str(e)


# Function to deploy service with environment variables
def deploy_service(service_name, image, env_vars):
    try:
        print(f"Deploying {service_name}...")

        run_client = get_services_client()

        print(f"Deploying {service_name}...")

        service = run_v2.Service(
            template=run_v2.RevisionTemplate(
                containers=[
                    run_v2.Container(
                        image=image,
                        env=[
                            run_v2.EnvVar(name=key, value=value)
                            for key, value in env_vars.items()
                        ],
                        ports=[run_v2.ContainerPort(container_port=8080)],
                    )
                ],
                timeout=Duration(seconds=300),  # 5 min timeout
            )
        )

        operation = run_client.create_service(
            parent=parent, service=service, service_id=service_name
        )
        operation.result()  # Wait for deployment
        print(f"Deployed {service_name}")

        # Add IAM policy binding to allow all users to invoke the service
        service_full_name = f"{parent}/services/{service_name}"
        policy = run_client.get_iam_policy(request={"resource": service_full_name})
        policy.bindings.append(
            policy_pb2.Binding(role="roles/run.invoker", members=["allUsers"])
        )
        run_client.set_iam_policy(request={"resource": service_full_name, "policy": policy})

        # Get service URL
        service_info = run_client.get_service(name=service_full_name)
        return service_info.uri
    
    except Exception as e:
        print(f"Error: {e}")
        raise e
    


# Function to refresh the service by updating the image
def refresh_service(service_name, image):
    run_client = get_services_client()
    parent = f"projects/{PROJECT_ID}/locations/{REGION}"

    service_full_name = f"{parent}/services/{service_name}"
    service = run_client.get_service(name=service_full_name)

    service.template.containers[0].image = image
    operation = run_client.update_service(service=service)
    operation.result()  # Wait for deployment
    print(f"Refreshed {service_name}")

def delete_service(service_name):
    run_client = get_services_client()
    parent = f"projects/{PROJECT_ID}/locations/{REGION}"

    service_full_name = f"{parent}/services/{service_name}"
    operation = run_client.delete_service(name=service_full_name)
    operation.result()  # Wait for deletion
    print(f"Deleted {service_name}")

def get_service_utilization(service_name):
    client = get_monitoring_client()
    project_name = f"projects/{PROJECT_ID}"

    # Define the metric types for Cloud Run
    metrics = {
        "request_count": "run.googleapis.com/request_count",
        "cpu_usage": "run.googleapis.com/container/cpu/utilizations",
        "memory_usage": "run.googleapis.com/container/memory/utilizations",
        # "egress_traffic": "run.googleapis.com/network/egress_bytes_count",
        # "instance_time": "run.googleapis.com/container/instance_time",
    }

    for metric_name, metric_type in metrics.items():
        print(f"\nFetching data for: {metric_name}")

        # Create a filter for the Cloud Run service
        filter_str = (
            f'metric.type="{metric_type}" '
            f'AND resource.labels.service_name="{service_name}" '
            f'AND resource.labels.location="{REGION}"'
        )

        request = monitoring_v3.ListTimeSeriesRequest(
            name=project_name,
            filter=filter_str,
            interval=monitoring_v3.TimeInterval(
                end_time={"seconds": int(time.time())},
                start_time={"seconds": int(time.time()) - 3600},  # Last 1 hour
            ),
            view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        )

        response = client.list_time_series(request)
        
        for time_series in response:
            print(f"Metric: {time_series}")
            for point in time_series.points:
                print(f"Time: {point.interval.end_time}, Value: {point.value}")

