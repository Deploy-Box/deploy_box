from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import time
import datetime
import json

class GCPWrapper():
    def __init__(self):
        self.__cloud_platform_creds = None

        self.__load_credentials()
        self.__get_auth_token()

    def __load_credentials(self):
        SERVICE_ACCOUNT_FILE = 'key.json'

        # Scopes needed for Cloud Run
        SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

        # Load credentials
        self.__cloud_platform_creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

    def __get_auth_token(self):
        # Refresh and get token
        auth_req = google.auth.transport.requests.Request()
        self.__cloud_platform_creds.refresh(auth_req)
        self.__token = self.__cloud_platform_creds.token

    def __request_helper(self, url):
        # Use the token in your request
        if not self.__token:
            self.__get_auth_token()

        headers = {
            'Authorization': f'Bearer {self.__token}'
        } 

        return requests.get(url, headers=headers).json()

    def get_billable_instance_time(self, epoch: str):
        epoch = int(epoch)

        return_item = {
                "stack_id": {
                    "cpu": 1031,
                    "ram": 230482
                },
                "stack_da": 242452
        }

        # Convert epoch to datetime
        dt = datetime.datetime.fromtimestamp(epoch)
        start_time = datetime.datetime(dt.year, dt.month, 1).strftime('%Y-%m-%dT00:00:00Z')
        end_time = (datetime.datetime(dt.year, dt.month + 1, 1) - datetime.timedelta(seconds=1)).strftime('%Y-%m-%dT00:00:00Z')

        SERVICE_URL = (
            'https://monitoring.googleapis.com/v3/projects/deploy-box/timeSeries'
            '?filter=metric.type="run.googleapis.com/container/billable_instance_time"'
            f'&interval.startTime={start_time}'
            f'&interval.endTime={end_time}'
            f'&aggregation.alignmentPeriod={3600 * 24 * 7}s'
            '&aggregation.perSeriesAligner=ALIGN_SUM'
        )

        return self.__request_helper(SERVICE_URL)


if __name__ == '__main__':
    gcp_wrapper = GCPWrapper()

    response = gcp_wrapper.get_billable_instance_time(time.time())

    with open('response.json', 'w') as f:
        json.dump(response, f, indent=4)

    print(response)