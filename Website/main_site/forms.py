from django import forms

INPUT_CLASS = (
    "w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg "
    "text-white placeholder-zinc-500 focus:outline-none focus:ring-2 "
    "focus:ring-emerald-500/50 focus:border-emerald-500"
)


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Your name",
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "you@example.com",
        }),
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "How can we help?",
        }),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": INPUT_CLASS,
            "rows": 5,
            "placeholder": "Tell us more...",
        }),
    )
