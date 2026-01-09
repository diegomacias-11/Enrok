from django import template

register = template.Library()


@register.filter
def has_group(user, group_name: str) -> bool:
    """
    Devuelve True si el usuario pertenece a un grupo con ese nombre (case-insensitive).
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__iexact=group_name).exists()
