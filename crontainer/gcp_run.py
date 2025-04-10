from urllib import response
import requests
import os


def exchange_client_credentials_for_token(
    client_id, client_secret, token_url
) -> dict | None:
    """Exchanges client credentials for an access token."""
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            print(f"Error obtaining client credentials token: {response.text}")
            return None

        return response.json()  # Contains the access token
    except Exception as e:
        print(f"Error during client credentials token exchange: {str(e)}")
        return None


def call_update_billing():
    token_url = "http://localhost:8000/o/token/"

    token = exchange_client_credentials_for_token(
        os.environ.get("CLIENT_ID"), os.environ.get("CLIENT_SECRET"), token_url
    )
    assert token is not None

    token = token.get("access_token")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        "http://localhost:8000/api/stack/update-billing/", headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"Error updating billing: {response.text}")


if __name__ == "__main__":
    call_update_billing()
