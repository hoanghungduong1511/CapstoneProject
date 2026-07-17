# SkinDiseases-AI

<p align="center">
  <strong>An Intelligent Skin Disease Analysis and Consultation System Powered by Computer Vision and Large Language Models.</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="#system-features">Features</a> ·
  <a href="#ai-pipeline">AI Pipeline</a> ·
  <a href="#system-architecture">Architecture</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#about-me">About</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" />
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img alt="Redis" src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img alt="AWS" src="https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white" />
  <img alt="OpenAI" src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" />
  <img alt="Gemini" src="https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

---

## Table of Contents

- [Overview](#overview)
- [System Features](#system-features)
- [AI Pipeline](#ai-pipeline)
- [Machine Learning Models](#machine-learning-models)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Demo](#demo)
- [Results](#results)
- [Key Learnings](#key-learnings)
- [Future Improvements](#future-improvements)
- [About Me](#about-me)

## Overview

SkinDiseases-AI is a graduation capstone project that explores how modern AI systems can support early skin disease screening and patient consultation from images. Skin conditions are increasingly common, while initial assessment often depends on access to dermatology specialists. This creates a practical need for intelligent systems that can assist users with preliminary analysis, structured explanations, and medical guidance.

The project combines Computer Vision, backend engineering, and Retrieval-Augmented Generation (RAG) into a production-style microservices architecture. It supports lesion segmentation, skin disease classification, AI-powered consultation, analysis history, and user management through a modern web application.

> Medical disclaimer: this system is designed to support preliminary screening and education. It does not replace professional medical diagnosis, treatment, or consultation with a qualified dermatologist.

## System Features

### Authentication

- JWT-based authentication for secure API access.
- Google OAuth login for a smoother user onboarding flow.
- Role-based authorization for user and administrator workflows.

### AI Analysis

- Upload and validate skin lesion images.
- Segment lesion regions using a deep learning segmentation model.
- Classify skin disease categories using transfer learning.
- Return confidence scores and structured prediction metadata.
- Visualize AI outputs to make results easier to interpret.

### AI Consultation

- Medical chatbot for follow-up questions and contextual guidance.
- Retrieval-Augmented Generation pipeline over a curated medical knowledge base.
- Context-aware responses grounded in retrieved disease information.
- Safety-oriented response generation for medical consultation scenarios.

### User Management

- Profile management and account information updates.
- Analysis history for previous image submissions and AI results.
- Chat history for consultation continuity.

### Admin Dashboard

- User management for administrative workflows.
- Monitoring and operational visibility.
- Analytics-oriented views for system usage and activity.

## AI Pipeline

The core AI workflow is designed as a multi-stage pipeline that transforms an input skin image into an interpretable analysis result and consultation context.

```mermaid
flowchart LR
    A[Input Skin Image] --> B[Image Preprocessing]
    B --> C[Lesion Segmentation Model]
    C --> D[Lesion Mask and Cropping]
    D --> E[Disease Classification Model]
    E --> F[Result Aggregation]
    F --> G[RAG Chatbot Context]
    G --> H[Final Recommendation]
```

Pipeline stages:

1. The user uploads a skin image through the web application.
2. The backend validates the image and forwards it to the AI service.
3. The segmentation model identifies the lesion area.
4. The lesion region is cropped or highlighted for downstream analysis.
5. The classification model predicts the most likely disease category.
6. The system aggregates confidence scores, metadata, and visualization outputs.
7. The chatbot retrieves relevant medical context from the knowledge base.
8. The user receives an AI-assisted explanation and recommendation.

## Machine Learning Models

### Segmentation

- U-Net-based segmentation architecture.
- EfficientNet-B3 encoder for stronger visual feature extraction.
- Dice Loss + Binary Cross Entropy Loss for lesion mask optimization.
- Fine-tuning strategy for medical image segmentation.
- Trained and evaluated with ISIC 2018 dataset resources.

### Classification

- Custom EfficientNet-B0 classifier.
- Transfer learning from pretrained visual backbones.
- Fine-tuning for skin disease recognition.
- Multi-dataset training strategy using:
  - HAM10000
  - PAD-UFES-20
  - DermNet

### Chatbot

- Retrieval-Augmented Generation pipeline.
- Vector search over medical knowledge chunks.
- LLM integration for natural language consultation.
- Medical context retrieval to improve factual grounding.
- Safety-focused prompting for healthcare-related responses.

## System Architecture

SkinDiseases-AI is organized as a monorepo with microservices. The frontend communicates with the main backend API, while AI-specific inference and chatbot workloads are isolated in a dedicated AI service.

```mermaid
flowchart TD
    U[User] --> C[Client Browser]
    C --> FE[Frontend Web App<br/>Next.js]
    FE --> API[Main Backend API<br/>FastAPI]
    API --> AI[AI Inference and Chatbot Service<br/>FastAPI]
    API --> DB[(PostgreSQL)]
    API --> Redis[(Redis)]
    API --> OBJ[(Object Storage / MinIO)]
    AI --> VDB[(Vector Database)]
    AI --> LLM[LLM Providers<br/>OpenAI / Gemini]
    AI --> Models[PyTorch Models]
```

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant API as Backend API
    participant AI as AI API
    participant DB as PostgreSQL
    participant LLM as LLM Service

    User->>FE: Upload skin image
    FE->>API: Submit analysis request
    API->>AI: Forward image for inference
    AI->>AI: Segment lesion and classify disease
    AI-->>API: Return AI result
    API->>DB: Save analysis history
    API-->>FE: Return structured result
    User->>FE: Ask follow-up question
    FE->>API: Send chat message
    API->>AI: Request RAG consultation
    AI->>LLM: Generate grounded response
    AI-->>API: Return medical consultation
    API-->>FE: Display response
```

## Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- TailwindCSS
- Zustand

### Backend

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis

### AI

- PyTorch
- OpenCV
- Albumentations
- Transformers
- Sentence Transformers

### DevOps

- Docker
- Docker Compose
- Nginx
- AWS EC2
- GitHub Actions

## Repository Structure

```text
CapstoneProject/
├── FE/                 # Frontend web application built with Next.js
├── API/                # Main backend API for auth, users, history, and orchestration
├── AI-API/             # AI inference, model serving, and RAG chatbot service
├── README.md           # Project documentation
└── .gitignore          # Repository-level ignore rules
```

Recommended production-oriented structure for future expansion:

```text
CapstoneProject/
├── frontend/           # Web application
├── api/                # Main backend API
├── ai-api/             # AI inference and chatbot service
├── models/             # Model artifacts or Git LFS pointers
├── notebooks/          # Training and experimentation notebooks
├── datasets/           # Dataset metadata or preprocessing scripts
├── docs/               # Technical documentation
├── docker/             # Deployment and infrastructure configuration
└── README.md
```

## Installation

### Prerequisites

- Git
- Node.js 18+
- pnpm
- Python 3.10+
- Docker and Docker Compose
- PostgreSQL
- Redis

### Clone Project

```bash
git clone https://github.com/hoanghungduong1511/CapstoneProject.git
cd CapstoneProject
```

### Environment Variables

Create environment files from the provided examples:

```bash
cp API/.env.example API/.env
cp AI-API/.env.example AI-API/.env
```

For the frontend, create `FE/.env.local` and configure the API endpoints used by the application.

### Docker Setup

From the backend service directory:

```bash
cd API
docker compose up -d --build
```

Depending on your deployment setup, you can extend `docker-compose.yml` to include the frontend and AI service as separate containers.

### Run Frontend

```bash
cd FE
pnpm install
pnpm dev
```

Default local URL:

```text
http://localhost:3000
```

### Run Backend API

```bash
cd API
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell:

```powershell
cd API
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Run AI Service

```bash
cd AI-API
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

On Windows PowerShell:

```powershell
cd AI-API
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Environment Variables

Example backend and AI service configuration:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/skindiseases
JWT_SECRET=replace-with-a-secure-secret
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

Never commit real `.env` files or production secrets to the repository.

## API Documentation

When running locally, the interactive API documentation is available at:

```text
Main Backend API Swagger: http://localhost:8000/docs
AI API Swagger:           http://localhost:8001/docs
```

Health check endpoints may be exposed depending on the active service configuration.

## Demo

### Screenshots

> Add screenshots of the upload flow, AI result page, chatbot, user dashboard, and admin dashboard.

### GIFs

> Add short GIFs demonstrating image analysis and chatbot consultation.

### Video Demo

> Add a link to a project walkthrough video or deployment demo.

## Results

The system demonstrates an end-to-end AI-assisted medical analysis workflow:

- Segmentation model produces lesion masks for visual localization.
- Classification model predicts likely skin disease categories with confidence scores.
- RAG chatbot retrieves medical context and generates consultation-style responses.
- Backend stores user analysis history, chat sessions, and structured AI outputs.
- Monorepo architecture separates frontend, backend, and AI inference concerns while keeping development centralized.

Detailed quantitative evaluation can be added as model reports become finalized.

## Key Learnings

This project demonstrates practical experience across AI engineering, backend development, and system design:

- Deep Learning model development and fine-tuning.
- Computer Vision for medical image segmentation and classification.
- NLP and Retrieval-Augmented Generation for consultation workflows.
- FastAPI backend design with authentication, authorization, and persistence.
- Database modeling with SQLAlchemy, Alembic, and PostgreSQL.
- Microservices communication between business APIs and AI inference services.
- Docker-based development and deployment workflows.
- Cloud deployment considerations for AWS EC2, object storage, and service orchestration.
- MLOps concerns such as model artifact management, reproducibility, and inference serving.

## Future Improvements

- Mobile application for easier image capture and consultation.
- Explainable AI visualizations such as Grad-CAM and richer lesion overlays.
- More diverse medical datasets for stronger generalization.
- Real-time consultation experience with streaming responses.
- CI/CD pipelines for automated testing and deployment.
- Model registry and versioned inference endpoints.
- Clinical validation workflow with expert dermatologist feedback.

## About Me

**Author:** Duong Vo Hoang Hung  
**Email:** `your-email@example.com`  
**LinkedIn:** `https://www.linkedin.com/in/your-linkedin`  
**GitHub:** [hoanghungduong1511](https://github.com/hoanghungduong1511)

---

<p align="center">
  Built as a technical showcase of AI Engineering, Backend Engineering, and Fullstack System Design.
</p>
