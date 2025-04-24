from django.contrib import admin
from stacks.models import PurchasableStack

# Register your models here.
class PurchasableStackAdmin(admin.ModelAdmin):
    search_fields = ("type", "variant", "version", "price_id")
    list_display = ("id", "type", "variant", "version", "price_id")


