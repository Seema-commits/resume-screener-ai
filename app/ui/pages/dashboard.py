import streamlit as st

from app.services.results_display import render_full_results

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------
# TITLE
# ---------------------------------------------------

st.title("📊 Screening Dashboard")

st.caption(
    "A clean view of the latest screening results, with "
    "download options. Run a screening on the main page first."
)

st.divider()

# ---------------------------------------------------
# RESULTS (read from shared session state - same
# browser session as the main page)
# ---------------------------------------------------

latest_result = st.session_state.get("latest_result")
latest_agent_mode = st.session_state.get("latest_agent_mode")

if latest_agent_mode == "Resume Screening" and latest_result:

    render_full_results(latest_result, show_downloads=True)

else:

    st.info(
        "No screening results yet. Go to the main page, enter a "
        "job description, upload resumes, and click "
        "'Screen Resumes Now' - results will appear here too."
    )