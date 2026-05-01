from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Shard, TemporalGrant, Book, Chapter, Order

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "phone", "role", "is_staff")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "phone", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "phone", "role", "password", "is_staff", "is_superuser"),
        }),
    )
    search_fields = ("email", "full_name", "phone")

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "price_cents")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("book", "order_index", "title", "shard")
    list_filter = ("book",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "pace", "amount_cents", "created_at")
    list_filter = ("book", "pace")
    search_fields = ("user__email", "stripe_session_id")

@admin.register(Shard)
class ShardAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created_at")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(TemporalGrant)
class TemporalGrantAdmin(admin.ModelAdmin):
    list_display = ("shard", "token", "expires_at", "current_views", "max_views")
    list_filter = ("shard", "expires_at")
    search_fields = ("token",)
