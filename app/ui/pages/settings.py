import streamlit as st

st.set_page_config(
    page_title="Settings",
    page_icon="🔑",
    layout="wide"
)

st.title("🔑 API Key Settings")

if "user_api_key" not in st.session_state:
    st.session_state.user_api_key = ""

st.markdown(
    """
    By default, this app uses a pre-configured Anthropic API key.
    , you can add your key below.

    """
)

st.divider()

if st.session_state.user_api_key:

    # -----------------------------------
    # A custom key is active - show status
    # only, no input field, one button.
    # -----------------------------------

    st.success("✅ Using your own API key for this session.")

    if st.button("🗑️ Clear key (use default instead)"):

        st.session_state.user_api_key = ""
        st.rerun()

else:

    # -----------------------------------
    # Default key in use - show input
    # field, one button.
    # -----------------------------------

    st.info("ℹ️ Currently using the app's default API key.")

    entered_key = st.text_input(
        "Your Anthropic API Key",
        type="password",
        label_visibility="visible"
    )

    if st.button("💾 Save key"):

        cleaned_key = entered_key.strip()

        if cleaned_key:
            st.session_state.user_api_key = cleaned_key
            st.rerun()
        else:
            st.warning("Enter a key first, or leave this page to keep using the default.")