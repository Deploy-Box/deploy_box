from django import forms


class EnvFileUploadForm(forms.Form):
    env_file = forms.FileField()
    framework = forms.ChoiceField(choices=(("mern", "mern"), ("django", "django")))
    select_location = forms.ChoiceField(choices=(("none", "none"), ("frontend", "frontend"), ("backend", "backend"), ("database", "database")), required=False)