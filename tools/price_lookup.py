import json
import os
from tavily import TavilyClient
from config import TAVILY_API_KEY, PRICES_FALLBACK_PATH

_tavily = None


def _get_tavily():
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
    return _tavily


def _load_fallback() -> dict:
    if os.path.exists(PRICES_FALLBACK_PATH):
        with open(PRICES_FALLBACK_PATH, "r") as f:
            return json.load(f)
    return {}


def lookup_price(model: str, variant: str = None) -> str:
    """
    Tool: Look up the price of a Kia model.
    Primary: Tavily web search on kia.com/us
    Fallback: local prices.json
    """
    # --- Tavily web search ---
    try:
        client = _get_tavily()
        query = f"Kia {model} {variant or ''} MSRP price 2024 2025 site:kia.com/us".strip()
        results = client.search(
            query=query,
            search_depth="basic",
            include_domains=["kia.com"],
            max_results=3,
        )
        snippets = [r["content"] for r in results.get("results", []) if r.get("content")]
        if snippets:
            combined = "\n".join(snippets[:3])
            return (
                f"Pricing information from kia.com/us for Kia {model}"
                f"{' ' + variant if variant else ''}:\n\n{combined}"
            )
    except Exception as e:
        print(f"  [PriceLookup] Tavily failed: {e}. Using fallback.")

    # --- Fallback: prices.json ---
    fallback = _load_fallback()
    model_data = fallback.get(model)
    if not model_data:
        return f"Price information for Kia {model} is not available. Please visit kia.com/us or contact us directly."

    if variant and variant in model_data:
        price = model_data[variant]
        return f"Kia {model} {variant}: Starting at ${price:,} MSRP (fallback data — verify at kia.com/us)"

    # Return all variants
    lines = [f"Kia {model} pricing (fallback data — verify at kia.com/us):"]
    for v, p in model_data.items():
        lines.append(f"  {v}: ${p:,}")
    return "\n".join(lines)
