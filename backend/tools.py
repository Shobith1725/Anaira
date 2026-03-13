"""
All tool functions that Groq LLM can call.
Each function talks to Supabase and broadcasts to dashboard.
execute_tool() is the single entry point called from voice_pipeline.

FIX vs old version:
- All supabase_client and dashboard_ws imports are LAZY (inside each function).
  Old version had top-level imports — if either module failed at startup,
  tools.py would fail to import entirely and FastAPI would not start.
- Unknown tool returns json.dumps error (never raises) so Groq loop never hangs.
"""

import json


async def execute_tool(tool_name: str, args: dict) -> str:
    """
    Central dispatcher called by groq.py after LLM tool call.
    Returns JSON string — fed back to LLM as tool result.
    Never raises — always returns JSON so the Groq tool loop never hangs.
    """
    handlers = {
        "identify_shipment":      _identify_shipment,
        "update_shipment_status": _update_shipment_status,
        "confirm_delivery":       _confirm_delivery,
        "report_delay":           _report_delay,
        "get_next_stop":          _get_next_stop,
        "report_damage":          _report_damage,
        "request_reroute":        _request_reroute,
        "escalate_to_human":      _escalate_to_human,
        "check_slots":            _check_slots,
        "book_appointment":       _book_appointment,
    }

    handler = handlers.get(tool_name)
    if not handler:
        # Return JSON — never raise. If this raised, Groq would get no tool result
        # and keep retrying the same tool call in an infinite loop.
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        return await handler(**args)
    except Exception as e:
        print(f"[TOOL ERROR] {tool_name}: {e}")
        return json.dumps({"error": str(e)})


# ── LOGISTICS TOOLS ───────────────────────────────────────────────────

async def _identify_shipment(tracking_number: str = None,
                              driver_id: str = None) -> str:
    from services.supabase_client import get_shipment_by_tracking, get_shipments_by_driver

    if tracking_number:
        shipment = await get_shipment_by_tracking(tracking_number)
    elif driver_id:
        shipments = await get_shipments_by_driver(driver_id)
        shipment = shipments[0] if shipments else None
    else:
        return json.dumps({"found": False, "message": "No tracking number or driver ID provided"})

    if not shipment:
        return json.dumps({"found": False, "message": "Shipment not found"})

    return json.dumps({
        "found":       True,
        "shipment_id": shipment["id"],
        "tracking":    shipment["tracking_number"],
        "status":      shipment["status"],
        "destination": shipment["destination"],
        "recipient":   shipment.get("recipient_name", "Unknown"),
        "priority":    shipment.get("priority_flag", False),
        "cargo_type":  shipment.get("cargo_type", "General"),
    })


async def _confirm_delivery(shipment_id: str,
                             recipient_name: str = None,
                             proof_type: str = "signature") -> str:
    from services.supabase_client import (
        update_shipment_status as db_update_status,
        log_logistics_event,
    )
    from dashboard_ws import broadcast

    await db_update_status(shipment_id, "delivered")
    await log_logistics_event(shipment_id, "proof_of_delivery", {
        "recipient":  recipient_name,
        "proof_type": proof_type,
    })
    await broadcast({
        "type":        "shipment_update",
        "shipment_id": shipment_id,
        "status":      "delivered",
        "event":       "proof_of_delivery",
        "recipient":   recipient_name,
    })
    return json.dumps({
        "success": True,
        "message": f"Delivery confirmed. Shipment {shipment_id} marked as delivered.",
    })


async def _update_shipment_status(shipment_id: str,
                                   status: str,
                                   notes: str = "") -> str:
    from services.supabase_client import (
        update_shipment_status as db_update_status,
        log_logistics_event,
    )
    from dashboard_ws import broadcast

    await db_update_status(shipment_id, status)
    await log_logistics_event(shipment_id, "status_update", {
        "new_status": status,
        "notes":      notes,
    })
    await broadcast({
        "type":        "shipment_update",
        "shipment_id": shipment_id,
        "status":      status,
        "event":       "status_update",
    })
    return json.dumps({"success": True, "message": f"Status updated to {status}"})


