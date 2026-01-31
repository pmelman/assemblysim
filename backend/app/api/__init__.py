"""
API Package

FastAPI routers and API services.
"""

from app.api.assemblies import router as assemblies_router
from app.api.websocket import (
    router as websocket_router,
    broadcast_to_assembly,
    get_connection_manager,
    ConnectionManager
)
from app.api.services import (
    create_assembly_with_citizens,
    generate_briefing_for_assembly,
    get_assembly_with_details,
    assign_citizens_to_groups
)

__all__ = [
    # Routers
    "assemblies_router",
    "websocket_router",
    # WebSocket
    "broadcast_to_assembly",
    "get_connection_manager",
    "ConnectionManager",
    # Services
    "create_assembly_with_citizens",
    "generate_briefing_for_assembly",
    "get_assembly_with_details",
    "assign_citizens_to_groups",
]
