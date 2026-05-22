import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from charts import build_figure

load_dotenv()

API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.set_page_config(page_title="W AI Reporting", layout="centered")

st.markdown(
    "<style>.block-container { padding-top: 1rem; } h1 { font-size: 1.8rem !important; }</style>",
    unsafe_allow_html=True,
)

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


def api_execute(sql: str, params: dict | None = None) -> dict:
    r = requests.post(
        f"{st.session_state.api_url}/api/execute",
        json={"sql_query": sql, "params": params},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


# --- header ---
connected = api_health()
dot_color = "green" if connected else "red"
st.markdown(
    f'# W AI Reporting &nbsp;<span style="color:{dot_color}; font-size:20px;">●</span>',
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

        if msg.get("exec_error"):
            st.error(msg["exec_error"])
        elif msg.get("results") is not None:
            df = pd.DataFrame(msg["results"], columns=msg["columns"])
            tab_names = ["Table", "Chart", "Query"]
            if msg.get("reasoning"):
                tab_names.append("Reasoning")
            tabs = st.tabs(tab_names)
            tab_table, tab_chart, tab_query = tabs[0], tabs[1], tabs[2]
            tab_reasoning = tabs[3] if len(tabs) > 3 else None

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
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")
                else:
                    st.info("Cannot render this chart type with the current data")
            with tab_query:
                active_params = {k: v for k, v in (msg.get("params") or {}).items() if v is not None}
                if msg.get("dax_query"):
                    tab_sql, tab_dax = st.tabs(["SQL", "DAX"])
                    with tab_sql:
                        if msg.get("template_key"):
                            st.caption(f"Tool: `{msg.get('tool_name', '')}` · Template: `{msg['template_key']}`")
                        st.code(msg["sql"], language="sql")
                        if active_params:
                            st.caption("Parameters")
                            st.json(active_params)
                    with tab_dax:
                        st.code(msg["dax_query"], language="python")
                else:
                    if msg.get("template_key"):
                        st.caption(f"Tool: `{msg.get('tool_name', '')}` · Template: `{msg['template_key']}`")
                    st.code(msg["sql"], language="sql")
                    if active_params:
                        st.caption("Parameters")
                        st.json(active_params)
            if tab_reasoning:
                with tab_reasoning:
                    st.info(msg["reasoning"])

# --- chat input ---
if prompt := st.chat_input("Ask a question about your data..."):
    chat_resp = None
    with st.spinner("Generating SQL..."):
        try:
            chat_resp = api_chat(prompt)
        except Exception as e:
            st.session_state.messages.append({
                "query": prompt, "sql": "", "chat_error": str(e),
                "results": None, "columns": [], "row_count": 0,
            })
            st.rerun()

    if chat_resp.get("status") == "sql_generated":
        msg = {
            "query": prompt,
            "sql": chat_resp["sql_query"],
            "tool_name": chat_resp.get("tool_name"),
            "template_key": chat_resp.get("template_key"),
            "params": chat_resp.get("params"),
            "dax_query": chat_resp.get("dax_query"),
            "reasoning": chat_resp.get("reasoning", ""),
            "results": None, "columns": [], "row_count": 0,
        }
        with st.spinner("Executing query..."):
            try:
                exec_resp = api_execute(chat_resp["sql_query"], params=chat_resp.get("params"))
                if exec_resp.get("status") == "success":
                    msg["results"] = exec_resp["rows"]
                    msg["columns"] = exec_resp["columns"]
                    msg["row_count"] = exec_resp["row_count"]
                    msg["retries"] = exec_resp.get("retries", 0)
                    msg["iterations"] = exec_resp.get("iterations", [])
                else:
                    msg["exec_error"] = exec_resp.get("error", "Unknown error")
                    msg["iterations"] = exec_resp.get("iterations", [])
            except Exception as e:
                msg["exec_error"] = str(e)
        st.session_state.messages.append(msg)
    else:
        status = chat_resp.get("status")
        error_msg = chat_resp.get("error", "SQL generation failed")
        if status == "no_template":
            error_msg = f"No matching template for this question."
        elif status == "invalid_params":
            error_msg = f"Invalid filter values — {error_msg}"
        st.session_state.messages.append({
            "query": prompt,
            "sql": chat_resp.get("sql_query", ""),
            "dax_query": chat_resp.get("dax_query"),
            "chat_error": error_msg,
            "results": None, "columns": [], "row_count": 0,
        })
    st.rerun()
