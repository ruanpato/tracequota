# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Nullable measured quantities plus documented normalization provenance."""

KEYS = {
    "input_total": (
        "tracequota.usage.input_total",
        "gen_ai.usage.input_tokens",
        "llm.token_count.prompt",
        "input_token_count",
    ),
    "input_uncached": ("tracequota.usage.input_uncached",),
    "cache_read": (
        "tracequota.usage.cache_read",
        "cache_read_tokens",
        "cached_token_count",
        "gen_ai.usage.cache_read.input_tokens",
        "llm.token_count.prompt_details.cache_read",
    ),
    "cache_write": (
        "tracequota.usage.cache_write",
        "cache_creation_tokens",
        "gen_ai.usage.cache_creation.input_tokens",
        "llm.token_count.prompt_details.cache_write",
    ),
    "output_total": (
        "tracequota.usage.output_total",
        "output_tokens",
        "output_token_count",
        "gen_ai.usage.output_tokens",
        "llm.token_count.completion",
    ),
    "reasoning": ("tracequota.usage.reasoning", "reasoning_token_count", "gen_ai.usage.reasoning.output_tokens"),
    "cache_storage_token_hours": ("tracequota.usage.cache_storage_token_hours",),
    "tool_requests": ("tracequota.usage.tool_requests",),
}


def normalize(attrs, client):
    warnings = []
    sources = {}
    usage = {}
    for metric, keys in KEYS.items():
        key = next((k for k in keys if k in attrs), None)
        quantity = None
        if key:
            try:
                raw = attrs[key]
                quantity = int(raw)
                if quantity < 0 or quantity != float(raw):
                    raise ValueError()
                sources[metric] = key
            except (ValueError, TypeError, OverflowError):
                quantity = None
                warnings.append(f"Invalid usage: {metric}")
        usage[metric] = quantity
    semantics = attrs.get("tracequota.usage.input_semantics", "unknown")
    if client == "claude_code" and "input_tokens" in attrs:
        semantics = "uncached"
        try:
            usage["input_uncached"] = int(attrs["input_tokens"])
            if usage["input_uncached"] < 0:
                raise ValueError()
            sources["input_uncached"] = "input_tokens"
        except (ValueError, TypeError):
            usage["input_uncached"] = None
            warnings.append("Invalid usage: input_uncached")
    elif semantics == "uncached" and usage["input_uncached"] is None:
        usage["input_uncached"] = usage["input_total"]
        usage["input_total"] = None
    elif semantics == "inclusive" and usage["input_uncached"] is None:
        values = [usage[k] for k in ("input_total", "cache_read", "cache_write")]
        if all(v is not None for v in values):
            quantity = values[0] - values[1] - values[2]
            if quantity >= 0:
                usage["input_uncached"] = quantity
            else:
                warnings.append("Cache quantities exceed inclusive input")
    if usage["input_total"] is None and all(
        usage[k] is not None for k in ("input_uncached", "cache_read", "cache_write")
    ):
        usage["input_total"] = sum(usage[k] for k in ("input_uncached", "cache_read", "cache_write"))
    if usage["input_uncached"] is None:
        warnings.append("Uncached input unavailable; input semantics may be unknown")
    output_semantics = attrs.get("tracequota.usage.output_semantics", "unknown")
    # Separate reasoning must not be added to output if output already includes it.
    if (
        output_semantics == "exclusive_reasoning"
        and usage["output_total"] is not None
        and usage["reasoning"] is not None
    ):
        usage["output_total"] += usage["reasoning"]
    return {
        **usage,
        "input_semantics": semantics,
        "output_semantics": output_semantics,
        "usage_semantics": "derived"
        if semantics == "inclusive" and usage["input_uncached"] is not None
        else "client_native"
        if client == "claude_code" and "input_tokens" in attrs
        else "partial"
        if warnings
        else "unknown"
        if semantics == "unknown"
        else "provider_native",
        "usage_source": sources,
        "normalizer": client if client != "unknown" else "generic",
        "normalizer_version": "1",
        "warnings": warnings,
    }
