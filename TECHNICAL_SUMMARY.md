# Technical Summary: Backend (Temporal Engine)

This document outlines the Django-based architecture for the Sapien Paradox platform.

## 🏛️ Architecture Overview
The backend is a Service-Oriented Django application using **Django Ninja** for high-performance, type-safe API delivery.

## 💾 Data Architecture (`core/models.py`)
- **`User`**: Custom user model extending `AbstractUser`. Uses `email` as the primary identifier. Stores `phone`, `full_name`, and `role`.
- **`Shard`**: The fundamental unit of modular content. Maps to a physical PDF/Media file.
- **`TemporalGrant`**: The security gateway. Implements:
    - `token`: Secure, short-form URL identifier (`shortuuid`).
    - `expires_at`: Hard time-based expiration.
    - `max_views`: Count-based access restriction.
    - `is_valid()`: Centralized logic for access validation.

## 🔌 API Layer (`core/api/`)
- **Authentication**: Session-based auth via `/api/auth/login` and `/api/auth/logout`.
- **Type-Safety**: Uses Pydantic schemas (in `core/schemas/`) for strict request/response validation.
- **Secure Streaming**: The `/api/shards/stream/` endpoint uses Django's `FileResponse`. This prevents the client from ever seeing the actual storage location of the PDF, serving it instead as a direct binary stream.

## ⚙️ Core Configurations
- **CORS**: Configured in `settings.py` via `django-cors-headers` to allow seamless interaction with the Vite/React frontend.
- **Session Security**: Configured for local dev with `Lax` same-site and `HttpOnly` cookies.
- **Media Management**: Centralized `MEDIA_ROOT` for managing uploaded Shard assets.

## 🛠️ Commands
- `python3 manage.py runserver`: Local development (Port 8000).
- `python3 manage.py makemigrations core && python3 manage.py migrate`: Schema updates.
- `python3 manage.py test core`: Run backend tests.
