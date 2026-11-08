from hbase_client import get_row, scan_prefix, scan_table


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _product(record: dict) -> dict:
    return {
        "product_id": record["rowkey"],
        "product_name": record.get("product_name"),
        "category_id": _to_int(record.get("category_id")),
        "revenue": _to_float(record.get("revenue")),
        "view_count": _to_int(record.get("view_count")),
        "orders_count": _to_int(record.get("orders_count")),
        "quantity_sold": _to_int(record.get("quantity_sold")),
    }


def fiche_produit(product_id: str) -> dict:
    record = get_row("product_analytics", str(product_id))
    if record is None:
        return {"error": f"Produit {product_id} introuvable"}
    return _product(record)


def top_produits(n: int = 10) -> list[dict]:
    products = [_product(r) for r in scan_table("product_analytics")]
    products.sort(key=lambda p: p["revenue"], reverse=True)
    return products[: max(1, min(int(n), 50))]


def ca_par_categorie() -> list[dict]:
    categories = [
        {
            "category_id": r["rowkey"],
            "category_name": r.get("category_name"),
            "department_id": _to_int(r.get("department_id")),
            "revenue": _to_float(r.get("revenue")),
            "quantity_sold": _to_int(r.get("quantity_sold")),
            "orders_count": _to_int(r.get("orders_count")),
            "products_count": _to_int(r.get("products_count")),
        }
        for r in scan_table("category_analytics")
    ]
    categories.sort(key=lambda c: c["revenue"], reverse=True)
    return categories


def vues_par_jour(product_id: str) -> list[dict]:
    rows = scan_prefix("product_views_daily", f"{product_id}#")
    return [
        {"product_id": str(product_id), "day": r.get("day"), "views": _to_int(r.get("count"))}
        for r in rows
    ]