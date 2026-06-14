from django import template
from ..models import Follow
from django.contrib.auth.models import AnonymousUser

register = template.Library()

@register.filter
def is_following(user, this_user):
    """Check if user follows this_user - usage: {{ user|is_following:this_user }}"""
    # Handle None or AnonymousUser
    if not user or not user.is_authenticated:
        return False
    
    # Unwrap SimpleLazyObject if needed
    if hasattr(user, '_wrapped'):
        user = user._wrapped
    if hasattr(this_user, '_wrapped'):
        this_user = this_user._wrapped
    
    # Final safety check
    if not hasattr(user, 'pk') or not user.pk or isinstance(user, AnonymousUser):
        return False
    
    return Follow.objects.filter(follower=user, following=this_user).exists()