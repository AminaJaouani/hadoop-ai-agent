import base64
import os

import requests
from urllib.parse import quote

HBASE_REST_URL = os.getenv("HBASE_REST_URL", "http://localhost:8070")
TIMEOUT = 10


def _decode(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


def _row_to_dict(row: dict) -> dict:
    """Converir une ligne HBase en dict """
    record = {"rowkey": _decode(row["key"])}
    for cell in row.get("Cell", []):
        column = _decode(cell["column"])          
        qualifier = column.split(":", 1)[-1]      
        record[qualifier] = _decode(cell["$"])
    return record


def get_row(table: str, rowkey: str) -> dict | None:
    """lire une seule ligne (accès direct HBase)"""
    resp = requests.get(f"{HBASE_REST_URL}/{table}/{quote(rowkey, safe='')}",
                        headers={"Accept": "application/json"}, timeout=TIMEOUT)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    rows = resp.json().get("Row", [])
    return _row_to_dict(rows[0]) if rows else None


def scan_table(table: str) -> list[dict]:
    """SCAN complet d'une petite table."""
    resp = requests.get(f"{HBASE_REST_URL}/{table}/*",
                        headers={"Accept": "application/json"}, timeout=TIMEOUT)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return [_row_to_dict(r) for r in resp.json().get("Row", [])]


def scan_prefix(table: str, prefix: str) -> list[dict]:
    """SCAN sur un préfixe de RowKey (ex. '19#' = historique du produit 19)."""
    resp = requests.get(f"{HBASE_REST_URL}/{table}/{quote(prefix, safe='')}*",
                        headers={"Accept": "application/json"}, timeout=TIMEOUT)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return [_row_to_dict(r) for r in resp.json().get("Row", [])]