import requests
import time
import datetime
import json

from django.conf import settings
from google.oauth2 import service_account
import google.auth.transport.requests


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

    def __load_credentials(self):
        SERVICE_ACCOUNT_FILE = "key.json"

        # Scopes needed for Cloud Run
        SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

        # Load credentials
        self.__cloud_platform_creds = (
            service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        )

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

        if method == "GET":
            response = requests.get(url, headers=headers)
            print(response.status_code)
            return response.json()
        elif method == "POST":
            return requests.post(url, headers=headers, json=data).json()
        elif method == "PUT":
            response = requests.get(url, headers=headers)
            if response.status_code == 404:
                print("Service not found")
                return None
            print(response.status_code)
            return response.json()
        elif method == "DELETE":
            return requests.delete(url, headers=headers).json()

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
        self, stack_id, github_repo, github_token, layer: str, port: int = 8080
    ):
        try:
            # Replace with your project ID
            github_url = (
                f"https://{github_token}:x-oauth-basic@github.com/{github_repo}.git"
            )
            github_repo_name = github_repo.split("/")[-1]
            print(github_url)
            print(github_repo_name)

            image_name = f"us-central1-docker.pkg.dev/{self.project_id}/deploy-box-repository/{layer}-{stack_id}".lower()

            # Define the Cloud Build steps
            build_steps = [
                {"name": "gcr.io/cloud-builders/git", "args": ["clone", github_url]},
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"docker build -t {image_name} ./{github_repo_name}/{layer}",
                    ],
                },
                {"name": "gcr.io/cloud-builders/docker", "args": ["push", image_name]},
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"""
                        gcloud run deploy {layer.lower()}-{stack_id} \
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
                        service_full_name="projects/{self.project_id}/locations/us-central1/services/{layer.lower()}-{stack_id}"
                        gcloud run services add-iam-policy-binding {layer.lower()}-{stack_id} \
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
            api_url = (
                f"https://cloudbuild.googleapis.com/v1/projects/{project_id}/builds"
            )

            # Submit the build
            print("Submitting build...")
            response = self.__request_helper(api_url, method="POST", data=build_config)

            if response is None or "name" not in response:
                print(f"Error creating build: {response}")
                return

            build_id = response["name"].split("/")[-1]
            print(f"Build submitted with ID: {build_id}")

            # Poll for build status
            print("Waiting for build to complete...")
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{project_id}/builds/{build_id}"

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
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={project_id}"
                )
            else:
                print(f"Build failed with status: {status}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={project_id}"
                )

        except Exception as e:
            print(f"An error occurred: {e}")

    def deploy_service(
        self,
        stack_id: str,
        image_name: str,
        layer: str,
        env_vars: dict | None = None,
        **kwargs,
    ) -> str:
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
            api_url = (
                f"https://cloudbuild.googleapis.com/v1/projects/{project_id}/builds"
            )

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
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{project_id}/builds/{build_id}"

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
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={project_id}"
                )
                return self.get_service_endpoint(service_name)
            else:
                print(f"Build failed with status: {status}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={project_id}"
                )

        except Exception as e:
            print(f"An error occurred: {e}")


    def redeploy_service(
        self,
        service_name: str,
        image_name: str,
        env_vars: dict | None = None,
        **kwargs,
    ) -> str:
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
                }
            ]

            # Define the build configuration
            build_config = {"steps": build_steps, "timeout": "600s"}

            # API endpoint for creating a build
            api_url = (
                f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/builds"
            )

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
            build_status_url = f"https://cloudbuild.googleapis.com/v1/projects/{project_id}/builds/{build_id}"

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
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={project_id}"
                )
                return self.get_service_endpoint(service_name)
            else:
                print(f"Build failed with status: {status}")
                print(
                    f"Build log URL: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={project_id}"
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


if __name__ == "__main__":
    gcp_wrapper = GCPUtils()

    print(gcp_wrapper.get_service_endpoint("backend-e1d72d93b09944e5"))
    # print(gcp_wrapper.put_service_envs("backend-9a77369a03984b9a", {"TEST": "TEST"}))

    # backend_image = "gcr.io/deploy-box/mern-backend"
    # backend_url = gcp_wrapper.deploy_service(
    #         "testing-1234",
    #         backend_image,
    #         "backend",
    #         {"MONGO_URI": "mongodb+srv://deployBoxUser-e9c9afbc1c0942c8:f45bdc78db0a@cluster0.yjaoi.mongodb.net/db-e9c9afbc1c0942c8?retryWrites=true&w=majority&appName=Cluster0"},
    #         port=5001
    #     )
