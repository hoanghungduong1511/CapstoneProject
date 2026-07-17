# SkinDiseases API

Backend API cho hệ thống quản lý bệnh da liễu — Đồ án tốt nghiệp.

## Tech Stack

- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL 16
- **ORM:** SQLAlchemy 2.0
- **Migration:** Alembic
- **Auth:** JWT (python-jose) + bcrypt
- **Docs:** Swagger UI + ReDoc (tích hợp sẵn)
- **Container:** Docker + Docker Compose

## Cấu trúc thư mục

```
app/
├── main.py                  # Entry point
├── core/
│   ├── config.py            # Settings (đọc từ .env)
│   └── security.py          # JWT & Password hashing
├── api/
│   └── v1/
│       ├── endpoints/
│       │   └── auth.py      # Auth endpoints
│       └── api.py           # Router aggregator
├── schemas/
│   └── auth.py              # Pydantic schemas
├── models/
│   └── user.py              # SQLAlchemy models
├── db/
│   ├── base.py              # Declarative Base
│   └── session.py           # Engine & Session
└── services/
    └── auth_service.py      # Business logic
```

## Chạy với Docker (Khuyến nghị) 

```bash
# 1. Sao chép file environment
cp .env.example .env

# 2. Build và chạy tất cả services
docker-compose up -d --build

# 3. Xem logs
docker-compose logs -f api
```

Sau khi chạy, truy cập:
- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **pgAdmin:** http://localhost:5050 (Email: admin@admin.com / Pass: admin)

## Chạy local (Không Docker)

```bash
# 1. Tạo virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Cấu hình .env (đổi POSTGRES_HOST=localhost)
cp .env.example .env

# 4. Chạy server
uvicorn app.main:app --reload --port 8000
```

## Docker Helper Scripts

```bash
bash scripts/docker.sh build           # Build images
bash scripts/docker.sh up              # Start services
bash scripts/docker.sh down            # Stop services
bash scripts/docker.sh logs            # Xem logs API
bash scripts/docker.sh db-shell        # Mở PostgreSQL shell
bash scripts/docker.sh migrate         # Chạy migration
bash scripts/docker.sh makemigrations  # Tạo migration mới
bash scripts/docker.sh clean           # Xoá tất cả (kể cả data)
```

## API Endpoints

| Method | Endpoint              | Mô tả                       | Auth |
|--------|-----------------------|------------------------------|------|
| GET    | `/`                   | Health check                 | ❌    |
| POST   | `/api/v1/auth/register` | Đăng ký tài khoản           | ❌    |
| POST   | `/api/v1/auth/login`    | Đăng nhập                   | ❌    |
| POST   | `/api/v1/auth/refresh`  | Làm mới token               | ❌    |
| GET    | `/api/v1/auth/me`       | Thông tin người dùng hiện tại | ✅    |

## Alembic Migration

```bash
# Tạo migration mới
alembic revision --autogenerate -m "mô tả thay đổi"

# Chạy migration
alembic upgrade head

# Rollback
alembic downgrade -1
```
