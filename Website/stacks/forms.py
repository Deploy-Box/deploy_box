from django import forms


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
