import time
from django import forms

from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from organizations.models import Organization
from organizations.services import create_organization
from accounts.models import UserProfile, User

current_year = time.strftime("%Y")

class CustomUserCreationForm(UserCreationForm):
    birthdate = forms.DateField(
        widget=forms.SelectDateWidget(years=range(int(current_year), 1899, -1)),
    )

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

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            if commit:
                user.save()
                UserProfile.objects.create(user=user, birthdate=self.cleaned_data["birthdate"])
            return user


class OrganizationSignUpForm(forms.ModelForm):
    org_name = forms.CharField()
    org_email = forms.EmailField()


    class Meta:
        model = Organization
        fields = [
            'org_name',
            'org_email'
        ]

    def save(self, commit=True, **kwargs):
        with transaction.atomic():
            user = kwargs.get('user')
            assert user is not None, "User must be provided to create organization"

            org = create_organization(user=user, name = self.cleaned_data['org_name'], email = self.cleaned_data['org_email'])

            return org


