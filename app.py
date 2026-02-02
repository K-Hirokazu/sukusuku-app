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
import plotly.graph_objects as go

# ==========================================
# 0. デザイン設定 (ピヨログ風・Warm Style)
# ==========================================
st.set_page_config(page_title="Baby Log", layout="centered", initial_sidebar_state="collapsed")

def local_css():
    st.markdown("""
    <style>
        /* 全体のフォントと背景 */
        .stApp {
            font-family: "Hiragino Maru Gothic Pro", "Yu Gothic", sans-serif;
            background-color: #FFF8E1; /* 優しいクリーム色 */
        }
        
        /* 入力フォームのカード化 */
        div[data-testid="stForm"] {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(255, 160, 0, 0.1);
            border: 2px solid #FFF3E0;
        }

        /* タイムラインのデザイン */
        .timeline-container {
            position: relative;
            padding-left: 30px;
            border-left: 3px solid #FFD54F; /* 縦線 */
            margin-left: 10px;
            margin-top: 20px;
        }
        
        .timeline-dot {
            position: absolute;
            left: -39px;
            top: 20px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background-color: #FFB300;
            border: 3px solid #FFF;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .entry-card {
            background-color: #FFFFFF;
            padding: 15px 20px;
            border-radius: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            position: relative;
        }

        .time-label {
            font-size: 0.8em;
            color: #8D6E63;
            font-weight: bold;
            margin-bottom: 5px;
        }

        /* ボタンのデザイン */
        div.stButton > button {
            background-color: #FFB74D;
            color: white;
            border-radius: 30px;
            padding: 10px 30px;
            border: none;
            font-weight: bold;
            box-shadow: 0 4px 0 #F57C00; /* 立体的なボタン */
            transition: all 0.1s;
        }
        div.stButton > button:active {
            transform: translateY(4px);
            box-shadow: none;
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
    sheet = client.open("すくすくログ").sheet1
    
    # --- 自動メンテナンス機能 ---
    # カテゴリ列(G列)などがなければ自動で追加する
    try:
        header = sheet.row_values(1)
        # G列(7番目)がなければ追加
        if len(header) < 7:
            sheet.update_cell(1, 7, "カテゴリ") # G1
        if len(header) < 8:
            sheet.update_cell(1, 8, "タイムスタンプ") # H1
    except:
        pass
        
    return sheet

def upload_image_to_drive(image_file, filename):
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
        return ""

def translate_text(text, target_lang):
    if not text or text == "": return ""
    try:
        target = 'en' if target_lang == 'en' else 'ja'
        return GoogleTranslator(source='auto', target=target).translate(text)
    except:
        return text

# ==========================================
# 2. 定数・辞書
# ==========================================
# カテゴリ別アイコン定義
ICONS = {
    "Growth": "📏", # 成長記録
    "Milk": "🍼",   # ミルク・食事
    "Diaper": "💩", # トイレ
    "Sleep": "💤",  # ねんね
    "Bath": "🛁",   # お風呂
    "Event": "🎉",  # イベント
    "Health": "🏥", # 病院・体調
    "Other": "📝"   # その他
}

KNOWLEDGE_BASE = {
    'jp': {'default': "順調に成長しています。", 0: "睡眠リズム未完成。1日25-30g増目安。", 1: "手足活発。外気浴OK。", 2: "表情が出る。クーイング。", 3: "首すわり。ハンドガード。", 4: "首しっかり。昼夜区別。", 5: "離乳食開始目安。", 6: "お座り安定。免疫切れ注意。"},
    'en': {'default': "Growing well.", 0: "Irregular sleep. Gain 25-30g/day.", 1: "Active limbs. Air baths OK.", 2: "Expressions, cooing.", 3: "Neck control. Hand regard.", 4: "Steady neck. Circadian rhythm.", 5: "Start solids.", 6: "Stable sitting. Watch colds."}
}

UI_TEXT = {
    'jp': {
        'title': 'Baby Log',
        'tab_record': '✏️ 記録',
        'tab_history': '📅 タイムライン',
        'date': '日付',
        'time': '時間',
        'category': 'アイコン選択',
        'height': '身長 (cm)',
        'weight': '体重 (kg)',
        'diary': 'メモ・日記',
        'photo': '写真を追加',
        'submit': '記録する',
        'success': '保存しました✨',
        'birthday_label': '誕生日',
        'save_bd': '更新',
        'no_data': 'データがありません',
        'cats': {"Growth": "成長記録", "Milk": "食事・授乳", "Diaper": "トイレ", "Sleep": "ねんね", "Bath": "お風呂", "Event": "できた！", "Health": "病院・薬", "Other": "その他"}
    },
    'en': {
        'title': 'Baby Log',
        'tab_record': '✏️ Record',
        'tab_history': '📅 Timeline',
        'date': 'Date',
        'time': 'Time',
        'category': 'Category',
        'height': 'Height (cm)',
        'weight': 'Weight (kg)',
        'diary': 'Note',
        'photo': 'Add Photo',
        'submit': 'Save Entry',
        'success': 'Saved! ✨',
        'birthday_label': 'Birthday',
        'save_bd': 'Update',
        'no_data': 'No data yet',
        'cats': {"Growth": "Growth", "Milk": "Meal/Milk", "Diaper": "Diaper", "Sleep": "Sleep", "Bath": "Bath", "Event": "Milestone", "Health": "Health", "Other": "Other"}
    }
}

# ==========================================
# 3. アプリケーション本体
# ==========================================
st.sidebar.markdown("## ⚙️ Settings")
lang_mode = st.sidebar.selectbox("Language", ["日本語", "English"])
lang_code = 'jp' if lang_mode == "日本語" else 'en'
text = UI_TEXT[lang_code]

sheet = get_sheet()
try:
    saved_bd_str = sheet.acell('G1').value
    default_date = datetime.datetime.strptime(saved_bd_str, '%Y-%m-%d').date() if saved_bd_str else datetime.date(2024, 1, 1)
except:
    default_date = datetime.date(2024, 1, 1)

birthday = st.sidebar.date_input(text['birthday_label'], default_date)
if st.sidebar.button(text['save_bd']):
    sheet.update(range_name='G1', values=[[str(birthday)]])
    st.sidebar.success("Updated!")
    st.rerun()

# ヘッダーエリア（赤ちゃんの月齢表示）
age = relativedelta(datetime.date.today(), birthday)
st.markdown(f"""
<div style="text-align:center; padding: 20px; background-color: #FFF3E0; border-radius: 15px; margin-bottom: 20px;">
    <h2 style="color:#F57C00; margin:0;">👶 {age.years * 12 + age.months}m {age.days}d</h2>
    <p style="color:#8D6E63; margin:0;">Today is Day {(datetime.date.today() - birthday).days}</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs([text['tab_record'], text['tab_history']])

# --- タブ1: 記録（ピヨログ風アイコン選択） ---
with tab1:
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            d_val = st.date_input(text['date'], datetime.date.today())
        with col2:
            t_val = st.time_input(text['time'], datetime.datetime.now())
            
        # カテゴリ選択（ラジオボタンを横並び風に）
        st.markdown(f"**{text['category']}**")
        cat_options = list(text['cats'].keys())
        cat_labels = [f"{ICONS[c]} {text['cats'][c]}" for c in cat_options]
        selected_cat_idx = st.radio("Category", range(len(cat_options)), format_func=lambda x: cat_labels[x], horizontal=True, label_visibility="collapsed")
        selected_cat_key = cat_options[selected_cat_idx]

        st.markdown("---")
        
        # 成長記録を選んだときだけ身長・体重を表示
        h_val, w_val = 0.0, 0.0
        if selected_cat_key == "Growth":
            c1, c2 = st.columns(2)
            with c1: h_val = st.number_input(text['height'], min_value=0.0, format="%.1f")
            with c2: w_val = st.number_input(text['weight'], min_value=0.0, format="%.3f")
        
        note_val = st.text_area(text['diary'], height=80)
        img_file = st.file_uploader(text['photo'], type=['jpg', 'jpeg', 'png'])
        
        submitted = st.form_submit_button(text['submit'], use_container_width=True)
        
        if submitted:
            try:
                # AIコメント生成（Growthの場合のみ詳細分析）
                full_comment = ""
                if selected_cat_key == "Growth" and w_val > 0:
                    months = age.years * 12 + age.months
                    knowledge = KNOWLEDGE_BASE[lang_code].get(months, KNOWLEDGE_BASE[lang_code]['default'])
                    full_comment = knowledge
                
                # 画像処理
                img_link = ""
                if img_file:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_link = upload_image_to_drive(img_file, f"baby_{ts}.jpg")

                # 保存 (G列=カテゴリ, H列=タイムスタンプ を追加)
                # 列順: 日付, 身長, 体重, 日記, AIコメント, 画像, カテゴリ, 時間
                sheet.append_row([str(d_val), h_val if h_val>0 else "", w_val if w_val>0 else "", note_val, full_comment, img_link, selected_cat_key, str(t_val)])
                st.success(text['success'])
            except Exception as e:
                st.error(f"Error: {e}")

# --- タブ2: タイムライン＆グラフ ---
with tab2:
    if st.button("🔄 Refresh"): st.rerun()
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        # データ整理
        df = df.rename(columns={
            '日付': 'Date', 'Date': 'Date',
            '身長': 'Height', 'Height': 'Height',
            '体重': 'Weight', 'Weight': 'Weight',
            '日記': 'Diary', 'Diary': 'Diary',
            'AIコメント': 'AI', 'AI Comment': 'AI',
            '画像': 'Image', 'Image': 'Image',
            'カテゴリ': 'Category', # 新しい列
            'タイムスタンプ': 'Time' # 新しい列
        })
        
        # 1. グラフ表示 (Growthデータがある場合のみ)
        growth_df = df[(df['Height'] != "") | (df['Weight'] != "")].copy()
        if not growth_df.empty:
            growth_df['Date'] = pd.to_datetime(growth_df['Date'])
            growth_df['Weight'] = pd.to_numeric(growth_df['Weight'], errors='coerce')
            
            st.markdown("### 📈 Growth Chart")
            fig = px.line(growth_df, x='Date', y='Weight', markers=True, line_shape='spline', color_discrete_sequence=['#F57C00'])
            fig.update_layout(plot_bgcolor='#FFF8E1', paper_bgcolor='#FFF8E1', margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # 2. タイムライン表示
        st.markdown("### 📅 Timeline")
        
        # 日付で降順ソート
        df['Date'] = pd.to_datetime(df['Date'])
        # 時間があれば結合してソート用にする
        df['DateTime'] = df.apply(lambda r: pd.to_datetime(f"{r['Date'].date()} {r.get('Time', '00:00:00')}") if 'Time' in r else r['Date'], axis=1)
        
        current_date = None
        
        for i, row in df.sort_values('DateTime', ascending=False).iterrows():
            # 日付ヘッダー
            row_date = row['Date'].strftime('%Y/%m/%d')
            if current_date != row_date:
                st.markdown(f"#### 🗓 {row_date}")
                current_date = row_date
            
            # データ準備
            cat_key = row.get('Category', 'Growth') # 古いデータはGrowth扱い
            if cat_key == "": cat_key = "Growth"
            
            icon = ICONS.get(cat_key, "📝")
            time_str = str(row.get('Time', ''))[:5] # 秒はカット
            
            # コンテンツの作成
            content_html = ""
            
            # 身長体重
            h = row.get('Height', '')
            w = row.get('Weight', '')
            if h or w:
                content_html += f"<div style='font-weight:bold; color:#E65100;'>{h}cm / {w}kg</div>"
            
            # 日記
            note = row.get('Diary', '')
            if lang_code == 'en': note = translate_text(str(note), 'en')
            if note:
                content_html += f"<div>{note}</div>"
            
            # 写真
            img_url = row.get('Image', '')
            img_html = ""
            if img_url and str(img_url).startswith('http'):
                img_html = f"<br><img src='{img_url}' style='width:100%; border-radius:10px; margin-top:5px;'>"
            
            # カード描画
            st.markdown(f"""
            <div class="timeline-container">
                <div class="timeline-dot" style="display:flex; justify-content:center; align-items:center; font-size:12px;">{icon}</div>
                <div class="entry-card">
                    <div class="time-label">{time_str} - {text['cats'].get(cat_key, cat_key)}</div>
                    {content_html}
                    {img_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info(text['no_data'])
