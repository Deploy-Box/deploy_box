from django import forms
from .models import Stack


class EnvFileUploadForm(forms.Form):
    env_file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".env",
                "class": "hidden",
            }
        )
    )
    framework = forms.ChoiceField(
        choices=(("mern", "mern"), ("django", "django")),
        widget=forms.Select(
            attrs={
                "class": "w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent"
            }
        ),
    )
    select_location = forms.ChoiceField(
        choices=(
            ("none", "none"),
            ("frontend", "frontend"),
            ("backend", "backend"),
            ("database", "database"),
        ),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent"
            }
        ),
    )


class StackSettingsForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
            'placeholder': 'Enter stack name'
        })
    )

    class Meta:
        model = Stack
        fields = ['name']


class EnvironmentVariablesForm(forms.Form):
    env_variables = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent font-mono text-sm',
            'rows': '15',
            'placeholder': 'KEY1=value1\nKEY2=value2\nKEY3=value3'
        }),
        required=False,
        help_text="Enter environment variables in KEY=value format, one per line"
    )
    
    env_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'accept': '.env'
        }),
        required=False,
        help_text="Upload a .env file as an alternative to manual entry"
    )
