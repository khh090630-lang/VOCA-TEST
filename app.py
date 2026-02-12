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
WRONG_SHEET_NAME = 'Wjsvoca' # 오답 시트 이름

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

# --- 2. 데이터 불러오기 함수 ---
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=600)
def get_data(sheet_name):
    url = get_url(sheet_name)
    df = pd.read_csv(url)
    # A, B열만 가져오기 (번호가 포함된 경우를 대비해 인덱싱 조정 가능)
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    df = df.dropna(subset=['Word'])
    return df

# --- 3. UI 구성 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")

# 사이드바 관리자 로그인
st.sidebar.header("🔑 Admin")
admin_pw = st.sidebar.text_input("비밀번호", type="password")
is_admin = (admin_pw == "1234") # 원하는 비밀번호로 수정하세요

menu = st.sidebar.radio("작업 선택", ["일반 시험지 생성", "오답 시험지 생성 (Wjsvoca)"])

st.title(f"📝 {menu}")

# --- 관리자 전용: 오답 번호 추출기 ---
if is_admin:
    st.markdown("### 🛠️ 오답 기록 도우미")
    with st.expander("틀린 번호 입력하기"):
        wrong_input = st.text_input("틀린 번호들을 입력하세요 (예: 1, 5, 12, 45)", "")
        if wrong_input:
            try:
                main_df = get_data(SHEET_NAME)
                # 입력받은 번호 파싱
                nums = [int(n.strip()) for n in wrong_input.split(',') if n.strip().isdigit()]
                # 원본 데이터에서 해당 인덱스 추출 (번호가 1부터 시작한다고 가정)
                wrong_result = main_df.iloc[[n-1 for n in nums if n <= len(main_df)]]
                
                st.write("▼ 아래 내용을 복사해서 **Wjsvoca** 시트에 붙여넣으세요.")
                csv_buffer = io.StringIO()
                wrong_result.to_csv(csv_buffer, index=False, header=False)
                st.text_area("복사용 텍스트", csv_buffer.getvalue(), height=150)
            except Exception as e:
                st.error(f"번호 추출 중 오류: {e}")

# --- 메인 로직 ---
try:
    # 메뉴 선택에 따라 시트 변경
    target_sheet = SHEET_NAME if menu == "일반 시험지 생성" else WRONG_SHEET_NAME
    df = get_data(target_sheet)
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
            pdf.set_font('Nanum', '', 12)
            col_width = 90  
            
            for i, item in enumerate(quiz_items, 1):
                word, meaning, origin_no = item
                question = word if mode == "영단어 보고 뜻 쓰기" else meaning
                
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_font('Nanum', '', 12)

                curr_x, curr_y = pdf.get_x(), pdf.get_y()
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

                curr_x, curr_y = pdf.get_x(), pdf.get_y()
                pdf.cell(col_width, 8, f"({origin_no}) {answer}", border=0)
                
                if i % 2 == 0:
                    pdf.set_xy(pdf.l_margin, curr_y + 8)
                else:
                    pdf.set_xy(curr_x + col_width + 10, curr_y)

            pdf_output = pdf.output(dest="S").encode("latin-1")
            st.download_button(
                label="📥 PDF 다운로드",
                data=pdf_output,
                file_name=f"voca_{menu}.pdf",
                mime="application/pdf"
            )

except Exception as e:
    st.error(f"데이터 로드 중 에러 발생: {e}")
