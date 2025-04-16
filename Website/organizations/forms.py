from django import forms

from .models import Organization, OrganizationMember # type: ignore
from accounts.models import User

class OrganizationCreateForm(forms.ModelForm): # type: ignore
    name = forms.CharField()
    email = forms.EmailField()

    class Meta:
        model = Organization
        fields = ['name', 'email']

class OrganizationMemberForm(forms.ModelForm):
    member = forms.CharField(max_length=100)
    ROLE_CHOICES = [('Admin', 'admin'), ('Member', 'member'),]
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = OrganizationMember
        fields = ['member', 'role']

class OrganizationCreateFormWithMembers(forms.Form):
    organization = OrganizationCreateForm()
    members = OrganizationMemberForm()