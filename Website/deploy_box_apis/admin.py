from django.contrib import admin

# Register your models here.
from .models import API


@admin.register(API)
class APIAdmin(admin.ModelAdmin):
    list_display = (
        "name", "description", "price_per_1000_requests", "endpoint", "category",
        "popular", "response_time", "created_at", "updated_at"
    )
    search_fields = ("name", "description", "endpoint", "category")
    list_filter = ("category", "popular", "created_at", "updated_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    fields = (
        "id", "api_key", "name", "description", "price_per_1000_requests", "endpoint",
        "icon", "category", "popular", "response_time", "features", "created_at", "updated_at"
    )
