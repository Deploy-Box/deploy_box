from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include(("main_site.urls", "main_site"), "main_site")),
    path("admin/", admin.site.urls),
    path("api/accounts/", include(("accounts.urls", "accounts"), "accounts")),
    path("api/stack/", include(("api.urls", "api"), "stack")),
    path("api/payments/", include(("payments.urls", "payments"), "payments")),
    path("api/github/", include(("github.urls", "github"), "github")),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]

if settings.DEBUG:
    # In debug mode, serve media files through Django
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Include django_browser_reload for live reloading in development
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]