# nanda_adapter/core/agentfacts.py
import os, json, datetime as dt
from typing import Any, Dict, Optional

try:
    from pymongo import MongoClient  # optional
except Exception:
    MongoClient = None

class AgentFacts:
    """
    Minimal AgentFacts store:
      - If MONGO_URL provided and PyMongo available, use MongoDB
      - Else fall back to a local JSON file (agent_facts.json)
    Sync API so you can call from non-async code.
    """
    def __init__(self, mongo_url: Optional[str] = None, db_name: str = "agent_registry"):
        self._use_mongo = False
        self._col = None
        self._file_path = os.path.join(os.getcwd(), "agent_facts.json")

        if mongo_url and MongoClient is not None:
            try:
                client = MongoClient(mongo_url, serverSelectionTimeoutMS=1500)
                db = client[db_name]
                # quick ping
                _ = client.server_info()
                self._col = db["agent_facts"]
                self._use_mongo = True
            except Exception:
                self._use_mongo = False  # fallback to file

    def _now(self) -> str:
        return dt.datetime.utcnow().isoformat()

    def _file_load(self) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self._file_path):
            return {}
        try:
            with open(self._file_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _file_save(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self._file_path, "w") as f:
            json.dump(data, f, indent=2)

    def set(self, agent_id: str, key: str, value: Dict[str, Any]) -> None:
        rec = {"agent_id": agent_id, "key": key, "value": value, "ts": self._now()}
        if self._use_mongo:
            self._col.update_one({"agent_id": agent_id, "key": key}, {"$set": rec}, upsert=True)
            return
        data = self._file_load()
        data[f"{agent_id}:{key}"] = rec
        self._file_save(data)

    def get(self, agent_id: str, key: str) -> Optional[Dict[str, Any]]:
        if self._use_mongo:
            return self._col.find_one({"agent_id": agent_id, "key": key}, {"_id": 0})
        data = self._file_load()
        return data.get(f"{agent_id}:{key}")

    def list(self, agent_id: str) -> Dict[str, Dict[str, Any]]:
        if self._use_mongo:
            out = {}
            for doc in self._col.find({"agent_id": agent_id}, {"_id": 0}):
                out[doc["key"]] = doc
            return out
        data = self._file_load()
        return {k.split(":", 1)[1]: v for k, v in data.items() if k.startswith(f"{agent_id}:")}
