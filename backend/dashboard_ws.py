"""
Dashboard WebSocket broadcaster.
Frontend warehouse dashboard connects here.
All events (emotion, transcript, shipment updates, thoughts)
are broadcast to every connected dashboard client.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json

router = APIRouter(tags=["dashboard"])

# All connected dashboard clients
_dashboard_clients: Set[WebSocket] = set()


@router.websocket("/ws/dashboard")
async def dashboard_ws(ws: WebSocket):
    """
    Warehouse dashboard connects to this endpoint.
    Receives all real-time events as JSON.
    """
    await ws.accept()
    _dashboard_clients.add(ws)
    print(f"[DASHBOARD] Client connected. Total: {len(_dashboard_clients)}")

    try:
        while True:
            # Keep connection alive — dashboard only receives, doesn't send
            await ws.receive_text()
    except WebSocketDisconnect:
        _dashboard_clients.discard(ws)
        print(f"[DASHBOARD] Client disconnected. Total: {len(_dashboard_clients)}")


async def broadcast(event: dict) -> None:
    """
    Send a JSON event to all connected dashboard clients.
    Called from voice_pipeline, tools, session, etc.
    """
    if not _dashboard_clients:
        return

    message = json.dumps(event)
    disconnected = set()

    for client in _dashboard_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)

    # Clean up disconnected clients
    _dashboard_clients.difference_update(disconnected)