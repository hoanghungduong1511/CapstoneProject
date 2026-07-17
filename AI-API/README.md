# SkinDiseases AI Service

Microservice AI cho hệ thống hỗ trợ chẩn đoán bệnh da liễu.

## 🏗 Architecture

```
Frontend → Backend API (:8000) → AI Service (:8001)
                 ↓                      ↓
              Postgres            AI Models:
              MinIO               ├── Skin Validation (EfficientNet-B0)
                                  └── Segmentation (U-Net + EfficientNet-B3)
```

## 📋 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/health` | Trạng thái service + models |
| `GET` | `/docs` | Swagger UI |
| `POST` | `/api/v1/validate-skin` | Kiểm tra ảnh có phải da người |
| `POST` | `/api/v1/segment` | Phân vùng tổn thương da |
| `POST` | `/api/v1/analyze` | Full pipeline (validate + segment) |
| `GET` | `/api/v1/chat/catalog` | Kho tri thức 10 lớp bệnh da |
| `POST` | `/api/v1/chat/generate` | CSV RAG + OpenAI/mock từ medical context |
| `POST` | `/api/v1/chat` | Endpoint chatbot tương thích dạng stateless |

Chatbot chạy được khi không có `OPENAI_API_KEY`: service dùng mock response có
guardrail để phát triển và kiểm thử. Dữ liệu RAG nằm tại
`data/processed/chatbot/disease_knowledge.csv`.

## 🚀 Chạy Local (Development)

```bash
# 1. Tạo virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Mở Swagger UI: http://localhost:8001/docs

## 🐳 Chạy với Docker

```bash
# Từ thư mục SkinDeseases-API (nơi có docker-compose.yml)
docker compose up ai-service --build

# Hoặc chạy toàn bộ stack
docker compose up --build
```

## 📁 Cấu trúc

```
SkinDeseases-AI-API/
├── ai_models/                   # Model weights + inference pipelines
│   ├── skin_validation/         # EfficientNet-B0 (15.6 MB)
│   └── segmentation/            # U-Net + EfficientNet-B3 (50.8 MB)
├── app/                         # FastAPI application
│   ├── main.py                  # App entry point + lifespan
│   ├── config.py                # Settings
│   ├── api/v1/endpoints/        # API endpoints
│   ├── schemas/                 # Pydantic response models
│   └── services/                # Model manager
├── Dockerfile
├── requirements.txt
└── .env
```
