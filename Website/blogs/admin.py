from django.contrib import admin
from .models import BlogPost

# Register your models here.

class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content')
    list_filter = ('author', 'created_at')
    ordering = ('-created_at',)
    fields = ('title', 'slug', 'content', 'author', 'tags')

admin.site.register(BlogPost, BlogPostAdmin)
