import requests
import os
from dotenv import load_dotenv
import json

def exchange_client_credentials_for_token(
) -> dict | None:
    """Exchanges client credentials for an access token."""
    load_dotenv()

    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
    }

    try:
        token_url = f"{os.getenv('BASE_URL')}/o/token/"
        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            print(f"Error obtaining client credentials token: {response.text}")
            return None

        return response.json()  # Contains the access token
    except Exception as e:
        print(f"Error during client credentials token exchange: {str(e)}")
        return None
    
def make_authenticated_api_request(url, method="get", json=None):
    token = exchange_client_credentials_for_token()
    headers = {"Authorization": f"Bearer {token.get('access_token')}"}
    full_url = f"{os.getenv('BASE_URL')}/{url}"

    if method == "POST":
        response = requests.post(full_url, headers=headers, json=json)
    else:
        response = requests.get(full_url, headers=headers)

    try:
        return response.json()
    except:
        print(f"Error during request: {response.text}")
        return response.text

if __name__ == "__main__":
    print(exchange_client_credentials_for_token())
