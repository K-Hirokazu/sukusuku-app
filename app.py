import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
from dateutil.relativedelta import relativedelta

# ==========================================
# 1. 知識データベース (一般教養・アドバイス)
# ==========================================
# AIが参照する「月齢ごとの一般的な成長目安とアドバイス」です
KNOWLEDGE_BASE = {
    'jp': {
        0: "【生後0ヶ月】睡眠リズムが未完成な時期です。1日あたり25〜30gの体重増加が目安です。授乳やミルクの間隔が短く大変な時期ですが、ママ・パパも休めるときに休んでくださいね。",
        1: "【生後1ヶ月】手足を活発に動かし始めます。1ヶ月健診が終わって少しホッとする頃ですね。外気浴を少しずつ始めても良い時期です。",
        2: "【生後2ヶ月】表情が出てきて「アー」「ウー」とお話し（クーイング）し始める子もいます。予防接種のスケジュール管理が大切になる時期です。",
        3: "【生後3ヶ月】首がすわり始める大きな節目です。自分の手を見つめる「ハンドガード」が見られるかも。満腹中枢ができ始め、遊び飲みも増えます。",
        4: "【生後4ヶ月】首がしっかりしてきて、縦抱きが安定します。昼夜の区別がつき始めます。寝返りの練習を始める子もいるかもしれません。",
        5: "【生後5ヶ月】離乳食の開始時期（ゴックン期）の目安です。支えてあげると座れるようになることも。下の歯が生え始める子もいます。",
        6: "【生後6ヶ月】お座りが安定してくる時期です。免疫が切れ始め、風邪を引きやすくなるので体調変化に注意しましょう。",
        # ...必要に応じて増やせます
        'default': "すくすくと成長していますね！個性を大切に見守りましょう。"
    },
    'en': {
        0: "[0 Months] Sleep cycles are irregular. Expected weight gain is 25-30g/day. It's a demanding time for feeding; ensure parents rest when possible.",
        1: "[1 Month] Limbs start moving actively. Time for the 1-month checkup. Short 'air baths' (fresh air) can begin.",
        2: "[2 Months] Expressions appear, and 'cooing' may start. Important time to manage the vaccination schedule.",
        3: "[3 Months] Neck control improves significantly. Babies may start staring at their hands (Hand Regard). Satiety centers develop, leading to 'play feeding'.",
        4: "[4 Months] Neck is steady; vertical holding becomes easier. Circadian rhythms develop. Some babies may start trying to roll over.",
        5: "[5 Months] Typical time to start solids (weaning). May sit with support. Lower teeth might start appearing.",
        6: "[6 Months] Sitting becomes more stable. Maternal immunity fades, so watch out for first colds.",
        'default': "Growing well! Cherish their unique pace."
    }
}

# ==========================================
# 2. 言語・UI設定
# ==========================================
UI_TEXT = {
    'jp': {
        'title': '👶 すくすく成長ログ',
        'tab_record': '記録する',
        'tab_history': 'これまでの分析',
        'date': '日付',
        'height': '身長 (cm)',
        'weight': '体重 (kg)',
        'diary': '日記・メモ',
        'submit': '保存＆AI分析開始',
        'success': 'データ保存完了！分析結果を表示します↓',
        'setting_header': '設定 / Settings',
        'birthday_label': 'お子さんの誕生日',
        'lang_label': '表示言語 / Language',
        'ai_result_title': '🤖 AI成長分析レポート',
        'no_data': 'まだデータがありません。最初の記録を入力してください！'
    },
    'en': {
        'title': '👶 SukuSuku Growth Log',
        'tab_record': 'New Entry',
        'tab_history': 'Analysis History',
        'date': 'Date',
        'height': 'Height (cm)',
        'weight': 'Weight (kg)',
        'diary': 'Diary / Notes',
        'submit': 'Save & Analyze',
        'success': 'Saved! See analysis below:',
        'setting_header': 'Settings',
        'birthday_label': 'Baby\'s Birthday',
        'lang_label': 'Language',
        'ai_result_title': '🤖 AI Growth Analysis Report',
        'no_data': 'No data yet. Please add the first entry!'
    }
}

# --- 言語切り替えロジック ---
st.sidebar.header("Settings")
lang_mode = st.sidebar.radio("Language", ["日本語", "English"])
lang_code = 'jp' if lang_mode == "日本語" else 'en'
text = UI_TEXT[lang_code]

# --- 誕生日の設定（月齢計算に必須） ---
# ※一度入力したら覚えておくためにSessionStateを使いますが、
# 本格的にはスプレッドシートに保存するか、ここで毎回入力します。
birthday = st.sidebar.date_input(text['birthday_label'], datetime.date(2024, 1, 1))

