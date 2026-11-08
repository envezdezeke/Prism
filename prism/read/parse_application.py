"""Label-anchored parser for the loan application (class ``application``)."""
from __future__ import annotations

import re
from typing import Any, Optional

from prism.read import docmodel
from prism.read.docmodel import ParsedApplication
from prism.read.labels import extract_labeled
from prism.read.settings import get_config
from prism.read.text import DocText

_MONEY_RE = re.compile(r"^\s*\$?\s*(-?[\d,]*\.?\d+)\s*$")


def _money_cents(value: Optional[str]) -> Optional[int]:
    """Minimal money parse: "$1,234.50" or plain digits."""
    if not value:
        return None
    m = _MONEY_RE.match(value)
    if not m:
        return None
    try:
        whole, _, frac = m.group(1).replace(",", "").partition(".")
        return int(whole or "0") * 100 + int((frac + "00")[:2]) if frac else int(whole) * 100
    except ValueError:
        return None


def parse_application(dt: DocText, doc: Any = None) -> ParsedApplication:
    cfg = get_config()
    labels = cfg.labels.get("application", {})
    stops = tuple(cfg.raw.get("stops") or ())
    values: dict[str, str] = {}
    for text in (dt.plain, dt.layout):
        for k, v in extract_labeled(text, labels, stops).items():
            if v and not values.get(k):
                values[k] = v
    amount = _money_cents(values.get("amount_requested"))
    missing = tuple(f for f in ("legal_name", "amount_requested")
                    if not values.get(f) or (f == "amount_requested" and amount is None))
    return ParsedApplication(legal_name=values.get("legal_name") or None, amount_cents=amount,
                             missing=missing)


docmodel.register("application", parse_application)
