"""Retailer listing scraper — the research arm of the database.

Fetches a product listing from a supported Canadian retailer and parses it
into a ``Listing``. Pure backend: no UI imports, usable from the Vault's
Forge Line, the CLI, or scripts. Parsers were proven against live pages
during the v0.5.0 database population.

Supported: bladescanada.com, houseofknives.ca.
"""
from __future__ import annotations

import html as html_mod
import re
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Meta-description labels used as value terminators when parsing specs.
_LABELS = (
    "Blade Length|Overall Length|Blade Width|Blade Thickness|Blade Material|Blade Grind|"
    "Blade Style|Blade Finish|Blade Steel|Hardness|Handle Length|Handle Width|Handle Thickness|"
    "Handle Material|Weight|Lock Type|Locking Mechanism|Opener|Opening|Pivot Assembly|Pocket Clip|"
    "Carry Position|Closed Length|Designer|Model|SKU|UPC|Made In|Steel|Clip|Sheath"
)
_STEEL_OK = re.compile(
    r"14C28N|8Cr1[34]MoV|9Cr18MoV|420|440|4116|SUJ2|\bD2\b|AUS ?-?\d+|VG ?-?10|S30V|S35VN|"
    r"S90V|S110V|M390|20CV|MagnaCut|Cru-?Wear|Elmax|CTS ?-?XHP|N690|154CM|Nitro ?-?V|\b3V\b|"
    r"BD1N|CPM|Stainless",
    re.I,
)


SUPPORTED_HOSTS = ("bladescanada.com", "houseofknives.ca")


def is_supported(url: str) -> bool:
    """Whether a URL belongs to a retailer this scraper can read."""
    return any(host in url for host in SUPPORTED_HOSTS)


class ScrapeError(RuntimeError):
    """The listing could not be fetched or parsed."""


class UnsupportedRetailer(ScrapeError):
    """The URL is not a supported retailer's product page."""


@dataclass
class Listing:
    url: str
    retailer: str
    listing_title: str = ""
    brand: str | None = None
    model: str | None = None
    price_cad: float | None = None
    availability: str | None = None
    blade_steel: str | None = None
    lock_type: str | None = None
    opening_method: str | None = None
    blade_length: str | None = None
    assisted: bool = False
    fields: dict[str, str] = field(default_factory=dict)

    def stamped_fields(self) -> list[tuple[str, str]]:
        """The parsed facts, in stamping order, for display layers."""
        out: list[tuple[str, str]] = [("source", self.retailer)]
        if self.brand:
            out.append(("brand", self.brand))
        if self.model:
            out.append(("model", self.model))
        if self.blade_steel:
            out.append(("steel", self.blade_steel))
        if self.lock_type:
            out.append(("lock", self.lock_type))
        if self.blade_length:
            out.append(("length", self.blade_length))
        if self.price_cad is not None:
            out.append(("price", f"${self.price_cad:,.2f} CAD"))
        if self.availability:
            out.append(("stock", self.availability))
        return out


def fetch_listing(url: str, timeout: float = 30.0) -> Listing:
    """Fetch and parse a supported retailer listing."""
    if "bladescanada.com" in url:
        return _parse_bladescanada(url, _get(url, timeout))
    if "houseofknives.ca" in url:
        return _parse_houseofknives(url, _get(url, timeout))
    raise UnsupportedRetailer(f"unsupported retailer: {url}")


# ----------------------------------------------------------------- internals

