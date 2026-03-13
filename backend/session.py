from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from services.supabase_client import (
    get_driver_by_phone_hash,
    get_caller_by_phone_hash,
    get_active_shipments_for_driver,
    get_route_for_driver,
    create_interaction,
    close_interaction,
)
from memory import store_session, get_session, delete_session
from config import settings

router = APIRouter(prefix="/session", tags=["session"])


class SessionStartRequest(BaseModel):
    phone_hash: str
    business_id: Optional[str] = None
    driver_id: Optional[str] = None


class SessionEndRequest(BaseModel):
    session_id: str
    outcome: Optional[str] = None
    duration_ms: Optional[int] = None


@router.post("/start")
async def start_session(req: SessionStartRequest):
    """
    Called by frontend before opening WebSocket.
    Looks up driver/caller from Supabase,
    builds session object, stores in memory.
    Returns session_id for WebSocket handshake.
    """
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    session = {
        "session_id":      session_id,
        "phone_hash":      req.phone_hash,
        "created_at":      now,
        "turn_history":    [],
        "detected_lang":   "en",
        "mode":            "logistics" if settings.LOGISTICS_MODE else "receptionist",
        # driver/caller fields populated below
        "driver_id":       None,
        "caller_id":       None,
        "driver_name":     "Driver",
        "active_shipments": [],
        "current_route":   None,
        "business_id":     req.business_id,
    }

    if settings.LOGISTICS_MODE:
        # Load driver profile
        driver = await get_driver_by_phone_hash(req.phone_hash)
        if driver:
            session["driver_id"]   = driver["id"]
            session["caller_id"]   = driver.get("caller_id")
            session["driver_name"] = driver.get("name", "Driver")

            # Pre-load active shipments
            shipments = await get_active_shipments_for_driver(driver["id"])
            session["active_shipments"] = shipments

            # Pre-load route
            route = await get_route_for_driver(driver["id"])
            session["current_route"] = route
    else:
        # Receptionist mode — load caller profile
        caller = await get_caller_by_phone_hash(req.phone_hash)
        if caller:
            session["caller_id"]   = caller["id"]
            session["driver_name"] = caller.get("name", "Caller")

    # Store session in memory
    store_session(session_id, session)

    # Log interaction start in Supabase
    interaction_id = await create_interaction(
        session_id  = session_id,
        caller_id   = session.get("caller_id"),
        driver_id   = session.get("driver_id"),
        mode        = session["mode"],
    )
    session["interaction_id"] = interaction_id
    store_session(session_id, session)

    print(f"[SESSION] Started {session_id} for {session['driver_name']}")

    return {
        "session_id":  session_id,
        "driver_name": session["driver_name"],
        "mode":        session["mode"],
        "shipment_count": len(session["active_shipments"]),
    }


@router.post("/end")
async def end_session(req: SessionEndRequest):
    """
    Called by frontend when user hangs up or closes widget.
    Closes interaction record in Supabase and cleans up memory.
    """
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Close interaction in Supabase
    if session.get("interaction_id"):
        await close_interaction(
            interaction_id = session["interaction_id"],
            outcome        = req.outcome or "completed",
            duration_ms    = req.duration_ms or 0,
        )

    delete_session(req.session_id)
    print(f"[SESSION] Ended {req.session_id}")

    return {"status": "closed", "session_id": req.session_id}


@router.get("/slots/{business_id}")
async def get_slots(business_id: str):
    """
    Returns available appointment slots for receptionist mode.
    Not used in logistics mode.
    """
    from services.supabase_client import get_available_slots
    slots = await get_available_slots(business_id)
    return {"slots": slots}