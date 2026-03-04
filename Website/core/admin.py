from django.contrib.admin import AdminSite
from django.views.decorators.csrf import csrf_exempt
from blogs.admin import BlogPostAdmin
from blogs.models import BlogPost
from stacks.admin import PurchasableStackAdmin, StackAdmin, MetricDefinitionAdmin
from stacks.models import PurchasableStack, Stack
from stacks.metrics.models import MetricDefinition
from accounts.admin import UserProfileAdmin
from accounts.models import UserProfile
from deploy_box_apis.admin import APIAdmin
from deploy_box_apis.models import API

# from payments.models import usage_information, billing_history
# from payments.admin import UsageInformationAdmin, BillingHistoryAdmin

class NoCSRFAdminSite(AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        # Apply csrf_exempt to all admin views
        for i, url in enumerate(urls):
            if hasattr(url, 'callback') and url.callback is not None:
                urls[i].callback = csrf_exempt(url.callback)
        return urls

# Create an instance of our custom admin site
admin_site = NoCSRFAdminSite()

# Register app models
admin_site.register(PurchasableStack, PurchasableStackAdmin)
admin_site.register(Stack, StackAdmin)
admin_site.register(MetricDefinition, MetricDefinitionAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
# admin_site.register(usage_information, UsageInformationAdmin)
# admin_site.register(billing_history, BillingHistoryAdmin)
admin_site.register(BlogPost, BlogPostAdmin)
admin_site.register(API, APIAdmin)

