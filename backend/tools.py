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
        # Original logistics tools
        "identify_shipment":      _identify_shipment,
        "update_shipment_status": _update_shipment_status,
        "confirm_delivery":       _confirm_delivery,
        "report_delay":           _report_delay,
        "get_next_stop":          _get_next_stop,
        "report_damage":          _report_damage,
        "request_reroute":        _request_reroute,
        "escalate_to_human":      _escalate_to_human,
        # Original receptionist tools
        "check_slots":            _check_slots,
        "book_appointment":       _book_appointment,
        # Warehouse tools (NEW)
        "get_warehouse_info":     _get_warehouse_info,
        "get_product_quantity":   _get_product_quantity,
        "get_delivery_order":     _get_delivery_order,
        "get_all_delivery_orders": _get_all_delivery_orders,
        "list_warehouse_products": _list_warehouse_products,
    }

    handler = handlers.get(tool_name)
    if not handler:
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


# ── WAREHOUSE TOOLS (NEW) ──────────────────────────────────────────────

async def _get_warehouse_info(warehouse_code: str = None,
                               warehouse_name: str = None) -> str:
    from services.supabase_client import get_warehouse_by_code, get_warehouse_by_name

    warehouse = None
    if warehouse_code:
        warehouse = await get_warehouse_by_code(warehouse_code)
    elif warehouse_name:
        warehouse = await get_warehouse_by_name(warehouse_name)

    if not warehouse:
        return json.dumps({
            "found":   False,
            "message": "Warehouse not found. Please check the warehouse code or name.",
        })

    return json.dumps({
        "found":          True,
        "warehouse_code": warehouse["warehouse_code"],
        "name":           warehouse["name"],
        "address":        warehouse["address"],
        "city":           warehouse["city"],
        "phone":          warehouse.get("phone", "Not available"),
        "manager":        warehouse.get("manager_name", "Not available"),
        "capacity":       warehouse.get("capacity_units"),
    })


async def _get_product_quantity(product_name: str,
                                 warehouse_code: str = None) -> str:
    from services.supabase_client import get_inventory_by_product

    results = await get_inventory_by_product(product_name, warehouse_code)

    if not results:
        return json.dumps({
            "found":   False,
            "message": f"No stock found for {product_name}." + (
                f" at {warehouse_code}" if warehouse_code else ""
            ),
        })

    # Build response for each warehouse that has this product
    stock_info = []
    for row in results:
        stock_info.append({
            "warehouse_code": row["warehouse_code"],
            "warehouse_name": row["warehouse_name"],
            "quantity":       row["quantity"],
            "unit":           row.get("unit", "units"),
            "low_stock":      row["quantity"] < 50,
        })

    total_qty = sum(r["quantity"] for r in results)
    return json.dumps({
        "found":        True,
        "product_name": product_name,
        "total_stock":  total_qty,
        "by_warehouse": stock_info,
    })


async def _get_delivery_order(order_id: str = None,
                               driver_id: str = None) -> str:
    from services.supabase_client import get_delivery_order_by_id, get_delivery_orders_by_driver

    order = None
    if order_id:
        order = await get_delivery_order_by_id(order_id)
    elif driver_id:
        orders = await get_delivery_orders_by_driver(driver_id)
        order = orders[0] if orders else None

    if not order:
        return json.dumps({
            "found":   False,
            "message": "Delivery order not found.",
        })

    return json.dumps({
        "found":            True,
        "order_id":         order["order_id"],
        "product_name":     order["product_name"],
        "quantity":         order["quantity"],
        "unit":             order.get("unit", "units"),
        "from_warehouse":   order["from_warehouse_code"],
        "destination":      order["destination_address"],
        "destination_city": order.get("destination_city", ""),
        "priority":         order.get("priority", "normal"),
        "special_notes":    order.get("special_notes", ""),
        "status":           order.get("status", "pending"),
    })


async def _get_all_delivery_orders(driver_id: str) -> str:
    from services.supabase_client import get_delivery_orders_by_driver

    orders = await get_delivery_orders_by_driver(driver_id)

    if not orders:
        return json.dumps({
            "found":   False,
            "message": "No pending delivery orders found for this driver.",
        })

    summary = []
    for o in orders:
        summary.append({
            "order_id":       o["order_id"],
            "product_name":   o["product_name"],
            "quantity":       o["quantity"],
            "unit":           o.get("unit", "units"),
            "destination":    o["destination_address"],
            "priority":       o.get("priority", "normal"),
            "special_notes":  o.get("special_notes", ""),
        })

    return json.dumps({
        "found":        True,
        "total_orders": len(summary),
        "orders":       summary,
    })


async def _list_warehouse_products(warehouse_code: str) -> str:
    from services.supabase_client import get_all_inventory_for_warehouse

    items = await get_all_inventory_for_warehouse(warehouse_code)

    if not items:
        return json.dumps({
            "found":          False,
            "warehouse_code": warehouse_code,
            "message":        f"No products found at {warehouse_code}.",
        })

    products = []
    for item in items:
        products.append({
            "product_name": item["product_name"],
            "quantity":     item["quantity"],
            "unit":         item.get("unit", "units"),
            "low_stock":    item["quantity"] < 50,
        })

    return json.dumps({
        "found":          True,
        "warehouse_code": warehouse_code,
        "product_count":  len(products),
        "products":       products,
    })