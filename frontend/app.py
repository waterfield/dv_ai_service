import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from charts import build_figure

load_dotenv()

API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.set_page_config(page_title="W AI Reporting", layout="centered")

# --- session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_url" not in st.session_state:
    st.session_state.api_url = API_URL


# --- API helpers ---
def api_health() -> bool:
    try:
        r = requests.get(f"{st.session_state.api_url}/api/health", timeout=5)
        return r.ok and r.json().get("database_connected", False)
    except Exception:
        return False


def api_chat(user_query: str) -> dict:
    r = requests.post(
        f"{st.session_state.api_url}/api/chat",
        json={"user_query": user_query},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def api_execute(sql: str) -> dict:
    r = requests.post(
        f"{st.session_state.api_url}/api/execute",
        json={"sql_query": sql},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


# --- header ---
connected = api_health()
dot_color = "green" if connected else "red"
st.markdown(
    f'# W AI Reporting &nbsp;<span style="color:{dot_color}; font-size:28px;">●</span>',
    unsafe_allow_html=True,
)

st.divider()

# --- chat history ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message("user"):
        st.write(msg["query"])

    with st.chat_message("assistant"):
        if msg.get("chat_error"):
            st.error(msg["chat_error"])
            continue

        with st.expander("Generated Query", expanded=not msg.get("results")):
            tab_sql, tab_dax = st.tabs(["SQL", "DAX"])
            with tab_sql:
                st.code(msg["sql"], language="sql")
            with tab_dax:
                if msg.get("dax_query"):
                    st.code(msg["dax_query"], language="python")
                else:
                    st.info("DAX query not available")

        if msg.get("exec_error"):
            st.error(msg["exec_error"])
        elif msg.get("results") is not None:
            df = pd.DataFrame(msg["results"], columns=msg["columns"])
            tab_table, tab_chart = st.tabs(["Table", "Chart"])
            with tab_table:
                st.dataframe(df, use_container_width=True)
                st.caption(f"{msg['row_count']} row(s) returned")
                if msg.get("retries", 0) > 0:
                    st.session_state["debug_iterations"] = msg.get("iterations", [])
                    st.page_link("pages/execution_details.py", label=f"⚠️ Succeeded after {msg['retries']} retry attempt(s) — view details", icon="🔍")
            with tab_chart:
                chart_type = st.selectbox(
                    "Chart type",
                    ["Auto", "Bar", "Line", "Pie"],
                    key=f"chart_type_{i}",
                )
                fig = build_figure(df, title=msg["query"], chart_type=chart_type.lower())
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Cannot render this chart type with the current data")
        else:
            if st.button("Run Query", key=f"run_{i}"):
                with st.spinner("Executing..."):
                    try:
                        resp = api_execute(msg["sql"])
                        if resp.get("status") == "success":
                            st.session_state.messages[i]["results"] = resp["rows"]
                            st.session_state.messages[i]["columns"] = resp["columns"]
                            st.session_state.messages[i]["row_count"] = resp["row_count"]
                            st.session_state.messages[i]["retries"] = resp.get("retries", 0)
                            st.session_state.messages[i]["iterations"] = resp.get("iterations", [])
                        else:
                            st.session_state.messages[i]["exec_error"] = resp.get("error", "Unknown error")
                            st.session_state.messages[i]["iterations"] = resp.get("iterations", [])
                    except Exception as e:
                        st.session_state.messages[i]["exec_error"] = str(e)
                st.rerun()

# --- chat input ---
if prompt := st.chat_input("Ask a question about your data..."):
    with st.spinner("Generating SQL..."):
        try:
            resp = api_chat(prompt)
            if resp.get("status") == "sql_generated":
                st.session_state.messages.append({
                    "query": prompt,
                    "sql": resp["sql_query"],
                    "dax_query": resp.get("dax_query"),
                    "results": None,
                    "columns": [],
                    "row_count": 0,
                })
            else:
                st.session_state.messages.append({
                    "query": prompt,
                    "sql": resp.get("sql_query", ""),
                    "dax_query": resp.get("dax_query"),
                    "chat_error": resp.get("error", "SQL validation failed"),
                    "results": None,
                    "columns": [],
                    "row_count": 0,
                })
        except Exception as e:
            st.session_state.messages.append({
                "query": prompt,
                "sql": "",
                "chat_error": str(e),
                "results": None,
                "columns": [],
                "row_count": 0,
            })
    st.rerun()
