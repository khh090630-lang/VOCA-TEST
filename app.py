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
        # 파일명이 NanumGothic.otf 인지 다시 한 번 확인하세요!
        font_file = 'NanumGothic.otf' 
        
        if os.path.exists(font_file):
            try:
                # [핵심 수정] fpdf2 전용: uni=True는 절대 쓰지 마세요. 
                # fname을 사용해 바이너리로 읽도록 명시합니다.
                self.add_font('Nanum', style='', fname=font_file)
            except Exception as e:
                st.error(f"폰트 등록 실패: {e}")
        else:
            st.error(f"❌ '{font_file}' 파일을 찾을 수 없습니다. 경로를 확인하세요.")

    def header(self):
        try:
            self.set_font('Nanum', size=16)
            self.cell(0, 10, 'English Vocabulary Test', ln=True, align='C')
            self.ln(5)
        except:
            # 폰트 로드 실패 시 비상용 폰트
            self.set_font('Helvetica', style='B', size=16)

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
            # fpdf2에서는 set_font('이름', size=숫자) 형식을 권장합니다.
            pdf.set_font('Nanum', size=12)
            col_width = 90  
            
            for i, item in enumerate(quiz_items, 1):
                word, meaning, origin_no = item
                question = word if mode == "영단어 보고 뜻 쓰기" else meaning
                
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_font('Nanum', size=12)

                curr_x, curr_y = pdf.get_x(), pdf.get_y()
                
                pdf.cell(col_width, 7, f"({origin_no}) {question}")
                pdf.set_xy(curr_x, curr_y + 7)
                pdf.set_font('Nanum', size=10)
                pdf.cell(col_width, 7, "Ans: ____________________")
                pdf.set_font('Nanum', size=12)
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 18)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)
            
            # 2페이지: 정답지
            pdf.add_page()
            pdf.set_font('Nanum', size=14)
            pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font('Nanum', size=11)
            
            for i, item in enumerate(quiz_items, 1):
                word, meaning, origin_no = item
                answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
                
                if pdf.get_y() > 270:
                    pdf.add_page()
                    pdf.set_font('Nanum', size=11)

                curr_x, curr_y = pdf.get_x(), pdf.get_y()
                pdf.cell(col_width, 8, f"({origin_no}) {answer}")
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 8)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)

            # [핵심] fpdf2의 출력은 bytes()로 변환해서 넘겨야 안전합니다.
            st.download_button(
                label="📥 PDF 다운로드",
                data=bytes(pdf.output()),
                file_name=f"voca_test_{start_num}_{end_num}.pdf",
                mime="application/pdf"
            )

except Exception as e:
    st.error(f"오류 발생: {e}")
