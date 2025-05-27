import requests
import time
import datetime
import json
import os

from django.conf import settings
from google.oauth2 import service_account
import google.auth.transport.requests
from google.cloud import storage


class GCPUtils:
    # Docs: https://cloud.google.com/python/docs/reference/
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GCPUtils, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if self.__initialized:
            return

        self.__cloud_platform_creds = None
        self.__initialized = True
        self.project_id = settings.GCP.get("PROJECT_ID")

        assert self.project_id is not None, "Project ID not found in settings"

        self.__load_credentials()
        self.__get_auth_token()

        print(f"Successfully initialized GCP utils")

    def __load_credentials(self):
        SERVICE_ACCOUNT_FILE = settings.GCP.get("KEY_PATH")

        # Scopes needed for Cloud Run
        SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

        # Load credentials
        self.__cloud_platform_creds = (
            service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        )
        
        # Print debug info
        print(f"Using service account: {self.__cloud_platform_creds.service_account_email}")
        print(f"Project ID: {self.project_id}")
        print(f"Service account file path: {SERVICE_ACCOUNT_FILE}")

    def __get_auth_token(self):
        # Refresh and get token
        auth_req = google.auth.transport.requests.Request()

        if self.__cloud_platform_creds is None:
            self.__load_credentials()

        assert (
            self.__cloud_platform_creds is not None
        ), "Cloud Platform credentials not found"

        self.__cloud_platform_creds.refresh(auth_req)
        self.__token = self.__cloud_platform_creds.token

    def __request_helper(self, url, method="GET", data=None) -> dict | None:
        # Use the token in your request
        if not self.__token:
            self.__get_auth_token()

        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Content-Type": "application/json",
        }

        response = None
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.get(url, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)

            if response is None:
                return None

            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            if response.status_code >= 400:
                print(f"Error response: {response.text}")
                return None
                
            return response.json()
            
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return None

    def get_billable_instance_time(self, epoch: float):
        epoch = int(epoch)

        # Convert epoch to datetime
        dt = datetime.datetime.fromtimestamp(epoch)
        start_time = datetime.datetime(dt.year, dt.month, 1).strftime(
            "%Y-%m-%dT00:00:00Z"
        )
        end_time = (
            datetime.datetime(dt.year, dt.month + 1, 1) - datetime.timedelta(seconds=1)
        ).strftime("%Y-%m-%dT00:00:00Z")

        SERVICE_URL = (
            "https://monitoring.googleapis.com/v3/projects/self.project_id/timeSeries"
            '?filter=metric.type="run.googleapis.com/container/billable_instance_time"'
            f"&interval.startTime={start_time}"
            f"&interval.endTime={end_time}"
            f"&aggregation.alignmentPeriod={3600 * 24 * 7}s"
            "&aggregation.perSeriesAligner=ALIGN_SUM"
        )
        return self.__request_helper(SERVICE_URL)

    def post_build_and_deploy(
        self,
        stack_id,
        github_repo,
        github_token,
        layer: str,
        name: str = "",
        root_directory: str = "",
        port: int = 8080,
    ):
        if name == "":
            name = layer

        root_directory_without_layer = root_directory

        if root_directory == "":
            root_directory = layer
        else:
            if layer == "":
                root_directory = f"{root_directory}"
            else:
                root_directory = f"{root_directory}/{layer}"

        try:
            # Replace with your project ID
            github_url = (
                f"https://{github_token}:x-oauth-basic@github.com/{github_repo}.git"
            )
            github_repo_name = github_repo.split("/")[-1]
            print(github_url)
            print(github_repo_name)

            image_name = f"us-central1-docker.pkg.dev/{self.project_id}/deploy-box-repository/{name}-{stack_id}".lower()

            # Define the Cloud Build steps
            build_steps = [
                {"name": "gcr.io/cloud-builders/git", "args": ["clone", github_url]},
                {
                    "name": "gcr.io/cloud-builders/gcloud",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        apt-get update && apt-get install -y zip && \
                        cd {github_repo_name}/{root_directory_without_layer} && \
                        zip -r source.zip . && \
                        gsutil cp source.zip gs://{self.project_id}-source-code/{stack_id}/source.zip
                        """,
                    ],
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"docker build -t {image_name} ./{github_repo_name}/{root_directory}",
                    ],
                },
                {"name": "gcr.io/cloud-builders/docker", "args": ["push", image_name]},
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        gcloud run deploy {name.lower()}-{stack_id} \
                            --image={image_name} \
                            --region=us-central1 \
                            --platform=managed \
                            --allow-unauthenticated
                        """,
                    ],
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        service_full_name="projects/{self.project_id}/locations/us-central1/services/{name.lower()}-{stack_id}"
                        gcloud run services add-iam-policy-binding {name.lower()}-{stack_id} \
                            --region=us-central1 \
                            --member="allUsers" \
                            --role="roles/run.invoker"
                        """,
                    ],
                },
            ]

            # Define the build configuration
            build_config = {"steps": build_steps, "timeout": "600s"}

            # API endpoint for creating a build
            api_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds"

            # Submit the build
            print("Submitting build...")
            response = self.__request_helper(api_url, method="POST", data=build_config)

            response.get("metadata", {})
            metadata = response.get("metadata", {})
            build = metadata.get("build", {})
            build_id = build.get("id", None)

            if not build_id:
                print(f"Error creating build: {response}")
                raise Exception("Error creating build")

            # Poll for build status
            print("Waiting for build to complete...")
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds/{build_id}"

            status = "UNKNOWN"
            while True:
                build_status = self.__request_helper(build_status_url)
                if build_status is None:
                    print("Error getting build status")
                    break

                status = build_status.get("status", "UNKNOWN")
                print(f"Build status: {status}")

                if status in [
                    "SUCCESS",
                    "FAILURE",
                    "INTERNAL_ERROR",
                    "TIMEOUT",
                    "CANCELLED",
                    "EXPIRED",
                ]:
                    break

                time.sleep(10)  # Wait 10 seconds before checking again

            if status == "SUCCESS":
                print(f"Build completed successfully: {build_id}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={self.project_id}"
                )
            else:
                print(f"Build failed with status: {status}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={self.project_id}"
                )

        except Exception as e:
            print(f"An error occurred: {e}")

    def deploy_mern_service(
        self,
        frontend_service_id: str,
        backend_service_id: str,
        frontend_image_name: str,
        backend_image_name: str,
        backend_env_vars: dict | None = None,
        **kwargs,
    ) -> dict:
        backend_env_vars_str = (
            ",".join([f'{k}="{v}"' for k, v in backend_env_vars.items()]) if backend_env_vars else ""
        )

        try:
            # Define the Cloud Build steps
            build_steps = [
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        gcloud run deploy service-{backend_service_id} \
                            --image={backend_image_name} \
                            --region=us-central1 \
                            --platform=managed \
                            --allow-unauthenticated \
                            --port=5000 \
                            --set-env-vars={backend_env_vars_str}
                            """,
                    ],
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        service_full_name="projects/{self.project_id}/locations/us-central1/services/{backend_service_id}"
                        gcloud run services add-iam-policy-binding service-{backend_service_id} \
                            --region=us-central1 \
                            --member="allUsers" \
                            --role="roles/run.invoker"
                        """,
                    ],
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        backend_url=$(gcloud run services describe service-{backend_service_id} --region=us-central1 --format='value(status.url)')
                        gcloud run deploy service-{frontend_service_id} \
                            --image={frontend_image_name} \
                            --region=us-central1 \
                            --platform=managed \
                            --allow-unauthenticated \
                            --port=8080 \
                            --set-env-vars="REACT_APP_BACKEND_URL=$backend_url"
                            """,
                    ],
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        service_full_name="projects/{self.project_id}/locations/us-central1/services/{frontend_service_id}"
                        gcloud run services add-iam-policy-binding service-{frontend_service_id} \
                            --region=us-central1 \
                            --member="allUsers" \
                            --role="roles/run.invoker"
                        """,
                    ],
                },
            ]

            # Define the build configuration
            build_config = {"steps": build_steps, "timeout": "600s"}

            # API endpoint for creating a build
            api_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds"

            # Submit the build
            print("Submitting build...")
            response = self.__request_helper(api_url, method="POST", data=build_config)

            if response is None:
                print(f"Error creating build: {response}")
                return {
                    "url": None,
                    "build_status_url": "ERROR",
                    "status": "ERROR",
                }

            response.get("metadata", {})
            metadata = response.get("metadata", {})
            build = metadata.get("build", {})
            build_id = build.get("id", None)

            if not build_id:
                print(f"Error creating build: {response}")
                return {
                    "url": None,
                    "build_status_url": "ERROR",
                    "status": "ERROR",
                }

            print(f"Build submitted with ID: {build_id}")

            # Poll for build status
            print("Waiting for build to complete...")
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds/{build_id}"

            return {
                "url": None,
                "build_status_url": build_status_url,
                "status": "STARTING",
            }

        except Exception as e:
            print(f"An error occurred: {e}")
            return {
                "url": None,
                "build_status_url": "ERROR",
                "status": "ERROR",
            }


    def deploy_service(
        self,
        stack_id: str,
        image_name: str,
        layer: str,
        env_vars: dict | None = None,
        **kwargs,
    ) -> dict:
        service_name = f"{layer.lower()}-{stack_id.lower()}"

        port = kwargs.get("port", 8080) if kwargs else 8080
        env_vars_str = (
            ",".join([f'{k}="{v}"' for k, v in env_vars.items()]) if env_vars else ""
        )
        print(env_vars_str)

        try:
            # Define the Cloud Build steps
            build_steps = [
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        gcloud run deploy {service_name} \
                            --image={image_name} \
                            --region=us-central1 \
                            --platform=managed \
                            --allow-unauthenticated \
                            --port={port} \
                            --set-env-vars={env_vars_str}
                            """,
                    ],
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        service_full_name="projects/{self.project_id}/locations/us-central1/services/{service_name}"
                        gcloud run services add-iam-policy-binding {service_name} \
                            --region=us-central1 \
                            --member="allUsers" \
                            --role="roles/run.invoker"
                        """,
                    ],
                },
            ]

            # Define the build configuration
            build_config = {"steps": build_steps, "timeout": "600s"}

            # API endpoint for creating a build
            api_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds"

            # Submit the build
            print("Submitting build...")
            response = self.__request_helper(api_url, method="POST", data=build_config)

            if response is None:
                print(f"Error creating build: {response}")
                return {
                    "url": None,
                    "build_status_url": None,
                    "status": "ERROR",
                }

            response.get("metadata", {})
            metadata = response.get("metadata", {})
            build = metadata.get("build", {})
            build_id = build.get("id", None)

            if not build_id:
                print(f"Error creating build: {response}")
                return {
                    "url": None,
                    "build_status_url": None,
                    "status": "ERROR",
                }

            print(f"Build submitted with ID: {build_id}")

            # Poll for build status
            print("Waiting for build to complete...")
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds/{build_id}"

            return {
                "url": None,
                "build_status_url": build_status_url,
                "status": "STARTING",
            }

        except Exception as e:
            print(f"An error occurred: {e}")
            return {
                "url": None,
                "build_status_url": None,
                "status": "ERROR",
            }

    def redeploy_service(
        self,
        service_name: str,
        image_name: str,
        env_vars: dict | None = None,
        **kwargs,
    ) -> str:
        port = kwargs.get("port", 8000) if kwargs else 8000
        env_vars_str = (
            ",".join([f'{k}="{v}"' for k, v in env_vars.items()]) if env_vars else ""
        )
        print(env_vars_str)

        try:
            # Define the Cloud Build steps
            build_steps = [
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        gcloud run deploy {service_name} \
                            --image={image_name} \
                            --region=us-central1 \
                            --platform=managed \
                            --allow-unauthenticated \
                            --port={port} \
                            --set-env-vars={env_vars_str}
                            """,
                    ],
                }
            ]

            # Define the build configuration
            build_config = {"steps": build_steps, "timeout": "600s"}

            # API endpoint for creating a build
            api_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds"

            # Submit the build
            print("Submitting build...")
            response = self.__request_helper(api_url, method="POST", data=build_config)

            if response is None:
                print(f"Error creating build: {response}")
                raise Exception("Error creating build")

            response.get("metadata", {})
            metadata = response.get("metadata", {})
            build = metadata.get("build", {})
            build_id = build.get("id", None)

            if not build_id:
                print(f"Error creating build: {response}")
                raise Exception("Error creating build")

            print(f"Build submitted with ID: {build_id}")

            # Poll for build status
            print("Waiting for build to complete...")
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds/{build_id}"

            status = "UNKNOWN"
            while True:
                build_status = self.__request_helper(build_status_url)
                if build_status is None:
                    print("Error getting build status")
                    break

                status = build_status.get("status", "UNKNOWN")
                print(f"Build status: {status}")

                if status in [
                    "SUCCESS",
                    "FAILURE",
                    "INTERNAL_ERROR",
                    "TIMEOUT",
                    "CANCELLED",
                    "EXPIRED",
                ]:
                    break

                time.sleep(10)  # Wait 10 seconds before checking again

            if status == "SUCCESS":
                print(f"Build completed successfully: {build_id}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={self.project_id}"
                )
                return self.get_service_endpoint(service_name)
            else:
                print(f"Build failed with status: {status}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={self.project_id}"
                )

        except Exception as e:
            print(f"An error occurred: {e}")

    def get_all_services(self) -> dict:
        url = f"https://run.googleapis.com/v2/projects/{self.project_id}/locations/us-central1/services"
        response = self.__request_helper(url)

        if response is None:
            return {"status": "error", "message": "No services found"}

        services = response.get("services", [])

        cleaned_services = []
        for service in services:
            cleaned_service = {
                "name": service.get("name", ""),
                "url": service.get("uri", ""),
                "created_at": service.get("createTime", ""),
                "updated_at": service.get("updateTime", ""),
            }
            cleaned_services.append(cleaned_service)

        return {"status": "success", "data": cleaned_services}

    def get_service_endpoint(self, service_name: str) -> str:
        url = f"https://run.googleapis.com/v2/projects/{self.project_id}/locations/us-central1/services/{service_name}"
        response = self.__request_helper(url)

        if response is None:
            raise Exception("Service not found")

        print(json.dumps(response, indent=4))

        service = response.get("urls", [""])[0]

        if not service:
            raise Exception("Service not found")

        print(f"Service URL: {service}")
        return service

    # TODO: This currently only grabs the latest logs, not a stream
    def stream_logs(
        self,
        service_names: list[str],
    ) -> dict:
        service_names = [name.lower() for name in service_names]
        service_names = [name.replace(" ", "-") for name in service_names]

        cleaned_logs = {}

        for service_name in service_names:

            if not (
                service_name.startswith("backend")
                or service_name.startswith("frontend")
                or service_name.startswith("database")
            ):
                continue

            url = f"https://logging.googleapis.com/v2/entries:list"
            response = self.__request_helper(
                url,
                method="POST",
                data={
                    "resourceNames": [f"projects/{self.project_id}"],
                    "filter": f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}" AND resource.labels.location="us-central1"',
                    "orderBy": "timestamp desc",
                    "pageSize": 20,
                },
            )

            if response is None:
                return {"status": "error", "message": "No logs found"}

            entries = response.get("entries", [])

            if len(entries) == 0:
                cleaned_logs.update({service_name: {"status": "success", "data": []}})
                continue

            cleaned_log_entries = []
            for entry in entries:
                if not "severity" in entry:
                    continue

                cleaned_log = {
                    "id": entry.get("insertId", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "log": entry.get("textPayload", ""),
                    "severity": entry.get("severity", ""),
                    "http_request": entry.get("httpRequest", {}),
                    "textPayload": entry.get("textPayload", ""),
                }

                cleaned_log_entries.append(cleaned_log)

            cleaned_logs.update(
                {service_name: {"status": "success", "data": cleaned_log_entries}}
            )

        print(json.dumps(cleaned_logs, indent=4))
        return {"status": "success", "data": cleaned_logs}
    
    def get_service_url(self, service_name: str) -> str:
        url = f"https://run.googleapis.com/v2/projects/{self.project_id}/locations/us-central1/services/service-{service_name}"
        response = self.__request_helper(url)

        if response is None:
            return ""

        print(json.dumps(response, indent=4))

        # The uri field is at the root level of the response, not in template
        return response.get("uri", "")

    def get_service_envs(self, service_name: str) -> dict:
        url = f"https://run.googleapis.com/v2/projects/{self.project_id}/locations/us-central1/services/{service_name}"
        response = self.__request_helper(url)

        print(json.dumps(response, indent=4))

        template = response.get("template", {})
        containers = template.get("containers", [{}])[0]
        env_vars_list = containers.get("env", [])

        env_vars = {}
        for env_var in env_vars_list:
            env_vars[env_var.get("name")] = env_var.get("value")

        return env_vars

    def put_service_envs(self, service_name: str, env_vars: dict) -> dict:
        # Get the existing service definition
        service_url = f"https://run.googleapis.com/v2/projects/{self.project_id}/locations/us-central1/services/{service_name}"
        service = self.__request_helper(service_url, method="GET")
        print(service)

        if not service:
            raise Exception(f"Could not fetch service: {service_name}")

        # Merge new env vars with existing ones
        container = service["template"]["containers"][0]
        existing_envs = {env["name"]: env["value"] for env in container.get("env", [])}
        merged_envs = {**existing_envs, **env_vars}

        self.redeploy_service(
            service_name,
            service["template"]["containers"][0]["image"],
            env_vars=merged_envs,
        )

    def get_build_status(self, build_status_url: str) -> str:
        response = self.__request_helper(build_status_url)

        if response is None:
            return "UNKNOWN"

        status = response.get("status", "UNKNOWN")

        if status == "SUCCESS":
            return "SUCCESS"
        elif status == "FAILURE":
            return "ERROR"
        elif status == "INTERNAL_ERROR":
            return "ERROR"
        elif status == "TIMEOUT":
            return "ERROR"
        elif status == "CANCELLED":
            return "ERROR"
        elif status == "EXPIRED":
            return "ERROR"

        return status
    
    def upload_file(self, source_file_path: str, destination_blob_name: str) -> str:
        self.client = storage.Client(project=self.project_id, credentials=self.__cloud_platform_creds)
        self.bucket = self.client.bucket("deploy-box-c5fb282126574ccd")
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        return f"File {source_file_path} uploaded to {destination_blob_name}."
    
    def configure_bucket(self) -> str:
        # # Configure the bucket for website hosting
# gsutil web set -m index.html -e index.html gs://YOUR_BUCKET_NAME
        self.client = storage.Client(project=self.project_id, credentials=self.__cloud_platform_creds)
        self.bucket = self.client.bucket("deploy-box-c5fb282126574ccd")
        
        # Configure bucket for website hosting
        self.bucket.configure_website(main_page_suffix='index.html', not_found_page='index.html')
        
        # Make bucket public
        policy = self.bucket.get_iam_policy()
        policy.bindings.append({
            "role": "roles/storage.objectViewer",
            "members": ["allUsers"]
        })
        self.bucket.set_iam_policy(policy)
        
        return f"Bucket {self.bucket.name} configured for website hosting."

    
    def upload_folder(self, source_file_path: str, destination_blob_name: str) -> str:
        """
        Upload a folder and its contents to GCS bucket.
        Args:
            source_file_path: Local folder path to upload
            destination_blob_name: Destination path in bucket
        Returns:
            Status message string
        """
        self.client = storage.Client(project=self.project_id, credentials=self.__cloud_platform_creds)
        self.bucket = self.client.bucket("deploy-box-c5fb282126574ccd")

        # Walk through the source directory
        uploaded_files = []
        for root, dirs, files in os.walk(source_file_path):
            for file in files:
                # Get full local path
                local_file = os.path.join(root, file)
                
                # Get relative path from source directory
                relative_path = os.path.relpath(local_file, source_file_path)
                
                # Construct destination blob path
                blob_path = os.path.join(destination_blob_name, relative_path)
                
                # Create blob and upload file
                blob = self.bucket.blob(blob_path)
                blob.upload_from_filename(local_file)
                uploaded_files.append(blob_path)

        return f"Uploaded {len(uploaded_files)} files to {destination_blob_name}"
    



# if __name__ == "__main__":
gcp_wrapper = GCPUtils()

print(gcp_wrapper.upload_folder("/Users/kalebbishop/Documents/repos/MERN-Pro/source_code/frontend/build", ""))
# gcp_wrapper.configure_bucket()