from payments.models import Prices
from django.http import (
    HttpRequest,
    JsonResponse
)
import json


def create_price_item(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name").lower()
            price = data.get("price")

            price_item = Prices.objects.filter(name=name).first()

            if not price_item:
                Prices.objects.create(name=name, price=price)

                return JsonResponse({"message": "item created"}, status=200)
            else:
                return JsonResponse({"message": "item already exists"}, status=400)
        except Exception as e:
            return JsonResponse({"message": f'and unexpected error returned {str(e)}'}, status = 500)       
    else:
        return JsonResponse({"message": "must be a post request"}, status=400)
    

def update_price_item(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            price_id = data.get("price_id")

            price_item = Prices.objects.get(id=price_id)

            if price_item:
                price_item.name = data.get("name", price_item.name).lower()
                price_item.price = data.get("price", price_item.price)
                price_item.save()

                return JsonResponse({"message": "prce item updated"}, status=200)
            else:
                return JsonResponse({"message": "price item does not exist"}, status=400)
        except Exception as e:
            return JsonResponse({"message": f'and unexpected error returned {str(e)}'}, status = 500)       

        
def delete_price_item(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            price_id = data.get("price_id")

            price_item = Prices.objects.filter(id=price_id).first()

            if price_item:
                price_item.delete()

                return JsonResponse({"message": "price item deleted"}, status=200)
            else:
                return JsonResponse({"message": "price item does not exist"}, status=404)
            
        except Exception as e:
            return JsonResponse({"message": f'and unexpected error returned {str(e)}'}, status = 500)       

def get_price_item_by_name(request: HttpRequest, name: str) -> JsonResponse:
    if request.method == "GET":
        try:
            price_item = Prices.objects.filter(name=name).first()

            if price_item:
                price = price_item.price

                return JsonResponse({"name": name, "price": price}, status=200)
            else:
                return JsonResponse({"message": "item does not exist"}, status=404)
        except Exception as e:
            return JsonResponse({"message": f'and unexpected error returned {str(e)}'}, status = 500)       


