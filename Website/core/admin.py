from django.contrib.admin import AdminSite
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import Application

class NoCSRFAdminSite(AdminSite):
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        # Apply csrf_exempt to all admin views
        for i, url in enumerate(urls):
            if hasattr(url, 'callback'):
                urls[i].callback = csrf_exempt(url.callback)
        return urls

# Create an instance of our custom admin site
admin_site = NoCSRFAdminSite()

# Register OAuth2 provider models
admin_site.register(Application)
