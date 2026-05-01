from django.db import models
import shortuuid
from django.utils import timezone
from datetime import timedelta

class Lead(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    book_id = models.CharField(max_length=100)
    book_title = models.CharField(max_length=255)
    pace = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.book_title}"

class Shard(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    file = models.FileField(upload_to="shards/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TemporalGrant(models.Model):
    shard = models.ForeignKey(Shard, on_delete=models.CASCADE, related_name="grants")
    token = models.CharField(max_length=22, unique=True, default=shortuuid.uuid)
    expires_at = models.DateTimeField()
    max_views = models.PositiveIntegerField(default=5)
    current_views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() < self.expires_at and self.current_views < self.max_views

    def __str__(self):
        return f"Grant for {self.shard.title} ({self.token})"
