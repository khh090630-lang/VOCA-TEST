import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
from urllib.parse import quote
import os

# --- 1. 설정 및 데이터 로드 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
SHEET_NAME = 'JS_voca' 

encoded_sheet_name = quote(SHEET_NAME)
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}&range=A1:B2001'

class VocaPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 폰트 파일 존재 여부 확인 (디버깅용)
        font_file = 'NanumGothic.otf'
        if not os.path.exists(font_file):
             st.error(f"❌ 폰트 파일을 찾을 수 없습니다: {font_file} 파일이 app.py와 같은 폴더에 있는지 확인하세요.")
        
        try:
            # 이름을 'Nanum'으로 등록
            self.add_font('Nanum', '', font_file, uni=True)
        except Exception as e:
            st.error(f"❌ 폰트 등록 중 오류 발생: {e}")

    def header(self):
        # 등록된 이름 'Nanum' 사용
        try:
            self.set_font('Nanum', '', 16)
            self.cell(0, 10, 'English Vocabulary Test', ln=True, align='C')
            self.ln(5)
        except:
            self.set_font('Arial', 'B', 16)

# --- 2. 데이터 불러오기 함수 ---
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=600)
def get_data():
    df = pd.read_csv(URL)
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    df = df.dropna(subset=['Word'])
    return df

# --- 3. UI 구성 ---
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
        if start_num > end_num:
            st.error("시작 번호가 끝 번호보다 클 수 없습니다.")
        else:
            selected_df = df.iloc[start_num-1 : end_num].copy()
            selected_df['Original_No'] = range(start_num, start_num + len(selected_df))
            
            quiz_items = selected_df.values.tolist()
            if shuffle:
                random.shuffle(quiz_items)

            pdf = VocaPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # 1페이지: 문제지
            pdf.add_page()
            pdf.set_font('Nanum', '', 12) # 여기서 소문자 nanum이 아닌지 확인!
            col_width = 90  
            
            for i, item in enumerate(quiz_items, 1):
                word, meaning, origin_no = item
                question = word if mode == "영단어 보고 뜻 쓰기" else meaning
                
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_font('Nanum', '', 12)

                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                
                pdf.cell(col_width, 7, f"({origin_no}) {question}", ln=0)
                pdf.set_xy(curr_x, curr_y + 7)
                pdf.set_font('Nanum', '', 10)
                pdf.cell(col_width, 7, "Ans: ____________________", ln=0)
                pdf.set_font('Nanum', '', 12)
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 18)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)
            
            # 2페이지: 정답지
            pdf.add_page()
            pdf.set_font('Nanum', '', 14)
            pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font('Nanum', '', 11)
            
            for i, item in enumerate(quiz_items, 1):
                word, meaning, origin_no = item
                answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
                
                if pdf.get_y() > 270:
                    pdf.add_page()
                    pdf.set_font('Nanum', '', 11)

                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                pdf.cell(col_width, 8, f"({origin_no}) {answer}", border=0)
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 8)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)

            pdf_output = pdf.output()
            st.download_button(
                label="📥 PDF 다운로드",
                data=bytes(pdf_output),
                file_name=f"voca_test_{start_num}_{end_num}.pdf",
                mime="application/pdf"
            )

except Exception as e:
    st.error(f"오류 발생: {e}")
