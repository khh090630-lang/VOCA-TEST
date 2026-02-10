import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
from urllib.parse import quote

# --- 1. 설정 및 데이터 로드 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM' 
SHEET_NAME = 'JS_voca' 

encoded_sheet_name = quote(SHEET_NAME)
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}'

class VocaPDF(FPDF):
    def __init__(self):
        super().__init__()
        try:
            self.add_font('Nanum', '', 'NanumGothic.otf', uni=True)
        except:
            pass

    def header(self):
        self.set_font('Nanum', '', 16)
        self.cell(0, 10, 'English Vocabulary Test', ln=True, align='C')
        self.ln(5)

@st.cache_data
def get_data():
    df = pd.read_csv(URL)
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    return df

st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")
st.title("📝 나만의 단어 시험지 생성기")

try:
    df = get_data()
    total_count = len(df)
    
    st.sidebar.header("⚙️ 시험지 설정")
    start_num = st.sidebar.number_input("시작 번호", min_value=1, max_value=total_count, value=1)
    end_num = st.sidebar.number_input("끝 번호", min_value=1, max_value=total_count, value=min(50, total_count))
    
    mode = st.sidebar.radio("시험 유형", ["영단어 보고 뜻 쓰기", "뜻 보고 영어 쓰기"])
    shuffle = st.sidebar.checkbox("단어 순서 무작위로 섞기", value=True)

    if st.button("📄 PDF 시험지 생성하기"):
        selected_df = df.iloc[start_num-1 : end_num].copy()
        selected_df['Original_No'] = range(start_num, end_num + 1)
        
        quiz_items = selected_df.values.tolist()
        if shuffle:
            random.shuffle(quiz_items)

        pdf = VocaPDF()
        col_width = 95 # 페이지 절반 너비 (A4 기준 약 190mm)

        # 1페이지: 문제지
        pdf.add_page()
        pdf.set_font('Nanum', '', 11)
        
        for i, item in enumerate(quiz_items, 1):
            word, meaning, origin_no = item
            question = word if mode == "영단어 보고 뜻 쓰기" else meaning
            
            # 질문 텍스트가 너무 길 경우 자르기 (너비 침범 방지)
            if len(question) > 20: 
                display_text = f"({origin_no}) {question[:18]}.."
            else:
                display_text = f"({origin_no}) {question}"
            
            # 현재 위치 저장
            curr_x = pdf.get_x()
            curr_y = pdf.get_y()

            # 질문 출력 (너비 고정)
            pdf.cell(col_width, 10, f"{display_text} : ____________________", border=0)
            
            # 2열 배치 로직
            if i % 2 == 0:
                pdf.ln(12) # 줄바꿈
            else:
                pdf.set_xy(curr_x + col_width, curr_y) # 옆 칸으로 이동

        # 2페이지: 정답지
        pdf.add_page()
        pdf.set_font('Nanum', '', 14)
        pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font('Nanum', '', 10)
        
        for i, item in enumerate(quiz_items, 1):
            word, meaning, origin_no = item
            answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
            
            curr_x = pdf.get_x()
            curr_y = pdf.get_y()
            
            pdf.cell(col_width, 10, f"({origin_no}) {answer}", border=0)
            
            if i % 2 == 0:
                pdf.ln(10)
            else:
                pdf.set_xy(curr_x + col_width, curr_y)

        pdf_output = bytes(pdf.output()) 
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_output,
            file_name=f"voca_test_{start_num}_{end_num}.pdf",
            mime="application/pdf"
        )

except Exception as e:
    st.error(f"에러 발생: {e}")
