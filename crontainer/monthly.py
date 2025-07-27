import requests
import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ.get("HOST")

def update_billing_history() -> None:
    requests.post(
        f"{HOST}/api/v1/payments/update_billing_history/",
    )

if __name__ == "__main__":
    update_billing_history()
