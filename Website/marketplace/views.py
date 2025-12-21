from django.shortcuts import render, get_object_or_404, redirect
from .models import DeveloperProfile
from stacks.models import PurchasableStack

def marketplace_home(request):
    """
    Lists all available experts.
    Support filtering by stack type via query parameter ?stack=type
    """
    stack_filter = request.GET.get('stack')
    developers = DeveloperProfile.objects.filter(is_available=True)
    
    if stack_filter:
        developers = developers.filter(specializations__type=stack_filter).distinct()

    # Get all distinct stack types for the filter dropdown/list
    stack_types = PurchasableStack.objects.values_list('type', flat=True).distinct()
    
    # Check if current user is already a developer
    is_developer = False
    if request.user.is_authenticated:
        is_developer = DeveloperProfile.objects.filter(user=request.user).exists()

    context = {
        "developers": developers,
        "stack_types": stack_types,
        "current_filter": stack_filter,
        "bg_dark": True,
        "is_developer": is_developer,
    }
    return render(request, "marketplace/index.html", context)


def developer_detail(request, profile_id):
    """
    Detailed view for a specific developer.
    """
    developer = get_object_or_404(DeveloperProfile, id=profile_id)
    return render(request, "marketplace/developer_detail.html", {"developer": developer, "bg_dark": True})


def register_developer(request):
    """
    Registration form for users to become developers on the marketplace.
    """
    # Check if user is already a developer
    if request.user.is_authenticated:
        try:
            existing_profile = DeveloperProfile.objects.get(user=request.user)
            # Redirect to their profile if they're already registered
            return redirect('main_site:marketplace:profile_detail', profile_id=existing_profile.id)
        except DeveloperProfile.DoesNotExist:
            pass
    
    if request.method == 'POST':
        from .forms import DeveloperProfileForm
        form = DeveloperProfileForm(request.POST)
        
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            form.save_m2m()  # Save the many-to-many specializations
            
            # Redirect to the new developer profile
            return redirect('main_site:marketplace:profile_detail', profile_id=profile.id)
    else:
        from .forms import DeveloperProfileForm
        form = DeveloperProfileForm()
    
    context = {
        "form": form,
        "bg_dark": True,
    }
    return render(request, "marketplace/register.html", context)
