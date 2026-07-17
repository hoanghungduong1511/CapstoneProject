#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Makefile-style helper script cho Docker
# Sử dụng: bash scripts/docker.sh [command]
# ═══════════════════════════════════════════════════════════════

set -e

case "$1" in
  build)
    echo "🔨 Building Docker images..."
    docker-compose build
    ;;
  up)
    echo "🚀 Starting all services..."
    docker-compose up -d
    echo "✅ Services started!"
    echo "   API:     http://localhost:8000"
    echo "   Swagger: http://localhost:8000/docs"
    echo "   ReDoc:   http://localhost:8000/redoc"
    echo "   pgAdmin: http://localhost:5050"
    ;;
  down)
    echo "🛑 Stopping all services..."
    docker-compose down
    ;;
  restart)
    echo "🔄 Restarting all services..."
    docker-compose down
    docker-compose up -d
    ;;
  logs)
    docker-compose logs -f "${2:-api}"
    ;;
  db-shell)
    echo "🗄️  Connecting to PostgreSQL..."
    docker-compose exec db psql -U postgres -d skin_diseases
    ;;
  migrate)
    echo "📦 Running Alembic migration..."
    docker-compose exec api alembic upgrade head
    ;;
  makemigrations)
    echo "📝 Generating new migration..."
    docker-compose exec api alembic revision --autogenerate -m "${2:-auto migration}"
    ;;
  clean)
    echo "🧹 Cleaning up everything (including volumes)..."
    docker-compose down -v --remove-orphans
    ;;
  *)
    echo "Usage: bash scripts/docker.sh {build|up|down|restart|logs|db-shell|migrate|makemigrations|clean}"
    echo ""
    echo "Commands:"
    echo "  build            Build Docker images"
    echo "  up               Start all services (detached)"
    echo "  down             Stop all services"
    echo "  restart          Restart all services"
    echo "  logs [service]   Follow logs (default: api)"
    echo "  db-shell         Open PostgreSQL shell"
    echo "  migrate          Run Alembic migrations"
    echo "  makemigrations   Generate new migration"
    echo "  clean            Remove everything including volumes"
    ;;
esac
