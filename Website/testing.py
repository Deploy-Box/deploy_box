from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import json
# Path to your service account key
SERVICE_ACCOUNT_FILE = 'key.json'
# SERVICE_URL = 'https://monitoring.googleapis.com/v3/projects/deploy-box/timeSeries?filter=metric.type="run.googleapis.com/request_count"&interval.startTime=2025-04-01T00:00:00Z&interval.endTime=2025-04-07T23:59:59Z'
SERVICE_URL = (
    'https://monitoring.googleapis.com/v3/projects/deploy-box/timeSeries'
    '?filter=metric.type="run.googleapis.com/container/billable_instance_time"'
    ' AND resource.label.service_name="website-1"'
    '&interval.startTime=2025-04-01T00:00:00Z'
    '&interval.endTime=2025-04-07T23:59:59Z'
    f'&aggregation.alignmentPeriod={3600 * 24 * 7}s'
    '&aggregation.perSeriesAligner=ALIGN_SUM'
)

# Scopes needed for Cloud Run
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

# Load credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

# Refresh and get token
auth_req = google.auth.transport.requests.Request()
credentials.refresh(auth_req)
token = credentials.token

# Use the token in your request
headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.get(SERVICE_URL, headers=headers)
print(response.status_code)

with open('response.json', 'w') as f:
    json.dump(response.json(), f, indent=4)

print(json.dumps(response.json(), indent=4))
