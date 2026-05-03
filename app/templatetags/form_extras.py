from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

register = template.Library()


def _to_decimal(value):
    """Converte valor de template para Decimal (evita float)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Aceita "1234,56" ou "1234.56"
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            return Decimal(s)
        except InvalidOperation:
            return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _format_br(value: Decimal, decimal_places: int) -> str:
    """Formata Decimal no padrão brasileiro: 1.234.567,89"""
    if decimal_places < 0:
        decimal_places = 0
    q = Decimal('1.' + ('0' * decimal_places)) if decimal_places else Decimal('1')
    value = value.quantize(q, rounding=ROUND_HALF_UP)
    neg = value < 0
    value = abs(value)
    # fmt US: grupos com vírgula, decimal com ponto
    fmt = ',' + ('.' + str(decimal_places) + 'f' if decimal_places else '.0f')
    us = format(value, fmt)
    if decimal_places:
        int_part, dec_part = us.split('.')
        int_part = int_part.replace(',', '.')
        out = f'{int_part},{dec_part}'
    else:
        out = us.replace(',', '.')
    return f'-{out}' if neg else out


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
    """Valor monetário no padrão brasileiro: R$ 1.234.567,89"""
    d = _to_decimal(value)
    if d is None:
        return 'R$ 0,00'
    return f'R$ {_format_br(d, 2)}'


@register.filter
def number_br(value, decimals=2):
    """Número no padrão brasileiro (1.234,56). Uso: {{ x|number_br }} ou {{ x|number_br:0 }}."""
    if isinstance(decimals, str):
        try:
            decimals = int(decimals.strip())
        except ValueError:
            decimals = 2
    elif decimals is None:
        decimals = 2
    else:
        try:
            decimals = int(decimals)
        except (TypeError, ValueError):
            decimals = 2

    d = _to_decimal(value)
    if d is None:
        return '0,' + ('0' * decimals) if decimals > 0 else '0'
    return _format_br(d, decimals)


@register.filter
def decimal_hours_as_hm(value):
    """
    Converte horas decimais (ex.: 5,5) em texto '5 h 30 min'.
    Entrada: número ou string numérica; None → '—'.
    """
    if value is None:
        return '—'
    try:
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        else:
            value = float(value)
    except (ValueError, TypeError):
        return '—'
    total_min = int(round(abs(value) * 60))
    h = total_min // 60
    m = total_min % 60
    parts = []
    if h > 0:
        parts.append(f'{h} h')
    if m > 0:
        parts.append(f'{m} min')
    if not parts:
        return '0 min'
    out = ' '.join(parts)
    if value < 0:
        out = f'- {out}'
    return out