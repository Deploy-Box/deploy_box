from django.shortcuts import render
from accounts.decorators.oauth_required import oauth_required

# Basic Routes
def home(request):
    return render(request, "home.html", {})

def stacks(request):
    return render(request, "stacks.html", {})

def pricing(request):
    return render(request, "pricing.html", {})

def profile(request):
    return render(request, "profile.html", {})

def maintenance(request):
    return render(request, "maintenance.html", {})

@oauth_required
def user_dashboard(request):
    return render(request, "user_dashboard.html", {})