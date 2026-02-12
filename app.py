import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
import requests  # 구글 시트 전송을 위해 추가
from urllib.parse import quote
import os

# --- 1. 설정 및 데이터 로드 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
SHEET_NAME = 'JS_voca' 
WRONG_SHEET_NAME = 'Wjsvoca' 

# 🔥 [중요] 배포 후 받은 구글 웹 앱 URL을 여기에 붙여넣으세요
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyxvuaqJzTjtBznCjZujEPI_tDMOjXtKZZDJr9c8_Bjnux0W2Jzm_V2lCavx0mo_jY/exec"

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

# --- 2. 데이터 불러오기 및 정렬 함수 ---
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=10) # 오답 반영을 위해 짧게 설정
def get_data(sheet_name):
    url = get_url(sheet_name)
    df = pd.read_csv(url)
    # A, B, C열 가져오기 (번호, 단어, 뜻)
    df = df.iloc[:, [0, 1, 2]] 
    df.columns = ['No', 'Word', 'Meaning']
    df = df.dropna(subset=['Word'])
    
    # [수정] 번호순 정렬 로직 추가
    df['No'] = pd.to_numeric(df['No'], errors='coerce')
    df = df.sort_values(by='No').reset_index(drop=True)
    return df

# --- 3. UI 구성 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")

# 사이드바 관리자 로그인 및 모드 선택
st.sidebar.header("🔑 Admin")
admin_pw = st.sidebar.text_input("비밀번호", type="password")
is_admin = (admin_pw == "1234") 

menu = st.sidebar.radio("작업 선택", ["일반 시험지 생성", "오답 학습지 관리/생성"])

st.title(f"📝 {menu}")

# --- [수정] 관리자 전용: 오답 자동 전송 기능 ---
if menu == "오답 학습지 관리/생성":
    st.markdown("### 🛠️ 오답 단어 자동 등록")
    with st.container():
        wrong_nos = st.text_input("틀린 번호들을 입력하세요 (예: 5, 23, 104)", placeholder="입력 후 아래 버튼 클릭")
        if st.button("🚀 구글 시트로 자동 전송"):
            if wrong_nos and "여기에" not in GAS_WEB_APP_URL:
                try:
                    res = requests.get(f"{GAS_WEB_APP_URL}?nos={wrong_nos}")
                    if res.status_code == 200:
                        st.success(f"성공: {res.text}")
                        st.cache_data.clear() # 데이터 즉시 갱신
                    else:
                        st.error("전송 실패. URL 배포 설정을 확인하세요.")
                except Exception as e:
                    st.error(f"에러 발생: {e}")
            else:
                st.warning("번호를 입력하거나 웹 앱 URL 설정을 확인하세요.")
    st.markdown("---")

# --- 4. 메인 로직 (PDF 생성) ---
try:
    target_sheet = SHEET_NAME if menu == "일반 시험지 생성" else WRONG_SHEET_NAME
    df = get_data(target_sheet)
    
    if df.empty:
        st.warning(f"{target_sheet} 시트에 데이터가 없습니다.")
    else:
        total_count = len(df)
        min_no = int(df['No'].min())
        max_no = int(df['No'].max())

        st.sidebar.header("⚙️ 시험지 설정")
        # [수정] 실제 단어 번호 기준으로 범위 선택 가능하게 변경
        start_range = st.sidebar.number_input("시작 번호 (범위)", min_value=min_no, max_value=max_no, value=min_no)
        end_range = st.sidebar.number_input("끝 번호 (범위)", min_value=min_no, max_value=max_no, value=max_no)
        
        # 범위 필터링
        filtered_df = df[(df['No'] >= start_range) & (df['No'] <= end_range)]
        
        if menu == "오답 학습지 관리/생성":
            st.info(f"선택한 범위({start_range}~{end_range}) 내 오답 단어 수: **{len(filtered_df)}**개")

        mode = st.sidebar.radio("시험 유형", ["영단어 보고 뜻 쓰기", "뜻 보고 영어 쓰기"])
        shuffle = st.sidebar.checkbox("단어 순서 무작위로 섞기", value=True)

        if st.button("📄 PDF 시험지 생성하기"):
            if filtered_df.empty:
                st.error("해당 범위 내에 단어가 없습니다.")
            else:
                quiz_items = filtered_df.values.tolist() # [No, Word, Meaning]
                if shuffle:
                    random.shuffle(quiz_items)

                pdf = VocaPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # 1페이지: 문제지
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
                
                # 2페이지: 정답지
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

                pdf_output = pdf.output(dest="S").encode("latin-1")
                st.download_button(
                    label="📥 PDF 다운로드",
                    data=pdf_output,
                    file_name=f"voca_{target_sheet}_{start_range}_{end_range}.pdf",
                    mime="application/pdf"
                )

except Exception as e:
    st.error(f"에러 발생: {e}")
