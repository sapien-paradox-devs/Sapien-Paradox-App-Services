from datetime import datetime
from ninja import NinjaAPI, Schema
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from .models import Lead, Shard, TemporalGrant
from typing import List

api = NinjaAPI()

class LeadIn(Schema):
    full_name: str
    email: str
    book_id: str
    book_title: str
    pace: str
    notes: str = ""

class LeadOut(Schema):
    id: int
    full_name: str
    created_at: datetime

@api.post("/leads/", response=LeadOut)
def create_lead(request, data: LeadIn):
    lead = Lead.objects.create(**data.dict())
    return lead

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
