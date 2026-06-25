from django import template
from django.core.files.storage import default_storage

register = template.Library()

@register.filter
def has_image(post):
    """Check if post has a valid image file"""
    try:
        if post.image and post.image.name:
            return default_storage.exists(post.image.name)
    except (ValueError, OSError, AttributeError):
        pass
    return False