from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.utils.html import format_html
from django.core.serializers.json import DjangoJSONEncoder
import json
from stacks.models import PurchasableStack, Stack

# Register your models here.
class PurchasableStackAdmin(admin.ModelAdmin):
    search_fields = ("type", "variant", "version", "price_id")
    list_display = ("id", "type", "variant", "version", "price_id")


class StackAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "project", "purchased_stack", "status", "created_at", "iac_editor_link")
    list_filter = ("status", "purchased_stack__type", "created_at")
    search_fields = ("name", "project__name", "purchased_stack__type")
    readonly_fields = ("id", "created_at", "updated_at")
    
    def iac_editor_link(self, obj):
        """Create a link to the IAC editor for this stack"""
        if obj.id:
            url = reverse('admin:stacks_stack_iac_editor', args=[obj.id])
            return format_html('<a href="{}" class="button">Edit IAC</a>', url)
        return "N/A"
    
    def get_urls(self):
        """Add custom URLs for the IAC editor"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/iac-editor/',
                self.admin_site.admin_view(self.iac_editor_view),
                name='stacks_stack_iac_editor',
            ),
        ]
        return custom_urls + urls
    
    def iac_editor_view(self, request, object_id):
        """View for editing the IAC JSON"""
        stack = get_object_or_404(Stack, pk=object_id)
        
        if request.method == 'POST':
            try:
                # Get the JSON data from the form
                iac_json = request.POST.get('iac_json', '{}')
                
                # Validate JSON
                iac_data = json.loads(iac_json)
                
                # Update the stack's IAC field
                stack.iac = iac_data
                stack.save()
                
                messages.success(request, f'IAC configuration for stack "{stack.name}" has been updated successfully.')
                return HttpResponseRedirect(
                    reverse('admin:stacks_stack_change', args=[object_id])
                )
                
            except json.JSONDecodeError as e:
                messages.error(request, f'Invalid JSON format: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error updating IAC: {str(e)}')
        
        # Get current IAC data
        current_iac = stack.iac or {}
        formatted_iac = json.dumps(current_iac, indent=2, cls=DjangoJSONEncoder)
        
        context = {
            'title': f'Edit IAC Configuration - {stack.name}',
            'stack': stack,
            'iac_json': formatted_iac,
            'opts': self.model._meta,
            'original': stack,
        }
        
        return render(request, 'admin/stacks/stack/iac_editor.html', context)


# Register the models
admin.site.register(PurchasableStack, PurchasableStackAdmin)
admin.site.register(Stack, StackAdmin)


