import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from charts import build_figure

load_dotenv()

API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.set_page_config(page_title="W AI Reporting", layout="wide", page_icon="📊")

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
.stChatMessage { border-radius: 12px; }
.error-card { background: #2d1b1b; border: 1px solid #7f3535; border-radius: 10px; padding: 14px 18px; margin: 4px 0; }
.error-card .error-title { color: #f87171; font-weight: 600; font-size: 0.95rem; margin-bottom: 8px; }
.error-card .error-meta { color: #9ca3af; font-size: 0.8rem; margin-bottom: 8px; font-family: monospace; }
.error-card .error-fields { color: #fca5a5; font-size: 0.85rem; line-height: 1.7; }
.info-card { background: #1b2d2d; border: 1px solid #2d6b6b; border-radius: 10px; padding: 14px 18px; margin: 4px 0; }
.info-card .info-title { color: #6ee7b7; font-weight: 600; font-size: 0.95rem; }
.info-card .info-body { color: #9ca3af; font-size: 0.85rem; margin-top: 4px; }
.status-dot-green { color: #22c55e; font-size: 12px; }
.status-dot-red { color: #ef4444; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

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


def render_error(msg: dict):
    error_type = msg.get("chat_error_type")

    if error_type == "invalid_params":
        tool = msg.get("chat_error_tool", "")
        template = msg.get("chat_error_template", "")
        raw = msg.get("chat_error", "")
        fields_html = "".join(
            f"<div>• {f.strip()}</div>"
            for f in raw.split(";") if f.strip()
        )
        meta = ""
        if tool or template:
            meta = f'<div class="error-meta">tool: {tool} &nbsp;·&nbsp; template: {template}</div>'
        st.markdown(f"""
        <div class="error-card">
            <div class="error-title">⚠ Invalid filter values</div>
            {meta}
            <div class="error-fields">{fields_html}</div>
        </div>
        """, unsafe_allow_html=True)

    elif error_type == "no_template":
        st.markdown("""
        <div class="info-card">
            <div class="info-title">No matching template</div>
            <div class="info-body">This question doesn't match any available data template. Try rephrasing or ask about AFE budgets, actuals, or cost centers.</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.error(msg.get("chat_error", "An error occurred"))


# --- header ---
connected = api_health()
col_title, col_status = st.columns([6, 1])
with col_title:
    st.markdown("## 📊 W AI Reporting")
with col_status:
    if connected:
        st.markdown('<p style="text-align:right; color:#22c55e; padding-top:12px;">● Connected</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="text-align:right; color:#ef4444; padding-top:12px;">● Disconnected</p>', unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.markdown("### 💡 What can I ask?")

    with st.expander("💰 Budget"):
        st.caption("Show me budget by cost center for 2024")
        st.caption("Budget per AFE this year")
        st.caption("Budget trend by year")
        st.caption("Budget by quarter for 2025")
        st.caption("What is the total budget?")

    with st.expander("📊 Actuals"):
        st.caption("Show actual spend by cost center")
        st.caption("Top 10 AFEs by actual spend")
        st.caption("Actual spend trend by year")
        st.caption("Actuals by quarter for 2024")
        st.caption("Show actuals by region")

    with st.expander("⚖️ Comparisons & Analysis"):
        st.caption("Budget vs actuals variance by year")
        st.caption("Budget vs actuals per AFE")
        st.caption("What % of budget is consumed by cost center?")
        st.caption("Full financial picture per AFE")
        st.caption("Which AFEs have the least remaining budget?")

    with st.expander("🗂️ AFE Master Data"):
        st.caption("List all open AFEs")
        st.caption("Show details for AFE-2025-001")
        st.caption("Which AFEs are past their completion date?")
        st.caption("Show rejected AFEs with reasons")
        st.caption("AFEs coming up for completion soon")

# --- empty state ---
if not st.session_state.messages:
    st.markdown("""
    <div style="text-align:center; padding: 60px 0 40px 0; color: #6b7280;">
        <div style="font-size: 2.5rem; margin-bottom: 12px;">💬</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #9ca3af; margin-bottom: 8px;">Ask a question about your AFE data</div>
        <div style="font-size: 0.85rem; color: #4b5563;">
            Try: <em>"Show me budget by cost center for 2024"</em> &nbsp;·&nbsp;
            <em>"Top 10 AFEs by actual spend"</em> &nbsp;·&nbsp;
            <em>"Budget vs actuals variance by year"</em><br><br>
            See <strong>💡 What can I ask?</strong> in the sidebar for all available questions.
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- chat history ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message("user"):
        st.write(msg["query"])

    with st.chat_message("assistant"):
        if msg.get("chat_error"):
            render_error(msg)
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
    with st.spinner("Thinking..."):
        try:
            chat_resp = api_chat(prompt)
        except Exception as e:
            st.session_state.messages.append({
                "query": prompt, "sql": "", "chat_error": str(e),
                "chat_error_type": "generic",
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
        error_entry = {
            "query": prompt,
            "sql": chat_resp.get("sql_query", ""),
            "chat_error_type": status,
            "chat_error_tool": chat_resp.get("tool_name", ""),
            "chat_error_template": chat_resp.get("template_key", ""),
            "chat_error": chat_resp.get("error", "SQL generation failed"),
            "results": None, "columns": [], "row_count": 0,
        }
        st.session_state.messages.append(error_entry)
    st.rerun()
