"""
Grounded Forecaster Copilot — Grok-powered (xAI) with tool-calling.

Architecture:
  User question (any language)
      ↓
  Grok (understands intent + language via xAI OpenAI-compatible API)
      ↓
  Calls grounded tool functions (data from results/)
      ↓
  Grok formats answer in user's language with citations
      ↓
  EXERCISE disclaimer always appended

Hard rules:
  - The LLM may ONLY state numbers returned by a tool call.
  - Every claim must have a [Source: ...] citation.
  - Every answer carries the EXERCISE disclaimer.
  - If no tool returns the data, say "I don't have that data."
"""

import json
import math
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

RESULTS_DIR = Path(__file__).parent.parent / "results"
DISCLAIMER = "⚠️ EXERCISE — This is a prototype output from SIH26081 ForeBlendCast. NOT an official IMD warning."

SYSTEM_PROMPT = """You are the ForeBlendCast Forecaster Copilot — a grounded disaster-warning assistant for India's National Weather Service.

HARD RULES:
1. You may ONLY state numbers returned by the tool calls below. NEVER invent, estimate, or guess any number.
2. Every number you mention MUST have a citation like [Source: results/districts_L1.json → field_name].
3. Every response MUST end with: "⚠️ EXERCISE — This is a prototype output from SIH26081 ForeBlendCast. NOT an official IMD warning."
4. If the user asks something the tools cannot answer, say "I don't have that data in my results."
5. You understand Hindi (हिन्दी), Bengali (বাংলা), Tamil (தமிழ்), Telugu (తెలుగు), Marathi (मराठी), and all Indian languages. Reply in the same language the user uses.
6. You are helpful, concise, and structured. Use markdown formatting with bold for key numbers.
7. When explaining why a district is at a certain alert tier, always mention: probabilities, blend weights, LOMO sensitivity, and model disagreement.
8. Thresholds: Green <64.5mm, Yellow ≥64.5mm, Orange ≥115.6mm, Red ≥204.5mm (IMD classification).
"""

# ═══════════════════════════════════════════════════════════════
#  Tool functions — these read ONLY from results/ files
# ═══════════════════════════════════════════════════════════════

def lookup_district(district_name: str, lead_day: int = 1) -> dict:
    """Look up forecast data for a specific district by name."""
    file_path = RESULTS_DIR / f"districts_L{lead_day}.json"
    if not file_path.exists():
        return {"error": "No forecast data available", "source": f"results/districts_L{lead_day}.json"}
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    districts = data.get("districts", [])
    q = district_name.strip().lower()
    
    for d in districts:
        if d["id"].lower() == q or d["name"].lower() == q:
            d["_source"] = f"results/districts_L{lead_day}.json"
            return d
    
    for d in districts:
        if q in d["name"].lower() or q in d["id"].lower():
            d["_source"] = f"results/districts_L{lead_day}.json"
            return d
    
    return {"error": f"District '{district_name}' not found", "source": f"results/districts_L{lead_day}.json"}


def list_alert_districts(tier: str = "red", lead_day: int = 1) -> dict:
    """List all districts at a given alert tier (red, orange, yellow, green)."""
    file_path = RESULTS_DIR / f"districts_L{lead_day}.json"
    if not file_path.exists():
        return {"error": "No forecast data available"}
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    districts = data.get("districts", [])
    filtered = [d for d in districts if d["tier"].lower() == tier.lower()]
    
    summary = []
    for d in filtered:
        summary.append({
            "name": d["name"],
            "state": d["state"],
            "tier": d["tier"],
            "p_gt_115p6": d["p_gt_115p6"],
            "population": d["population"],
            "precip_p90_mm": d["precip_p90_mm"],
        })
    
    return {
        "tier": tier,
        "count": len(filtered),
        "total_population": sum(d["population"] for d in filtered),
        "districts": summary,
        "_source": f"results/districts_L{lead_day}.json"
    }


def get_verification_ladder() -> dict:
    """Get the verification ladder showing skill scores (RMSE, MAE, FSS) for each model strategy."""
    file_path = RESULTS_DIR / "ladder.json"
    if not file_path.exists():
        return {"error": "No ladder data available"}
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    rows = []
    for row in data.get("rows", []):
        m = row.get("metrics", {}).get("L1", {})
        rmse = m.get("rmse", None)
        mae = m.get("mae", None)
        fss = m.get("fss50", None)
        def _finite(x):
            return x if isinstance(x, (int, float)) and math.isfinite(x) else None
        rows.append({
            "rung": row["rung"],
            "strategy": row["strategy"],
            "rmse": _finite(rmse),
            "mae": _finite(mae),
            "fss50": _finite(fss),
        })
    
    return {"rows": rows, "_source": "results/ladder.json"}


