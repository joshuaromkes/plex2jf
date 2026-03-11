"""API routes package."""
from src.routes.servers import router as servers_router
from src.routes.users import router as users_router
from src.routes.settings import router as settings_router
from src.routes.dashboard import router as dashboard_router
from src.routes.system import router as system_router

__all__ = [
    "servers_router",
    "users_router",
    "settings_router",
    "dashboard_router",
    "system_router",
]