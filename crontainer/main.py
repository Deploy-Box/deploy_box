import requests
import json
from pymongo import MongoClient

def send_data(data, token):
    headers ={
        "Authorization": f"Bearer {token}",
        'Content-Type': 'application/json'
    }  
    url = "https://deploy-box.onrender.com/api/stacks/update_database_usage"
    requests.post(url, data=data, headers=headers)


def check_db_size():

    token = "dOSRVMH8oBFlwsq7oRjVTws3RAh5n8"
    headers ={
        "Authorization": f"Bearer {token}"
    }    
    data = requests.get("https://deploy-box.onrender.com/api/stacks/get_all_stacks", headers=headers)

    storage_amounts_dict = {}

    for stack_id, uris in data.json().get("stacks").items():
        for uri in uris:
            client = MongoClient(uri)
            db = client.get_default_database()
            stats = db.command("dbstats")
            storage_size = stats.get("storageSize")

            if stack_id in storage_amounts_dict:
                storage_amounts_dict[stack_id] += storage_size
            else:
                storage_amounts_dict[stack_id] = storage_size

    json_data = json.dumps(storage_amounts_dict)
    send_data(json_data, token)


if __name__ == '__main__':
    check_db_size()



