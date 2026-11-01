import streamlit as st
from core import auth
from core.i18n import L, STATES
from ui import session, theme
from ui.common import esc

ERR = {"bad_mobile": ("Enter a 10 digit mobile number starting with 6, 7, 8 or 9.", "6, 7, 8 या 9 से शुरू होने वाला 10 अंकों का मोबाइल नंबर भरें।"),
       "bad_name": ("Please enter your name.", "कृपया अपना नाम भरें।"),
       "short_pw": ("Password must have at least 6 characters.", "पासवर्ड कम से कम 6 अक्षर का होना चाहिए।"),
       "exists": ("This mobile number is already registered. Please sign in.", "यह मोबाइल नंबर पहले से पंजीकृत है। कृपया साइन इन करें।")}

FEATURES = [
    ("Decisions, not guesses", "सटीक फ़ैसले, अंदाज़े नहीं", "Harvest, irrigation, spray and selling advice with reasons, options compared and a confidence level.", "कटाई, सिंचाई, छिड़काव और बिक्री की सलाह: कारण, विकल्पों की तुलना और भरोसे के स्तर के साथ।"),
    ("Your field, day by day", "आपका खेत, रोज़", "Tracks crop stage from sowing date and plans your week around the real forecast.", "बुवाई की तारीख से फसल की अवस्था देखता है और असली पूर्वानुमान के हिसाब से हफ्ते की योजना बनाता है।"),
    ("Crop Doctor", "फसल डॉक्टर", "Take a photo of a leaf. Image checks and neural networks screen for common diseases.", "पत्ती की फोटो लें। इमेज जांच और न्यूरल नेटवर्क आम रोगों की शुरुआती पहचान करते हैं।"),
    ("Best mandi after transport", "परिवहन के बाद सबसे अच्छी मंडी", "Live Agmarknet prices ranked by what you actually take home, with price history.", "सीधे Agmarknet भाव, जो आपके हाथ में असल में आएगा उसके हिसाब से, भाव के इतिहास के साथ।"),
    ("Flood and weather watch", "बाढ़ और मौसम निगरानी", "River flow, heavy rain, heat and frost chances from 51 forecast runs.", "51 पूर्वानुमान रन से नदी का बहाव, भारी बारिश, गर्मी और पाले की संभावना।"),
    ("Diary and profit", "डायरी और मुनाफ़ा", "Record work, costs and sales for each field and see your profit.", "हर खेत का काम, खर्च और बिक्री लिखें और मुनाफ़ा देखें।"),
]


def render():
    lang = st.session_state.get("lang_guest", "en")
    with st.sidebar:
        st.markdown(theme.brand(L(lang, "Smart farming decisions", "समझदार खेती के फ़ैसले")), unsafe_allow_html=True)
        lang = st.radio("Language / भाषा", ["en", "hi"], format_func=lambda x: {"en": "English", "hi": "हिन्दी"}[x], horizontal=True, key="lang_guest")
    st.markdown(theme.hero(L(lang, "From forecast to farm decision", "पूर्वानुमान से खेत के फ़ैसले तक"),
                           L(lang, "Weather, river, soil, mandi prices and crop photos, in one place for your fields.", "मौसम, नदी, मिट्टी, मंडी भाव और फसल की फोटो, आपके खेतों के लिए एक जगह।"),
                           "clear", False, 0.45, "wheat"), unsafe_allow_html=True)
    left, right = st.columns([1.15, 1])
    with left:
        cols = st.columns(2)
        for i, f in enumerate(FEATURES):
            with cols[i % 2]:
                st.markdown(f'<div class="feature"><b>{esc(L(lang, f[0], f[1]))}</b><div>{esc(L(lang, f[2], f[3]))}</div></div>', unsafe_allow_html=True)
    with right:
        tab_in, tab_up = st.tabs([L(lang, "Sign in", "साइन इन"), L(lang, "Create account", "खाता बनाएं")])
        with tab_in:
            with st.form("signin"):
                m = st.text_input(L(lang, "Mobile number", "मोबाइल नंबर"), max_chars=10, key="si_m")
                p = st.text_input(L(lang, "Password", "पासवर्ड"), type="password", key="si_p")
                if st.form_submit_button(L(lang, "Sign in", "साइन इन"), use_container_width=True):
                    tries = st.session_state.get("tries", 0)
                    u = auth.login(m, p) if tries < 8 else None
                    if tries >= 8:
                        st.error(L(lang, "Too many attempts. Reload the page and try again.", "बहुत ज़्यादा कोशिशें। पेज दोबारा खोलकर कोशिश करें।"))
                    elif u:
                        u["lang"] = lang
                        session.sign_in(u)
                        st.rerun()
                    else:
                        st.session_state["tries"] = tries + 1
                        st.error(L(lang, "Mobile number or password is wrong.", "मोबाइल नंबर या पासवर्ड गलत है।"))
        with tab_up:
            with st.form("signup"):
                n = st.text_input(L(lang, "Your name", "आपका नाम"), key="su_n")
                m2 = st.text_input(L(lang, "Mobile number", "मोबाइल नंबर"), max_chars=10, key="su_m")
                p2 = st.text_input(L(lang, "Choose a password (6 or more characters)", "पासवर्ड चुनें (6 या अधिक अक्षर)"), type="password", key="su_p")
                stt = st.selectbox(L(lang, "State", "राज्य"), STATES, index=STATES.index("Bihar"), key="su_s")
                if st.form_submit_button(L(lang, "Create account", "खाता बनाएं"), use_container_width=True):
                    u, err = auth.register(m2, n, p2, lang, stt)
                    if err:
                        st.error(L(lang, *ERR[err]))
                    else:
                        session.sign_in(u)
                        st.rerun()
            st.caption(L(lang, "Your password is stored as a salted hash. Sign-in by SMS code is on the roadmap.", "आपका पासवर्ड नमक के साथ हैश करके सेव होता है। एसएमएस कोड से साइन इन आगे जोड़ा जाएगा।"))
