import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
import requests
from urllib.parse import quote
import os

# --- 1. 설정 및 데이터 로드 ---
# 원본 단어장 파일 ID
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
# 🔥 [수정] 오답 시트 파일의 실제 ID를 여기에 입력하세요
W_SHEET_ID = '1WzJ58eKSPeBcO7wg6_XZUzedin385rWJp_eoLB8Ez2w'

SHEET_NAME = 'JS_voca'
WRONG_SHEET_NAME = 'Wjsvoca'
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwT3P3EcV1Luf9HgcxzRChyH2dDMIO4xo3cuLbOsqZCQRjc-YjorMc2ojQg3JKYokJf/exec"

def get_sheet_url(file_id, sheet_name):
    encoded_name = quote(sheet_name)
    # A1:C2001로 범위를 확장하여 번호(A), 단어(B), 뜻(C)을 모두 가져옵니다.
    return f'https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}&range=A1:C2001'

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

# --- 2. 데이터 불러오기 함수 ---
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=5)
def get_data(file_id, sheet_name):
    url = get_sheet_url(file_id, sheet_name)
    df = pd.read_csv(url)
    # [구조 수정] A(0):번호, B(1):단어, C(2):뜻
    df = df.iloc[:, [0, 1, 2]]
    df.columns = ['No', 'Word', 'Meaning']
    df = df.dropna(subset=['Word'])
    return df

# --- 3. UI 구성 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")

# 사이드바 관리자 로그인
st.sidebar.header("🔐 Admin Access")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
is_admin = (admin_pw == "1234")

menu_options = ["일반 시험지 생성"]
if is_admin:
    menu_options.append("관리자: 오답 관리 및 생성")

menu = st.sidebar.selectbox("메뉴 선택", menu_options)
st.title(f"📝 {menu}")

try:
    # 🔥 [수정] 메뉴에 따라 타겟 파일 ID와 시트 이름 변경
    if "관리자" in menu:
        target_file_id = W_SHEET_ID
        target_sheet = WRONG_SHEET_NAME
    else:
        target_file_id = SHEET_ID
        target_sheet = SHEET_NAME

    df = get_data(target_file_id, target_sheet)
    total_count = len(df)

    # 관리자 전용 오답 전송 UI
    if is_admin and "관리자" in menu:
        st.subheader("🛠️ 오답 단어 자동 등록")
        wrong_nos = st.text_input("틀린 번호 입력 (예: 5, 23, 104)")
        if st.button("🚀 구글 시트로 전송"):
            if wrong_nos and "https://script" in GAS_WEB_APP_URL:
                res = requests.get(f"{GAS_WEB_APP_URL}?nos={wrong_nos}")
                if res.status_code == 200:
                    st.success(f"전송 성공: {res.text}")
                    st.cache_data.clear()
                else: st.error("전송 실패")
            else: st.warning("번호를 입력하거나 URL 설정을 확인하세요.")
        st.markdown("---")
        st.subheader("📄 오답 학습지 생성")

    # 시험지 설정 UI
    st.sidebar.header("⚙️ 시험지 설정")
    # 실제 데이터의 번호(No열) 기준으로 범위 설정
    min_no = int(df['No'].min()) if not df.empty else 1
    max_no = int(df['No'].max()) if not df.empty else 1
    
    start_num = st.sidebar.number_input("시작 번호", min_value=min_no, max_value=max_no, value=min_no)
    end_num = st.sidebar.number_input("끝 번호", min_value=min_no, max_value=max_no, value=max_no)
    
    st.sidebar.write(f"현재 로드된 단어 수: **{total_count}개**")
    mode = st.sidebar.radio("시험 유형", ["영단어 보고 뜻 쓰기", "뜻 보고 영어 쓰기"])
    shuffle = st.sidebar.checkbox("단어 순서 무작위로 섞기", value=True)

    if st.button("📄 PDF 시험지 생성하기"):
        if start_num > end_num:
            st.error("시작 번호가 끝 번호보다 클 수 없습니다.")
        else:
            # 실제 'No' 열의 값을 기준으로 필터링
            selected_df = df[(df['No'] >= start_num) & (df['No'] <= end_num)].copy()
            
            quiz_items = selected_df.values.tolist() # [No, Word, Meaning] 순서
            if shuffle:
                random.shuffle(quiz_items)

            pdf = VocaPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # --- 1페이지: 문제지 ---
            pdf.add_page()
            pdf.set_font('Nanum', '', 12)
            col_width = 90
            
            for i, item in enumerate(quiz_items, 1):
                origin_no, word, meaning = item
                question = word if mode == "영단어 보고 뜻 쓰기" else meaning
                
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_font('Nanum', '', 12)

                curr_x, curr_y = pdf.get_x(), pdf.get_y()
                
                pdf.cell(col_width, 7, f"({int(origin_no)}) {question}", ln=0)
                pdf.set_xy(curr_x, curr_y + 7)
                pdf.set_font('Nanum', '', 10)
                pdf.cell(col_width, 7, "Ans: ____________________", ln=0)
                pdf.set_font('Nanum', '', 12)
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 18)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)
            
            # --- 2페이지: 정답지 ---
            pdf.add_page()
            pdf.set_font('Nanum', '', 14)
            pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font('Nanum', '', 11)
            
            for i, item in enumerate(quiz_items, 1):
                origin_no, word, meaning = item
                answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
                
                if pdf.get_y() > 270:
                    pdf.add_page()
                    pdf.set_font('Nanum', '', 11)

                curr_x, curr_y = pdf.get_x(), pdf.get_y()
                pdf.cell(col_width, 8, f"({int(origin_no)}) {answer}", border=0)
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 8)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)

            # 기존에 잘 작동하던 PDF 출력 방식 그대로 유지
            pdf_output = pdf.output(dest="S").encode("latin-1")

            st.download_button(
                label="📥 PDF 다운로드",
                data=pdf_output,
                file_name=f"voca_test_{start_num}_{end_num}.pdf",
                mime="application/pdf"
            )

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
