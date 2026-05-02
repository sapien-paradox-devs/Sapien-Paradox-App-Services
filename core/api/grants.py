from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from ..models import TemporalGrant, Chapter
from ..schemas.auth import ErrorOut
from ..schemas.grants import GrantOut

# Token-only auth per cross-cutting decision #10: anyone holding the token
# can read; we deliberately ignore TemporalGrant.user on these endpoints.
router = Router()


def _classify(grant: TemporalGrant):
    """Return ('valid'|'locked'|'expired_or_exhausted', None)."""
    now = timezone.now()
    if grant.unlock_at is not None and now < grant.unlock_at:
        return "locked"
    if now >= grant.expires_at or grant.current_views >= grant.max_views:
        return "expired_or_exhausted"
    return "valid"


@router.get("/{token}", response={200: GrantOut, 403: ErrorOut, 404: ErrorOut})
def get_grant(request: HttpRequest, token: str):
    grant = TemporalGrant.objects.select_related("shard").filter(token=token).first()
    if grant is None:
        return 404, {"detail": "grant not found"}

    state = _classify(grant)
    if state == "locked":
        return 403, {"detail": "grant locked"}
    if state == "expired_or_exhausted":
        return 404, {"detail": "grant expired"}

    chapter = Chapter.objects.select_related("book").filter(shard=grant.shard).first()
    if chapter is None:
        return 404, {"detail": "grant has no chapter"}

    return 200, {
        "chapter": {
            "title": chapter.title,
            "order_index": chapter.order_index,
            "book_title": chapter.book.title,
        },
        "shard_id": grant.shard.slug,
        "opened_at": grant.opened_at,
    }


@router.post("/{token}/open", response={200: dict, 403: ErrorOut, 404: ErrorOut})
def open_grant(request: HttpRequest, token: str):
    grant = TemporalGrant.objects.filter(token=token).first()
    if grant is None:
        return 404, {"detail": "grant not found"}

    state = _classify(grant)
    if state == "locked":
        return 403, {"detail": "grant locked"}
    if state == "expired_or_exhausted":
        return 404, {"detail": "grant expired"}

    if grant.opened_at is None:
        grant.opened_at = timezone.now()
        grant.save(update_fields=["opened_at"])

    return 200, {}