def _get(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except OSError as exc:
        raise ScrapeError(f"fetch failed: {exc}") from exc


def _clean(value: str) -> str | None:
    value = html_mod.unescape(value).replace('"', " in").replace("”", " in")
    value = value.encode("ascii", "ignore").decode()
    value = re.sub(r"\s*\|\s*", " / ", value)
    value = re.sub(r"\s+", " ", value).strip(" :;,.-/")
    return value or None


def _meta_desc(page: str) -> str:
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', page, re.I)
    return html_mod.unescape(m.group(1)) if m else ""


def _spec(desc: str, label_pat: str) -> str | None:
    m = re.search(rf"(?:{label_pat})\s*:\s*(.*?)(?=(?:{_LABELS})\s*:|$)", desc)
    return _clean(m.group(1)) if m else None


def _parse_bladescanada(url: str, page: str) -> Listing:
    listing = Listing(url=url, retailer="Blades Canada / Warriors and Wonders")
    title_m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    raw_title = html_mod.unescape(title_m.group(1)) if title_m else ""
    title = raw_title.split(" : Blades Canada")[0].strip()
    title = re.sub(r"\s*\[[^\]]*\]\s*-?\s*\$?[\d,.]*\s*(CDN)?\s*$", "", title).strip()
    listing.listing_title = title

    price_m = re.search(r"\$\s*([\d,]+\.\d{2})\s*CDN", raw_title) or re.search(
        r'id="productPrices".{0,200}?\$\s*(?:<span class="dollars">)?([\d,]+)(?:</span>)?\.(\d{2})\s*CDN',
        page, re.S)
    if price_m:
        whole = price_m.group(1).replace(",", "")
        cents = price_m.group(2) if price_m.lastindex == 2 else None
        listing.price_cad = float(f"{whole}.{cents}") if cents else float(whole)

    if re.search(r"coming\s*soon", raw_title, re.I):
        listing.availability = "coming soon"
    elif re.search(r"Add to Cart", page, re.I):
        listing.availability = "in stock"
    elif re.search(r"out of stock|sold out", page, re.I):
        listing.availability = "out of stock"

    brand_m = re.search(r"bladescanada\.com/([^/]+?)-Knives/", url, re.I)
    if brand_m:
        listing.brand = brand_m.group(1).replace("-", " ").strip()
    elif title:
        listing.brand = title.split()[0]
    if title and listing.brand:
        first = title.split(",")[0].strip()
        model = re.sub(rf"^{re.escape(listing.brand)}\s*", "", first, flags=re.I).strip()
        sku_m = re.search(r",\s*([A-Z0-9][A-Z0-9.\-]{3,})\s*$", title)
        if sku_m:
            model = f"{model} ({sku_m.group(1)})"
        listing.model = model or None

    desc = _meta_desc(page)
    steel = _spec(desc, "Blade Material|Blade Steel|Steel Type")
    if steel and _STEEL_OK.search(steel) and len(steel) <= 30:
        listing.blade_steel = steel
    lock = _spec(desc, "Lock Type|Locking Mechanism")
    if lock and "lock" in lock.lower() and len(lock) <= 30:
        listing.lock_type = lock
    opener = _spec(desc, "Opener|Opening")
    if opener and len(opener) <= 40:
        listing.opening_method = opener
    length = _spec(desc, "Blade Length")
    if length and re.search(r"\d", length) and len(length) <= 30:
        listing.blade_length = length

    listing.assisted = bool(re.search(r"assisted", raw_title, re.I))
    return listing


def _parse_houseofknives(url: str, page: str) -> Listing:
    listing = Listing(url=url, retailer="House of Knives")
    title_m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    title = html_mod.unescape(title_m.group(1)).split("|")[0].strip() if title_m else ""
    listing.listing_title = title
    if title:
        listing.brand = title.split()[0]
        listing.model = " ".join(title.split()[1:]) or None

    m = re.search(r'"price":\{"without_tax":\{"formatted":"\$([\d,]+\.\d{2})"', page)
    if m:
        listing.price_cad = float(m.group(1).replace(",", ""))
    if re.search(r'"availability"\s*:\s*"https?://schema\.org/InStock"|"instock":true', page):
        listing.availability = "in stock"
    elif re.search(r'"availability"\s*:\s*"https?://schema\.org/OutOfStock"', page):
        listing.availability = "out of stock"
    listing.assisted = bool(re.search(r"assisted", title, re.I))
    return listing
