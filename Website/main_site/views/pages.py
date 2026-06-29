import logging
import os

from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.views import View

from main_site.forms import ContactForm
from main_site.utils import send_email

logger = logging.getLogger(__name__)


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


def contact(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message_body = form.cleaned_data["message"]

            notification_emails = os.environ.get(
                "CONTACT_NOTIFICATION_EMAILS", "kalebwbishop@gmail.com"
            )
            to_emails = [e.strip() for e in notification_emails.split(",")]

            html_content = (
                "<body>"
                f"<h2>New Contact Form Submission</h2>"
                f"<p><strong>Name:</strong> {name}</p>"
                f"<p><strong>Email:</strong> {email}</p>"
                f"<p><strong>Subject:</strong> {subject}</p>"
                f"<hr>"
                f"<p>{message_body}</p>"
                "</body>"
            )

            try:
                send_email(
                    to_emails=to_emails,
                    subject=f"Deploy Box Contact: {subject}",
                    html_content=html_content,
                )
                messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
            except Exception:
                logger.exception("Failed to send contact form email")
                messages.error(request, "Something went wrong sending your message. Please try again later.")

            return redirect("contact")
    else:
        form = ContactForm()

    return render(request, "contact.html", {"form": form, "show_footer": False})


def maintenance(request: HttpRequest) -> HttpResponse:
    return render(request, "maintenance.html", {})


def still_configuring(request: HttpRequest) -> HttpResponse:
    return render(request, "still_configuring.html", {"show_footer": False})


def subdomain_not_found(request: HttpRequest) -> HttpResponse:
    subdomain = request.GET.get("subdomain", "")
    return render(request, "subdomain_not_found.html", {"subdomain": subdomain})


def google_verification(request: HttpRequest) -> HttpResponse:
    """Google verification view."""
    # This is a static HTML file for Google Search Console verification
    return render(request, "google_stuff/google0f33857d0e9df9a5.html", content_type="text/html")


def sitemap(request: HttpRequest) -> HttpResponse:
    """Sitemap view."""
    # This is a static XML file for sitemap
    return render(request, "google_stuff/sitemap.xml", content_type="application/xml")


# Documentation pages
def docs(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/docs.html", {"show_footer": False})


def docs_getting_started(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/getting_started.html", {"show_footer": False})


def docs_stacks(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/stacks.html", {"show_footer": False})


def docs_organizations(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/organizations.html", {"show_footer": False})


def docs_projects(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/projects.html", {"show_footer": False})


def docs_billing(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/billing.html", {"show_footer": False})


def docs_api(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/api.html", {"show_footer": False})


class ComponentsView(View):
    """Class-based view for components."""

    def components(self, request: HttpRequest) -> HttpResponse:
        """Components view."""
        return render(request, "components/components.html", {})


components_view = ComponentsView()
