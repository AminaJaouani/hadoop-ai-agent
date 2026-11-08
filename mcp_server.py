from fastapi import FastAPI, HTTPException, Query
from fastapi_mcp import FastApiMCP

import tools

app = FastAPI(
    title="DataCo MCP Server",
    description="Outils d'analyse DataCo : données Hadoop (Hive/Impala) matérialisées dans HBase.",
    version="1.0.0",
)


@app.get("/health", operation_id="health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/tools/fiche_produit/{product_id}", operation_id="fiche_produit", tags=["tools"])
def fiche_produit(product_id: str):
    """Fiche d'un produit identifié par son product_id :
    nom, catégorie, chiffre d'affaires, nombre de vues, nombre de commandes, quantité vendue."""
    result = tools.fiche_produit(product_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/tools/top_produits", operation_id="top_produits", tags=["tools"])
def top_produits(n: int = Query(10, ge=1, le=50, description="Nombre de produits à renvoyer")):
    return tools.top_produits(n)


@app.get("/tools/ca_par_categorie", operation_id="ca_par_categorie", tags=["tools"])
def ca_par_categorie():
    return tools.ca_par_categorie()


@app.get("/tools/vues_par_jour/{product_id}", operation_id="vues_par_jour", tags=["tools"])
def vues_par_jour(product_id: str):
    return tools.vues_par_jour(product_id)


mcp = FastApiMCP(
    app,
    name="DataCo MCP",
    description="Outils d'analyse des ventes et des consultations DataCo",
    include_operations=["fiche_produit", "top_produits", "ca_par_categorie", "vues_par_jour"],
)
mcp.mount_http()  # MCP : http://localhost:8000/mcp