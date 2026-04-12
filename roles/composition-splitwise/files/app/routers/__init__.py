from .auth import router as auth_router
from .groups import router as groups_router
from .transactions import router as transactions_router
from .web import router as web_router

__all__ = ["auth_router", "groups_router", "transactions_router", "web_router"]
