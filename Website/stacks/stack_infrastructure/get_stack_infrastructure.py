import json
import os

def get_stack_infrastructure(purchaseable_stack: str) -> dict:
    stack_infrastructure_mapping = {
        "MOBILE.": "mobile_testing.json",
    }

    try:
        with open(os.path.join(os.path.dirname(__file__), stack_infrastructure_mapping[purchaseable_stack]), "r") as f:
            return json.load(f)
    except KeyError:
        print(f"No stack infrastructure mapping found for '{purchaseable_stack}'.")
        return {}
    except FileNotFoundError:
        print(f"Stack infrastructure file for '{purchaseable_stack}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON for stack infrastructure file of '{purchaseable_stack}'.")
        return {}