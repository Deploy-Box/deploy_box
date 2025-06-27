from django import forms

from .models import Project, ProjectMember # type: ignor
from organizations.models import Organization, OrganizationMember
from accounts.models import UserProfile

class ProjectCreateForm(forms.ModelForm): # type: ignore
    name = forms.CharField()
    description = forms.CharField()
    organization = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Project
        fields = ['name', 'description', 'organization']

class ProjectSettingsForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
            'placeholder': 'Enter project name'
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
            'rows': '4',
            'placeholder': 'Enter project description'
        })
    )

    class Meta:
        model = Project
        fields = ['name', 'description']

class ProjectMemberForm(forms.ModelForm):
    member = forms.CharField(max_length=100, required=False)
    ROLE_CHOICES = [('Admin', 'admin'), ('Member', 'member'),]
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = ProjectMember
        fields = ['member', 'role']

class ProjectCreateFormWithMembers(forms.Form):
    project = ProjectCreateForm()
    members = ProjectMemberForm()
