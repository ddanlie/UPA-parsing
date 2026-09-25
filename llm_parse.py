from dotenv import load_dotenv
import os
from typing import Any, cast
from openai import OpenAI
import json

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_HOST_BASE_URL = os.getenv("LLM_HOST_BASE_URL", "")
ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")
EMPTY_COLS = ["" for i in range(len(ITEM_COLS))]

def llm_resolve_cols(text: str) -> list[str]:
    client = OpenAI(
        api_key=LLM_API_KEY, 
        base_url=LLM_HOST_BASE_URL
    )
    response = client.chat.completions.create(
        model="runware/qwen3.5-9b",
        timeout=5,
        messages=[
            {
                "role": "user",
                "content": f"`{text}` Look at the item content description. Parse the following columns: " + ", ".join(ITEM_COLS) + ". If a column is not present, return an empty string for that column. Return only a JSON object with these column names as keys.",
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