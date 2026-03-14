from supabase import create_client, Client
from config import settings
from datetime import datetime
import json

_client: Client = None


def _db() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


# ── DRIVERS & CALLERS ─────────────────────────────────────────────────

async def get_driver_by_phone_hash(phone_hash: str) -> dict | None:
    result = (
        _db().table("drivers")
             .select("id, driver_code, vehicle_type, caller_id, callers(name, preferred_lang)")
             .eq("callers.phone_hash", phone_hash)
             .eq("active_shift", True)
             .limit(1)
             .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    caller = row.get("callers") or {}
    return {
        "id":          row["id"],
        "driver_code": row["driver_code"],
        "vehicle":     row["vehicle_type"],
        "caller_id":   row["caller_id"],
        "name":        caller.get("name", "Driver"),
        "lang":        caller.get("preferred_lang", "en"),
    }


async def get_caller_by_phone_hash(phone_hash: str) -> dict | None:
    result = (
        _db().table("callers")
             .select("id, name, preferred_lang")
             .eq("phone_hash", phone_hash)
             .limit(1)
             .execute()
    )
    return result.data[0] if result.data else None


# ── SHIPMENTS ────────────────────────────────────────────────────────

async def get_shipment_by_tracking(tracking_number: str) -> dict | None:
    result = (
        _db().table("shipments")
             .select("*")
             .eq("tracking_number", tracking_number)
             .limit(1)
             .execute()
    )
    return result.data[0] if result.data else None


async def get_shipments_by_driver(driver_id: str) -> list:
    result = (
        _db().table("shipments")
             .select("*")
             .eq("driver_id", driver_id)
             .in_("status", ["pending", "in_transit", "out_for_delivery"])
             .order("priority_flag", desc=True)
             .execute()
    )
    return result.data or []


async def get_active_shipments_for_driver(driver_id: str) -> list:
    return await get_shipments_by_driver(driver_id)


async def update_shipment_status(shipment_id: str, status: str) -> None:
    update_data: dict = {"status": status}
    if status == "delivered":
        update_data["delivered_at"] = datetime.utcnow().isoformat()

    _db().table("shipments")\
         .update(update_data)\
         .eq("id", shipment_id)\
         .execute()


# ── ROUTES ────────────────────────────────────────────────────────────

async def get_route_for_driver(driver_id: str) -> dict | None:
    result = (
        _db().table("routes")
             .select("id, route_code, waypoints, status")
             .eq("assigned_driver_id", driver_id)
             .eq("status", "active")
             .limit(1)
             .execute()
    )
    return result.data[0] if result.data else None


async def get_next_waypoint(driver_id: str,
                             current_stop: int = None) -> dict | None:
    route = await get_route_for_driver(driver_id)
    if not route:
        return None

    waypoints = route.get("waypoints", [])
    if not waypoints:
        return None

    # Find next undelivered delivery stop
    for wp in waypoints:
        if wp.get("type") != "delivery":
            continue
        if current_stop is not None and wp.get("stop", 0) <= current_stop:
            continue
        tracking = wp.get("shipment")
        if not tracking:
            return wp
        shipment = await get_shipment_by_tracking(tracking)
        if shipment and shipment["status"] not in ["delivered", "failed", "returned"]:
            return wp

    return None


# ── LOGISTICS EVENTS ─────────────────────────────────────────────────

async def log_logistics_event(shipment_id: str,
                               event_type:  str,
                               payload:     dict) -> None:
    _db().table("logistics_events").insert({
        "shipment_id": shipment_id,
        "event_type":  event_type,
        "payload":     json.dumps(payload),
    }).execute()


# ── APPOINTMENTS (receptionist mode) ─────────────────────────────────

async def get_available_slots(business_id: str) -> list:
    result = (
        _db().table("appointments")
             .select("slot_time")
             .eq("business_id", business_id)
             .eq("status", "available")
             .order("slot_time")
             .limit(10)
             .execute()
    )
    return [r["slot_time"] for r in (result.data or [])]


async def book_appointment(business_id: str,
                            caller_id:   str,
                            slot_time:   str,
                            notes:       str = "") -> dict | None:
    result = (
        _db().table("appointments").insert({
            "business_id": business_id,
            "caller_id":   caller_id,
            "slot_time":   slot_time,
            "status":      "booked",
            "notes":       notes,
        }).execute()
    )
    return result.data[0] if result.data else None


# ── INTERACTIONS ──────────────────────────────────────────────────────

async def create_interaction(session_id: str,
                              caller_id:  str,
                              driver_id:  str,
                              mode:       str) -> str | None:
    result = (
        _db().table("interactions").insert({
            "session_id": session_id,
            "caller_id":  caller_id,
            "driver_id":  driver_id,
            "mode":       mode,
        }).execute()
    )
    return result.data[0]["id"] if result.data else None


async def close_interaction(interaction_id: str,
                             outcome:        str,
                             duration_ms:    int) -> None:
    _db().table("interactions")\
         .update({"outcome": outcome, "duration_ms": duration_ms})\
         .eq("id", interaction_id)\
         .execute()


# ── WAREHOUSES (NEW) ──────────────────────────────────────────────────

async def get_warehouse_by_code(warehouse_code: str) -> dict | None:
    result = (
        _db().table("warehouses")
             .select("*")
             .ilike("warehouse_code", warehouse_code)
             .limit(1)
             .execute()
    )
    return result.data[0] if result.data else None


async def get_warehouse_by_name(name: str) -> dict | None:
    result = (
        _db().table("warehouses")
             .select("*")
             .ilike("name", f"%{name}%")
             .limit(1)
             .execute()
    )
    return result.data[0] if result.data else None


# ── INVENTORY (NEW) ───────────────────────────────────────────────────

async def get_inventory_by_product(product_name: str,
                                    warehouse_code: str = None) -> list:
    """
    Returns all inventory rows matching the product name.
    Joins with warehouses table to get warehouse_name.
    Optionally filters by warehouse_code.
    """
    query = (
        _db().table("inventory")
             .select("quantity, unit, warehouse_code, warehouses(name), products(name)")
             .ilike("products.name", f"%{product_name}%")
    )
    if warehouse_code:
        query = query.ilike("warehouse_code", warehouse_code)

    result = query.execute()

    rows = []
    for row in (result.data or []):
        warehouse_info = row.get("warehouses") or {}
        product_info   = row.get("products") or {}
        rows.append({
            "warehouse_code": row["warehouse_code"],
            "warehouse_name": warehouse_info.get("name", row["warehouse_code"]),
            "product_name":   product_info.get("name", product_name),
            "quantity":       row["quantity"],
            "unit":           row.get("unit", "units"),
        })
    return rows


async def get_all_inventory_for_warehouse(warehouse_code: str) -> list:
    """
    Returns all products stocked at a specific warehouse.
    """
    result = (
        _db().table("inventory")
             .select("quantity, unit, products(name)")
             .ilike("warehouse_code", warehouse_code)
             .order("quantity", desc=True)
             .execute()
    )

    rows = []
    for row in (result.data or []):
        product_info = row.get("products") or {}
        rows.append({
            "product_name": product_info.get("name", "Unknown"),
            "quantity":     row["quantity"],
            "unit":         row.get("unit", "units"),
        })
    return rows


# ── DELIVERY ORDERS (NEW) ─────────────────────────────────────────────

async def get_delivery_order_by_id(order_id: str) -> dict | None:
    result = (
        _db().table("delivery_orders")
             .select("*, warehouses!from_warehouse_code(name)")
             .ilike("order_id", order_id)
             .limit(1)
             .execute()
    )
    if not result.data:
        return None
    return _format_delivery_order(result.data[0])


async def get_delivery_orders_by_driver(driver_id: str) -> list:
    result = (
        _db().table("delivery_orders")
             .select("*, warehouses!from_warehouse_code(name)")
             .eq("assigned_driver_id", driver_id)
             .in_("status", ["pending", "in_progress"])
             .order("priority", desc=True)
             .execute()
    )
    return [_format_delivery_order(row) for row in (result.data or [])]


def _format_delivery_order(row: dict) -> dict:
    """Normalize a delivery_orders row into a clean dict for tools."""
    warehouse_info = row.get("warehouses") or {}
    return {
        "order_id":            row["order_id"],
        "product_name":        row["product_name"],
        "quantity":            row["quantity"],
        "unit":                row.get("unit", "units"),
        "from_warehouse_code": row["from_warehouse_code"],
        "from_warehouse_name": warehouse_info.get("name", row["from_warehouse_code"]),
        "destination_address": row["destination_address"],
        "destination_city":    row.get("destination_city", ""),
        "priority":            row.get("priority", "normal"),
        "special_notes":       row.get("special_notes", ""),
        "status":              row.get("status", "pending"),
        "assigned_driver_id":  row.get("assigned_driver_id"),
    }