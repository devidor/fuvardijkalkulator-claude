"""Exportálható, felhasználói munkamenetenként elkülönített LDM-napló."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math


def uj_bejegyzes(terv_hash, hivatkozas, kovetes):
    return {"schema": 1, "terv_hash": terv_hash, "hivatkozas": hivatkozas,
            "rogzitve": datetime.now(timezone.utc).isoformat(),
            **json.loads(json.dumps(asdict(kovetes), default=str))}


def beolvas_naplo(data):
    if len(data) > 5_000_000:
        raise ValueError("Legfeljebb 5 MB méretű napló tölthető be.")
    try:
        rows = json.loads(data)
        if not isinstance(rows, list) or len(rows) > 10000: raise ValueError()
        for row in rows:
            if not isinstance(row, dict) or row.get("schema") != 1: raise ValueError()
            if not isinstance(row.get("terv_hash"), str): raise ValueError()
            for key in ("tervezett_fizikai_ldm", "tervezett_elszamolasi_ldm", "visszaigazolt_ldm", "tenyleges_ldm"):
                value = row[key]
                if value is None and key in ("visszaigazolt_ldm", "tenyleges_ldm"): continue
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0: raise ValueError()
        return rows
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise ValueError("Érvénytelen napló. FuvarDíj 4.0 JSON-exportot töltsön be.") from None
