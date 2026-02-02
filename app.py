import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import datetime
from dateutil.relativedelta import relativedelta
from deep_translator import GoogleTranslator
import plotly.express as px
import streamlit_shadcn_ui as ui
from streamlit_option_menu import option_menu
import time
import textwrap

# ==========================================
# 0. デザイン & CSS設定
# ==========================================
st.set_page_config(page_title="Baby Log", layout="centered", initial_sidebar_state="collapsed")

def local_css():
    st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA; font-family: sans-serif; }
        .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
        
        /* カードデザイン */
        .custom-card {
            background: white; padding: 20px; border-radius: 16px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px;
        }
        
        /* タイムライン */
        .timeline-box {
            border-left: 3px solid #E2E8F0; padding-left: 20px; margin-left: 5px; padding-bottom: 25px; position: relative;
        }
        .timeline-icon {
            position: absolute; left: -11.5px; top: 0; background: white;
            border: 3px solid #E2E8F0; border-radius: 50%; width: 20px; height: 20px;
            text-align: center; font-size: 12px; line-height: 15px;
        }
        
        /* ボタンデザイン修正 */
        div.stButton > button {
            width: 100%; border-radius: 12px; font-weight: bold;
            border: 1px solid #E2E8F0; background-color: white; color: #333;
            transition: all 0.2s;
            height: auto; min-height: 50px; /* 押しやすくする */
            white-space: pre-wrap; /* 文字の折り返し許可 */
        }
        div.stButton > button:hover {
            border-color: #3B82F6; color: #3B82F6; background-color: #EFF6FF;
        }
        /* 選択中のボタン強調 */
        div.stButton > button:focus:not(:active) {
            border-color: #3B82F6; color: #3B82F6;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 1. バックエンド関数
# ==========================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_connection():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=60)
def fetch_data():
    client = get_connection()
    try:
        sheet = client.open("すくすくログ").sheet1
        return sheet.get_all_records()
    except Exception:
        return []

def save_entry(row_data):
    client = get_connection()
    sheet = client.open("すくすくログ").sheet1
    sheet.append_row(row_data)
    fetch_data.clear()

def upload_image(image_file):
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': f"baby_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"}
        media = MediaIoBaseUpload(image_file, mimetype='image/jpeg')
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webContentLink').execute()
        return file.get('webContentLink')
    except: return ""

def translate(text, lang):
    if not text: return ""
    try:
        target = 'en' if lang == 'en' else 'ja'
        return GoogleTranslator(source='auto', target=target).translate(str(text))
    except: return text

# ==========================================
# 2. 定数設定
# ==========================================
ICONS = {"Growth": "📏", "Milk": "🍼", "Diaper": "💩", "Sleep": "💤", "Bath": "🛁", "Event": "🎉", "Health": "🏥", "Other": "📝"}
CATS_JP = {"Growth":"成長","Milk":"食事","Diaper":"トイレ","Sleep":"ねんね","Bath":"お風呂","Event":"できた","Health":"病院","Other":"他"}
CATS_EN = {"Growth":"Growth","Milk":"Meal","Diaper":"Diaper","Sleep":"Sleep","Bath":"Bath","Event":"Milestone","Health":"Health","Other":"Other"}

KNOWLEDGE = {
    'jp': {0: "+25-30g/日増が目安", 1: "手足活発・外気浴OK", 2: "クーイング開始", 3: "首すわり・ハンドガード", 4: "首安定・昼夜区別", 5: "離乳食開始目安", 6: "お座り安定"},
    'en': {0: "+25-30g/day gain", 1: "Active limbs", 2: "Cooing starts", 3: "Neck control", 4: "Steady neck", 5: "Start solids", 6: "Stable sitting"}
}

# ==========================================
# 3. アプリ本体
# ==========================================
if 'lang' not in st.session_state: st.session_state['lang'] = 'jp'
# カテゴリ初期化
if 'cat' not in st.session_state: st.session_state['cat'] = "Growth"

lang = st.session_state['lang']
cats = CATS_JP if lang == 'jp' else CATS_EN

# --- データ取得 ---
records = fetch_data()
df = pd.DataFrame(records)

# 誕生日処理
try:
    birthday = datetime.date(2024, 1, 1)
except:
    birthday = datetime.date(2024, 1, 1)

today = datetime.date.today()
age = relativedelta(today, birthday)
months_old = age.years * 12 + age.months

# --- ヘッダー ---
cols = st.columns(3)
with cols[0]: ui.metric_card(title="Age", content=f"{months_old}m", description=f"{age.days}d", key="c1")
with cols[1]: ui.metric_card(title="Days", content=f"{(today-birthday).days}", description="Total", key="c2")
with cols[2]:
    last_w = "-"
    if not df.empty and '体重' in df.columns:
        valid_w = df[pd.to_numeric(df['体重'], errors='coerce').notna()]
        if not valid_w.empty: last_w = valid_w.iloc[-1]['体重']
    ui.metric_card(title="Weight", content=f"{last_w}", description="kg", key="c3")

st.markdown("<br>", unsafe_allow_html=True)

# --- メニュー ---
selected = option_menu(
    None, ["Record", "Analysis", "Settings"], 
    icons=["pencil-fill", "graph-up", "gear"], 
    orientation="horizontal",
    styles={"container": {"padding": "0", "background-color": "transparent"}, "nav-link": {"font-size": "14px"}}
)

# === ページ1: 記録 ===
if selected == "Record":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    
    # ★修正ポイント：ボタンの状態を確実に更新する関数
    def change_cat(new_cat):
        st.session_state['cat'] = new_cat

    # カテゴリボタン一覧
    keys = list(cats.keys())
    for r in range(2):
        cols = st.columns(4)
        for c in range(4):
            idx = r * 4 + c
            if idx < len(keys):
                k = keys[idx]
                label = f"{ICONS[k]}\n{cats[k]}"
                
                # 選択されているボタンはラベルを変える（視覚的なフィードバック）
                if st.session_state['cat'] == k:
                    label = f"✅\n{cats[k]}"
                    
                # on_clickを使って確実に切り替える
                cols[c].button(label, key=f"btn_{k}", on_click=change_cat, args=(k,))

    curr = st.session_state['cat']
    # 選択中のカテゴリをテキストでも表示
    st.markdown(f"<div style='text-align:center; margin:10px 0; font-weight:bold; color:#2563EB;'>{ICONS[curr]} {cats[curr]}</div>", unsafe_allow_html=True)

    with st.form("entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d_val = c1.date_input("Date", datetime.date.today())
        t_val = c2.time_input("Time", datetime.datetime.now())

        h_val, w_val = 0.0, 0.0
        # 成長記録のときだけ身長・体重入力
        if curr == "Growth":
            c1, c2 = st.columns(2)
            h_val = c1.number_input("Height cm", 0.0, format="%.1f")
            w_val = c2.number_input("Weight kg", 0.0, format="%.3f")

        note = st.text_area("Memo")
        img = st.file_uploader("Photo", type=['jpg','png'])

        if st.form_submit_button("Save Entry", type="primary"):
            try:
                ai_msg = ""
                if curr == "Growth" and w_val > 0:
                    base_know = KNOWLEDGE['jp' if lang=='jp' else 'en'].get(months_old, "")
                    ai_msg = f"{base_know}"
                
                link = upload_image(img) if img else ""
                
                save_entry([str(d_val), h_val or "", w_val or "", note, ai_msg, link, curr, str(t_val)])
                st.success("Saved!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Save Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# === ページ2: 分析 ===
elif selected == "Analysis":
    if not df.empty:
        # 列名統一
        cols_map = {'日付':'Date','身長':'Height','体重':'Weight','日記':'Diary','AIコメント':'AI','画像':'Image','カテゴリ':'Category','タイムスタンプ':'Time'}
        df = df.rename(columns=cols_map)
        
        # グラフ
        if 'Category' in df.columns and 'Weight' in df.columns:
            g_df = df[(df['Category']=='Growth')].copy()
            g_df['Weight'] = pd.to_numeric(g_df['Weight'], errors='coerce')
            g_df = g_df.dropna(subset=['Weight'])
            if not g_df.empty:
                st.caption("Weight Chart")
                fig = px.line(g_df, x='Date', y='Weight', markers=True)
                st.plotly_chart(fig, use_container_width=True)

        # タイムライン
        st.caption("Recent Activities")
        for i, row in df.iloc[::-1].iterrows():
            cat = row.get('Category', 'Growth')
            icon = ICONS.get(cat, "📝")
            diary = str(row.get('Diary', ''))
            ai_comment = str(row.get('AI', ''))
            
            if lang == 'en': 
                diary = translate(diary, 'en')
                ai_comment = translate(ai_comment, 'en')

            # デザイン崩れ防止
            card_html = textwrap.dedent(f"""
            <div class="timeline-box">
                <div class="timeline-icon">{icon}</div>
                <div style="background:white; padding:15px; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size:12px; color:#888; font-weight:bold;">
                        {row.get('Date')} {str(row.get('Time',''))[:5]}
                    </div>
                    <div style="margin-top:5px; color:#333;">{diary}</div>
                    {(f"<div style='color:#2563EB; font-weight:bold; margin-top:5px;'>{row.get('Height')}cm / {row.get('Weight')}kg</div>" if row.get('Weight') else "")}
                    {(f"<div style='background:#F1F5F9; padding:8px; border-radius:8px; margin-top:8px; font-size:12px;'>🤖 {ai_comment}</div>" if ai_comment else "")}
                    {(f"<img src='{row.get('Image')}' style='width:100%; border-radius:8px; margin-top:8px;'>" if str(row.get('Image')).startswith('http') else "")}
                </div>
            </div>
            """)
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("No data found.")

# === ページ3: 設定 ===
elif selected == "Settings":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("Settings")
    
    if st.radio("Language", ["日本語", "English"]) == "English":
        st.session_state['lang'] = 'en'
    else:
        st.session_state['lang'] = 'jp'
        
    st.markdown("---")
    if st.button("Reload Data (強制更新)"):
        fetch_data.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
