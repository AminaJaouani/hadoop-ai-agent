import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SKILLS_DIR = Path(__file__).parent / "skills"


def load_skills() -> str:
    return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(SKILLS_DIR.glob("*.md")))

FUNCTION_DECLARATIONS = [
    {
        "name": "fiche_produit",
        "description": "Fiche analytique d'un produit : nom, catégorie, chiffre d'affaires, vues, commandes, quantité vendue.",
        "parameters": {"type": "object",
                       "properties": {"product_id": {"type": "string", "description": "Identifiant du produit, ex. '1004'"}},
                       "required": ["product_id"]},
    },
    {
        "name": "top_produits",
        "description": "Les n produits qui génèrent le plus de chiffre d'affaires.",
        "parameters": {"type": "object",
                       "properties": {"n": {"type": "integer", "description": "Nombre de produits (1 à 50)"}}},
    },
    {
        "name": "ca_par_categorie",
        "description": "Chiffre d'affaires, quantités vendues et commandes par catégorie de produits.",
    },
    {
        "name": "vues_par_jour",
        "description": "Nombre de consultations par jour de la page d'un produit.",
        "parameters": {"type": "object",
                       "properties": {"product_id": {"type": "string", "description": "Identifiant du produit"}},
                       "required": ["product_id"]},
    },
]


def call_tool(name: str, args: dict):
    if name == "fiche_produit":
        resp = requests.get(f"{MCP_SERVER_URL}/tools/fiche_produit/{args['product_id']}", timeout=30)
    elif name == "top_produits":
        resp = requests.get(f"{MCP_SERVER_URL}/tools/top_produits", params={"n": int(args.get("n", 10))}, timeout=30)
    elif name == "ca_par_categorie":
        resp = requests.get(f"{MCP_SERVER_URL}/tools/ca_par_categorie", timeout=30)
    elif name == "vues_par_jour":
        resp = requests.get(f"{MCP_SERVER_URL}/tools/vues_par_jour/{args['product_id']}", timeout=30)
    else:
        return {"error": f"Outil inconnu : {name}"}
    if resp.status_code == 404:
        return {"error": resp.json().get("detail", "Introuvable")}
    resp.raise_for_status()
    return resp.json()


def ask(question: str, history: list[dict] | None = None) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY manquante (fichier .env)")

    client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(api_version="v1beta"),
    )
    config = types.GenerateContentConfig(
        system_instruction=load_skills(),
        tools=[types.Tool(function_declarations=FUNCTION_DECLARATIONS)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    contents = []
    for msg in history or []:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    tool_calls_log = []
    for _ in range(5):  
        response = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)

        if not response.function_calls:  
            return {"answer": response.text, "tool_calls": tool_calls_log}

        contents.append(response.candidates[0].content)  
        for fc in response.function_calls:
            args = dict(fc.args or {})
            result = call_tool(fc.name, args)
            tool_calls_log.append({"tool": fc.name, "args": args, "result": result})
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_function_response(name=fc.name, response={"result": result})],
            ))

    return {"answer": "Analyse interrompue (trop d'appels d'outils).", "tool_calls": tool_calls_log}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Quel est le chiffre d'affaires par catégorie ?"
    out = ask(q)
    for call in out["tool_calls"]:
        print(f"[outil appelé] {call['tool']}({call['args']})")
    print("\n" + out["answer"])