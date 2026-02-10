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
# 중요: &range=A1:B2001 을 추가하여 2000번 단어까지 강제로 읽어옵니다.
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}&range=A1:B2001'

class VocaPDF(FPDF):
    def __init__(self):
        super().__init__()
        try:
            # 폰트 파일명이 나눔고딕.otf 라면 이름을 맞춰주세요.
            self.add_font('Nanum', '', 'NanumGothic.otf', uni=True)
        except:
            pass

    def header(self):
        self.set_font('Nanum', '', 16)
        self.cell(0, 10, 'English Vocabulary Test', ln=True, align='C')
        self.ln(5)

# --- 2. 데이터 불러오기 함수 ---
# 캐시가 꼬이는 것을 방지하기 위해 설정을 추가했습니다.
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=600)
def get_data():
    # 데이터를 읽어올 때 제목 행이 없더라도 에러가 나지 않도록 처리
    df = pd.read_csv(URL)
    # 첫 번째, 두 번째 열만 선택
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    # 혹시 모를 빈 줄 제거
    df = df.dropna(subset=['Word'])
    return df

# --- 3. UI 구성 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")
st.title("📝 나만의 단어 시험지 생성기")
st.info("구글 스프레드시트의 2,000단어 데이터를 연동합니다.")

try:
    df = get_data()
    total_count = len(df)
    
    st.sidebar.header("⚙️ 시험지 설정")
    # 시작 번호와 끝 번호의 최댓값을 total_count로 자동 설정
    start_num = st.sidebar.number_input("시작 번호", min_value=1, max_value=total_count, value=1)
    end_num = st.sidebar.number_input("끝 번호", min_value=1, max_value=total_count, value=min(50, total_count))
    
    st.sidebar.write(f"현재 로드된 단어 수: **{total_count}개**")

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
            pdf.set_font('Nanum', '', 12)
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
                
                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                pdf.cell(col_width, 10, f"({origin_no}) {answer}", border=0)
                
                if i % 2 == 0:
                    pdf.ln(10)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)

            # 출력 스트림 처리
            pdf_output = pdf.output()
            
            st.download_button(
                label="📥 PDF 다운로드",
                data=bytes(pdf_output),
                file_name=f"voca_test_{start_num}_{end_num}.pdf",
                mime="application/pdf"
            )

except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다. 구글 시트의 '링크가 있는 모든 사용자-뷰어' 설정과 시트 이름을 확인하세요. 에러: {e}")