def get_alert_summary(lead_day: int = 1) -> dict:
    """Get a summary count of districts by alert tier."""
    file_path = RESULTS_DIR / f"districts_L{lead_day}.json"
    if not file_path.exists():
        return {"error": "No forecast data available"}
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    districts = data.get("districts", [])
    meta = data.get("meta", {})
    
    counts = {"red": 0, "orange": 0, "yellow": 0, "green": 0}
    pops = {"red": 0, "orange": 0, "yellow": 0, "green": 0}
    for d in districts:
        t = d["tier"].lower()
        if t in counts:
            counts[t] += 1
            pops[t] += d["population"]
    
    return {
        "cycle": meta.get("cycle", "unknown"),
        "total_districts": len(districts),
        "counts": counts,
        "exposed_population": pops,
        "_source": f"results/districts_L{lead_day}.json"
    }


# ═══════════════════════════════════════════════════════════════
#  OpenAI-compatible tool schemas for xAI Grok
# ═══════════════════════════════════════════════════════════════

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_district",
            "description": "Look up forecast data for a specific district by name. Returns alert tier, probabilities, blend weights, LOMO sensitivity, population, and model disagreement. Use this whenever the user asks about a specific district.",
            "parameters": {
                "type": "object",
                "properties": {
                    "district_name": {
                        "type": "string",
                        "description": "The name of the district to look up (e.g. 'Nalbari', 'Kamrup', 'Dhubri')"
                    },
                    "lead_day": {
                        "type": "integer",
                        "description": "The forecast lead day (default 1)",
                        "default": 1
                    }
                },
                "required": ["district_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_alert_districts",
            "description": "List all districts at a given alert tier (red, orange, yellow, green). Use when the user asks 'which districts are red?' or 'show all orange alerts' or 'how many red districts?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "string",
                        "description": "The alert tier to filter by: 'red', 'orange', 'yellow', or 'green'",
                        "enum": ["red", "orange", "yellow", "green"]
                    },
                    "lead_day": {
                        "type": "integer",
                        "description": "The forecast lead day (default 1)",
                        "default": 1
                    }
                },
                "required": ["tier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_verification_ladder",
            "description": "Get the verification ladder showing skill scores (RMSE, MAE, FSS) for each model strategy. Use when the user asks about accuracy, skill, or model performance.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_alert_summary",
            "description": "Get a summary count of districts by alert tier. Use when the user asks for an overview or general status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_day": {
                        "type": "integer",
                        "description": "The forecast lead day (default 1)",
                        "default": 1
                    }
                }
            }
        }
    }
]

# Map function names to actual functions
TOOL_FUNCTIONS = {
    "lookup_district": lookup_district,
    "list_alert_districts": list_alert_districts,
    "get_verification_ladder": get_verification_ladder,
    "get_alert_summary": get_alert_summary,
}


# ═══════════════════════════════════════════════════════════════
#  Copilot engine using xAI Grok (OpenAI-compatible)
# ═══════════════════════════════════════════════════════════════

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("XAI_API_KEY", "").strip()
        if not api_key:
            return None
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


async def ask_copilot(question: str, lead_day: int = 1) -> dict:
    """
    Process a user question through the grounded Groq copilot.
    Falls back to deterministic mode if no API key is configured.
    """
    client = _get_client()

    if client is None:
        return None  # Signal caller to use the old deterministic path

    augmented = f"[Context: lead_day={lead_day}]\n\nUser: {question}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": augmented},
    ]

    sources = set()
    max_rounds = 5  # Safety limit for tool-call loops

    try:
        for _ in range(max_rounds):
            response = await client.chat.completions.create(
                model=os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b"),
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.3,
            )

            choice = response.choices[0]

            # If no tool calls, we have the final answer
            if choice.finish_reason != "tool_calls" or not choice.message.tool_calls:
                answer_text = choice.message.content or "I could not generate a response."
                break

            # Process tool calls
            # Add assistant message with tool calls to conversation
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                # Execute the grounded tool function
                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn is None:
                    result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        result = {"error": str(e)}

                # Track sources
                if isinstance(result, dict) and "_source" in result:
                    sources.add(result["_source"])

                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })
        else:
            answer_text = "I ran out of processing steps. Please try a simpler question."

        # Ensure disclaimer
        if "EXERCISE" not in answer_text:
            answer_text += f"\n\n{DISCLAIMER}"

        # If no sources were collected, infer from the default
        if not sources:
            sources.add(f"results/districts_L{lead_day}.json")

        return {
            "answer": answer_text,
            "disclaimer": DISCLAIMER,
            "sources": list(sources),
            "mode": "grok",
        }

    except Exception as e:
        print(f"[Copilot] Grok error: {e}")
        return None  # Fall back to deterministic
