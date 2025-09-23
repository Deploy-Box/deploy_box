from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.admin import admin_site


urlpatterns = [
    # Main site URLs (frontend)
    path("", include(("main_site.urls", "main_site"), namespace="main_site")),
    # Blogs app URLs
    path("blogs/", include(("blogs.urls", "blogs"), namespace="blogs")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    # Admin interface
    path("admin/", admin_site.urls),
    # API endpoints
    path(
        "api/v1/",
        include(
            [
                # User account management
                path(
                    "accounts/", include(("accounts.urls", "accounts"), namespace="accounts")
                ),
                # Stack management
                path("stacks/", include(("stacks.urls", "stacks"), namespace="stacks")),

                # Project management
                path(
                    "projects/",
                    include(("projects.urls", "projects"), namespace="projects"),
                ),

                # Organization management
                path(
                    "organizations/",
                    include(
                        ("organizations.urls", "organizations"),
                        namespace="organizations",
                    ),
                ),

                # Payment processing
                path(
                    "payments/",
                    include(("payments.urls", "payments"), namespace="payments"),
                ),
                # GitHub integration
                path("github/", include(("github.urls", "github"), namespace="github")),
            ]
        ),
    ),
    # OAuth2 provider
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("programmer_marketplace/", include(("programmer_marketplace.urls", "programmer_marketplace"), namespace="programmer_marketplace"))
]

if settings.DEBUG:
    # In debug mode, serve media files through Django
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Include django_browser_reload for live reloading in development
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
