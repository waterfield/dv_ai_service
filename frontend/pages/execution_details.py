import streamlit as st

st.set_page_config(page_title="Execution Details", layout="wide")
st.title("Query Execution Details")
st.page_link("app.py", label="← Back to chat")
st.divider()

iterations = st.session_state.get("debug_iterations", [])

if not iterations:
    st.info("No execution details available. Run a query from the chat first.")
    st.stop()

st.caption(f"{len(iterations)} attempt(s) total")

for item in iterations:
    attempt = item["attempt"] if isinstance(item, dict) else item.attempt
    sql = item["sql"] if isinstance(item, dict) else item.sql
    error = item.get("error") if isinstance(item, dict) else item.error
    success = item["success"] if isinstance(item, dict) else item.success

    if success:
        label = f"✅ Attempt {attempt} — succeeded"
        expanded = attempt > 1
    else:
        label = f"❌ Attempt {attempt} — failed"
        expanded = True

    with st.expander(label, expanded=expanded):
        st.markdown("**SQL executed:**")
        st.code(sql, language="sql")
        if error:
            st.markdown("**Error:**")
            st.error(error)
