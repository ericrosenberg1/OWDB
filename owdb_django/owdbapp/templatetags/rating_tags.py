"""
Template tag: render the favorite/rating widget on a gated entity's detail
page.

Backed by UserRating (models.py), which associates to an entity through a
hand-rolled (entity_type, entity_id) pair rather than Django's contenttypes
GenericForeignKey. Looks up the current viewer's own UserRating row (if any)
for the entity and hands it to partials/rating_widget.html, which renders a
favorite toggle and a 1-10 rating control. Both controls post to
`views.rate_entity` — the widget itself never writes anything.

Renders nothing for anonymous visitors: favoriting/rating is a logged-in
feature (see the OWDB Playbook, "Filling the Card").
"""

from __future__ import annotations

from django import template

from ..models import UserRating

register = template.Library()


@register.inclusion_tag("partials/rating_widget.html", takes_context=True)
def rating_widget(context, entity, entity_type):
    """
    Usage: {% load rating_tags %} ... {% rating_widget wrestler "wrestler" %}

    `entity_type` must be one of UserRating.ENTITY_TYPE_CHOICES (also
    mirrored in views.RATING_ENTITY_MODELS) — it's the value stored on the
    UserRating row and posted back by the widget's form.
    """
    request = context.get("request")
    user = getattr(request, "user", None)
    is_authenticated = bool(user and user.is_authenticated)

    user_rating = None
    if is_authenticated:
        user_rating = UserRating.objects.filter(
            user=user, entity_type=entity_type, entity_id=entity.pk
        ).first()

    return {
        "request": request,
        "is_authenticated": is_authenticated,
        "entity_type": entity_type,
        "entity_id": entity.pk,
        "user_rating": user_rating,
        "rating_range": range(1, 11),
    }
