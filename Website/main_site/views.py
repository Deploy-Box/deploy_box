from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from accounts.forms import CustomUserCreationForm as form

from core.decorators import oauth_required

# Basic Routes
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html", {})

def stacks(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks.html", {})

def pricing(request: HttpRequest) -> HttpResponse:
    return render(request, "pricing.html", {})

def profile(request: HttpRequest) -> HttpResponse:
    return render(request, "profile.html", {})

def maintenance(request: HttpRequest) -> HttpResponse:
    return render(request, "maintenance.html", {})

# Authentication Routes
def login(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/login.html", {})

def signup(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/signup.html", {'form': form})

def logout(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/logout.html", {})  

# Payment Routes
STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)

@oauth_required()
def home_page_view(request: HttpRequest) -> HttpResponse:
    return render(request, "payments/home.html")

@oauth_required()
def add_card_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "payments/add-card.html",
        {"stripe_publishable_key": STRIPE_PUBLISHABLE_KEY},
    )

@oauth_required()
def success_view(request: HttpRequest) -> HttpResponse:
    return render(request, "payments/success.html")

@oauth_required()
def cancelled_view(request: HttpRequest) -> HttpResponse:
    return render(request, "payments/cancelled.html")

