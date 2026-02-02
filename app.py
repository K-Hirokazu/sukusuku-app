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
# 0. デザイン & CSS設定 (Modern Mobile Style)
# ==========================================
st.set_page_config(page_title="Baby Log", layout="centered", initial_sidebar_state="collapsed")

def local_css():
    st.markdown("""
    <style>
        /* アプリ全体の背景とフォント */
        .stApp {
            background-color: #F8F9FA; /* 明るいグレーホワイト */
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        
        /* Streamlitの余計なヘッダー・余白を消す */
        header {visibility: hidden;}
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
        }

        /* タイムラインのスタイル */
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
        
        /* フォームとカードのスタイル */
        .custom-card {
            background: white;
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            margin-bottom: 16px;
        }

        /* 数値入力欄をシンプルに */
        div[data-baseweb="input"] {
            background-color: #F1F5F9;
            border-radius: 10px;
            border: none;
        }
        
        /* ボタンをモダンに */
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
        div.stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 8px rgba(37, 99, 235, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 1. バックエンド関数
# ==========================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_creds():
    return Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)

def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    sheet = client.open("すくすくログ").sheet1
    # 列自動追加
    try:
        if len(sheet.row_values(1)) < 8:
            sheet.update_cell(1, 7, "カテゴリ")
            sheet.update_cell(1, 8, "タイムスタンプ")
    except: pass
    return sheet

def upload_image_to_drive(image_file, filename):
    try:
        creds = get_creds()
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
# 言語設定（セッション管理）
if 'lang' not in st.session_state: st.session_state['lang'] = 'jp'
lang_code = st.session_state['lang']
t = TEXT[lang_code]

# データ取得
sheet = get_sheet()
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
# モダンなUIライブラリを使用
cols = st.columns(3)
with cols[0]:
    ui.metric_card(title="Age", content=f"{months_old}m", description=f"{age.days}d", key="card1")
with cols[1]:
    ui.metric_card(title="Days", content=f"{(today - birthday).days}", description="Total", key="card2")
with cols[2]:
    # 最新体重を取得して表示
    try:
        all_data = sheet.get_all_records()
        last_weight = next((r['体重'] for r in reversed(all_data) if r['体重']), "-")
        ui.metric_card(title="Weight", content=f"{last_weight}", description="kg", key="card3")
    except:
        ui.metric_card(title="Weight", content="-", description="kg", key="card3")

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- ナビゲーションメニュー (モダンなピル型) ---
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
    
    # カテゴリ選択（アイコンボタン風）
    st.caption(t['cat'])
    cat_keys = list(t['cats'].keys())
    # 4列x2行でアイコンを並べる
    c1, c2, c3, c4 = st.columns(4)
    cols_list = [c1, c2, c3, c4]
    
    # セッションステートで選択カテゴリを保持
    if 'selected_cat' not in st.session_state: st.session_state['selected_cat'] = "Growth"
    
    for i, key in enumerate(cat_keys):
        with cols_list[i % 4]:
            label = f"{ICONS[key]}\n{t['cats'][key]}"
            if st.button(label, key=f"btn_{key}", use_container_width=True):
                st.session_state['selected_cat'] = key
    
    curr_cat = st.session_state['selected_cat']
    st.markdown(f"<div style='text-align:center; margin:15px 0; font-weight:bold; color:#2563EB;'>Selected: {ICONS[curr_cat]} {t['cats'][curr_cat]}</div>", unsafe_allow_html=True)

    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: d_val = st.date_input(t['date'], datetime.date.today())
        with col2: t_val = st.time_input(t['time'], datetime.datetime.now())

        h_val, w_val = 0.0, 0.0
        if curr_cat == "Growth":
            c1, c2 = st.columns(2)
            with c1: h_val = st.number_input("Height (cm)", min_value=0.0, format="%.1f")
            with c2: w_val = st.number_input("Weight (kg)", min_value=0.0, format="%.3f")

        note_val = st.text_area(t['memo'], height=80)
        img_file = st.file_uploader("Photo", type=['jpg', 'png'])

        if st.form_submit_button(t['save']):
            try:
                # AIコメント
                ai_msg = ""
                if curr_cat == "Growth" and w_val > 0:
                    ai_msg = KNOWLEDGE[lang_code].get(months_old, KNOWLEDGE[lang_code]['default'])
                
                # 画像
                link = ""
                if img_file:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    link = upload_image_to_drive(img_file, f"baby_{ts}.jpg")

                sheet.append_row([str(d_val), h_val if h_val>0 else "", w_val if w_val>0 else "", note_val, ai_msg, link, curr_cat, str(t_val)])
                st.success(t['success'])
            except Exception as e: st.error(str(e))
    
    st.markdown("</div>", unsafe_allow_html=True)

# === ページ2: 分析 & タイムライン ===
elif selected == t['nav'][1]: # Analysis
    df = pd.DataFrame(sheet.get_all_records())
    
    if not df.empty:
        # データ前処理
        df = df.rename(columns={'日付':'Date','身長':'Height','体重':'Weight','日記':'Diary','AIコメント':'AI','画像':'Image','カテゴリ':'Category','タイムスタンプ':'Time'})
        df['Date'] = pd.to_datetime(df['Date'])
        
        # グラフ
        st.caption("Growth Chart")
        growth_df = df[(df['Category']=='Growth') & (pd.to_numeric(df['Weight'], errors='coerce') > 0)].copy()
        if not growth_df.empty:
            fig = px.line(growth_df, x='Date', y='Weight', markers=True, line_shape='spline')
            fig.update_traces(line_color='#2563EB', line_width=3)
            fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        
        # タイムライン
        st.caption("Timeline")
        df['DateTime'] = df.apply(lambda r: pd.to_datetime(f"{r['Date'].date()} {r.get('Time', '00:00:00')}") if 'Time' in r and r['Time'] else r['Date'], axis=1)
        
        for i, row in df.sort_values('DateTime', ascending=False).iterrows():
            cat = row.get('Category', 'Growth')
            icon = ICONS.get(cat, "📝")
            diary = row.get('Diary', '')
            if lang_code == 'en': diary = translate_text(str(diary), 'en')
            
            # HTMLで直接デザイン
            st.markdown(f"""
            <div class="timeline-box">
                <div class="timeline-icon">{icon}</div>
                <div style="background: white; padding: 15px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-size: 12px; color: #94A3B8; font-weight: bold; margin-bottom: 4px;">
                        {row['Date'].strftime('%m/%d')} {str(row.get('Time',''))[:5]}
                    </div>
                    <div style="font-size: 15px; color: #1E293B;">
                        {diary}
                    </div>
                    {(f"<div style='font-weight:bold; color:#2563EB; margin-top:4px;'>{row['Height']}cm / {row['Weight']}kg</div>" if row.get('Weight') else "")}
                    {(f"<div style='margin-top:8px; font-size:12px; background:#F1F5F9; padding:8px; border-radius:8px;'>🤖 {row['AI']}</div>" if row.get('AI') else "")}
                    {(f"<img src='{row['Image']}' style='width:100%; border-radius:8px; margin-top:8px;'>" if str(row.get('Image')).startswith('http') else "")}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(t['no_data'])

# === ページ3: 設定 ===
elif selected == t['nav'][2]: # Settings
    st.markdown(f"<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("Settings")
    
    # 言語設定
    new_lang = st.radio("Language", ["日本語", "English"], horizontal=True)
    lang_code_new = 'jp' if new_lang == "日本語" else 'en'
    if lang_code_new != st.session_state['lang']:
        st.session_state['lang'] = lang_code_new
        st.rerun()

    st.markdown("---")
    
    # 誕生日設定
    new_bd = st.date_input(t['bd'], birthday)
    if st.button(t['update']):
        sheet.update(range_name='G1', values=[[str(new_bd)]])
        st.success("Updated!")
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)
