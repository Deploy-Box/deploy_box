import time

from django.http import JsonResponse, HttpRequest  # type: ignore

from core.wrappers.GCPWrapper.main import GCPWrapper
from core.helpers import gcp_id_extractor
from api.models import Stack
from payments.models import Prices


def get_billable_instance_time(epoch: float) -> dict:
    gcp_wrapper = GCPWrapper()
    response = gcp_wrapper.get_billable_instance_time(epoch=epoch)

    return_data = {}

    for time_series_item in response.get("timeSeries", []):
        service_name = (
            time_series_item.get("resource", {}).get("labels", {}).get("service_name")
        )

        if service_name.startswith("frontend"):
            stack_id = gcp_id_extractor(service_name, option="frontend")
        else:
            stack_id = gcp_id_extractor(service_name, option="backend")

        if stack_id in return_data.keys():
            return_data[stack_id] += (
                time_series_item.get("points", [{}])[0]
                .get("value", {})
                .get("doubleValue")
            )
        else:
            return_data[stack_id] = (
                time_series_item.get("points", [{}])[0]
                .get("value", {})
                .get("doubleValue")
            )

    return return_data


def update_billing_cpu(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        data = get_billable_instance_time(time.time())

        price_item = Prices.objects.filter(name="cpu_usage_multiple").first()

        if price_item is None:
            return JsonResponse({"error": "price not found"}, status=404)

        price = price_item.price

        for stack_id, usage in data.items():
            try:
                stack = Stack.objects.get(id=stack_id)
            except Stack.DoesNotExist:
                continue

            stack.pending_billed = usage * price
            print(stack.pending_billed)
            stack.save()

        return JsonResponse({"success": "Billing updated"}, status=200)

    return JsonResponse({"error": "only post"}, status=405)


if __name__ == "__main__":
    get_billable_instance_time(time.time())
