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

# --- 2. 데이터 불러오기 함수 ---
@st.cache_data
def get_data():
    df = pd.read_csv(URL)
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    return df

# --- 3. UI 구성 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")
st.title("📝 나만의 단어 시험지 생성기")
st.info("구글 스프레드시트의 2행부터 1번 단어로 인식합니다.")

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
        # 자동 페이지 넘김으로 인한 잘림 방지 (하단 여백 15mm 설정)
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # 1페이지: 문제지
        pdf.add_page()
        pdf.set_font('Nanum', '', 12)
        col_width = 90  
        
        for i, item in enumerate(quiz_items, 1):
            word, meaning, origin_no = item
            question = word if mode == "영단어 보고 뜻 쓰기" else meaning
            
            # 페이지 끝에 도달했는지 확인 (새 페이지 생성)
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_font('Nanum', '', 12)

            curr_x = pdf.get_x()
            curr_y = pdf.get_y()
            
            # 1. 질문 출력
            pdf.cell(col_width, 7, f"({origin_no}) {question}", ln=0)
            
            # 2. 밑줄 출력 (질문 바로 아래 7mm 지점)
            pdf.set_xy(curr_x, curr_y + 7)
            pdf.set_font('Nanum', '', 10) # 밑줄 안내 문구는 살짝 작게
            pdf.cell(col_width, 7, "Ans: ____________________", ln=0)
            pdf.set_font('Nanum', '', 12) # 다시 원래 크기로
            
            # 3. 다음 위치 설정
            if i % 2 == 0:
                # 짝수번째면 다음 줄로 (세로 간격 확보)
                pdf.set_xy(pdf.l_margin, curr_y + 18)
            else:
                # 홀수번째면 오른쪽 열로 이동하되 높이는 유지
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
            
            curr_x = pdf.get_x()
            curr_y = pdf.get_y()
            pdf.cell(col_width, 10, f"({origin_no}) {answer}", border=0)
            
            if i % 2 == 0:
                pdf.ln(10)
            else:
                pdf.set_xy(curr_x + col_width + 10, curr_y)

        pdf_output = bytes(pdf.output()) 
        
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_output,
            file_name=f"voca_test_{start_num}_{end_num}.pdf",
            mime="application/pdf"
        )

except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다. 에러: {e}")
