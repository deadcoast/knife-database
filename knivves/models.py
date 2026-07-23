from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

NULLISH = {"", "none", "null", "unknown", "—", "-"}


def clean_text(value: Any, fallback: str = "Unknown") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return fallback if text.lower() in NULLISH else text


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = value.replace(".", "-").replace("/", "-").replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "unnamed-knife"


def normalize_classification(value: Any) -> str:
    if value is None:
        return "unclassified"
    text = str(value).strip().lower()
    if text in {"approved", "rejected", "unclassified"}:
        return text
    return text or "unclassified"


def coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace("CAD", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class KnifeView:
    """Read-only view wrapper around one raw knife record."""

    raw: dict[str, Any]

    @property
    def id(self) -> str:
        return clean_text(self.raw.get("id"), "")

    @property
    def brand(self) -> str:
        return clean_text(self.raw.get("brand"))

    @property
    def model(self) -> str:
        return clean_text(self.raw.get("model"))

    @property
    def display_name(self) -> str:
        if self.brand == "Unknown" and self.model == "Unknown":
            return self.id or "Unknown knife"
        if self.brand == "Unknown":
            return self.model
        if self.model == "Unknown":
            return self.brand
        return f"{self.brand} {self.model}"

    @property
    def classification(self) -> str:
        return normalize_classification(self.raw.get("user_classification"))

    @property
    def tags(self) -> list[str]:
        tags = self.raw.get("user_tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, list):
            return []
        return [str(tag).strip() for tag in tags if str(tag).strip()]

    @property
    def sections(self) -> list[str]:
        """SectionIDs — the application's formal word for tags. Same storage."""
        return self.tags

    @property
    def is_new(self) -> bool:
        """Materialized freshness flag, governed by the update generations."""
        return bool(self.raw.get("new"))

    @property
    def buy_priority(self) -> int | None:
        """BuyList rank (1 = most sought), materialized from the buy list."""
        value = self.raw.get("buy_priority")
        return value if isinstance(value, int) and value > 0 else None

    @property
    def date_added(self) -> str:
        return clean_text(self.raw.get("date_added"), "")

    @property
    def research_status(self) -> str:
        return clean_text(self.raw.get("research_status"), "unknown")

    @property
    def acquisition_status(self) -> str:
        return clean_text(self.raw.get("acquisition_status"), "unknown")

    @property
    def mechanism(self) -> dict[str, Any]:
        mechanism = self.raw.get("mechanism") or {}
        return mechanism if isinstance(mechanism, dict) else {}

    @property
    def opening_method(self) -> str:
        return clean_text(self.mechanism.get("opening_method"))

    @property
    def lock_type(self) -> str:
        return clean_text(self.mechanism.get("lock_type"))

    @property
    def assist_type(self) -> str:
        return clean_text(self.mechanism.get("assist_type"))

    @property
    def blade_length(self) -> str:
        return clean_text(self.mechanism.get("blade_length"))

    @property
    def blade_steel(self) -> str:
        return clean_text(self.mechanism.get("blade_steel"))

    @property
    def prohibited_flag_value(self) -> bool | None:
        value = self.mechanism.get("clear_prohibited_mechanism_found")
        return value if isinstance(value, bool) else None

    @property
    def prohibited_flag(self) -> str:
        if self.prohibited_flag_value is True:
            return "yes"
        if self.prohibited_flag_value is False:
            return "no"
        return "unknown"

    @property
    def retailers(self) -> list[dict[str, Any]]:
        retailers = self.raw.get("canadian_online_retailers") or []
        return [r for r in retailers if isinstance(r, dict)]

    @property
    def retailer_count(self) -> int:
        return len(self.retailers)

    @property
    def has_canadian_retailer(self) -> bool:
        return self.retailer_count > 0

    @property
    def retailer_names(self) -> list[str]:
        return [clean_text(r.get("retailer"), "Unknown retailer") for r in self.retailers]

    @property
    def prices(self) -> list[float]:
        values = [coerce_float(r.get("listed_price_cad")) for r in self.retailers]
        return [v for v in values if v is not None]

    @property
    def price(self) -> float | None:
        return min(self.prices) if self.prices else None

    @property
    def max_price(self) -> float | None:
        return max(self.prices) if self.prices else None

    @property
    def price_label(self) -> str:
        if not self.prices or self.price is None:
            return "—"
        if self.price == self.max_price:
            return f"${self.price:,.2f}"
        return f"${self.price:,.2f}–${self.max_price:,.2f}"

    @property
    def best_retailer(self) -> dict[str, Any] | None:
        if not self.retailers:
            return None
        priced: list[tuple[float, dict[str, Any]]] = []
        for retailer in self.retailers:
            price = coerce_float(retailer.get("listed_price_cad"))
            if price is not None:
                priced.append((price, retailer))
        if priced:
            return sorted(priced, key=lambda pair: pair[0])[0][1]
        return self.retailers[0]

    @property
    def source_input(self) -> str:
        return clean_text(self.raw.get("source_input"), "")

    @property
    def notes(self) -> str:
        return clean_text(self.raw.get("notes"), "")

    @property
    def is_canadian_verified(self) -> bool:
        return self.retailer_count > 0 or self.research_status == "canadian_retailer_verified"

    @property
    def is_pending(self) -> bool:
        return "pending" in self.research_status.lower() or "pending" in self.acquisition_status.lower()

    def haystack(self) -> str:
        parts: Iterable[Any] = [
            self.id,
            self.brand,
            self.model,
            self.display_name,
            self.classification,
            self.research_status,
            self.acquisition_status,
            self.opening_method,
            self.blade_steel,
            self.lock_type,
            self.assist_type,
            self.blade_length,
            self.prohibited_flag,
            " ".join(self.tags),
            " ".join(self.retailer_names),
            self.notes,
            self.source_input,
            "new" if self.is_new else "",
            f"buylist priority {self.buy_priority}" if self.buy_priority else "",
        ]
        return " ".join(str(part) for part in parts if part).lower()

    def flat(self) -> dict[str, Any]:
        best = self.best_retailer or {}
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "classification": self.classification,
            "tags": ", ".join(self.tags),
            "research_status": self.research_status,
            "acquisition_status": self.acquisition_status,
            "opening_method": self.opening_method,
            "lock_type": self.lock_type,
            "assist_type": self.assist_type,
            "blade_length": self.blade_length,
            "blade_steel": self.blade_steel,
            "clear_prohibited_mechanism_found": self.prohibited_flag,
            "new": self.is_new,
            "buy_priority": self.buy_priority,
            "date_added": self.date_added or None,
            "price_cad": self.price,
            "retailer": best.get("retailer") if isinstance(best, dict) else None,
            "retailer_url": best.get("url") if isinstance(best, dict) else None,
            "retailer_count": self.retailer_count,
            "notes": self.notes,
        }


def knife_views(db: dict[str, Any]) -> list[KnifeView]:
    knives = db.get("knives") or []
    return [KnifeView(k) for k in knives if isinstance(k, dict)]


def next_unique_id(existing_ids: set[str], base: str) -> str:
    candidate = slugify(base)
    if candidate not in existing_ids:
        return candidate
    counter = 2
    while f"{candidate}-{counter}" in existing_ids:
        counter += 1
    return f"{candidate}-{counter}"
