from django import template

register = template.Library()


@register.filter
def vnd(value):
    """
    Định dạng tiền Việt Nam.
    Ví dụ:
    100000 -> 100.000
    1290000 -> 1.290.000
    """

    if value is None or value == "":
        return "0"

    try:
        value = int(value)
    except (ValueError, TypeError):
        return value

    return f"{value:,}".replace(",", ".")