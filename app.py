import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io

# --- 1. 설정 및 데이터 로드 ---
# 여기에 복사한 구글 시트 ID를 넣으세요
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM' 
SHEET_NAME = '조정식_voca' # 시트 하단 탭 이름
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

class VocaPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 한글 폰트 등록 (파일이 같은 경로에 있어야 함)
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
    # 필요한 열만 추출 (첫 번째 열: 영어, 두 번째 열: 뜻 가정)
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
        # 범위 선택 (사용자 입력 번호는 1번부터 시작하지만 인덱스는 0부터)
        selected_df = df.iloc[start_num-1 : end_num].copy()
        
        # 실제 시트상의 번호(행 번호) 추가
        selected_df['Original_No'] = range(start_num, end_num + 1)
        
        quiz_items = selected_df.values.tolist()
        if shuffle:
            random.shuffle(quiz_items)

        # PDF 제작
        pdf = VocaPDF()
        
        # 1페이지: 문제지
        pdf.add_page()
        pdf.set_font('Nanum', '', 12)
        col_width = 90
        
        for i, item in enumerate(quiz_items, 1):
            word, meaning, origin_no = item
            question = word if mode == "영단어 보고 뜻 쓰기" else meaning
            text = f"({origin_no}) {question} : ________________"
            
            pdf.cell(col_width, 10, text, border=0)
            if i % 2 == 0: pdf.ln(10)
        
        # 2페이지: 정답지
        pdf.add_page()
        pdf.set_font('Nanum', '', 14)
        pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font('Nanum', '', 11)
        
        for i, item in enumerate(quiz_items, 1):
            word, meaning, origin_no = item
            answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
            text = f"({origin_no}) {answer}"
            
            pdf.cell(col_width, 10, text, border=0)
            if i % 2 == 0: pdf.ln(10)

        # 다운로드 버튼
        pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_output,
            file_name=f"voca_test_{start_num}_{end_num}.pdf",
            mime="application/pdf"
        )

except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다. ID와 공유 설정을 확인하세요! \n에러: {e}")
