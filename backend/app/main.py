# FastAPI application factory
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import get_settings, is_demo_mode
from backend.app.core.database import init_db
from backend.app.api.routes import health, analysis, auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (cleanup if needed)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered cloud cost analysis for AWS, GCP, and Azure",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG or is_demo_mode() else None,
        redoc_url="/redoc" if settings.DEBUG or is_demo_mode() else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if is_demo_mode() else ["http://localhost:3000", "https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(analysis.router)

    @app.get("/")
    def root():
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()