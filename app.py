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

# --- 3. UI 구성 및 관리자 체크 ---
st.set_page_config(page_title="Voca PDF Generator", page_icon="📝")

# 사이드바 관리자 로그인
st.sidebar.header("🔑 Admin Access")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
DEV_PASSWORD = "your_password" # <--- 사용하실 비밀번호로 수정하세요!

is_admin = (admin_pw == DEV_PASSWORD)

if is_admin:
    st.title("🛠️ 오답 노트 관리 (Wjsvoca)")
    st.info("선택한 단어들을 'Wjsvoca' 시트 양식(번호, 단어, 뜻)으로 변환합니다.")
    
    try:
        df = get_data()
        df['No'] = range(1, len(df) + 1)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("1️⃣ 오답 단어 선택")
            manual_input = st.text_input("틀린 번호 입력 (예: 1, 5, 10, 22)", "")
            
            search = st.text_input("또는 단어 검색", "")
            filtered = df[df['Word'].str.contains(search, case=False)] if search else df.head(50)
            
            selected_indices = st.multiselect(
                "리스트에서 직접 선택",
                options=filtered.index,
                format_func=lambda x: f"[{df.loc[x, 'No']}] {df.loc[x, 'Word']} : {df.loc[x, 'Meaning']}"
            )
        
        with col2:
            st.subheader("2️⃣ Wjsvoca 붙여넣기용 결과")
            
            # 번호 파싱
            manual_idx = []
            if manual_input:
                try:
                    nums = [int(n.strip()) for n in manual_input.split(',')]
                    manual_idx = [n-1 for n in nums if 0 < n <= len(df)]
                except:
                    st.error("번호 형식이 올바르지 않습니다.")
            
            final_idx = list(set(selected_indices) | set(manual_idx))
            final_idx.sort()
            
            if final_idx:
                # Wjsvoca 시트 양식에 맞춰 No, Word, Meaning 순서로 정렬
                wrong_df = df.loc[final_idx, ['No', 'Word', 'Meaning']]
                st.dataframe(wrong_df, use_container_width=True, hide_index=True)
                
                # 구글 시트에 붙여넣기 좋은 CSV 형식 (탭 구분자 사용 시 엑셀/시트에 더 잘 붙습니다)
                output = io.StringIO()
                wrong_df.to_csv(output, index=False, header=False, sep='\t')
                paste_text = output.getvalue()
                
                st.text_area("내용 복사 (Ctrl+C 후 시트의 A열 셀에 Ctrl+V)", paste_text, height=250)
                st.caption("※ 번호, 단어, 뜻 순서로 정렬되어 있습니다.")
            else:
                st.write("선택된 오답이 없습니다.")
                
    except Exception as e:
        st.error(f"데이터 오류: {e}")

else:
    # --- 일반 시험지 생성기 화면 ---
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
                
                # [문제지/정답지 생성 로직 생략 - 기존과 동일]
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

                st.download_button(label="📥 PDF 다운로드", data=bytes(pdf.output()), file_name=f"voca_test_{start_num}_{end_num}.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
