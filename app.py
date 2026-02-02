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

# ==========================================
# 0. デザイン & CSS設定
# ==========================================
st.set_page_config(page_title="Baby Log", layout="centered", initial_sidebar_state="collapsed")

def local_css():
    st.markdown("""
    <style>
        .stApp {
            background-color: #F8F9FA;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        header {visibility: hidden;}
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
        }
        .timeline-box {
            border-left: 2px solid #E2E8F0;
            padding-left: 20px;
            margin-left: 10px;
            padding-bottom: 20px;
            position: relative;
        }
        .timeline-icon {
            position: absolute;
            left: -11px;
            top: 0;
            background: white;
            border: 2px solid #E2E8F0;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            text-align: center;
            font-size: 12px;
            line-height: 18px;
        }
        .custom-card {
            background: white;
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-bottom: 16px;
        }
        div[data-baseweb="input"] {
            background-color: #F1F5F9;
            border-radius: 10px;
            border: none;
        }
        div.stButton > button {
            width: 100%;
            background-image: linear-gradient(to right, #3B82F6, #2563EB);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 12px 24px;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 1. バックエンド関数 (高速化対応)
# ==========================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# ★ここが修正ポイント：接続をキャッシュして高速化
@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open("すくすくログ").sheet1
    return sheet

def upload_image_to_drive(image_file, filename):
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(image_file, mimetype='image/jpeg')
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webContentLink').execute()
        return file.get('webContentLink')
    except: return ""

def translate_text(text, target_lang):
    if not text: return ""
    try:
        target = 'en' if target_lang == 'en' else 'ja'
        return GoogleTranslator(source='auto', target=target).translate(text)
    except: return text

# ==========================================
# 2. 定数 & 辞書
# ==========================================
ICONS = {"Growth": "📏", "Milk": "🍼", "Diaper": "💩", "Sleep": "💤", "Bath": "🛁", "Event": "🎉", "Health": "🏥", "Other": "📝"}

KNOWLEDGE = {
    'jp': {0: "睡眠リズム未完成。+25-30g/日。", 1: "手足活発。外気浴OK。", 2: "表情が出る。クーイング。", 3: "首すわり。ハンドガード。", 4: "首しっかり。昼夜区別。", 5: "離乳食開始目安。", 6: "お座り安定。免疫切れ注意。", 'default': "順調な成長です。"},
    'en': {0: "Irregular sleep. +25-30g/day.", 1: "Active limbs. Air baths OK.", 2: "Expressions, cooing.", 3: "Neck control. Hand regard.", 4: "Steady neck. Circadian rhythm.", 5: "Start solids.", 6: "Stable sitting. Watch colds.", 'default': "Growing well."}
}

TEXT = {
    'jp': {'nav': ["記録", "分析", "設定"], 'cat': "カテゴリ", 'date': "日付", 'time': "時間", 'memo': "メモ", 'save': "保存", 'success': "保存完了", 'bd': "誕生日", 'update': "更新", 'no_data': "データなし", 'cats': {"Growth":"成長","Milk":"食事","Diaper":"トイレ","Sleep":"ねんね","Bath":"お風呂","Event":"できた","Health":"病院","Other":"他"}},
    'en': {'nav': ["Record", "Analysis", "Settings"], 'cat': "Category", 'date': "Date", 'time': "Time", 'memo': "Memo", 'save': "Save", 'success': "Saved", 'bd': "Birthday", 'update': "Update", 'no_data': "No Data", 'cats': {"Growth":"Growth","Milk":"Meal","Diaper":"Diaper","Sleep":"Sleep","Bath":"Bath","Event":"Milestone","Health":"Health","Other":"Other"}}
}

# ==========================================
# 3. アプリケーション本体
# ==========================================
if 'lang' not in st.session_state: st.session_state['lang'] = 'jp'
lang_code = st.session_state['lang']
t = TEXT[lang_code]

# シート接続 (キャッシュ済み)
sheet = get_sheet()

# 誕生日取得 (G1)
try:
    saved_bd = sheet.acell('G1').value
    birthday = datetime.datetime.strptime(saved_bd, '%Y-%m-%d').date() if saved_bd else datetime.date(2024, 1, 1)
except:
    birthday = datetime.date(2024, 1, 1)

# 月齢計算
today = datetime.date.today()
age = relativedelta(today, birthday)
months_old = age.years * 12 + age.months

# --- ヘッダー（概要カード） ---
cols = st.columns(3)
with cols[0]:
    ui.metric_card(title="Age", content=f"{months_old}m", description=f"{age.days}d", key="card1")
with cols[1]:
    ui.metric_card(title="Days", content=f"{(today - birthday).days}", description="Total", key="card2")
with cols[2]:
    try:
        # 最新の体重を取得 (少し重い処理なので例外処理で囲む)
        all_vals = sheet.get_all_values()
        # ヘッダーを除いて後ろから見ていく
        last_weight = "-"
        if len(all_vals) > 1:
            for row in reversed(all_vals):
                if len(row) > 2 and row[2]: # 3列目が体重
                    last_weight = row[2]
                    break
        ui.metric_card(title="Weight", content=f"{last_weight}", description="kg", key="card3")
    except:
        ui.metric_card(title="Weight", content="-", description="kg", key="card3")

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- ナビゲーションメニュー ---
selected = option_menu(
    menu_title=None,
    options=t['nav'],
    icons=["pencil-fill", "graph-up-arrow", "gear-fill"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#ffffff", "border-radius": "15px"},
        "icon": {"color": "#64748b", "font-size": "14px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "5px", "--hover-color": "#f1f5f9"},
        "nav-link-selected": {"background-color": "#2563EB", "font-weight": "600"},
    }
)

# === ページ1: 記録 ===
if selected == t['nav'][0]: # Record
    st.markdown(f"<div class='custom-card'>", unsafe_allow_html=True)
    
    if 'selected_cat' not in st.session_state: st.session_state['selected_cat'] = "Growth"
