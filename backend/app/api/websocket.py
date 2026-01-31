"""
WebSocket Module

Provides real-time updates for assembly status and deliberation messages.
"""

import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Connections are organized by assembly ID to enable targeted broadcasts.
    """

    def __init__(self):
        # Map of assembly_id -> list of WebSocket connections
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, assembly_id: int):
        """
        Accept a new WebSocket connection for an assembly.

        Args:
            websocket: The WebSocket connection
            assembly_id: ID of the assembly to subscribe to
        """
        await websocket.accept()

        if assembly_id not in self.active_connections:
            self.active_connections[assembly_id] = []

        self.active_connections[assembly_id].append(websocket)
        logger.info(f"WebSocket connected for assembly {assembly_id}")

    def disconnect(self, websocket: WebSocket, assembly_id: int):
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            assembly_id: ID of the assembly
        """
        if assembly_id in self.active_connections:
            try:
                self.active_connections[assembly_id].remove(websocket)
                logger.info(f"WebSocket disconnected for assembly {assembly_id}")

                # Clean up empty lists
                if not self.active_connections[assembly_id]:
                    del self.active_connections[assembly_id]
            except ValueError:
                pass  # Connection not in list

    async def broadcast_to_assembly(self, assembly_id: int, message: dict):
        """
        Broadcast a message to all connections for an assembly.

        Args:
            assembly_id: ID of the assembly
            message: Message dict to broadcast
        """
        if assembly_id not in self.active_connections:
            return

        # Add metadata
        message["assembly_id"] = assembly_id
        message["timestamp"] = datetime.utcnow().isoformat()

        message_json = json.dumps(message)

        # Track failed connections for cleanup
        failed_connections = []

        for connection in self.active_connections[assembly_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                failed_connections.append(connection)

        # Clean up failed connections
        for connection in failed_connections:
            self.disconnect(connection, assembly_id)

    async def broadcast_to_all(self, message: dict):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dict to broadcast
        """
        message["timestamp"] = datetime.utcnow().isoformat()
        message_json = json.dumps(message)

        for assembly_id, connections in list(self.active_connections.items()):
            failed_connections = []
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    failed_connections.append(connection)

            for connection in failed_connections:
                self.disconnect(connection, assembly_id)

    def get_connection_count(self, assembly_id: Optional[int] = None) -> int:
        """
        Get the number of active connections.

        Args:
            assembly_id: Optional assembly ID to filter by

        Returns:
            Number of active connections
        """
        if assembly_id is not None:
            return len(self.active_connections.get(assembly_id, []))

        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/assemblies/{assembly_id}")
async def websocket_endpoint(websocket: WebSocket, assembly_id: int):
    """
    WebSocket endpoint for real-time assembly updates.

    Clients connect to this endpoint to receive:
    - Status updates (citizen generation progress, etc.)
    - New deliberation messages
    - Vote updates
    - Error notifications

    Message format:
    {
        "type": "status_update" | "new_message" | "vote_update" | "error",
        "assembly_id": 1,
        "data": { ... },
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    await manager.connect(websocket, assembly_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "assembly_id": assembly_id,
            "message": f"Connected to assembly {assembly_id}",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (could be ping/pong or commands)
                data = await websocket.receive_text()

                # Parse and handle client messages
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, assembly_id, message)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": datetime.utcnow().isoformat()
                    })

            except WebSocketDisconnect:
                break

    finally:
        manager.disconnect(websocket, assembly_id)


async def handle_client_message(
    websocket: WebSocket,
    assembly_id: int,
    message: dict
):
    """
    Handle messages received from WebSocket clients.

    Args:
        websocket: The WebSocket connection
        assembly_id: ID of the assembly
        message: The received message
    """
    message_type = message.get("type", "unknown")

    if message_type == "ping":
        # Respond to ping with pong
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })

    elif message_type == "subscribe":
        # Client confirming subscription (already connected)
        await websocket.send_json({
            "type": "subscribed",
            "assembly_id": assembly_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    elif message_type == "get_status":
        # Client requesting current assembly status
        from app.models.database import get_db_session
        from app.models.models import Assembly

        with get_db_session() as db:
            assembly = db.query(Assembly).filter(
                Assembly.id == assembly_id
            ).first()

            if assembly:
                await websocket.send_json({
                    "type": "status",
                    "assembly_id": assembly_id,
                    "data": {
                        "status": assembly.status.value,
                        "num_citizens": assembly.num_citizens,
                        "topic": assembly.topic
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Assembly not found",
                    "timestamp": datetime.utcnow().isoformat()
                })

    else:
        # Unknown message type
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_to_assembly(assembly_id: int, message: dict):
    """
    Utility function to broadcast to an assembly.

    This can be imported and used by other modules (services, etc.)
    to send WebSocket updates.

    Args:
        assembly_id: ID of the assembly
        message: Message dict to broadcast
    """
    await manager.broadcast_to_assembly(assembly_id, message)


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
