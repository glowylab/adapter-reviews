# nanda_adapter/core/payments.py
"""
Payment and A2A quote system for NANDA agents.
- Uses Claude to check if a peer agent can accept payment.
- Reads/writes AgentFacts (wallets, txns, questions).
- Sends payment quotes over A2A (x402-compatible).
"""

import os, time, json, hashlib, requests
from datetime import datetime
from nanda_adapter.core.agentfacts import AgentFacts

REGISTRY_URL = os.getenv("REGISTRY_URL")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "agent_registry")

facts = AgentFacts(MONGO_URL, DB_NAME)

# ---- helpers --------------------------------------------------------------
def _now_iso(): return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def _qhash(s: str): return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
def _af_get(aid, key): return facts.get(aid, key)
def _af_set(aid, key, val): facts.set(aid, key, val)

def _points_get(owner: str) -> int:
    row = _af_get(owner, f"wallet:{owner}")
    return int(row["value"].get("balance", 0)) if row else 0

def _points_set(owner: str, balance: int):
    _af_set(owner, f"wallet:{owner}", {
        "@type": "AgentFacts",
        "category": "wallet",
        "owner": owner,
        "balance": balance,
        "observedAt": _now_iso()
    })

def _txn_add(txn_id, from_user, to_agent, points, question, peer_agent_id):
    _af_set(to_agent, f"txn:{txn_id}", {
        "@type": "AgentFacts",
        "category": "transaction",
        "txnId": txn_id,
        "from": from_user,
        "to": to_agent,
        "points": points,
        "question": question,
        "peer_agent": peer_agent_id,
        "observedAt": _now_iso()
    })

def _resolve_agent(agent_or_id: str):
    try:
        r = requests.post(f"{REGISTRY_URL}/resolve", json={"agent_id": agent_or_id}, timeout=10)
        if r.status_code == 404: return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[resolve] error: {e}")
        return None

def _send_a2a(receiver_id: str, payload: dict) -> dict:
    info = _resolve_agent(receiver_id)
    if not info or not info.get("agent_url"):
        raise RuntimeError("A2A resolution failed")
    endpoint = info["agent_url"].rstrip("/") + "/handle_external_message"
    r = requests.post(endpoint, json={"from": os.getenv("AGENT_ID","default"), "message": payload}, timeout=20)
    r.raise_for_status()
    return r.json()

def _claude_can_accept_payment(peer_card: dict | None) -> bool:
    card = peer_card or {}
    base = card.get("card") if isinstance(card.get("card"), dict) else card
    econ = (base or {}).get("economy", {})
    caps = (base or {}).get("capabilities", {})

    # heuristic if no API key
    if not ANTHROPIC_API_KEY:
        has_points = isinstance(econ.get("pricing"), dict)
        has_cap = "payments.points" in json.dumps(caps) or "x402" in json.dumps(caps)
        return has_points or has_cap

    # real Claude query
    try:
        prompt = (
            "Check if an AI agent can accept payment from its AgentFacts JSON. "
            "Return only 'true' or 'false'.\n\n"
            f"AgentFacts: {json.dumps(base, ensure_ascii=False)}"
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 20,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        resp.raise_for_status()
        text = "".join(block.get("text","") if isinstance(block,dict) else block for block in resp.json().get("content",[]))
        t = text.strip().lower()
        return "true" in t and "false" not in t
    except Exception as e:
        print(f"[claude] fallback: {e}")
        return bool(econ or caps)

def _decide_points(question: str, seen_before: bool) -> int:
    base = 6
    if len(question) > 120: base += 2
    if any(k in question.lower() for k in ["matrix","gaussian","proof","opencv","unreal","swiftui","jetson","agent"]):
        base += 2
    if seen_before: base -= 2
    return max(5, min(10, base))

# ---- Main quote & charge ---------------------------------------------------
def quote_and_charge_points_via_a2a(username: str, peer_identifier: str, question: str, use_x402: bool = True) -> dict:
    peer = _resolve_agent(peer_identifier)
    if not peer: return {"ok": False, "error": "peer_not_found"}
    peer_id = peer["agent_id"]

    can_accept = _claude_can_accept_payment(peer)
    if not can_accept:
        return {"ok": False, "error": "peer_cannot_accept_payment"}

    self_id = os.getenv("AGENT_ID","default")
    qkey = f"q:{username}:{_qhash(question)}"
    seen = _af_get(self_id, qkey) is not None
    _af_set(self_id, qkey, {
        "@type": "AgentFacts",
        "category": "interaction",
        "user": username,
        "question": question,
        "observedAt": _now_iso()
    })

    if seen:
        payload = {"type": "quote", "points": 0, "reason": "repeat_question"}
        try: a2a_resp = _send_a2a(peer_id, payload)
        except Exception as e: a2a_resp = {"error": str(e)}
        return {"ok": True, "charged": False, "points": 0, "a2a_response": a2a_resp}

    points = _decide_points(question, seen_before=False)
    user_bal = _points_get(username)
    if user_bal < points:
        return {"ok": False, "error": "insufficient_points", "required": points, "available": user_bal}

    _points_set(username, user_bal - points)
    agent_bal = _points_get(self_id)
    _points_set(self_id, agent_bal + points)

    txn_id = f"txn_{int(time.time())}_{_qhash(username+question)}"
    _txn_add(txn_id, username, self_id, points, question, peer_id)

    payload = {
        "type": "x402.quote" if use_x402 else "price_quote",
        "amount_points": points,
        "currency": "POINTS",
        "question": question
    }
    try: a2a_resp = _send_a2a(peer_id, payload)
    except Exception as e: a2a_resp = {"error": str(e)}

    return {"ok": True, "charged": True, "points": points, "txn_id": txn_id, "a2a_response": a2a_resp}
