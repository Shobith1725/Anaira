from groq import Groq
from config import settings
import json

client = Groq(api_key=settings.GROQ_API_KEY)

# ── TOOL SCHEMAS passed to Groq ───────────────────────────────────────
LOGISTICS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "identify_shipment",
            "description": "Identify a shipment by tracking number or driver ID. Call when driver mentions a shipment, package, or tracking number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {"type": "string", "description": "e.g. TRK-124"},
                    "driver_id":       {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_delivery",
            "description": "Confirm a delivery is complete. Call when driver says delivery is done, delivered, completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_id":    {"type": "string"},
                    "recipient_name": {"type": "string"},
                    "proof_type": {
                        "type": "string",
                        "enum": ["signature", "photo", "left_at_door",
                                 "customer_absent", "handed_to_neighbor"],
                    },
                },
                "required": ["shipment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_shipment_status",
            "description": "Update shipment status. Use for pickup confirmed, out for delivery, failed attempts, returns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_transit", "out_for_delivery",
                                 "delivered", "failed", "returned", "damaged"],
                    },
                    "notes": {"type": "string"},
                },
                "required": ["shipment_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_delay",
            "description": "Report a delivery delay. Call when driver mentions being late, stuck, blocked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_id":             {"type": "string"},
                    "reason":                  {"type": "string"},
                    "estimated_delay_minutes": {"type": "integer"},
                },
                "required": ["shipment_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_stop",
            "description": "Get the next delivery stop on driver's route. Call when driver asks where to go next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "driver_id":    {"type": "string"},
                    "current_stop": {"type": "integer"},
                },
                "required": ["driver_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_damage",
            "description": "Report a damaged package. Call when driver mentions damage, crushed box, broken items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_id": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["shipment_id", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_reroute",
            "description": "Request a route change. Call when driver reports a blocked road, accident, or obstacle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_id":          {"type": "string"},
                    "obstacle_description": {"type": "string"},
                },
                "required": ["shipment_id", "obstacle_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate to a human dispatcher. Use for emergencies, breakdowns, complex issues AI cannot resolve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason":      {"type": "string"},
                    "urgency":     {"type": "string", "enum": ["low", "medium", "high", "emergency"]},
                    "shipment_id": {"type": "string"},
                },
                "required": ["reason", "urgency"],
            },
        },
    },
]

RECEPTIONIST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_slots",
            "description": "Check available appointment slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string"},
                },
                "required": ["business_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment slot for a caller.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string"},
                    "caller_id":   {"type": "string"},
                    "slot_time":   {"type": "string"},
                    "notes":       {"type": "string"},
                },
                "required": ["business_id", "caller_id", "slot_time"],
            },
        },
    },
]


def _build_system_prompt(driver_name:      str,
                          emotion_directive: str,
                          active_shipments:  list,
                          current_route:     dict,
                          mode:              str) -> str:
    # ✅ FIXED: detected_language removed entirely.
    # Language is hardcoded to English in both the prompt and DeepGram params.
    # Previously, DeepGram's detected_language field returned 'es' even when
    # language='en' was set, causing Groq to respond in Spanish.

    if mode == "logistics":
        shipment_summary = ""
        if active_shipments:
            lines = [
                f"  - {s['tracking_number']}: {s['status']} → {s['destination']}"
                for s in active_shipments[:5]
            ]
            shipment_summary = "DRIVER'S ACTIVE SHIPMENTS:\n" + "\n".join(lines)

        route_summary = ""
        if current_route and current_route.get("waypoints"):
            wps   = current_route["waypoints"]
            stops = [
                f"  Stop {w['stop']}: {w['address']} ({w.get('type', '')})"
                for w in wps
            ]
            route_summary = "DRIVER'S ROUTE:\n" + "\n".join(stops)

        return f"""You are ANAIRA, an AI voice dispatch assistant for a logistics company.

DRIVER NAME: {driver_name}
LANGUAGE: You MUST always respond in English only. Never use any other language under any circumstances.
TONE DIRECTIVE: {emotion_directive}

{shipment_summary}

{route_summary}

YOUR ROLE:
- Help drivers confirm deliveries, report delays, get next stop directions
- Identify shipments from context — driver may say "the package" or just a number
- Always confirm the action you took out loud so driver knows it worked
- Keep every response UNDER 30 WORDS — drivers are on the road
- For route guidance speak the address simply and clearly
- If driver has an emergency, escalate immediately

RULES:
- Never invent shipment details — always use tools to look them up
- Never reveal you are an AI unless directly asked
- Always confirm every database action out loud
- ENGLISH ONLY — regardless of what language the driver speaks in"""

    else:
        return f"""You are ANAIRA, an AI receptionist assistant.

CALLER NAME: {driver_name}
LANGUAGE: You MUST always respond in English only. Never use any other language.
TONE DIRECTIVE: {emotion_directive}

YOUR ROLE:
- Help callers book and manage appointments
- Be warm, professional, and efficient
- Keep responses concise and clear

RULES:
- Always use tools to check and book slots — never guess availability
- Confirm every booking out loud with the date and time
- ENGLISH ONLY — regardless of what language the caller speaks in"""


async def respond(transcript:        str,
                  emotion_directive:  str,
                  driver_name:        str,
                  driver_id:          str,
                  detected_language:  str,   # kept in signature for compatibility
                  turn_history:       list,
                  active_shipments:   list,
                  current_route:      dict,
                  mode:               str,
                  tool_executor) -> tuple[str, list]:
    """
    Main LLM call.
    Returns (response_text, updated_turn_history).
    detected_language param kept for call-site compatibility but is no longer
    used inside — English is hardcoded throughout.
    """
    system_prompt = _build_system_prompt(
        driver_name       = driver_name,
        emotion_directive = emotion_directive,
        # ✅ detected_language NOT passed — removed from _build_system_prompt
        active_shipments  = active_shipments,
        current_route     = current_route,
        mode              = mode,
    )

    tools = LOGISTICS_TOOLS if mode == "logistics" else RECEPTIONIST_TOOLS

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(turn_history[-8:])
    messages.append({"role": "user", "content": transcript})

    # ── First LLM call ────────────────────────────────────────
    response = client.chat.completions.create(
        model       = "llama-3.3-70b-versatile",
        messages    = messages,
        tools       = tools,
        tool_choice = "auto",
        temperature = 0.3,
        max_tokens  = 200,
    )

    msg = response.choices[0].message

    # ── Tool call loop ────────────────────────────────────────
    while msg.tool_calls:
        messages.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)

            print(f"[TOOL CALL] {tool_name}({tool_args})")
            result = await tool_executor(tool_name, tool_args)
            print(f"[TOOL RESULT] {result[:120]}")

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result,
            })

        response = client.chat.completions.create(
            model       = "llama-3.3-70b-versatile",
            messages    = messages,
            temperature = 0.3,
            max_tokens  = 200,
        )
        msg = response.choices[0].message

    final_text = (msg.content or "Done, noted.").strip()

    # Update turn history
    turn_history.append({"role": "user",      "content": transcript})
    turn_history.append({"role": "assistant", "content": final_text})
    turn_history = turn_history[-8:]

    return final_text, turn_history