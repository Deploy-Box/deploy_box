from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views import View


# Basic Routes
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html", {"show_footer": False})


def stacks(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks.html", {"show_footer": False})


def mern_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mern_stack.html", {"show_footer": False})


def django_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/django_stack.html", {"show_footer": False})


def mean_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mean_stack.html", {"show_footer": False})


def lamp_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/lamp_stack.html", {"show_footer": False})


def mevn_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mevn_stack.html", {"show_footer": False})


def mobile_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mobile_stack.html", {"show_footer": False})


def llm_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/llm_stack.html", {"show_footer": False})


def ai_data_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/ai_data_stack.html", {"show_footer": False})


def computer_vision_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/computer_vision_stack.html", {"show_footer": False})


def image_generation_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/image_generation_stack.html", {"show_footer": False})


def ai_agents_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/ai_agents_stack.html", {"show_footer": False})


def pricing(request: HttpRequest) -> HttpResponse:
    return render(request, "pricing.html", {"show_footer": False})


def profile(request: HttpRequest) -> HttpResponse:
    github_linked = False
    github_username = None
    if request.user.is_authenticated:
        from github.models import Token
        token = Token.objects.filter(user=request.user).first()
        if token:
            github_linked = True
            github_user = request.session.get("github_user")
            if github_user:
                github_username = github_user.get("login")
    return render(request, "profile.html", {
        "show_footer": False,
        "github_linked": github_linked,
        "github_username": github_username,
    })


def maintenance(request: HttpRequest) -> HttpResponse:
    return render(request, "maintenance.html", {})


def still_configuring(request: HttpRequest) -> HttpResponse:
    return render(request, "still_configuring.html", {"show_footer": False})


def subdomain_not_found(request: HttpRequest) -> HttpResponse:
    return render(request, "subdomain_not_found.html")


def google_verification(request: HttpRequest) -> HttpResponse:
    """Google verification view."""
    # This is a static HTML file for Google Search Console verification
    return render(request, "google_stuff/google0f33857d0e9df9a5.html", content_type="text/html")


def sitemap(request: HttpRequest) -> HttpResponse:
    """Sitemap view."""
    # This is a static XML file for sitemap
    return render(request, "google_stuff/sitemap.xml", content_type="application/xml")


class ComponentsView(View):
    """Class-based view for components."""

    def components(self, request: HttpRequest) -> HttpResponse:
        """Components view."""
        return render(request, "components/components.html", {})


components_view = ComponentsView()
