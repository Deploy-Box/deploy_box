from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from django.db import transaction
from .models import UserProfile

class UserProfileAdmin(UserAdmin):
    model = UserProfile
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'delete_account_button')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = ['deactivate_users', 'activate_users']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Email Verification', {'fields': ('email_verification_token', 'new_email')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    def delete_account_button(self, obj):
        """Custom button to delete user account"""
        if obj and obj.is_superuser:
            return format_html(
                '<span style="color: #999;">Cannot delete superuser</span>'
            )
        if obj:
            return format_html(
                '<a class="button" href="{}" style="background: #dc2626; color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none;">Delete Account</a>',
                f'/admin/accounts/userprofile/{obj.id}/delete-account/'
            )
        return ''
    
    def delete_selected_users(self, request, queryset):
        """Bulk action to delete selected users"""
        # Filter out superusers
        non_superusers = queryset.filter(is_superuser=False)
        superusers = queryset.filter(is_superuser=True)
        
        deleted_count = 0
        with transaction.atomic():
            for user in non_superusers:
                user.delete()
                deleted_count += 1
        
        if deleted_count > 0:
            self.message_user(request, f'Successfully deleted {deleted_count} user(s).')
        
        if superusers.exists():
            self.message_user(request, 'Cannot delete superuser accounts.', level=messages.WARNING)
        
        if deleted_count == 0 and not superusers.exists():
            self.message_user(request, 'No users were deleted.')
    
    
    def deactivate_users(self, request, queryset):
        """Bulk action to deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Successfully deactivated {updated} user(s).')
    
    
    def activate_users(self, request, queryset):
        """Bulk action to activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Successfully activated {updated} user(s).')
        
    def get_urls(self):
        """Add custom URLs for delete account functionality"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/delete-account/',
                self.admin_site.admin_view(self.delete_account_view),
                name='accounts_userprofile_delete_account',
            ),
        ]
        return custom_urls + urls
    
    def delete_account_view(self, request, object_id):
        """Handle account deletion from admin"""
        try:
            user = self.get_object(request, object_id)
            if user is None:
                messages.error(request, 'User not found.')
                return HttpResponseRedirect('../')
            
            if user.is_superuser:
                messages.error(request, 'Cannot delete superuser accounts.')
                return HttpResponseRedirect('../')
            
            # Delete the user
            username = user.username
            user.delete()
            
            messages.success(request, f'Account for user "{username}" has been successfully deleted.')
            return HttpResponseRedirect('../')
            
        except UserProfile.DoesNotExist:
            messages.error(request, 'User not found.')
            return HttpResponseRedirect('../')
        except Exception as e:
            messages.error(request, f'Error deleting account: {str(e)}')
            return HttpResponseRedirect('../')

# Register the custom admin
admin.site.register(UserProfile, UserProfileAdmin)
