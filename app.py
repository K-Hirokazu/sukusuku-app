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
import textwrap # デザイン崩れを直すための魔法の道具

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
        
        /* タイムライン（崩れ防止のための調整） */
        .timeline-box {
            border-left: 3px solid #E2E8F0; 
            padding-left: 20px; 
            margin-left: 5px; 
            padding-bottom: 25px; 
            position: relative;
        }
        .timeline-icon {
            position: absolute; 
            left: -11.5px; 
            top: 0; 
            background: white;
            border: 3px solid #E2E8F0; 
            border-radius: 50%; 
            width: 20px; 
            height: 20px;
            text-align: center; 
            font-size: 12px; 
            line-height: 15px;
        }
        
        /* ボタン修正 */
        div.stButton > button {
            width: 100%; border-radius: 12px; font-weight: bold;
            border: 1px solid #E2E8F0; background-color: white; color: #333;
            transition: all 0.2s;
        }
        div.stButton > button:hover {
            border-color: #3B82F6; color: #3B82F6; background-color: #EFF6FF;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 1. バックエンド関数（キャッシュ機能付き）
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
        # 翻訳エラーが出ても止まらないようにする
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
if 'lang' not in
