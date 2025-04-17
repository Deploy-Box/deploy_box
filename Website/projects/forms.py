from django import forms

from .models import Project, ProjectMember # type: ignor
from organizations.models import Organization, OrganizationMember
from accounts.models import User

class ProjectCreateForm(forms.ModelForm): # type: ignore
    name = forms.CharField()
    description = forms.CharField()
    organization = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Project
        fields = ['name', 'description', 'organization']

class ProjectMemberForm(forms.ModelForm):
    member = forms.CharField(max_length=100)
    ROLE_CHOICES = [('Admin', 'admin'), ('Member', 'member'),]
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = ProjectMember
        fields = ['member', 'role']

class ProjectCreateFormWithMembers(forms.Form):
    project = ProjectCreateForm()
    members = ProjectMemberForm()
