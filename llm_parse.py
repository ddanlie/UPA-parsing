import sys

from dotenv import load_dotenv
import os
from typing import Any, cast
from openai import OpenAI
import json

load_dotenv()

LOCAL_LLM = os.getenv("LOCAL_LLM", "false").lower() == "true"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_HOST_BASE_URL = os.getenv("LLM_HOST_BASE_URL", "")
ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")
EMPTY_COLS = ["" for i in range(len(ITEM_COLS))]

models = [
    "runware/qwen3.5-9b",
    "runware/qwen3.5-4b",
    "gemma-4-31b-it",
    "deepseek-v4-flash"
] if not LOCAL_LLM else ["Ling-3.0-tiny-Q6_K.gguf"]

def llm_resolve_cols(text: str) -> list[str]:

    for i, model in enumerate(models):
        try:
            client = OpenAI(
                api_key  = "xxx" if LOCAL_LLM else LLM_API_KEY,
                base_url = "http://127.0.0.1:8080/v1" if LOCAL_LLM else LLM_HOST_BASE_URL
            )
            response = client.chat.completions.create(
                model=model,
                timeout=10,
                messages=[
                    {
                        "role": "user",
                        "content": f"`{text}` Look at the item content description. Parse the following columns: " + ", ".join(ITEM_COLS) + ". If a column is not present, return an empty string for that column. Return only valid JSON.",
                    },
                ],
                reasoning_effort="none",
                extra_body={
                    "enable_thinking": False,
                    "chat_template_kwargs": {
                        "enable_thinking": False
                    }
                },
                response_format=cast(Any, {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "vehicle",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                                "brand": {"type": "string"},
                                "colors": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "motor power": {"type": "number"},
                                "battery power capacity": {"type": "string"},
                                "range": {"type": "number"},
                                "speed": {"type": "number"}
                            },
                            "required": [
                                "url",
                                "name",
                                "price",
                                "brand",
                                "colors",
                                "motor power",
                                "battery power capacity",
                                "range",
                                "speed"
                            ],
                            "additionalProperties": False
                        }
                    }
                })
            )
            break
        except Exception as e:
            print(f"Error with model {model}. Fallback attempts: ({i}/{len(models)}): {e}", file=sys.stderr)
            continue
        
        
        
    if not response.choices[0].message.content:
        return EMPTY_COLS 
    content = response.choices[0].message.content.lstrip()
    try:
        item = json.loads(content)
    except json.JSONDecodeError:
        item, _ = json.JSONDecoder().raw_decode(content)
    
    return [
        str(item.get(col, "")) if col != "colors" else ",".join(item.get(col, [])) for col in ITEM_COLS
    ]
