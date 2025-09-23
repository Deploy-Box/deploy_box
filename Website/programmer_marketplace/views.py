from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from .forms import CreateDeveloperForm


#define views here
def developer(request: HttpRequest):
    if request.method == "POST":
        form = CreateDeveloperForm(request.POST)
        if form.is_valid():
            developer = form.save(commit=False)
            developer.user = request.user
            developer.save()
            return redirect("/")
        else:
            return render(request, "developer.html", {"form": form}, status=400)
    else:
        return render(request, "developer.html", {'form': CreateDeveloperForm})
    

def marketplace(request: HttpRequest):
    return render(request, "marketplace.html")