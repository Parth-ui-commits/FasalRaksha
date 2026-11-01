import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="FasalRaksha", layout="wide", initial_sidebar_state="expanded")

from core import auth
from core.i18n import L
from ui import auth_view, pages, session, theme

st.markdown(theme.inject(), unsafe_allow_html=True)
user = session.current_user()
if not user:
    auth_view.render()
    st.stop()

NAV = [("overview", "Overview", "मुख्य पृष्ठ"), ("field", "Field dashboard", "खेत का डैशबोर्ड"), ("doctor", "Crop Doctor", "फसल डॉक्टर"),
       ("diary", "Diary and profit", "डायरी और मुनाफ़ा"), ("ask", "Ask assistant", "सहायक से पूछें"), ("fields", "My fields", "मेरे खेत"),
       ("help", "Help and schemes", "मदद और योजनाएं"), ("sources", "Data sources", "डेटा स्रोत")]
PAGES = {"overview": pages.overview, "field": pages.field_page, "doctor": pages.doctor, "diary": pages.diary,
         "ask": pages.assistant, "fields": pages.fields_page, "help": pages.help_page, "sources": pages.sources}

lang = user.get("lang", "en")
with st.sidebar:
    new = st.radio("Language / भाषा", ["en", "hi"], index=["en", "hi"].index(lang), format_func=lambda x: {"en": "English", "hi": "हिन्दी"}[x], horizontal=True, key="lang_pick")
    if new != lang:
        auth.set_lang(user["id"], new)
        user["lang"] = lang = new
    st.markdown(theme.brand(L(lang, "Smart farming decisions", "समझदार खेती के फ़ैसले")), unsafe_allow_html=True)
    keys = [k for k, _, _ in NAV]
    st.session_state.setdefault("nav", "overview")
    page = st.radio(L(lang, "Menu", "मेनू"), keys, format_func=lambda k: next(L(lang, en, hi) for kk, en, hi in NAV if kk == k), key="nav", label_visibility="collapsed")
    st.markdown(f'<div class="note">{user["name"]} / {user["mobile"]}</div>', unsafe_allow_html=True)
    if st.button(L(lang, "Refresh data", "डेटा ताज़ा करें"), use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.button(L(lang, "Sign out", "साइन आउट"), use_container_width=True):
        session.sign_out()
        st.rerun()

PAGES[page](user, lang)
st.markdown(theme.divider(), unsafe_allow_html=True)
st.markdown(f'<div class="note" style="text-align:center">{L(lang, "FasalRaksha uses live open data. Confirm major decisions with your local KVK.", "फसलरक्षा सीधे खुले डेटा का उपयोग करती है। बड़े फ़ैसले से पहले अपने KVK से पुष्टि करें।")}</div>', unsafe_allow_html=True)
