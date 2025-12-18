from django import template

from ..linking import build_about_with_links, build_linked_from_summary

register = template.Library()


@register.filter
def about_with_links(obj):
    """Append linked-from context to the about text for display."""
    return build_about_with_links(obj)


@register.filter
def linked_from(obj):
    """Return only the linked-from summary (without the about body)."""
    return build_linked_from_summary(obj)
