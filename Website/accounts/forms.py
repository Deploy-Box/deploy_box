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
        widget=forms.SelectDateWidget(
            years=range(int(current_year), 1899, -1),
            empty_label=("Year", "Month", "Day"),
            attrs={"class": "border rounded-lg px-3 py-2 mt-1 mb-5 text-sm w-full"},
        ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": "border rounded-lg px-3 py-2 mt-1 mb-5 text-sm w-full"}
            )

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            if commit:
                user.save()
                UserProfile.objects.create(
                    user=user, birthdate=self.cleaned_data["birthdate"]
                )
            return user


class OrganizationSignUpForm(forms.ModelForm):
    org_name = forms.CharField()
    org_email = forms.EmailField()

    class Meta:
        model = Organization
        fields = ["org_name", "org_email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": "border rounded-lg px-3 py-2 mt-1 mb-5 text-sm w-full"}
            )

    def save(self, commit=True, **kwargs):
        with transaction.atomic():
            user = kwargs.get("user")
            assert user is not None, "User must be provided to create organization"

            org = create_organization(
                user=user,
                name=self.cleaned_data["org_name"],
                email=self.cleaned_data["org_email"],
            )

            return org
