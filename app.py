import os

import pandas as pd
import requests
import streamlit as st
import agent

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

st.set_page_config(page_title="DataCo Agent", page_icon="📊", layout="wide")
st.title("📊 DataCo – Analyse des ventes")
st.caption("Streamlit → Serveur MCP FastAPI → HBase (données préparées par Hive/Impala)")


def call_tool(name: str, args: dict):
    if name == "fiche_produit":
        resp = requests.get(f"{MCP_SERVER_URL}/tools/fiche_produit/{args['product_id']}", timeout=30)
    elif name == "top_produits":
        resp = requests.get(f"{MCP_SERVER_URL}/tools/top_produits", params={"n": args["n"]}, timeout=30)
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


def show_result(tool: str, result):
    if isinstance(result, dict) and "error" in result:
        st.warning(result["error"])
        return
    if isinstance(result, dict):
        st.table(pd.DataFrame(list(result.items()), columns=["Champ", "Valeur"]))
        return
    df = pd.DataFrame(result)
    if df.empty:
        st.info("Aucun résultat.")
        return
    st.dataframe(df, use_container_width=True)
    if tool == "ca_par_categorie":
        st.bar_chart(df.set_index("category_name")["revenue"])
    elif tool == "top_produits":
        st.bar_chart(df.set_index("product_name")["revenue"])
    elif tool == "vues_par_jour":
        st.bar_chart(df.set_index("day")["views"])

with st.sidebar:
    st.header("État des services")
    try:
        requests.get(f"{MCP_SERVER_URL}/health", timeout=3).raise_for_status()
        st.success("Serveur MCP : OK")
    except Exception:
        st.error(f"Serveur MCP injoignable ({MCP_SERVER_URL})")

tab_chat, tab_tools = st.tabs(["💬 Assistant IA", "🛠️ Outils directs"])

#  Onglet 1 : chat avec l'agent 
with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            for call in msg.get("tool_calls", []):
                with st.expander(f"🔧 Outil appelé : {call['tool']}({call['args']})"):
                    show_result(call["tool"], call["result"])

    question = st.chat_input("Posez votre question sur les ventes DataCo…")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            try:
                history = [{"role": m["role"], "content": m["content"]}
                           for m in st.session_state.messages[:-1]]
                with st.spinner("Analyse en cours…"):
                    out = agent.ask(question, history)
                st.markdown(out["answer"])
                for call in out["tool_calls"]:
                    with st.expander(f"🔧 Outil appelé : {call['tool']}({call['args']})", expanded=True):
                        show_result(call["tool"], call["result"])
                st.session_state.messages.append(
                    {"role": "assistant", "content": out["answer"], "tool_calls": out["tool_calls"]})
            except Exception as exc:
                st.error(f"Erreur : {exc}")

#  Onglet 2 : appel direct des outils (sans IA) 
with tab_tools:
    st.subheader("🛠️ Outils du serveur MCP")
    choice = st.selectbox(
        "Outil",
        ["ca_par_categorie", "top_produits", "fiche_produit", "vues_par_jour"],
        format_func=lambda t: {
            "ca_par_categorie": "Chiffre d'affaires par catégorie",
            "top_produits": "Top produits par chiffre d'affaires",
            "fiche_produit": "Fiche d'un produit",
            "vues_par_jour": "Vues par jour d'un produit",
        }[t],
    )
    args = {}
    if choice == "top_produits":
        args["n"] = st.slider("Nombre de produits", 1, 20, 10)
    elif choice == "fiche_produit":
        args["product_id"] = st.text_input("product_id", "1004")
    elif choice == "vues_par_jour":
        args["product_id"] = st.text_input("product_id", "19")

    if st.button("Exécuter"):
        try:
            show_result(choice, call_tool(choice, args))
        except Exception as exc:
            st.error(f"Erreur : {exc}")