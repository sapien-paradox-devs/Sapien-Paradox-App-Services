from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
import shortuuid
from django.utils import timezone
from django.conf import settings


def generate_token():
    return shortuuid.uuid()

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
    first_name = None
    last_name = None
    
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+\d{1,15}$', message="Phone number must be in E.164 format: +1234567890")]
    )
    full_name = models.CharField(max_length=255)
    
    class Role(models.TextChoices):
        READER = "reader", "Reader"
        ADMIN = "admin", "Admin"
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.READER
    )
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

class Book(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    price_cents = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    order_index = models.IntegerField()  # 1-based
    title = models.CharField(max_length=255)
    shard = models.OneToOneField(Shard, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("book", "order_index")
        ordering = ["order_index"]

    def __str__(self):
        return f"{self.book.title} - Ch {self.order_index}: {self.title}"

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="orders")
    
    class Pace(models.TextChoices):
        CRAWL = "crawl", "Crawl"
        STEADY = "steady", "Steady"
        SOAR = "soar", "Soar"
    
    pace = models.CharField(max_length=10, choices=Pace.choices)
    stripe_session_id = models.CharField(max_length=255, unique=True)
    amount_cents = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.user.email} - {self.book.title}"

class TemporalGrant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grants", null=True, blank=True)
    shard = models.ForeignKey(Shard, on_delete=models.CASCADE, related_name="grants")
    token = models.CharField(max_length=22, unique=True, default=generate_token)
    unlock_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    max_views = models.PositiveIntegerField(default=5)
    current_views = models.PositiveIntegerField(default=0)
    opened_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        now = timezone.now()
        unlocked = self.unlock_at is None or now >= self.unlock_at
        return unlocked and now < self.expires_at and self.current_views < self.max_views

    def __str__(self):
        return f"Grant for {self.shard.title} ({self.token})"
