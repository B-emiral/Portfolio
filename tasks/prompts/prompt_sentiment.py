# ./tasks/prompts/prompt_sentiment.py
from __future__ import annotations

INSTRUCTION = """ Classify the sentiment. Respond ONLY with JSON:
        '{"sentiment": "<positive|neutral|negative>", "confidence": 0..1}.' """

FEW_SHOTS = [
    {
        "text": "I absolutely love this product! Exceeded expectations.",
        "sentiment": "positive",
        "confidence": 0.95,
    },
    {
        "text": "Terrible service, complete waste of money.",
        "sentiment": "negative",
        "confidence": 0.92,
    },
    {
        "text": "The weather is cloudy today.",
        "sentiment": "neutral",
        "confidence": 0.80,
    },
]


def build_sentiment_prompt(text: str, in_context_learning: str = "zero-shot") -> str:
    lines: list[str] = []
    lines.append(INSTRUCTION)
    if in_context_learning == "zero-shot":
        pass
    elif in_context_learning == "few-shot":
        lines.append("Examples:")
        for ex in FEW_SHOTS:
            lines.append(
                f'input: "{ex["text"]}"\noutput:'
                f'{{"sentiment": "{ex["sentiment"]}", "confidence":{ex["confidence"]}}}'
            )
    else:
        # fallback to basic
        pass
    lines.append("-------YOUR TURN-------")
    lines.append(f'Input: "{text}"')
    return "\n".join(lines)
