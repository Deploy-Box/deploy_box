from django.shortcuts import render
from .models import BlogPost
from django.views.generic import ListView, DetailView

# Create your views here.

class BlogPostListView(ListView):
    model = BlogPost
    template_name = "blogpost_list.html"
    context_object_name = "blogposts"

class BlogPostDetailView(DetailView):
    model = BlogPost
    template_name = "blogpost_detail.html"
    context_object_name = "blogpost"
