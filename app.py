import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import datetime
from dateutil.relativedelta import relativedelta

# ==========================================
# 0. デザイン設定 (Apple風スタイル)
# ==========================================
st.set_page_config(page_title="Growth Log", layout="centered")

def local_css():
    st.markdown("""
    <style>
        /* 全体のフォントと背景 */
        .stApp {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #F5F5F7;
            color: #1D1D1F;
        }
        
        /* 入力フォームのカード化 */
        div[data-testid="stForm"] {
            background-color: #FFFFFF;
            padding: 30px;
            border-radius: 18px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            border: 1px solid #E5E5E5;
        }

        /* タイムラインのカード化 */
        .entry-card {
            background-color: #FFFFFF;
            padding: 24px;
            border-radius: 18px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
            margin-bottom: 20px;
            border: 1px solid #F0F0F0;
        }
        
        /* ボタンのスタイル (Apple Blue) */
        div.stButton > button {
            background-color: #0071e3;
            color: white;
            border-radius: 980px;
            border: none;
            padding: 10px 24px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #0077ED;
            transform: scale(1.02);
        }
        
        /* 見出しのスタイル */
        h1, h2, h3 {
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        
        /* タブのスタイル */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px;
            color: #86868b;
            font-weight: 400;
        }
        .stTabs [aria-selected="true"] {
            color: #1D1D1F;
            font-weight: 600;
            border-bottom: 2px solid #0071e3;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 1. システム設定・接続
# ==========================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    return Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)

def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    # ワークシートを開く
    sheet = client.open("すくすくログ").sheet1
    return sheet

def upload_image_to_drive(image_file, filename):
    """Googleドライブに画像をアップロードしてリンクを返す関数"""
    try:
        creds = get_creds()
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(image_file, mimetype='image/jpeg')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webContentLink'
        ).execute()
        
        return file.get('webContentLink')
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# 2. 知識データベース (テキストのみ)
# ==========================================
KNOWLEDGE_BASE = {
    'jp': {
        'default': "順調に成長しています。日々の変化を楽しんでください。",
        0: "睡眠リズムが未完成な時期です。1日あたり25〜30gの体重増加が目安です。",
        1: "手足を活発に動かし始めます。外気浴を少しずつ始めても良い時期です。",
        2: "表情が出てきて、クーイング（あー、うー）が始まる時期です。",
        3: "首がすわり始める大きな節目です。自分の手を見つめるようになります。",
        4: "首がしっかりして縦抱きが安定します。昼夜の区別がつき始めます。",
        5: "離乳食の開始時期の目安です。支えてあげると座れるようになることも。",
        6: "お座りが安定してくる時期です。免疫が切れ始め、風邪に注意が必要です。"
    },
    'en': {
        'default': "Growing well. Enjoy the daily changes.",
        0: "Sleep cycles are irregular. Expected weight gain is 25-30g/day.",
        1: "Limbs start moving actively. Short air baths can begin.",
        2: "Expressions appear, and cooing may start.",
        3: "Neck control improves. Babies may start staring at their hands.",
        4: "Neck is steady. Circadian rhythms develop.",
        5: "Typical time to start solids. May sit with support.",
        6: "Sitting becomes more stable. Watch out for first colds."
    }
}

UI_TEXT = {
    'jp': {
        'title': 'Growth Log',
        'tab_record': 'Entry',
        'tab_history': 'History',
        'date': 'Date',
        'height': 'Height (cm)',
        'weight': 'Weight (kg)',
        'diary': 'Note',
        'photo': 'Take Photo',
        'submit': 'Save',
        'success': 'Saved successfully',
        'setting_header': 'Settings',
        'birthday_label': 'Birthday',
        'lang_label': 'Language',
        'save_bd': 'Update Birthday',
        'ai_title': 'Analysis',
        'no_data': 'No data recorded yet.'
    },
    'en': {
        'title': 'Growth Log',
        'tab_record': 'Entry',
        'tab_history': 'History',
        'date': 'Date',
        'height': 'Height (cm)',
        'weight': 'Weight (kg)',
        'diary': 'Note',
        'photo': 'Take Photo',
        'submit': 'Save',
        'success': 'Saved successfully',
        'setting_header': 'Settings',
        'birthday_label': 'Birthday',
        'lang_label': 'Language',
        'save_bd': 'Update Birthday',
        'ai_title': 'Analysis',
        'no_data': 'No data recorded yet.'
    }
}

# ==========================================
# 3. アプリケーション本体
# ==========================================

# --- サイドバー設定 ---
st.sidebar.markdown("## Settings")
lang_mode = st.sidebar.selectbox("Language", ["日本語", "English"])
lang_code = 'jp' if lang_mode == "日本語" else 'en'
text = UI_TEXT[lang_code]

# --- 誕生日の管理 (スプレッドシートのZ1セルを使用) ---
sheet = get_sheet()

# 誕生日を読み込む
try:
    saved_bd_str = sheet.acell('Z1').value
    if saved_bd_str:
        default_date = datetime.datetime.strptime(saved_bd_str, '%Y-%m-%d').date()
    else:
        default_date = datetime.date(2024, 1, 1)
except:
    default_date = datetime.date(2024, 1, 1)

# 誕生日入力フォーム
birthday = st.sidebar.date_input(text['birthday_label'], default_date)

# 誕生日が変更されたら保存するボタン
if st.sidebar.button(text['save_bd']):
    sheet.update('Z1', str(birthday))
    st.sidebar.success("Updated!")
    st.rerun()

# --- メイン画面 ---
st.title(text['title'])

tab1, tab2 = st.tabs([text['tab_record'], text['tab_history']])

# --- タブ1: 入力 ---
with tab1:
    with st.form("entry_form", clear_on_submit=True):
        st.markdown("### New Entry")
        
        col1, col2 = st.columns(2)
        with col1:
            d_val = st.date_input(text['date'], datetime.date.today())
            h_val = st.number_input(text['height'], min_value=0.0, format="%.1f")
        with col2:
            # 写真撮影 (カメラ入力)
            img_file = st.camera_input(text['photo'])
            w_val = st.number_input(text['weight'], min_value=0.0, format="%.3f")
            
        note_val = st.text_area(text['diary'], height=100)
        
        submitted = st.form_submit_button(text['submit'])
        
        if submitted:
            try:
                # 1. データの準備
                all_records = sheet.get_all_records()
                prev_data = all_records[-1] if all_records else None
                
                # 2. AI分析ロジック
                age = relativedelta(d_val, birthday)
                months_old = age.years * 12 + age.months
                knowledge = KNOWLEDGE_BASE[lang_code].get(months_old, KNOWLEDGE_BASE[lang_code]['default'])
                
                analysis_msg = ""
                if prev_data:
                    try:
                        prev_w = float(str(prev_data.get('体重') or prev_data.get('Weight') or 0).replace(',',''))
                        diff = w_val - prev_w
                        if lang_code == 'jp':
                            analysis_msg = f"前回比 {diff:+.2f}kg"
                        else:
                            analysis_msg = f"{diff:+.2f}kg vs last"
                    except:
                        pass
                
                full_comment = f"{knowledge}\n{analysis_msg}"

                # 3. 画像のアップロード処理
                img_link = ""
                if img_file is not None:
                    # ファイル名を「日付_時刻.jpg」にする
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_filename = f"baby_{ts}.jpg"
                    img_link = upload_image_to_drive(img_file, img_filename)

                # 4. 保存 (日付, 身長, 体重, 日記, AIコメント, 画像リンク)
                sheet.append_row([str(d_val), h_val, w_val, note_val, full_comment, img_link])
                
                st.success(text['success'])
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- タブ2: 履歴 ---
with tab2:
    if st.button("Refresh"):
        st.rerun()
        
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # 新しい順に表示
            for i, row in df.iloc[::-1].iterrows():
                # カスタムCSSデザインのカードを表示
                st.markdown(f"""
                <div class="entry-card">
                    <div style="color: #86868b; font-size: 0.9em; margin-bottom: 4px;">{row['日付']}</div>
                    <div style="font-size: 1.1em; font-weight: 600; margin-bottom: 12px;">
                        {row['身長']} cm / {row['体重']} kg
                    </div>
                    <div style="color: #1d1d1f; line-height: 1.5; margin-bottom: 16px;">
                        {row['日記']}
                    </div>
                    <div style="background-color: #F5F5F7; padding: 12px; border-radius: 8px; font-size: 0.9em; color: #424245;">
                        <strong style="color: #0071e3;">AI Analysis:</strong><br>
                        {row['AIコメント']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 画像があれば表示
                img_url = row.get('画像') or row.get('Image')
                if img_url and str(img_url).startswith('http'):
                    st.image(img_url, width=200)
                    
        else:
            st.info(text['no_data'])
            
    except Exception as e:
        st.error("Data load error")
