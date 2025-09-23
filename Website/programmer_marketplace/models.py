from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField


STACK_EXPERTISE_CHOICES = [
    ('MERN', 'MongoDB, Express, React, Node'),
    ('MEAN', 'MongoDB, Express, Angular, Node'),
    ('MEVN', 'MongoDB, Express, Vue.js, Node'),
    ('LAMP', 'Linux, Apache, MySQL, PHP'),
    ('DJANGO', 'Django, Python, REST Framework'),
]

# Create your models here.
class Developer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = user.description
    stack_expertise = ArrayField(
        models.CharField(max_length=10, choices=STACK_EXPERTISE_CHOICES)
    )
    location = models.CharField(max_length=100)
    github_profile = models.URLField(max_length=200)
