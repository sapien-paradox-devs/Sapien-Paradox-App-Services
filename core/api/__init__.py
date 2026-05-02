from ninja import NinjaAPI
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from ..models import Shard, TemporalGrant
from .auth import router as auth_router
from .grants import router as grants_router

api = NinjaAPI()

api.add_router("/auth", auth_router)
api.add_router("/grants", grants_router)

@api.get("/shards/validate/")
def validate_shard(request, token: str):
    grant = get_object_or_404(TemporalGrant, token=token)
    if grant.is_valid():
        return {
            "status": "valid",
            "shard_id": grant.shard.slug,
            "expires_at": grant.expires_at,
            "title": grant.shard.title
        }
    return {"status": "expired"}

@api.get("/shards/stream/")
def stream_shard(request, token: str):
    grant = get_object_or_404(TemporalGrant, token=token)
    if not grant.is_valid():
        return api.create_response(request, {"detail": "Token expired or invalid"}, status=403)
    
    # Increment view count
    grant.current_views += 1
    grant.save()
    
    return FileResponse(grant.shard.file.open(), content_type="application/pdf")
