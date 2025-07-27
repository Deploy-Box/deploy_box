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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = kwargs.get("queryset", None) or self.model._meta.get_field("author").remote_field.model.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(BlogPost, BlogPostAdmin)
