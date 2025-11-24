from django import template

register = template.Library()


@register.filter
def is_required(field):
    """Check if a form field is required"""
    if hasattr(field, 'field'):
        return field.field.required
    return False


@register.filter
def get_field_errors(field):
    """Get all errors for a field"""
    if hasattr(field, 'errors'):
        return field.errors
    return []


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
