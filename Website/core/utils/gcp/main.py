import requests
import time
import datetime
import json

from django.conf import settings
from google.oauth2 import service_account
import google.auth.transport.requests


class GCPUtils:
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

        print(self.__token)

    def __request_helper(self, url, method="GET", data=None):
        # Use the token in your request
        if not self.__token:
            self.__get_auth_token()

        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Content-Type": "application/json",
        }

        if method == "GET":
            return requests.get(url, headers=headers).json()
        elif method == "POST":
            return requests.post(url, headers=headers, json=data).json()
        elif method == "PUT":
            return requests.put(url, headers=headers, json=data).json()
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
            "https://monitoring.googleapis.com/v3/projects/deploy-box/timeSeries"
            '?filter=metric.type="run.googleapis.com/container/billable_instance_time"'
            f"&interval.startTime={start_time}"
            f"&interval.endTime={end_time}"
            f"&aggregation.alignmentPeriod={3600 * 24 * 7}s"
            "&aggregation.perSeriesAligner=ALIGN_SUM"
        )

        return self.__request_helper(SERVICE_URL)

    def post_build_and_deploy(self, stack_id, github_repo, github_token, layer: str):
        try:
            # Replace with your project ID
            project_id = "deploy-box"
            github_url = (
                f"https://{github_token}:x-oauth-basic@github.com/{github_repo}.git"
            )
            github_repo_name = github_repo.split("/")[-1]
            print(github_url)
            print(github_repo_name)

            image_name = f"us-central1-docker.pkg.dev/deploy-box/deploy-box-repository/{layer}-{stack_id}".lower()

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
                        service_full_name="projects/deploy-box/locations/us-central1/services/{layer.lower()}-{stack_id}"
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
                    "resourceNames": ["projects/deploy-box"],
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


if __name__ == "__main__":
    gcp_wrapper = GCPUtils()

    print(gcp_wrapper.stream_logs(["frontend-5", "backend-5"]))
