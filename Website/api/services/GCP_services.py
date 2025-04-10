import json
from django.http import JsonResponse, HttpRequest
from core.wrappers.GCPWrapper.main import GCPWrapper
from api.models import Stack
from payments.models import Prices
import time

def get_billable_instance_time(epoch: str) -> dict:
    gcp_wrapper = GCPWrapper()
    response = gcp_wrapper.get_billable_instance_time(epoch=epoch)

    return_data = {}

    for time_series_item in response.get("timeSeries", []):
        service_name = time_series_item.get("resource", {}).get("labels", {}).get("service_name")

        if service_name in return_data.keys():
            return_data[service_name] += time_series_item.get("points", [{}])[0].get("value", {}).get("doubleValue")
        else:
            return_data[service_name] = time_series_item.get("points", [{}])[0].get("value", {}).get("doubleValue")

    return return_data


def update_billing_cpu(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        data = get_billable_instance_time(time.time())

        print(data)
        price_item = Prices.objects.filter(name="cpu_usage_multiple").first()
        price = price_item.price

        for stack_id, usage in data.items():
            stack = Stack.objects.get(id=stack_id)
            stack.pending_billed = (usage * price)

    else:
        return JsonResponse({"error": "only post"}, 405)
            
    
if __name__ == "__main__":
    get_billable_instance_time(time.time())