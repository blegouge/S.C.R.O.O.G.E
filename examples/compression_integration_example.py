#!/usr/bin/env python3
"""
Example integration showing prompt interception before OpenAI/Anthropic calls.
"""
from __future__ import annotations

from compression_middleware import PromptCompressionMiddleware

RAW_CONTEXT_1 = "Status: Bug_X_Resolved\nActive_Branch: main\nOwner: Platform"
RAW_CONTEXT_2 = "We introduced adaptive token thresholds and need to validate cache hit ratio."
RAW_CONTEXT_3 = "Current issue: repeated short prompts should bypass heavy summarization."
LATEST_QUESTION = "Can you package the final request with static, semi-static and dynamic blocks?"


def build_openai_payload() -> dict:
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "Global system prompts, Caveman rules, and skill definitions.",
            },
            {"role": "user", "content": RAW_CONTEXT_1},
            {
                "role": "assistant",
                "content": RAW_CONTEXT_2,
            },
            {"role": "user", "content": RAW_CONTEXT_3},
            {"role": "user", "content": LATEST_QUESTION},
        ],
        "temperature": 0.2,
        "global_state": {"Project": "cursor-config"},
    }

    middleware = PromptCompressionMiddleware(
        default_rate=0.6,
        min_chars_to_compress=400,
        summarizer_mode="auto",
    )
    return middleware.before_llm_call(payload)


def build_anthropic_payload() -> dict:
    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 1200,
        "messages": [
            {
                "role": "system",
                "content": "Global system prompts, Caveman rules, and skill definitions.",
            },
            {"role": "assistant", "content": RAW_CONTEXT_1},
            {"role": "user", "content": RAW_CONTEXT_2},
            {"role": "user", "content": RAW_CONTEXT_3},
            {"role": "user", "content": LATEST_QUESTION},
        ],
        "global_state": {"Project": "cursor-config"},
    }

    middleware = PromptCompressionMiddleware(
        default_rate=0.55,
        min_chars_to_compress=400,
        summarizer_mode="auto",
    )
    return middleware.before_llm_call(payload)


if __name__ == "__main__":
    print("OpenAI payload with compression:")
    print(build_openai_payload())
    print("\nAnthropic payload with compression:")
    print(build_anthropic_payload())
