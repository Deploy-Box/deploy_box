from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Avg
from .models import usage_information, billing_history, Prices

# Register your models here.

@admin.register(usage_information)
class UsageInformationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'organization_name', 
        'stack_name', 
        'current_usage', 
        'monthly_usage', 
        'created_at', 
        'updated_at'
    ]
    
    list_filter = [
        'organization__name',
        'stack__name',
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'organization__name',
        'stack__name',
        'id',
    ]
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    ordering = ['-created_at']
    
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'organization', 'stack')
        }),
        ('Usage Data', {
            'fields': ('current_usage', 'monthly_usage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def organization_name(self, obj):
        return obj.organization.name if obj.organization else 'N/A'
    
    def stack_name(self, obj):
        return obj.stack.name if obj.stack else 'N/A'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'stack')

@admin.register(billing_history)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'organization_name',
        'amount',
        'billed_usage',
        'status',
        'payment_method',
        'created_at',
        'paid_on'
    ]
    
    list_filter = [
        'status',
        'organization__name',
        'payment_method',
        'created_at',
        'paid_on',
    ]
    
    search_fields = [
        'organization__name',
        'description',
        'id',
    ]
    
    readonly_fields = ['id', 'created_at']
    
    ordering = ['-created_at']
    
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'organization', 'amount', 'description')
        }),
        ('Usage & Payment', {
            'fields': ('billed_usage', 'payment_method', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'paid_on'),
            'classes': ('collapse',)
        }),
    )
    
    def organization_name(self, obj):
        return obj.organization.name if obj.organization else 'N/A'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')

@admin.register(Prices)
class PricesAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'created_at', 'updated_at']
    list_filter = ['name', 'created_at', 'updated_at']
    search_fields = ['name', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'price')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
