from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import shortuuid
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)  # E.164 format: +1234567890
    full_name = models.CharField(max_length=255)
    
    class Role(models.TextChoices):
        READER = "reader", "Reader"
        ADMIN = "admin", "Admin"
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.READER
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone"]

    def __str__(self):
        return self.email

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
