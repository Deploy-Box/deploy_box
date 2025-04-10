
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