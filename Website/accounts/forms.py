from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from organizations.models import Organization


class CustomUserCreationForm(UserCreationForm):
    birthdate = forms.DateField()

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "birthdate",
        ]


class OrganizationSignUpForm(forms.ModelForm):
    org_name = forms.CharField()
    org_email = forms.EmailField()


    class Meta:
        model = Organization
        fields = [
            'org_name',
            'org_email'
        ]


