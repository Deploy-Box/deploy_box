"""Periodic credit-limit check.

Calls the Django admin endpoint to auto-pause stacks whose organization has
exceeded its monthly credit allowance.  Intended to be scheduled hourly (or
after each usage-recorder run).
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ.get("HOST")


def check_credit_limits() -> None:
    """POST to the credit-limits endpoint and log the result."""
    url = f"{HOST}/api/v1/stacks/admin/check-credit-limits/"
    try:
        resp = requests.post(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        paused = data.get("paused", [])
        errors = data.get("errors", [])
        if paused:
            print(f"Auto-paused {len(paused)} stack(s): {paused}")
        if errors:
            print(f"Errors: {errors}")
        if not paused and not errors:
            print("All organizations within credit limits.")
    except Exception as exc:
        print(f"Credit-limit check failed: {exc}")


if __name__ == "__main__":
    check_credit_limits()
