import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
import requests
from urllib.parse import quote
import os

# --- 1. 설정 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
SHEET_NAME = 'JS_voca' 
WRONG_SHEET_NAME = 'Wjsvoca' 

# 🔥 [중요] 구글 앱 스크립트 배포 후 받은 URL을 여기에 넣으세요
GAS_WEB_APP_URL = "여기에_URL을_붙여넣으세요"

def get_url(sheet_name):
    encoded_name = quote(sheet_name)
    return f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_name}'

class VocaPDF(FPDF):
    def __init__(self):
        super().__init__()
        base_path = os.getcwd()
        font_path = os.path.join(base_path, "NanumGothic.ttf") 
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")
        self.add_font('Nanum', '', font_path, uni=True)

    def header(self):
        self.set_font('Nanum', '', 16)
        self.cell(0, 10, 'English Vocabulary Test', ln=True, align='C')
        self.ln(5)

# --- 2. 데이터 불러오기 ---
@st.cache_data(show_spinner="데이터 로드 중...", ttl=5)
def get_data(sheet_name):
    try:
        url = get_url(sheet_name)
        df = pd.read_csv(url)
        # [구조 수정] A:번호(0), B:단어(1), C:뜻(2)
        df = df.iloc[:, [0, 1, 2]] 
        df.columns = ['No', 'Word', 'Meaning']
        df = df.dropna(subset=['Word'])
        df['No'] = pd.to_numeric(df['No'], errors='coerce')
        df = df.sort_values(by='No').reset_index(drop=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['No', 'Word', 'Meaning'])

# --- 3. UI 구성 ---
st.set_page_config(page_title="Voca PDF System", page_icon="📝")

st.sidebar.header("🔐 Admin Access")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
is_admin = (admin_pw == "1234") # 비밀번호 설정

menu_options = ["일반 시험지 생성"]
if is_admin:
    menu_options.append("관리자: 오답 관리 및 생성")

menu = st.sidebar.selectbox("메뉴 선택", menu_options)
st.title(f"📝 {menu}")

# --- 4. 메인 로직 ---
try:
    target_sheet = WRONG_SHEET_NAME if "관리자" in menu else SHEET_NAME
    df = get_data(target_sheet)

    if is_admin and "관리자" in menu:
        st.subheader("🛠️ 오답 단어 자동 등록")
        wrong_nos = st.text_input("틀린 번호 입력 (예: 5, 23, 104)", placeholder="번호 입력 후 버튼 클릭")
        if st.button("🚀 구글 시트로 전송"):
            if wrong_nos and "여기에" not in GAS_WEB_APP_URL:
                res = requests.get(f"{GAS_WEB_APP_URL}?nos={wrong_nos}")
                if res.status_code == 200:
                    st.success(f"전송 성공: {res.text}")
                    st.cache_data.clear()
                else: st.error("전송 실패")
            else: st.warning("번호를 입력하거나 GAS URL 설정을 확인하세요.")
        st.markdown("---")

    if df.empty:
        st.warning(f"'{target_sheet}' 시트에 데이터가 없습니다. (공유 설정 확인 필요)")
    else:
        # 번호 범위 설정
        min_v, max_v = int(df['No'].min()), int(df['No'].max())
        st.sidebar.header("⚙️ 시험지 설정")
        start_range = st.sidebar.number_input("시작 번호", min_value=min_v, max_value=max_v, value=min_v)
        end_range = st.sidebar.number_input("끝 번호", min_value=min_v, max_value=max_v, value=max_v)

        filtered_df = df[(df['No'] >= start_range) & (df['No'] <= end_range)]
        st.info(f"선택 범위 내 단어 수: **{len(filtered_df)}**개")

        mode = st.sidebar.radio("시험 유형", ["영단어 보고 뜻 쓰기", "뜻 보고 영어 쓰기"])
        shuffle = st.sidebar.checkbox("무작위 섞기", value=True)

        if st.button("📄 PDF 생성하기"):
            if filtered_df.empty:
                st.error("해당 범위에 단어가 없습니다.")
            else:
                quiz_items = filtered_df.values.tolist()
                if shuffle: random.shuffle(quiz_items)

                pdf = VocaPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # 1페이지: 문제지
                pdf.add_page()
                pdf.set_font('Nanum', '', 12)
                col_width = 90
                for i, item in enumerate(quiz_items, 1):
                    no, word, meaning = item
                    question = word if mode == "영단어 보고 뜻 쓰기" else meaning
                    if pdf.get_y() > 250:
                        pdf.add_page()
                        pdf.set_font('Nanum', '', 12)
                    cx, cy = pdf.get_x(), pdf.get_y()
                    pdf.cell(col_width, 7, f"({int(no)}) {question}")
                    pdf.set_xy(cx, cy + 7)
                    pdf.set_font('Nanum', '', 10); pdf.cell(col_width, 7, "Ans: ____________________")
                    pdf.set_font('Nanum', '', 12)
                    if i % 2 == 0: pdf.set_xy(pdf.l_margin, cy + 18)
                    else: pdf.set_xy(cx + col_width + 10, cy)
                
                # 2페이지: 정답지
                pdf.add_page()
                pdf.set_font('Nanum', '', 14); pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C'); pdf.ln(5)
                pdf.set_font('Nanum', '', 11)
                for i, item in enumerate(quiz_items, 1):
                    no, word, meaning = item
                    answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
                    if pdf.get_y() > 270:
                        pdf.add_page(); pdf.set_font('Nanum', '', 11)
                    cx, cy = pdf.get_x(), pdf.get_y()
                    pdf.cell(col_width, 8, f"({int(no)}) {answer}")
                    if i % 2 == 0: pdf.set_xy(pdf.l_margin, cy + 8)
                    else: pdf.set_xy(cx + col_width + 10, cy)

                # 🔥 [핵심 수정] 파일 안 열림 방지 로직
                pdf_output = pdf.output() # fpdf2 버전은 bytes를 직접 반환
                if isinstance(pdf_output, str): # 구버전 대응
                    pdf_output = pdf_output.encode("latin-1")
                
                st.download_button(
                    label="📥 PDF 다운로드", 
                    data=pdf_output, 
                    file_name=f"voca_test.pdf", 
                    mime="application/pdf"
                )

except Exception as e:
    st.error(f"오류 발생: {e}")
