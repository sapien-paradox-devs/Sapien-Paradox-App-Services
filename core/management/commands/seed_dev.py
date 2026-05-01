import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from core.models import User, Book, Chapter, Shard
from django.conf import settings

class Command(BaseCommand):
    help = "Seeds the database with development data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")

        # 1. Create a dummy user
        user, created = User.objects.get_or_create(
            email="dev@example.com",
            defaults={
                "full_name": "Dev User",
                "phone": "+1234567890",
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            self.stdout.write(f"Created user: {user.email}")

        # 2. Create dummy book
        book, created = Book.objects.get_or_create(
            slug="sapien-paradox",
            defaults={
                "title": "The Sapien Paradox",
                "price_cents": 1900,
            }
        )
        if created:
            self.stdout.write(f"Created book: {book.title}")

        # 3. Create dummy chapters and shards
        for i in range(1, 6):
            shard_slug = f"shard-{i}"
            shard, created = Shard.objects.get_or_create(
                slug=shard_slug,
                defaults={
                    "title": f"Shard {i} PDF Content",
                }
            )
            
            if created:
                # Create a tiny dummy PDF file
                dummy_content = b"%PDF-1.1\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000062 00000 n\n0000000117 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
                shard.file.save(f"{shard_slug}.pdf", ContentFile(dummy_content))
                shard.save()
                self.stdout.write(f"Created shard: {shard.slug}")

            chapter, created = Chapter.objects.get_or_create(
                book=book,
                order_index=i,
                defaults={
                    "title": f"Chapter {i}: The Beginning of Part {i}",
                    "shard": shard,
                }
            )
            if created:
                self.stdout.write(f"Created chapter {i}: {chapter.title}")

        self.stdout.write(self.style.SUCCESS("Successfully seeded development data"))
