from django import forms
from .models import Developer, STACK_EXPERTISE_CHOICES

class CreateDeveloperForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500",
            "rows": 3,
            "placeholder": "Tell us about yourself..."
        })
    )
    stack_expertise = forms.MultipleChoiceField(
        choices=STACK_EXPERTISE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            "class": "space-y-2"
        })
    )
    location = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500",
            "placeholder": "Your location"
        })
    )
    github_profile = forms.URLField(
        widget=forms.URLInput(attrs={
            "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500",
            "placeholder": "https://github.com/your-handle"
        })
    )

    class Meta:
        model = Developer
        fields = ['description', "stack_expertise", "location", "github_profile"]
