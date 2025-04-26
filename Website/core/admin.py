from django.contrib.admin import AdminSite
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import Application
from stacks.admin import PurchasableStackAdmin
from stacks.models import PurchasableStack

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

# Register OAuth2 provider models
admin_site.register(Application)
admin_site.register(PurchasableStack, PurchasableStackAdmin)


