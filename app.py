import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
from urllib.parse import quote
from streamlit_gsheets import GSheetsConnection

# --- 1. 설정 및 데이터 로드 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
SHEET_NAME = 'JS_voca' 
WRONG_SHEET_NAME = 'Wjsvoca'
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

# 구글 시트 연결 객체
conn = st.connection("gsheets", type=GSheetsConnection)

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
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=60)
def get_data(sheet_name):
    # gsheets 커넥션을 사용하여 데이터 읽기
    df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=sheet_name)
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    df = df.dropna(subset=['Word'])
    return df

# --- 3. UI 구성 및 관리자 체크 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")

# 사이드바 관리자 로그인 및 메뉴 선택
st.sidebar.header("🔑 Admin Access")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
DEV_PASSWORD = "your_password" # <--- 비밀번호 수정

is_admin = (admin_pw == DEV_PASSWORD)

# 메뉴 선택 (일반 또는 오답)
menu = st.sidebar.radio("시험지 모드", ["일반 단어장", "오답 단어장 (Wjsvoca)"])

if is_admin:
    st.title("🛠️ 오답 노트 자동 관리 (Wjsvoca)")
    
    try:
        main_df = get_data(SHEET_NAME)
        main_df['No'] = range(1, len(main_df) + 1)
        
        st.subheader("➕ 오답 즉시 기록")
        manual_input = st.text_input("틀린 번호 입력 (예: 1, 5, 10)", help="번호를 입력하고 기록 버튼을 누르면 구글 시트에 즉시 반영됩니다.")
        
        if st.button("🚀 구글 시트에 오답 기록하기"):
            if manual_input:
                try:
                    nums = [int(n.strip()) for n in manual_input.split(',')]
                    # 기록할 데이터 추출 (No, Word, Meaning 형식)
                    to_add = main_df.iloc[[n-1 for n in nums if 0 < n <= len(main_df)]].copy()
                    
                    # 기존 오답 데이터 읽기
                    try:
                        existing_wrong = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=WRONG_SHEET_NAME)
                    except:
                        existing_wrong = pd.DataFrame(columns=['Word', 'Meaning'])
                    
                    # 데이터 병합 및 중복 제거
                    updated_df = pd.concat([existing_wrong, to_add[['Word', 'Meaning']]], ignore_index=True)
                    updated_df = updated_df.drop_duplicates(subset=['Word'], keep='first')
                    
                    # 시트 업데이트 (A열엔 번호 부여)
                    updated_df.insert(0, 'No', range(1, len(updated_df) + 1))
                    conn.update(spreadsheet=SPREADSHEET_URL, worksheet=WRONG_SHEET_NAME, data=updated_df)
                    
                    st.success(f"{len(nums)}개의 단어가 Wjsvoca 시트에 저장되었습니다!")
                    st.cache_data.clear() # 데이터 갱신을 위해 캐시 삭제
                except Exception as e:
                    st.error(f"기록 실패: {e}")
            else:
                st.warning("번호를 입력해주세요.")
                
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
    st.markdown("---")

# --- 메인 시험지 생성 화면 ---
st.title(f"📝 {menu} 시험지 생성기")

try:
    # 선택된 메뉴에 따라 데이터 로드
    target_sheet = SHEET_NAME if menu == "일반 단어장" else WRONG_SHEET_NAME
    df = get_data(target_sheet)
    total_count = len(df)
    
    if total_count == 0:
        st.warning("단어장이 비어 있습니다.")
    else:
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
                
                # 문제지 생성
                pdf.add_page()
                pdf.set_font('Nanum', '', 12)
                col_width = 90  
                for i, item in enumerate(quiz_items, 1):
                    word, meaning, origin_no = item
                    question = word if mode == "영단어 보고 뜻 쓰기" else meaning
                    if pdf.get_y() > 250: pdf.add_page(); pdf.set_font('Nanum', '', 12)
                    curr_x, curr_y = pdf.get_x(), pdf.get_y()
                    pdf.cell(col_width, 7, f"({origin_no}) {question}", ln=0)
                    pdf.set_xy(curr_x, curr_y + 7)
                    pdf.set_font('Nanum', '', 10)
                    pdf.cell(col_width, 7, "Ans: ____________________", ln=0)
                    pdf.set_font('Nanum', '', 12)
                    if i % 2 == 0: pdf.set_xy(pdf.l_margin, curr_y + 18)
                    else: pdf.set_xy(curr_x + col_width + 10, curr_y)

                # 정답지 생성
                pdf.add_page()
                pdf.set_font('Nanum', '', 14); pdf.cell(0, 10, "정답지 (Answer Key)", ln=True, align='C'); pdf.ln(5); pdf.set_font('Nanum', '', 11)
                for i, item in enumerate(quiz_items, 1):
                    word, meaning, origin_no = item
                    answer = meaning if mode == "영단어 보고 뜻 쓰기" else word
                    if pdf.get_y() > 270: pdf.add_page(); pdf.set_font('Nanum', '', 11)
                    curr_x, curr_y = pdf.get_x(), pdf.get_y()
                    pdf.cell(col_width, 8, f"({origin_no}) {answer}", border=0)
                    if i % 2 == 0: pdf.set_xy(pdf.l_margin, curr_y + 8)
                    else: pdf.set_xy(curr_x + col_width + 10, curr_y)

                st.download_button(label="📥 PDF 다운로드", data=bytes(pdf.output()), file_name=f"voca_{menu}_{start_num}.pdf", mime="application/pdf")

except Exception as e:
    st.error(f"데이터 로드 에러: {e}")
