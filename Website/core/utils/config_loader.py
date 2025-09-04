import json
import os
from dotenv import load_dotenv

def load_config():
    load_dotenv()

    env = os.environ.get("ENV")

    if not env:
        print("ENV is not set")
        env = "dev"

    filename = f"config.{env.lower()}.json"
    with open(filename, "r") as f:
        config = json.load(f)
        for key, value in config.items():
            os.environ[key] = value
            print(f"Loaded {key} from {filename}", os.environ.get(key))
    

