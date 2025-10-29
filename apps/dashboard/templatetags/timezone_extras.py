"""
Custom template filters for timezone handling.
"""
from django import template
from django.utils import timezone
import pytz

register = template.Library()

@register.filter
def qld_timezone(value):
    """
    Convert a datetime to Queensland timezone and format with dynamic timezone abbreviation.
    Usage: {{ datetime|qld_timezone }}
    """
    if not value:
        return ''
    
    qld_tz = pytz.timezone('Australia/Brisbane')
    localized_time = value.astimezone(qld_tz)
    return localized_time.strftime('%d-%m-%Y %H:%M %Z')

@register.filter
def qld_timezone_full(value):
    """
    Convert a datetime to Queensland timezone with full timestamp and dynamic timezone abbreviation.
    Usage: {{ datetime|qld_timezone_full }}
    """
    if not value:
        return ''
    
    qld_tz = pytz.timezone('Australia/Brisbane')
    localized_time = value.astimezone(qld_tz)
    return localized_time.strftime('%d-%m-%Y %H:%M:%S %Z')