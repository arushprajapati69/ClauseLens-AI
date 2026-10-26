"""Thin Ollama wrapper for ClauseLens AI.

Enforces:
- Native JSON schema structured output via format= parameter.
- Temperature 0 for deterministic outputs.
- Timeout 120s.
- Zero blind retries: failures degrade gracefully to structured error responses.
"""

import json
from typing import Any, Dict, List, Optional
import ollama
import config

ANSWER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bottom_line": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["condition", "deadline", "fee", "exclusion", "eligibility", "other"]
                    },
                    "chunk_id": {"type": "string"},
                    "quote": {"type": "string"}
                },
                "required": ["text", "type", "chunk_id", "quote"]
            }
        },
        "missing_info": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["bottom_line", "claims", "missing_info"]
}

CONFLICT_JUDGE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "relation": {
            "type": "string",
            "enum": ["conflict", "consistent", "unrelated"]
        },
        "topic": {"type": "string"},
        "explanation": {"type": "string"},
        "quote_a": {"type": "string"},
        "quote_b": {"type": "string"}
    },
    "required": ["relation", "topic", "explanation", "quote_a", "quote_b"]
}

REFUND_TIER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "tiers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "min_days_notice": {"type": "integer"},
                    "refund_percent": {"type": "integer"},
                    "chunk_id": {"type": "string"},
                    "quote": {"type": "string"}
                },
                "required": ["min_days_notice", "refund_percent", "chunk_id", "quote"]
            }
        },
        "flat_fee": {"type": "integer"},
        "fee_chunk_id": {"type": "string"},
        "fee_quote": {"type": "string"}
    },
    "required": ["tiers", "flat_fee", "fee_chunk_id", "fee_quote"]
}


class LLMClient:
    def __init__(self, host: str = config.OLLAMA_HOST, model: str = config.GEN_MODEL, timeout: float = config.LLM_TIMEOUT):
        self.host = host
        self.model = model
        self.timeout = timeout
        self.client = ollama.Client(host=self.host, timeout=self.timeout)

    def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calls Ollama chat with JSON schema enforcement and temperature 0.
        
        Zero blind retries: returns {"ok": True, "data": dict} or {"ok": False, "error": str}.
        """
        chosen_model = model or self.model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat(
                model=chosen_model,
                messages=messages,
                format=schema,
                options={"temperature": 0.0, "num_predict": 180}
            )
            raw_content = response.message.content.strip()
            parsed = json.loads(raw_content)
            return {"ok": True, "data": parsed, "raw": raw_content}
        except json.JSONDecodeError as jde:
            return {"ok": False, "error": f"Failed to parse model JSON: {jde}", "raw": raw_content if 'raw_content' in locals() else ""}
        except Exception as e:
            return {"ok": False, "error": f"Ollama chat call failed: {e}"}
