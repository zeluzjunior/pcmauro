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


@register.filter
def currency_br(value):
    """Format a number as Brazilian Real currency (R$ 1.234,56)"""
    if value is None:
        return 'R$ 0,00'
    
    try:
        # Convert to float if it's a Decimal or string
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        else:
            value = float(value)
        
        # Format with Brazilian locale: dot for thousands, comma for decimals
        # First format with US locale (comma for thousands, dot for decimals)
        formatted_us = f"{value:,.2f}"
        # Split into integer and decimal parts
        if '.' in formatted_us:
            int_part, dec_part = formatted_us.split('.')
            # Replace comma (thousands separator) with dot
            int_part = int_part.replace(',', '.')
            # Combine with comma as decimal separator
            formatted = f"{int_part},{dec_part}"
        else:
            # No decimal part
            formatted = formatted_us.replace(',', '.')
        
        return f'R$ {formatted}'
    except (ValueError, TypeError):
        return 'R$ 0,00'


@register.filter
def number_br(value, decimals=2):
    """Format a number with Brazilian locale (1.234,56)"""
    if value is None:
        return '0,00' if decimals > 0 else '0'
    
    try:
        # Convert to float if it's a Decimal or string
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        else:
            value = float(value)
        
        # Format with Brazilian locale: dot for thousands, comma for decimals
        # First format with US locale (comma for thousands, dot for decimals)
        if decimals > 0:
            formatted_us = f"{value:,.{decimals}f}"
        else:
            formatted_us = f"{value:,.0f}"
        
        # Split into integer and decimal parts
        if '.' in formatted_us:
            int_part, dec_part = formatted_us.split('.')
            # Replace comma (thousands separator) with dot
            int_part = int_part.replace(',', '.')
            # Combine with comma as decimal separator
            formatted = f"{int_part},{dec_part}"
        else:
            # No decimal part
            formatted = formatted_us.replace(',', '.')
        
        return formatted
    except (ValueError, TypeError):
        return '0,00' if decimals > 0 else '0'