# ==========================================
# 3. 機能関数
# ==========================================
def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("すくすくログ").sheet1

def analyze_growth(current_date, weight, height, diary_text, prev_data, birthday):
    """
    データと一般知識を組み合わせてコメントを生成する関数
    """
    # 月齢計算
    age = relativedelta(current_date, birthday)
    months_old = age.years * 12 + age.months
    
    # 知識ベースからのアドバイス取得
    knowledge = KNOWLEDGE_BASE[lang_code].get(months_old, KNOWLEDGE_BASE[lang_code]['default'])
    
    # データ分析
    analysis_msg = ""
    if prev_data:
        prev_w = float(prev_data.get('体重') or prev_data.get('Weight') or 0)
        diff = weight - prev_w
        
        if lang_code == 'jp':
            analysis_msg = f"前回の記録から **{diff:+.2f}kg** 変化しました。"
            if diff > 0.5:
                analysis_msg += " 急激に大きくなっていますね！成長スパートかもしれません。"
            elif diff < 0:
                analysis_msg += " 少し体重が減っています。活動量が増えた影響かもしれませんが、続くようなら様子を見てください。"
        else:
            analysis_msg = f"Weight changed by **{diff:+.2f}kg** since last record."
            if diff > 0.5:
                analysis_msg += " A significant increase! Likely a growth spurt."
            elif diff < 0:
                analysis_msg += " Slight weight loss. Monitor if it continues, but may be due to increased activity."
    else:
        if lang_code == 'jp':
            analysis_msg = "これが最初のデータポイントです。ここから成長を見守っていきましょう！"
        else:
            analysis_msg = "First data point recorded. Let's track the journey from here!"

    # 最終的なコメント生成
    if lang_code == 'jp':
        full_comment = f"""
        【データ分析】
        現在、生後{months_old}ヶ月{age.days}日です。
        {analysis_msg}
        
        【今月の成長知識・アドバイス】
        {knowledge}
        
        【メモへのコメント】
        「{diary_text}」という記録、大切な思い出になりますね。
        """
    else:
        full_comment = f"""
        [Data Analysis]
        Age: {months_old} months and {age.days} days.
        {analysis_msg}
        
        [Developmental Milestones]
        {knowledge}
        
        [Note]
        Documenting "{diary_text}" creates a precious memory.
        """
    
    return full_comment.strip()

# ==========================================
# 4. メインアプリ処理
# ==========================================
st.title(text['title'])

tab1, tab2 = st.tabs([text['tab_record'], text['tab_history']])

with tab1:
    with st.form("entry_form"):
        d_val = st.date_input(text['date'], datetime.date.today())
        h_val = st.number_input(text['height'], min_value=0.0, format="%.1f")
        w_val = st.number_input(text['weight'], min_value=0.0, format="%.3f") # 細かく3桁まで
        note_val = st.text_area(text['diary'])
        
        submitted = st.form_submit_button(text['submit'])
        
        if submitted:
            try:
                sheet = get_sheet()
                all_records = sheet.get_all_records()
                
                # 直近データ取得
                prev_data = all_records[-1] if all_records else None
                
                # ★ここでAI分析を実行
                ai_result = analyze_growth(d_val, w_val, h_val, note_val, prev_data, birthday)
                
                # 保存 (画像は今回は空欄)
                # 日本語モードでも英語モードでも、スプレッドシートには日本語ヘッダーの列に書き込みます
                sheet.append_row([str(d_val), h_val, w_val, note_val, ai_result, ""])
                
                st.success(text['success'])
                st.info(ai_result) # その場で分析結果を表示
                
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    if st.button("Reload"):
        st.experimental_rerun()
        
    try:
        sheet = get_sheet()
        df = pd.DataFrame(sheet.get_all_records())
        
        if not df.empty:
            # 最新順に並び替え
            for i, row in df.iloc[::-1].iterrows():
                # カード形式で表示
                with st.container():
                    st.markdown("---")
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.subheader(f"{row['日付']}")
                        st.metric("Height", f"{row['身長']} cm")
                        st.metric("Weight", f"{row['体重']} kg")
                    with col2:
                        st.caption(text['diary'])
                        st.write(f"{row['日記']}")
                        st.caption(text['ai_result_title'])
                        # AIコメントを目立たせる
                        st.info(f"{row['AIコメント']}")
        else:
            st.info(text['no_data'])
            
    except Exception as e:
        st.write("Setting up...")
