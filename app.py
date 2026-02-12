import streamlit as st
import pandas as pd
import random
from fpdf import FPDF
import io
from urllib.parse import quote
import streamlit_authenticator as stauth
import bcrypt

# --- 1. 설정 및 데이터 로드 ---
SHEET_ID = '1VdVqTA33lWopMV-ExA3XUy36YAwS3fJleZvTNRQNeDM'
SHEET_NAME = 'JS_voca' 

encoded_sheet_name = quote(SHEET_NAME)
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}&range=A1:B2001'

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
@st.cache_data(show_spinner="단어장을 불러오는 중입니다...", ttl=600)
def get_data():
    df = pd.read_csv(URL)
    df = df.iloc[:, [0, 1]] 
    df.columns = ['Word', 'Meaning']
    df = df.dropna(subset=['Word'])
    return df

# --- 3. 로그인 설정 ---
names = ["사용자1"]
usernames = ["user1"]
passwords = ["1234"]

# bcrypt를 이용한 안전한 해싱
hashed_passwords = [bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') for password in passwords]

credentials = {
    "usernames": {
        usernames[0]: {
            "name": names[0],
            "password": hashed_passwords[0]
        }
    }
}

# 인증 객체 생성
authenticator = stauth.Authenticate(
    credentials,
    "voca_cookie",
    "voca_key",
    30
)

# --- 4. 로그인 및 UI 구성 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")

# [수정된 부분] 최신 버전에서는 login 호출 시 반환값을 처리하는 방식이 달라졌습니다.
# 안전하게 객체 내부 상태를 사용하는 방식으로 변경합니다.
authenticator.login()

if st.session_state["authentication_status"]:
    # 로그인 성공 시
    authenticator.logout('Logout', 'sidebar')
    st.title(f"📝 {st.session_state['name']}님의 단어 시험지 생성기")
    st.info("구글 스프레드시트의 2,000단어 데이터를 연동합니다.")

    try:
        df = get_data()
        total_count = len(df)
        
        st.sidebar.header("⚙️ 시험지 설정")
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
        st.error(f"데이터를 불러오지 못했습니다. 에러: {e}")

elif st.session_state["authentication_status"] is False:
    st.error('사용자 이름 또는 비밀번호가 틀렸습니다.')
elif st.session_state["authentication_status"] is None:
    st.warning('로그인이 필요합니다.')
