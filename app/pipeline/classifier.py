import json
import asyncio
from typing import List
from openai import AsyncOpenAI
from .prompts import CLASSIFY_PROMPT

MODEL_NAME = "qwen/qwen3.5-35b-a3b"
N_SAMPLES = 3


async def _classify_single(client: AsyncOpenAI, content: str) -> List[str]:
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "classification_result",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "categories": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["categories"],
                        "additionalProperties": False,
                    },
                },
            },
            temperature=0.7,  # Slight randomness for self-consistency
        )

        reply = response.choices[0].message.content.strip()
        # Clean up Markdown json blocks if present
        if reply.startswith("```json"):
            reply = reply[7:-3].strip()
        elif reply.startswith("```"):
            reply = reply[3:-3].strip()

        data = json.loads(reply)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "categories" in data:
            return data.get("categories", [])
        return []
    except Exception as e:
        print(f"Classification error: {e}")
        return []


async def classify_content(client: AsyncOpenAI, content: str) -> List[str]:
    """Runs classification N times and takes the majority vote for categories."""
    tasks = [_classify_single(client, content) for _ in range(N_SAMPLES)]
    results = await asyncio.gather(*tasks)

    category_counts = {}
    for res in results:
        for cat in set(res):  # use set to avoid double-counting within one response
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Majority vote: threshold is N_SAMPLES // 2 + 1 (i.e., at least 2 out of 3)
    threshold = N_SAMPLES // 2 + 1
    final_categories = [
        cat for cat, count in category_counts.items() if count >= threshold
    ]

    # Simple validation against allowed list to prevent hallucinated categories
    allowed = {
        "Provokasi",
        "SARA",
        "Separatisme",
        "Disinformasi",
        "Ujaran Kebencian",
        "Hoaks",
        "Penghinaan",
        "Makar",
        "Ancaman",
        "Pelanggaran Keamanan Informasi",
        "Kekerasan",
        "Penistaan Agama",
        "Misinformasi",
    }

    return [c for c in final_categories if c in allowed]
