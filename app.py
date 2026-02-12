import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
import os
from urllib.parse import quote

# --- 1. 설정 및 데이터 로드 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
W_SHEET_ID = '1WzJ58eKSPeBcO7wg6_XZUzedin385rWJp_eoLB8Ez2w'

SHEET_NAME = 'JS_voca'
WRONG_SHEET_NAME = 'Wjsvoca'

def get_sheet_url(file_id, sheet_name):
    encoded_name = quote(sheet_name)
    return f'https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}&range=A1:C2001'

class VocaPDF(FPDF):
    def __init__(self, title_text): # 제목을 인자로 받음
        super().__init__()
        self.title_text = title_text
        base_path = os.getcwd()
        font_path = os.path.join(base_path, "NanumGothic.ttf")
        if not os.path.exists(font_path):
            st.error("폰트 파일이 없습니다.")
            st.stop()
        self.add_font('Nanum', '', font_path, uni=True)

    def header(self):
        self.set_font('Nanum', '', 16)
        self.cell(0, 10, self.title_text, ln=True, align='C') # 설정된 제목 출력
        self.ln(5)

@st.cache_data(show_spinner="데이터 로드 중...", ttl=5)
def get_data(file_id, sheet_name):
    try:
        url = get_sheet_url(file_id, sheet_name)
        df = pd.read_csv(url)
        df = df.iloc[:, [0, 1, 2]]
        df.columns = ['No', 'Word', 'Meaning']
        df = df.dropna(subset=['Word'])
        df['No'] = pd.to_numeric(df['No'], errors='coerce')
        return df.dropna(subset=['No'])
    except:
        return pd.DataFrame(columns=['No', 'Word', 'Meaning'])

# --- 2. UI 구성 ---
st.set_page_config(page_title="Voca Generator", page_icon="📝")

st.sidebar.header("🔐 Admin Access")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
is_admin = (admin_pw == "1234")

menu_options = ["일반 시험지 생성"]
if is_admin:
    menu_options.append("관리자: 오답 관리 및 생성")

menu = st.sidebar.selectbox("메뉴 선택", menu_options)
st.title(f"📝 {menu}")

# 데이터 로드 및 PDF 제목 설정
if "관리자" in menu:
    source_df = get_data(SHEET_ID, SHEET_NAME)
    df = get_data(W_SHEET_ID, WRONG_SHEET_NAME)
    pdf_title = "Wrong Vocabulary Test" # 관리자용 제목
else:
    df = get_data(SHEET_ID, SHEET_NAME)
    pdf_title = "English Vocabulary Test" # 일반용 제목

try:
    if is_admin and "관리자" in menu:
        st.subheader("🔍 1. 오답 단어 추출 (수동 복사용)")
        input_nos = st.text_input("틀린 번호를 입력하세요 (예: 5, 12, 104)")
        if input_nos:
            target_nos = [int(n.strip()) for n in input_nos.split(",") if n.strip().isdigit()]
            extracted_df = source_df[source_df['No'].isin(target_nos)]
            if not extracted_df.empty:
                st.dataframe(extracted_df, use_container_width=True)
                st.code(extracted_df.to_csv(index=False, header=False, sep='\t'), language='text')
        st.markdown("---")
        st.subheader("📄 2. 오답 학습지 범위 설정")

    st.sidebar.header("⚙️ 시험지 설정")
    if not df.empty:
        real_min = int(df['No'].min())
        real_max = int(df['No'].max())
        
        start_num = st.sidebar.number_input(f"시작 번호", value=real_min)
        end_num = st.sidebar.number_input(f"끝 번호", value=real_max)
        mode = st.sidebar.radio("시험 유형", ["영단어 보고 뜻 쓰기", "뜻 보고 영어 쓰기"])
        shuffle = st.sidebar.checkbox("단어 순서 섞기", value=True)

        if st.button("📄 PDF 생성하기"):
            selected_df = df[(df['No'] >= start_num) & (df['No'] <= end_num)].copy()
            if selected_df.empty:
                st.error("해당 범위에 단어가 없습니다.")
            else:
                quiz_items = selected_df.values.tolist()
                if shuffle: random.shuffle(quiz_items)

                # --- PDF 생성 (pdf_title 전달) ---
                pdf = VocaPDF(pdf_title)
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font('Nanum', '', 12)
                
                col_width = 90
                for i, item in enumerate(quiz_items, 1):
                    no, word, meaning = item
                    q = word if mode == "영단어 보고 뜻 쓰기" else meaning
                    if pdf.get_y() > 250: pdf.add_page()
                    cx, cy = pdf.get_x(), pdf.get_y()
                    pdf.cell(col_width, 7, f"({int(no)}) {q}", ln=0)
                    pdf.set_xy(cx, cy + 7)
                    pdf.set_font('Nanum', '', 10)
                    pdf.cell(col_width, 7, "Ans: ____________________", ln=0)
                    pdf.set_font('Nanum', '', 12)
                    if i % 2 == 0: pdf.set_xy(pdf.l_margin, cy + 18)
                    else: pdf.set_xy(cx + col_width + 10, cy)
                
                pdf.add_page()
                pdf.set_font('Nanum', '', 14); pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C'); pdf.ln(5)
                pdf.set_font('Nanum', '', 11)
                for i, item in enumerate(quiz_items, 1):
                    no, word, meaning = item
                    ans = meaning if mode == "영단어 보고 뜻 쓰기" else word
                    if pdf.get_y() > 270: pdf.add_page()
                    cx, cy = pdf.get_x(), pdf.get_y()
                    pdf.cell(col_width, 8, f"({int(no)}) {ans}", border=0)
                    if i % 2 == 0: pdf.set_xy(pdf.l_margin, cy + 8)
                    else: pdf.set_xy(cx + col_width + 10, cy)

                st.download_button(label="📥 PDF 다운로드", data=pdf.output(dest="S").encode("latin-1"),
                                 file_name=f"test_{start_num}_{end_num}.pdf", mime="application/pdf")
except Exception as e:
    st.error(f"오류: {e}")