async def _report_delay(shipment_id: str,
                         reason: str,
                         estimated_delay_minutes: int = None) -> str:
    from services.supabase_client import log_logistics_event
    from dashboard_ws import broadcast

    await log_logistics_event(shipment_id, "delay_reported", {
        "reason":                  reason,
        "estimated_delay_minutes": estimated_delay_minutes,
    })
    await broadcast({
        "type":        "shipment_update",
        "shipment_id": shipment_id,
        "event":       "delay_reported",
        "reason":      reason,
        "delay_mins":  estimated_delay_minutes,
    })
    return json.dumps({
        "success": True,
        "message": "Delay logged and warehouse notified.",
    })


async def _get_next_stop(driver_id: str,
                          current_stop: int = None) -> str:
    from services.supabase_client import get_next_waypoint

    waypoint = await get_next_waypoint(driver_id, current_stop)
    if not waypoint:
        return json.dumps({
            "found":   False,
            "message": "No more stops on your route today. Head back to the warehouse.",
        })
    return json.dumps({
        "found":    True,
        "address":  waypoint["address"],
        "stop":     waypoint["stop"],
        "shipment": waypoint.get("shipment", ""),
        "type":     waypoint.get("type", "delivery"),
    })


async def _report_damage(shipment_id: str,
                          description: str) -> str:
    from services.supabase_client import (
        update_shipment_status as db_update_status,
        log_logistics_event,
    )
    from dashboard_ws import broadcast

    await db_update_status(shipment_id, "damaged")
    await log_logistics_event(shipment_id, "damage_report", {
        "description": description,
    })
    await broadcast({
        "type":        "shipment_update",
        "shipment_id": shipment_id,
        "status":      "damaged",
        "event":       "damage_report",
        "urgent":      True,
        "description": description,
    })
    return json.dumps({
        "success": True,
        "message": "Damage reported. Do not deliver. Supervisor has been notified.",
    })


async def _request_reroute(shipment_id: str,
                            obstacle_description: str) -> str:
    from services.supabase_client import log_logistics_event
    from dashboard_ws import broadcast

    await log_logistics_event(shipment_id, "reroute_request", {
        "obstacle": obstacle_description,
    })
    await broadcast({
        "type":        "shipment_update",
        "shipment_id": shipment_id,
        "event":       "reroute_request",
        "obstacle":    obstacle_description,
        "urgent":      True,
    })
    return json.dumps({
        "success": True,
        "message": "Reroute request sent to dispatch. Wait for confirmation.",
    })


async def _escalate_to_human(reason: str,
                              urgency: str = "medium",
                              shipment_id: str = None) -> str:
    from services.supabase_client import log_logistics_event
    from dashboard_ws import broadcast

    if shipment_id:
        await log_logistics_event(shipment_id, "escalation", {
            "reason":  reason,
            "urgency": urgency,
        })
    await broadcast({
        "type":        "escalation",
        "reason":      reason,
        "urgency":     urgency,
        "shipment_id": shipment_id,
    })
    return json.dumps({
        "success": True,
        "message": "Dispatcher has been alerted and will contact you shortly.",
    })


# ── RECEPTIONIST TOOLS ────────────────────────────────────────────────

async def _check_slots(business_id: str) -> str:
    from services.supabase_client import get_available_slots

    slots = await get_available_slots(business_id)
    if not slots:
        return json.dumps({"found": False, "message": "No available slots found"})
    return json.dumps({"found": True, "slots": slots[:5]})


async def _book_appointment(business_id: str,
                             caller_id: str,
                             slot_time: str,
                             notes: str = "") -> str:
    from services.supabase_client import book_appointment

    result = await book_appointment(business_id, caller_id, slot_time, notes)
    if result:
        return json.dumps({
            "success":        True,
            "appointment_id": result["id"],
            "slot_time":      slot_time,
            "message":        f"Appointment booked for {slot_time}",
        })
    return json.dumps({"success": False, "message": "Could not book that slot"})