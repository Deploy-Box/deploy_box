
from django.db import models

TYPE_CHOICES = [
	('RESOURCE', 'Resource'),
	('DATA', 'Data'),
]

class BaseResourceModel(models.Model):
	index = models.IntegerField(default=0)
	name = models.CharField(max_length=255)
	type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='RESOURCE')
	stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
