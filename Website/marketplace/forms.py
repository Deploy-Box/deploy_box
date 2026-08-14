from django import forms
from .models import DeveloperProfile
from stacks.models import PurchasableStack


class DeveloperProfileForm(forms.ModelForm):
    """Form for creating/editing developer profiles"""
    
    class Meta:
        model = DeveloperProfile
        fields = [
            'tagline',
            'bio',
            'hourly_rate',
            'specializations',
            'is_available',
            'github_url',
            'linkedin_url',
            'website_url',
        ]
        widgets = {
            'tagline': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500',
                'placeholder': 'e.g., Full-Stack JavaScript Expert'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500',
                'rows': 5,
                'placeholder': 'Tell us about your expertise, experience, and what makes you unique...'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500',
                'placeholder': '125.00',
                'step': '0.01'
            }),
            'specializations': forms.CheckboxSelectMultiple(attrs={
                'class': 'text-emerald-500 focus:ring-emerald-500 bg-zinc-900 border-zinc-700'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-emerald-500 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500 focus:ring-2'
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500',
                'placeholder': 'https://github.com/yourusername'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500',
                'placeholder': 'https://linkedin.com/in/yourprofile'
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 bg-zinc-950/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500',
                'placeholder': 'https://yourwebsite.com'
            }),
        }
        labels = {
            'tagline': 'Professional Headline',
            'bio': 'About You',
            'hourly_rate': 'Hourly Rate ($)',
            'specializations': 'Your Stack Expertise',
            'is_available': 'Available for new projects',
            'github_url': 'GitHub Profile (Optional)',
            'linkedin_url': 'LinkedIn Profile (Optional)',
            'website_url': 'Personal Website (Optional)',
        }
        help_texts = {
            'tagline': 'A short, catchy description of your expertise (e.g., "Full-Stack MERN Expert")',
            'bio': 'Describe your experience, skills, and what makes you stand out',
            'hourly_rate': 'Your standard hourly rate in USD',
            'specializations': 'Select all technology stacks you specialize in',
        }
