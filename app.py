import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import google.generativeai as genai
import time
import datetime
import plotly.express as px
import altair as alt
import extra_streamlit_components as stx
import requests
import os
import hashlib

# --- Modules ---
from modules.config import *
from modules.logger_setup import logger
from modules.export_utils import create_excel, create_docx, generate_ris
from modules.ml_utils import generate_network_graph
from modules.data_fetcher import fetch_journal_info, parse_journal_data, run_data_pipeline, extract_text_from_pdf

st.set_page_config(page_title="RehaBeyond Scholar", page_icon="🏛️", layout="wide")

@st.cache_resource(experimental_allow_widgets=True)
def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()

# --- Secure Cookie Hashing ---
USER_HASH = hashlib.sha256(f"user_salt_{WEB_PASSWORD}".encode()).hexdigest()
ADMIN_HASH = hashlib.sha256(f"admin_salt_{ADMIN_PASSWORD}".encode()).hexdigest()

# --- Premium UI CSS ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&display=swap');
    html, body, [class*="css"], .stMarkdown { font-family: 'Pretendard', sans-serif; color: #1A1A1A; background-color: #FAFAFA; }
    h1, h2, h3, h4, .serif-title { font-family: 'Playfair Display', 'Nanum Myeongjo', serif !important; font-weight: 700; color: #111111; letter-spacing: -0.02em; }
    .stApp { background-color: #FAFAFA; }
    .journal-badge { display: inline-block; padding: 3px 8px; font-size: 0.75rem; font-weight: 600; border-radius: 4px; margin-right: 6px; margin-top: 5px; }
    .badge-pub { background-color: #F5F5F5; color: #555; border: 1px solid #E0E0E0; }
    .badge-h { background-color: #E3F2FD; color: #1565C0; border: 1px solid #90CAF9; }
    .badge-if { background-color: #FFF8E1; color: #F57F17; border: 1px solid #FFE082; }
    .badge-works { background-color: #F3E5F5; color: #6A1B9A; border: 1px solid #CE93D8; }
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button { background-color: transparent; color: #111111; border: 1px solid #111111; border-radius: 0px; font-weight: 500; transition: all 0.3s ease; padding: 0.5rem 1.2rem; }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover { background-color: #111111; color: #ffffff; border: 1px solid #111111; }
    div.stButton > button[kind="primary"] { background-color: #111111; color: #ffffff; border: none; font-weight: 600; padding: 0.75rem 0; }
    div.stButton > button[kind="primary"]:hover { background-color: #333333; }
    .stTabs [data-baseweb="tab-list"] { gap: 1.5rem; border-bottom: 1px solid #EAEAEA; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { height: 3.5rem; background-color: transparent; border-radius: 0px; color: #888888; font-weight: 400; font-size: 1.05rem; }
    .stTabs [aria-selected="true"] { color: #111111 !important; font-weight: 600; border-bottom: 2px solid #111111 !important; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea { border-radius: 0px; border: none; border-bottom: 1px solid #CCCCCC; background-color: transparent; padding-left: 5px; }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-bottom: 2px solid #111111; box-shadow: none !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #EAEAEA; }
    .metric-box { background: #fff; border: 1px solid #eaeaea; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #111; }
    .metric-label { font-size: 0.9rem; color: #777; margin-top: 5px; }
    [data-testid="stForm"] { border: none !important; padding: 0 !important; }
    .stTooltipIcon { color: #1565C0 !important; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session States ---
for state in ["authenticated", "is_admin"]:
    if state not in st.session_state: st.session_state[state] = False
for state in ["df", "ai_report", "review_draft", "pico_draft", "match_report", "toast_msg"]:
    if state not in st.session_state: st.session_state[state] = None
for state in ["chat_messages", "pdf_chat_messages"]:
    if state not in st.session_state: st.session_state[state] = []
for state in ["pdf_context"]:
    if state not in st.session_state: st.session_state[state] = ""
if "cart" not in st.session_state: st.session_state.cart = {}

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg["msg"], icon=st.session_state.toast_msg["icon"])
    st.session_state.toast_msg = None

# --- Auto Login ---
if not st.session_state.authenticated:
    auth_cookie = cookie_manager.get(cookie="rehab_auth")
    if auth_cookie == USER_HASH: st.session_state.authenticated = True; st.session_state.is_admin = False; st.rerun()
    elif auth_cookie == ADMIN_HASH: st.session_state.authenticated = True; st.session_state.is_admin = True; st.rerun()

# --- 🔒 Login Screen ---
if not st.session_state.authenticated:
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-bottom: 0;' class='serif-title'>RehaBeyond</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #777; font-weight: 300; letter-spacing: 0.15em; margin-bottom: 3rem; margin-top: 10px;'>ENTERPRISE SCHOLAR EDITION</p>", unsafe_allow_html=True)
        with st.form("login_form"):
            pwd_input = st.text_input("Access Code", type="password", placeholder="Enter access code and press Enter", label_visibility="collapsed", help="Authorized access code is required.")
            st.markdown("<br>", unsafe_allow_html=True)
            remember_me = st.checkbox("☑️ Keep me logged in for 30 days on this device", value=True)
            if st.form_submit_button("ENTER PORTAL", use_container_width=True):
                if pwd_input in [WEB_PASSWORD, ADMIN_PASSWORD]:
                    is_admin = (pwd_input == ADMIN_PASSWORD)
                    if remember_me:
                        cookie_val = ADMIN_HASH if is_admin else USER_HASH
                        cookie_manager.set("rehab_auth", cookie_val, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    logger.info(f"✅ Login Success (Admin: {is_admin})")
                    st.session_state.toast_msg = {"msg": "Welcome!", "icon": "👑" if is_admin else "👋"}
                    st.session_state.authenticated = True; st.session_state.is_admin = is_admin; time.sleep(0.5); st.rerun()
                else:
                    logger.warning("❌ Invalid Access Code")
                    st.error("❌ Invalid Access Code")
    st.stop()

def render_journal_html(info):
    return f"<div style='margin-bottom: 5px; line-height: 1.6;'><div style='font-weight: 700; font-size: 1.05rem; color: #111; margin-bottom: 4px;'>📖 {info['name']} <span style='font-weight: 400; color: #888; font-size: 0.85rem;'>(ISSN: {info['issn']})</span></div><div><span class='journal-badge badge-if' title='Avg. citations over last 2 yrs (IF proxy)'>📈 2Yr-IF: {info['if_2yr']}</span> <span class='journal-badge badge-h' title='Journal\\'s highly cited impact index'>🔥 H-index: {info['h_index']}</span> <span class='journal-badge badge-pub'>🏢 {info['pub']}</span> <span class='journal-badge badge-works'>📚 Works: {info['works']:,}</span></div></div>"

# --- Header ---
col_title, col_logout = st.columns([9, 1])
with col_title:
    admin_badge = " <span style='font-size:0.9rem; background:#E53935; color:#fff; padding:2px 8px; border-radius:15px; vertical-align:middle;' title='Admin privileges active'>ADMIN</span>" if getattr(st.session_state, 'is_admin', False) else ""
    st.markdown(f"<h1 style='margin-bottom: 5px;' class='serif-title'>RehaBeyond Scholar <span style='font-size:1.2rem; color:#E53935;'>V12.2 PRO</span>{admin_badge}</h1>", unsafe_allow_html=True)
with col_logout:
    if st.button("Logout", help="Log out and return to the login screen."):
        cookie_manager.delete("rehab_auth")
        st.session_state.authenticated = False; st.session_state.is_admin = False; time.sleep(0.5); st.rerun()

# 🛎️ Badges
def on_major_change():
    if st.session_state.get("major_input", "").strip(): st.session_state.toast_msg = {"msg": "👨‍⚕️ Major applied!", "icon": "✅"}
def on_kw_change():
    if st.session_state.get("kw_input", "").strip(): st.session_state.toast_msg = {"msg": "🎯 Precision filter activated!", "icon": "✅"}
    else: st.session_state.toast_msg = {"msg": "🔄 Precision filter deactivated", "icon": "✅"}

def reset_all_states():
    logger.info("🔄 System Reset Clicked")
    st.session_state.cart = {}
    st.session_state.df = None
    st.session_state.pdf_context = ""
    st.session_state.ai_report = None
    st.session_state.review_draft = None
    st.session_state.pico_draft = None
    st.session_state.match_report = None
    st.session_state.chat_messages = []
    st.session_state.pdf_chat_messages = []
    for key in ["major_input", "kw_input", "search_kw_input", "manual_issn_input"]:
        if key in st.session_state: del st.session_state[key]
    st.session_state.toast_msg = {"msg": "🧹 All settings and cart have been cleared!", "icon": "✨"}

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h3 class='serif-title'>Curation Settings</h3>", unsafe_allow_html=True)
    st.text_input("💡 Your Specific Major/Field", key="major_input", on_change=on_major_change, placeholder="Type and press Enter", help="AI will tailor analysis reports and PICO matrices based on this major/perspective.")
    user_major = st.session_state.get("major_input", "").strip()
    if user_major: st.markdown(f"<div style='padding:5px 10px; background-color:#E3F2FD; color:#1565C0; border-radius:5px; font-size:0.85rem; margin-top:-10px; margin-bottom:10px;'>✅ <b>'{user_major}'</b> Applied</div>", unsafe_allow_html=True)

    st.markdown("<h4 style='color:#111; margin-top: 15px;'>🎯 Precision Filter</h4>", unsafe_allow_html=True)
    st.text_input("Mandatory Keyword", key="kw_input", on_change=on_kw_change, placeholder="Type and press Enter (e.g., stroke)", label_visibility="collapsed", help="Filters out papers that include these keywords in the Title or Abstract from your cart journals. (Leave blank to scan overall trends)")
    target_kw = st.session_state.get("kw_input", "").strip()

    if target_kw: st.markdown(f"<div style='padding:5px 10px; background-color:#FFEBEE; color:#C62828; border-radius:5px; font-size:0.85rem; margin-top:-10px; margin-bottom:10px;'>🎯 <b>'{target_kw}'</b> Filter ON</div>", unsafe_allow_html=True)

    st.markdown("---")
    start_year, end_year = st.slider("📅 Publication Year Range", 1900, 2026, (2010, 2024), help="Drag to set the publication year range for exploration.")
    top_n = st.slider("🔢 Max Extraction Count", 10, 1000, 100, step=10, help="Max number of papers to extract. We recommend at least 50 for effective Machine Learning clustering.")
    search_mode = st.radio("Exploration Mode", ["⚡ Ultra-fast Scan (Bestsellers)", "🧠 Deep Network (Classic Roots)"], help="Ultra-fast Scan: Finds the most highly cited hot papers within the selected years.\n\nDeep Network: Backtracks the core root papers commonly referenced by recent publications.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.button("🔄 Clear Settings & Cart (Reset All)", on_click=reset_all_states, use_container_width=True, help="Clears all inputs, search results, and cart completely.")

# --- Cart ---
col_cart1, col_cart2 = st.columns([8, 2])
with col_cart1: st.markdown("<h3 class='serif-title'>🛒 Target Journals Cart</h3>", unsafe_allow_html=True)
with col_cart2:
    if st.session_state.cart and st.button("🗑️ Empty Cart", use_container_width=True, help="Removes all journals from the cart."):
        st.session_state.cart = {}; st.rerun()

if not st.session_state.cart: st.info("👇 Please add journals to explore using the Discovery tabs below.")
else:
    for issn, info in list(st.session_state.cart.items()):
        c1, c2 = st.columns([9, 1])
        c1.markdown(f"<div style='padding: 12px; background:#fff; border:1px solid #eee; border-left:4px solid #111; margin-bottom:8px;'>{render_journal_html(info)}</div>", unsafe_allow_html=True)
        if c2.button("✕", key=f"del_{issn}", help="Remove this journal from the cart."): del st.session_state.cart[issn]; st.rerun()

# --- Journal Search ---
st.markdown("<br><h3 class='serif-title'>🔍 Discover & Add</h3>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🌟 Global Presets", "🔎 Database Search", "✍️ Manual ISSN"])

with tab1:
    cols = st.columns(3)
    for i, (cat, jrnls) in enumerate(GLOBAL_PRESETS.items()):
        with cols[i % 3]:
            st.markdown(f"<div style='background:#F5F5F5; padding:5px 10px; border-radius:3px; margin-bottom:10px;' title='Top authoritative journals in this academic field.'><b>{cat}</b></div>", unsafe_allow_html=True)
            for j, (j_name, issn) in enumerate(jrnls.items()):
                c1, c2 = st.columns([3, 1])
                c1.write(f"▪️ {j_name}")
                if issn in st.session_state.cart: c2.button("✔", key=f"p_{i}_{j}_{issn}", disabled=True, help="Already in the cart.")
                elif c2.button("+", key=f"a_{i}_{j}_{issn}", help=f"Add '{j_name}' to the cart."):
                    info = fetch_journal_info(issn)
                    if info: st.session_state.cart[issn] = info; st.session_state.toast_msg = {"msg": f"Added successfully!", "icon": "✅"}; st.rerun()

with tab2:
    with st.form("sf"):
        ca, cb = st.columns([5, 1])
        with ca: skw = st.text_input("Search", key="search_kw_input", label_visibility="collapsed", placeholder="Search journal name or keyword and press Enter (e.g., cardiology)", help="Fetches major journals sorted by the number of published works from the global database.")
        with cb: sbm = st.form_submit_button("Search", use_container_width=True)
        if sbm and skw:
            try:
                res = requests.get(f"https://api.openalex.org/sources?search={skw.replace(' ','+')}&filter=type:journal&sort=works_count:desc&per-page=15").json()
                st.session_state.skw_res = [parse_journal_data(r) for r in res.get("results", []) if r.get("issn_l")]
                st.toast("Search complete!", icon="🔍")
            except: st.error("Search error")
    if "skw_res" in st.session_state:
        for idx, info in enumerate(st.session_state.skw_res):
            c1, c2 = st.columns([8, 2])
            c1.markdown(f"<div style='border-bottom:1px dashed #eee;'>{render_journal_html(info)}</div>", unsafe_allow_html=True)
            if info['issn'] in st.session_state.cart: c2.button("Added", key=f"sad_{idx}_{info['issn']}", disabled=True)
            elif c2.button("Add +", key=f"sa_{idx}_{info['issn']}", help="Add this searched journal to the cart."):
                st.session_state.cart[info['issn']] = info; st.session_state.toast_msg = {"msg": "Added successfully!", "icon": "✅"}; st.rerun()

with tab3:
    with st.form("if", clear_on_submit=True):
        cc, cd = st.columns([4, 1])
        with cc: missn = st.text_input("ISSN", key="manual_issn_input", label_visibility="collapsed", placeholder="Enter 8-digit ISSN and press Enter (e.g., 0003-9993)", help="If you know the exact ISSN, the server will reverse-lookup metadata and add it to the cart.")
        with cd: ibm = st.form_submit_button("Lookup & Add +", use_container_width=True)
        if ibm and missn:
            info = fetch_journal_info(missn.strip())
            if info: st.session_state.cart[missn.strip()] = info; st.session_state.toast_msg = {"msg": "Added successfully!", "icon": "✅"}; st.rerun()
            else: st.error("ISSN not found.")

st.markdown("<br><hr style='border-top: 2px solid #111; margin-bottom: 2rem;'>", unsafe_allow_html=True)

# --- Pre-Flight Briefing Board ---
if st.session_state.cart:
    mode_text = "Trend Bestsellers" if "Ultra-fast" in search_mode else "Classic Roots"
    kw_text = f"<br>🎯 <b>Precision Keyword</b>: <span style='color:#E53935; font-weight:bold;'>'{target_kw}'</span>" if target_kw else ""
    st.markdown(f"""
    <div style='background-color:#F0F4F8; padding:20px; border-radius:8px; border-left:5px solid #1565C0; margin-bottom: 20px;' title='Final checklist of your commands before starting the extraction engine.'>
        <h4 style='margin-top:0; color:#1565C0;'>📋 Pre-Flight Briefing (Ready for Extraction)</h4>
        <div style='font-size:1.05rem; line-height:1.6;'>
            ✔️ <b>Target Journals</b>: {len(st.session_state.cart)}<br>
            ✔️ <b>Publication Years</b>: {start_year} ~ {end_year}<br>
            ✔️ <b>Mode</b>: {mode_text} (Max {top_n} papers){kw_text}
        </div>
    </div>
    """, unsafe_allow_html=True)
    btn_label = f"🚀 EXTRACT DATA FOR [{target_kw}]" if target_kw else "🚀 RUN DATA EXTRACTION"
else: btn_label = "🚀 RUN DATA EXTRACTION"

if st.button(btn_label, type="primary", use_container_width=True, help="Starts global API fetching and ML analysis based on these conditions."):
    if not st.session_state.cart: st.error("Cart is empty!")
    else:
        st.session_state.df = None; st.session_state.ai_report = None; st.session_state.review_draft = None; st.session_state.pico_draft = None; st.session_state.match_report = None; st.session_state.chat_messages = []; st.session_state.pdf_chat_messages = []
        pbar = st.progress(0, text="Preparing extraction engine...")
        st.session_state.df = run_data_pipeline(list(st.session_state.cart.keys()), start_year, end_year, top_n, search_mode, target_kw, pbar)
        time.sleep(0.5); pbar.empty()
        if st.session_state.df is not None and not st.session_state.df.empty:
            st.balloons(); st.toast("Data extraction complete!", icon="✅")

# ==========================================
# 🌟 Result UI Tabs
# ==========================================
if st.session_state.df is not None:
    df = st.session_state.df
    st.markdown("<br>", unsafe_allow_html=True)
    if df.empty: st.warning("No results match your criteria.")
    else:
        filter_text = f" <span style='font-size:1.1rem; color:#E53935; font-weight:normal;'>(🎯 Precision Filter Applied: '{target_kw}')</span>" if target_kw else ""
        st.markdown(f"<h2 class='serif-title'>🌟 Data Curation Complete{filter_text}</h2>", unsafe_allow_html=True)

        tabs_list = ["📊 3D Universe & Dashboard", "📑 DB & Excel Export", "✨ AI Planner & PICO", "🎯 Desk Reject Defense", "📄 PDF Assistant & Chatbot"]
        if getattr(st.session_state, 'is_admin', False): tabs_list.append("🛠️ Admin Control Tower")
        ui_tabs = st.tabs(tabs_list)

        with ui_tabs[0]:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='metric-box' title='Total extracted papers matching the criteria.'><div class='metric-value'>{len(df)}</div><div class='metric-label'>Total Papers</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box' title='Number of freely readable Open Access (OA) papers.'><div class='metric-value'>{df['OA_Link'].notna().sum()}</div><div class='metric-label'>Open Access (OA)</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box' title='Average citation count per paper globally.'><div class='metric-value'>{int(df['Citations'].mean())}</div><div class='metric-label'>Avg. Citations</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-box' title='Velocity (Total Citations / Years since publication). Indicates how fast a paper is gaining traction.'><div class='metric-value'>{df['Velocity (Cites/Yr)'].max()}</div><div class='metric-label'>Max Velocity (Cites/Yr)</div></div>", unsafe_allow_html=True)

            if 'PCA_x' in df.columns:
                st.markdown("<br><h3 title='A 3D universe where ML clusters abstracts into 4 distinct semantic topics. Rotate and zoom with your mouse.'>🌌 AI Machine Learning Knowledge Clusters 3D Map</h3>", unsafe_allow_html=True)
                df_3d = df.dropna(subset=['PCA_x']).copy()
                df_3d['Size'] = df_3d['Citations'].apply(lambda x: x + 10)
                st.plotly_chart(px.scatter_3d(df_3d, x='PCA_x', y='PCA_y', z='PCA_z', color='Topic_Cluster', size='Size', hover_name='Title', opacity=0.7).update_layout(margin=dict(l=0, r=0, b=0, t=0), height=550), use_container_width=True)

            st.markdown("<h4 title='Network map showing relations between top papers, journals, and ML topics. Drag the nodes to interact.'>🕸️ Knowledge Network (Interactive)</h4>", unsafe_allow_html=True)
            net_html = generate_network_graph(df)
            if net_html: components.html(net_html, height=450)

        with ui_tabs[1]:
            c1, c2 = st.columns([1, 1])
            fs = f"RehaBeyond_{CURRENT_YEAR}"
            with c1: st.download_button("📥 Download Excel (.xlsx)", data=create_excel(df), file_name=f"{fs}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, help="Download the full paper list perfectly formatted in Excel without encoding issues.")
            with c2: st.download_button("📥 Download .RIS (Zotero/EndNote)", data=generate_ris(df), file_name=f"{fs}.ris", mime="application/x-research-info-systems", use_container_width=True, help="Drag this into Zotero or EndNote to instantly add hundreds of citations.")

            d_cols = [c for c in df.columns if c not in ['Abstract', 'PCA_x', 'PCA_y', 'PCA_z']]
            st.dataframe(df[d_cols], use_container_width=True, hide_index=True, column_config={"DOI": st.column_config.LinkColumn("DOI 🔗", display_text="Link"), "OA_Link": st.column_config.LinkColumn("🔓 PDF", display_text="Open PDF")})

        with ui_tabs[2]:
            cb1, cb2, cb3 = st.columns(3)
            with cb1: r1 = st.button("🧠 Generate Research Gaps", type="primary", use_container_width=True, help="AI proposes 3 actionable, novel follow-up research ideas (Research Gaps) based on top papers.")
            with cb2: r2 = st.button("📄 Draft Review Paper", type="primary", use_container_width=True, help="AI writes a systematic review draft (Intro-Body-Conclusion) with in-text citations using top 50 papers.")
            with cb3: r3 = st.button("📊 Extract PICO Table", type="primary", use_container_width=True, help="Extracts P (Population), I (Intervention), C (Comparison), O (Outcome) matrix as a Markdown table.")

            if r1 or r2 or r3:
                if not GEMINI_API_KEY: st.error("GEMINI_API_KEY is missing.")
                else:
                    genai.configure(api_key=GEMINI_API_KEY)
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    max_p = min(len(df), 15) if r3 else 50
                    ctx = "".join([f"[Rank {r['Rank']}] {r['Title']} | Authors:{r.get('Authors','')}\nAbstract: {str(r['Abstract'])[:400]}...\n\n" for _, r in df.head(max_p).iterrows()])
                    dt = f"top authority in [{user_major}]" if user_major else "world-class academic Editor-in-Chief"

                    if r3:
                        prm = f"You are a {dt}. Analyze the top {max_p} papers to draft a Systematic Review EBM PICO matrix. Please reply in English.\n[Format] Markdown Table\n[Data]\n{ctx}"
                        msg = "Generating PICO matrix..."
                    elif r1:
                        prm = f"You are a {dt}. Analyze these papers and propose 3 specific, novel Research Gaps for future studies. Please reply in English.\n[Data]\n{ctx}"
                        msg = "Synthesizing research gaps..."
                    else:
                        prm = f"You are a {dt}. Write a structured review paper draft (Introduction, Body, Conclusion) using the data below. You MUST use in-text citations. Please reply in English.\n[Data]\n{ctx}"
                        msg = "Drafting review..."

                    with st.spinner(msg):
                        try:
                            res_txt = m.generate_content(prm).text
                            if r3: st.session_state.pico_draft = res_txt; st.toast("PICO extracted!", icon="📊")
                            elif r1: st.session_state.ai_report = res_txt; st.toast("Research gaps generated!", icon="✨")
                            else: st.session_state.review_draft = res_txt; st.toast("Review draft complete!", icon="📄")
                        except Exception as e: st.error(f"Error: {e}")

            for k, tit, f_name in [("pico_draft", "📊 EBM PICO Matrix", "PICO"), ("ai_report", "💡 AI Research Proposal", "Research_Gap"), ("review_draft", "📄 Review Paper Draft", "Review")]:
                if st.session_state.get(k):
                    c_hd, c_dw = st.columns([8, 2]); c_hd.markdown(f"### {tit}"); c_dw.download_button("📥 Download Word", data=create_docx(tit, st.session_state[k]), file_name=f"{f_name}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, help="Instantly save the results as a formatted Word document.", key=f"dl_{k}")
                    st.container(border=True).markdown(st.session_state[k], unsafe_allow_html=True)

        with ui_tabs[3]:
            st.markdown("<p style='color:#666;'>Input your abstract, and the AI acts as a ruthless Editor-in-Chief from 'Nature' or 'NEJM' to pinpoint Desk-Reject vulnerabilities and provide defense strategies before submission.</p>", unsafe_allow_html=True)
            with st.form("match_form", border=False):
                my_title = st.text_input("My Paper (Draft) Title", placeholder="e.g., Effect of Robot-Assisted Therapy on Stroke Patients...", help="Enter the working title of your manuscript.")
                my_abstract = st.text_area("My Paper Abstract Summary", height=150, help="Freely write your research objectives, methods, and expected outcomes for a precise AI review.")
                if st.form_submit_button("🔪 Start Desk-Reject Simulation", type="primary", use_container_width=True, help="AI reviews from a top-tier editor's perspective, criticizing fatal logic errors and offering defense strategies."):
                    if not GEMINI_API_KEY: st.error("API key is missing.")
                    elif not my_title and not my_abstract: st.warning("Please provide input.")
                    else:
                        genai.configure(api_key=GEMINI_API_KEY)
                        ctx = "".join([f"[{r['Journal']}] {r['Title']} (Citations:{r['Citations']})\nAbstract: {str(r['Abstract'])[:200]}...\n\n" for _, r in df.head(50).iterrows()])
                        prm = f"You are a ruthless Editor-in-Chief. Compare the journal trend with my paper, mercilessly point out 3 fatal weaknesses for a Desk Reject, and consult on defense strategies. Please reply in English.\n[Trends]\n{ctx}\n[My Paper]\n- Title: {my_title}\n- Abstract: {my_abstract}"
                        with st.spinner("Conducting rigorous peer review..."):
                            try: st.session_state.match_report = genai.GenerativeModel('gemini-2.5-flash').generate_content(prm).text; st.toast("Simulation complete!", icon="🎯")
                            except: st.error("Error occurred")
            if st.session_state.get("match_report"):
                ch, cd = st.columns([8, 2]); ch.markdown("### 🔪 Defense Simulation Results"); cd.download_button("📥 Download Word", data=create_docx("Defense_Strategy", st.session_state.match_report), file_name="Defense.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, help="Save simulation results as a Word document.")
                st.container(border=True).markdown(st.session_state.match_report, unsafe_allow_html=True)

        with ui_tabs[4]:
            col_pdf, col_chat = st.columns([1, 1])
            with col_pdf:
                st.markdown("<h3 title='Upload a PDF from your PC. AI will perfectly read and memorize its contents.'>📄 Local PDF Parser</h3>", unsafe_allow_html=True)
                uploaded_file = st.file_uploader("📂 Upload PDF Paper", type="pdf", help="Uploaded documents are not saved permanently and are only used for real-time analysis.")
                if uploaded_file:
                    with st.spinner("Extracting text from PDF..."):
                        pdf_text = extract_text_from_pdf(uploaded_file.read())
                        if pdf_text: st.session_state.pdf_context = pdf_text; st.success(f"✅ Extraction complete! ({len(pdf_text):,} chars) Ask the chatbot on the right!")
                        else: st.error("Extraction failed.")
            with col_chat:
                st.markdown("<h3 title='Ask questions comfortably like in a chat, based on the extracted paper database or the uploaded PDF!'>💬 Unified AI Chatbot</h3>", unsafe_allow_html=True)
                chat_container = st.container(border=True, height=400)
                with chat_container:
                    if not st.session_state.chat_messages: st.session_state.chat_messages.append({"role": "assistant", "content": "Ask me anything!"})
                    for msg in st.session_state.chat_messages:
                        with st.chat_message(msg["role"]): st.markdown(msg["content"])
                with st.form("chat_f", clear_on_submit=True):
                    ch1, ch2 = st.columns([8,2])
                    with ch1: prompt = st.text_input("Question", label_visibility="collapsed", placeholder="Type your question and press Enter", help="Ask freely based on the extracted Paper DB or uploaded PDF.")
                    with ch2: chat_sbm = st.form_submit_button("Send", use_container_width=True)
                    if chat_sbm and prompt:
                        st.session_state.chat_messages.append({"role": "user", "content": prompt})
                        with chat_container:
                            with st.chat_message("user"): st.markdown(prompt)
                            if not GEMINI_API_KEY: st.error("API key missing")
                            else:
                                genai.configure(api_key=GEMINI_API_KEY)
                                ctx_db = "".join([f"[Rank {r['Rank']}] {r['Title']}\nAbstract: {str(r['Abstract'])[:200]}...\n\n" for _, r in df.head(50).iterrows()])
                                pdf_ctx = f"\n[Uploaded Full-text PDF]\n{st.session_state.pdf_context[:50000]}\n" if st.session_state.get("pdf_context") else ""
                                with st.chat_message("assistant"):
                                    with st.spinner("Analyzing..."):
                                        try:
                                            res = genai.GenerativeModel('gemini-2.5-flash').generate_content(f"Answer the following question based on the Database and the Uploaded PDF. Please reply in English.\n[DB]\n{ctx_db}{pdf_ctx}\n[Question]\n{prompt}").text
                                            st.markdown(res); st.session_state.chat_messages.append({"role": "assistant", "content": res})
                                        except: st.error("Error")

        if getattr(st.session_state, 'is_admin', False) and len(ui_tabs) > 5:
            with ui_tabs[5]:
                st.markdown("<h3 style='color:#C62828;'>🛠️ System Control Center</h3>", unsafe_allow_html=True)
                c_ad1, c_ad2 = st.columns(2)
                if c_ad1.button("🧹 Clear API Memory Cache", use_container_width=True, help="Frees up memory held by the Docker server for optimal performance."): st.cache_data.clear(); st.cache_resource.clear(); st.toast("Cache cleared", icon="✅")
                if c_ad2.button("🗑️ Clear Log File", use_container_width=True, help="Deletes all black-box error records below."):
                    try:
                        with open("/app/rehab_scholar.log", "w") as f: f.write(""); st.toast("Logs deleted", icon="🗑️")
                    except Exception as e: st.error(f"Deletion failed: {e}")
                st.markdown("#### 📝 Real-time Black Box (/app/rehab_scholar.log)")
                try:
                    with open("/app/rehab_scholar.log", "r", encoding="utf-8") as f: st.code("".join(f.readlines()[-100:]), language="bash")
                except: st.warning("No logs generated yet.")
