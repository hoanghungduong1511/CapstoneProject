# ═══════════════════════════════════════════════════════════════
# SkinDiseases API — PowerShell Helper Script
# Sử dụng: .\scripts\dev.ps1 <command>
# ═══════════════════════════════════════════════════════════════

param(
    [Parameter(Position=0)]
    [string]$Command,

    [Parameter(Position=1)]
    [string]$Arg1
)

switch ($Command) {
    "build" {
        Write-Host "🔨 Building Docker images..." -ForegroundColor Cyan
        docker-compose build
    }
    "up" {
        Write-Host "🚀 Starting all services..." -ForegroundColor Green
        docker-compose up -d --build
        Write-Host ""
        Write-Host "✅ Services started!" -ForegroundColor Green
        Write-Host "   API:     http://localhost:8000" -ForegroundColor Yellow
        Write-Host "   Swagger: http://localhost:8000/docs" -ForegroundColor Yellow
        Write-Host "   ReDoc:   http://localhost:8000/redoc" -ForegroundColor Yellow
        Write-Host "   pgAdmin: http://localhost:5050" -ForegroundColor Yellow
    }
    "down" {
        Write-Host "🛑 Stopping all services..." -ForegroundColor Red
        docker-compose down
    }
    "restart" {
        Write-Host "🔄 Restarting all services..." -ForegroundColor Cyan
        docker-compose down
        docker-compose up -d --build
    }
    "logs" {
        $service = if ($Arg1) { $Arg1 } else { "api" }
        docker-compose logs -f $service
    }
    "db-shell" {
        Write-Host "🗄️ Connecting to PostgreSQL..." -ForegroundColor Cyan
        docker-compose exec db psql -U postgres -d skin_diseases
    }
    "migrate" {
        Write-Host "📦 Running Alembic migration..." -ForegroundColor Cyan
        docker-compose exec api alembic upgrade head
    }
    "makemigrations" {
        $msg = if ($Arg1) { $Arg1 } else { "auto migration" }
        Write-Host "📝 Generating new migration: $msg" -ForegroundColor Cyan
        docker-compose exec api alembic revision --autogenerate -m $msg
    }
    "clean" {
        Write-Host "🧹 Cleaning up everything (including volumes)..." -ForegroundColor Red
        docker-compose down -v --remove-orphans
    }
    "status" {
        docker-compose ps
    }
    default {
        Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host " SkinDiseases API — Dev Helper" -ForegroundColor White
        Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Usage: .\scripts\dev.ps1 <command> [arg]" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor White
        Write-Host "  build              Build Docker images"
        Write-Host "  up                 Start all services (detached)"
        Write-Host "  down               Stop all services"
        Write-Host "  restart            Restart all services"
        Write-Host "  logs [service]     Follow logs (default: api)"
        Write-Host "  db-shell           Open PostgreSQL shell"
        Write-Host "  migrate            Run Alembic migrations"
        Write-Host "  makemigrations [m] Generate new migration"
        Write-Host "  clean              Remove everything including volumes"
        Write-Host "  status             Show running containers"
    }
}
