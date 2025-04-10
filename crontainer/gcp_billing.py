import requests
import os
from Website.core.helpers.exchange_client_credentials import exchange_client_credentials_for_token


def call_update_billing():
    token_url = "https://deploy-box.onrender.com/o/token/"

    token = exchange_client_credentials_for_token(
        os.environ.get("CLIENT_ID"), os.environ.get("CLIENT_SECRET"), token_url
    )
    assert token is not None

    token = token.get("access_token")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        "https://deploy-box.onrender.com/api/stack/update-billing/", headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"Error updating billing: {response.text}")


if __name__ == "__main__":
    call_update_billing()
