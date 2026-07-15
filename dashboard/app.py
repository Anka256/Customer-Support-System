import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Dashboard-only credentials — read from this service's own environment,
# never exposed to whoever is using the dashboard in a browser.
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000").rstrip("/")
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")

if not DASHBOARD_API_KEY:
    st.error("DASHBOARD_API_KEY is not set. Configure it in this service's environment.")
    st.stop()

HEADERS = {"X-API-Key": DASHBOARD_API_KEY}

st.set_page_config(page_title="Customer Support System — Dashboard", layout="wide")


@st.cache_data(ttl=10)
def fetch_tickets() -> list[dict]:
    resp = requests.get(f"{BACKEND_API_URL}/tickets", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_ticket_detail(ticket_id: str) -> dict:
    resp = requests.get(f"{BACKEND_API_URL}/tickets/{ticket_id}", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def status_badge(status: str) -> str:
    return ":green[**🟢 AUTO READY**]" if status == "auto_ready" else ":orange[**🟡 MANUAL REVIEW**]"


st.title("Customer Support System")
st.caption("Internal ticket triage dashboard — not customer-facing")

col1, _ = st.columns([1, 5])
with col1:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()

try:
    tickets = fetch_tickets()
except requests.RequestException as exc:
    st.error(f"Could not reach backend API at {BACKEND_API_URL}: {exc}")
    st.stop()

if not tickets:
    st.info("No tickets yet.")
    st.stop()

df = pd.DataFrame(tickets)
df["status_display"] = df["status"].map(
    lambda s: "🟢 auto_ready" if s == "auto_ready" else "🟡 manual_review"
)

display_df = df[
    ["id", "category", "priority", "status_display", "detected_language", "confidence_score", "created_at"]
].rename(
    columns={
        "id": "Ticket ID",
        "category": "Category",
        "priority": "Priority",
        "status_display": "Status",
        "detected_language": "Language",
        "confidence_score": "Confidence",
        "created_at": "Created At",
    }
)

st.subheader(f"Tickets ({len(df)})")
event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

selected_rows = event.selection.rows if event and event.selection else []

if not selected_rows:
    st.caption("Select a row above to view the ticket detail and draft reply.")
else:
    selected_id = df.iloc[selected_rows[0]]["id"]

    try:
        detail = fetch_ticket_detail(selected_id)
    except requests.RequestException as exc:
        st.error(f"Could not load ticket detail: {exc}")
        st.stop()

    st.divider()
    st.subheader("Ticket Detail")

    badge_col, meta_col = st.columns([1, 3])
    with badge_col:
        st.markdown(status_badge(detail["status"]))
    with meta_col:
        st.write(
            f"**Category:** {detail['category'] or '—'} &nbsp;·&nbsp; "
            f"**Priority:** {detail['priority'] or '—'} &nbsp;·&nbsp; "
            f"**Confidence:** {detail['confidence_score'] if detail['confidence_score'] is not None else '—'} &nbsp;·&nbsp; "
            f"**Language:** {detail['detected_language'] or '—'} &nbsp;·&nbsp; "
            f"**Retries:** {detail['retry_count']}"
        )

    st.markdown("**Original ticket:**")
    st.text_area(
        "Original ticket text",
        detail["raw_text"],
        height=120,
        disabled=True,
        label_visibility="collapsed",
    )

    st.markdown("**Summary:**")
    st.write(detail["summary"] or "—")

    st.markdown("**Draft reply:**")
    st.text_area(
        "Draft reply",
        detail["draft_reply"] or "—",
        height=150,
        disabled=True,
        label_visibility="collapsed",
    )

    with st.expander("Execution logs (step-by-step pipeline trace)"):
        logs_df = pd.DataFrame(detail["logs"])
        if logs_df.empty:
            st.write("No logs recorded.")
        else:
            st.dataframe(
                logs_df[["step_name", "duration_ms", "success", "error_message", "created_at"]],
                use_container_width=True,
                hide_index=True,
            )
