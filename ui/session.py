import streamlit as st
from core import auth


def current_user():
    ss = st.session_state
    if ss.get("user"):
        return ss["user"]
    tok = st.query_params.get("t")
    u = auth.user_from_token(tok) if tok else None
    if u:
        ss["user"], ss["token"] = u, tok
    return u


def sign_in(user):
    tok = auth.make_session(user["id"])
    st.session_state["user"], st.session_state["token"] = user, tok
    st.query_params["t"] = tok


def sign_out():
    if st.session_state.get("token"):
        auth.end_session(st.session_state["token"])
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.query_params.clear()
