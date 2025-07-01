from django.db import models
from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from core.fields import ShortUUIDField

# Create your models here.

class Prices(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=20)
    price = models.FloatField(default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class usage_information(models.Model):
    id = ShortUUIDField(primary_key=True)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='usage_info')
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE, related_name='usage_info')
    current_usage = models.FloatField(default=0.00)
    monthly_usage = models.FloatField(default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Usage Information"
    
    @classmethod
    def get_total_current_usage_for_organization(cls, organization):
        """Get total current usage for an organization"""
        result = cls.objects.filter(organization=organization).aggregate(
            total_usage=Sum('current_usage')
        )
        return result['total_usage'] or 0.00
    
    @classmethod
    def get_total_monthly_usage_for_organization(cls, organization):
        """Get total monthly usage for an organization"""
        result = cls.objects.filter(organization=organization).aggregate(
            total_monthly=Sum('monthly_usage')
        )
        return result['total_monthly'] or 0.00
    
    @classmethod
    def get_usage_by_stack(cls, organization):
        """Get usage grouped by stack for an organization"""
        return cls.objects.filter(organization=organization).values('stack__name').annotate(
            total_current=Sum('current_usage'),
            total_monthly=Sum('monthly_usage')
        )
    
    @classmethod
    def get_total_usage_summary(cls, organization):
        """Get complete usage summary for an organization"""
        return cls.objects.filter(organization=organization).aggregate(
            total_current=Sum('current_usage'),
            total_monthly=Sum('monthly_usage')
        )
    
    @classmethod
    def get_daily_usage_for_organization(cls, organization, date=None):
        """Get usage for a specific day for an organization"""
        if date is None:
            date = timezone.now().date()
        
        result = cls.objects.filter(
            organization=organization,
            created_at__date=date
        ).aggregate(
            total_current=Sum('current_usage'),
            total_monthly=Sum('monthly_usage')
        )
        return result
    
    @classmethod
    def get_weekly_usage_for_organization(cls, organization, start_date=None):
        """Get usage for the last 7 days for an organization"""
        if start_date is None:
            start_date = timezone.now().date() - timedelta(days=6)
        
        end_date = start_date + timedelta(days=7)
        
        result = cls.objects.filter(
            organization=organization,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        ).aggregate(
            total_current=Sum('current_usage'),
            total_monthly=Sum('monthly_usage'),
            avg_current=Avg('current_usage'),
            avg_monthly=Avg('monthly_usage')
        )
        return result
    
    @classmethod
    def get_monthly_usage_for_organization(cls, organization, year=None, month=None):
        """Get usage for a specific month for an organization"""
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        
        result = cls.objects.filter(
            organization=organization,
            created_at__year=year,
            created_at__month=month
        ).aggregate(
            total_current=Sum('current_usage'),
            total_monthly=Sum('monthly_usage'),
            avg_current=Avg('current_usage'),
            avg_monthly=Avg('monthly_usage'),
            days_count=models.Count('id')
        )
        return result
    
    @classmethod
    def get_yearly_usage_for_organization(cls, organization, year=None):
        """Get usage for a specific year for an organization"""
        if year is None:
            year = timezone.now().year
        
        result = cls.objects.filter(
            organization=organization,
            created_at__year=year
        ).aggregate(
            total_current=Sum('current_usage'),
            total_monthly=Sum('monthly_usage'),
            avg_current=Avg('current_usage'),
            avg_monthly=Avg('monthly_usage'),
            days_count=models.Count('id')
        )
        return result
    
    @classmethod
    def get_usage_trends_by_stack(cls, organization, days=30):
        """Get usage trends by stack for the last N days"""
        start_date = timezone.now().date() - timedelta(days=days)
        
        return cls.objects.filter(
            organization=organization,
            created_at__date__gte=start_date
        ).values('stack__name', 'created_at__date').annotate(
            daily_current=Sum('current_usage'),
            daily_monthly=Sum('monthly_usage')
        ).order_by('stack__name', 'created_at__date')
    
    @classmethod
    def get_latest_usage_for_organization(cls, organization):
        """Get the most recent usage entry for each stack in an organization"""
        return cls.objects.filter(
            organization=organization
        ).values('stack__name').annotate(
            latest_current=models.Subquery(
                cls.objects.filter(
                    organization=models.OuterRef('organization'),
                    stack__name=models.OuterRef('stack__name')
                ).order_by('-created_at').values('current_usage')[:1]
            ),
            latest_monthly=models.Subquery(
                cls.objects.filter(
                    organization=models.OuterRef('organization'),
                    stack__name=models.OuterRef('stack__name')
                ).order_by('-created_at').values('monthly_usage')[:1]
            ),
            last_updated=models.Subquery(
                cls.objects.filter(
                    organization=models.OuterRef('organization'),
                    stack__name=models.OuterRef('stack__name')
                ).order_by('-created_at').values('created_at')[:1]
            )
        )

class billing_history(models.Model):
    class BillingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        
    id = ShortUUIDField(primary_key=True)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='billing_history')
    amount = models.FloatField(default=0.00)
    description = models.CharField(max_length=255, blank=True, null=True)
    billed_usage = models.FloatField(default=0.00)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default=BillingStatus.PENDING, choices=BillingStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Billing History"
