import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 설정 ---
# 구글 시트 URL (본인의 시트 주소로 교체하세요)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1B8Vn0qMx8j_O1-0qVFZznHK4BaTnRFMwIfc2YCcKZVE/edit?usp=sharing"

st.set_page_config(page_title="구글시트 스마트 가계부", layout="wide")
st.title("💰 구글시트 연동 가계부")

# 구글 시트 연결 초기화
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 함수: 데이터 불러오기 ---
def load_data(month_name):
    try:
        # 해당 월의 워크시트를 읽어옵니다.
        return conn.read(spreadsheet=SHEET_URL, worksheet=month_name)
    except:
        # 시트가 없으면 빈 데이터프레임 반환
        return pd.DataFrame(columns=["날짜", "분류", "상품명", "금액"])

# --- 입력창 섹션 ---
CATEGORIES = ["식료품", "의류", "가전", "교통비", "저축", "기타"]
now = datetime.now()

with st.form("input_form", clear_on_submit=True):
    st.subheader("📝 내역 입력")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        date = st.date_input("날짜", value=now)
    with col2:
        category = st.selectbox("분류", CATEGORIES)
    with col3:
        item = st.text_input("상품명")
    with col4:
        price = st.number_input("금액", min_value=0, step=100)
    
    submit = st.form_submit_button("기록하기")

if submit:
    month_name = f"{date.month}월"
    existing_data = load_data(month_name)
    
    new_data = pd.DataFrame([{"날짜": date.strftime("%Y-%m-%d"), "분류": category, "상품명": item, "금액": price}])
    updated_df = pd.concat([existing_data, new_data], ignore_index=True)
    
    # 구글 시트에 업데이트
    conn.update(spreadsheet=SHEET_URL, worksheet=month_name, data=updated_df)
    st.success(f"{month_name} 시트에 기록되었습니다!")
    st.rerun()

# --- 데이터 수정 및 삭제 섹션 ---
st.divider()
current_month = f"{now.month}월"
selected_month = st.selectbox("조회 및 수정할 월 선택", [f"{i}월" for i in range(1, 13)], index=now.month-1)

df = load_data(selected_month)

if not df.empty:
    st.subheader(f"📊 {selected_month} 내역 관리")
    st.write("💡 행 왼쪽을 선택 후 Delete 키를 누르거나, 내용을 직접 수정 후 아래 저장 버튼을 누르세요.")
    
    # [핵심] 수정 및 삭제가 가능한 데이터 에디터
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic", # 행 추가/삭제 가능하게 설정
        key="editor"
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 변경사항 저장"):
            # 수정한 데이터를 구글 시트에 다시 덮어씁니다.
            conn.update(spreadsheet=SHEET_URL, worksheet=selected_month, data=edited_df)
            st.success("구글 시트에 성공적으로 저장되었습니다!")
            st.rerun()

    # --- 간단 통계 ---
    if not edited_df.empty:
        st.write("---")
        summary = edited_df.groupby("분류")["금액"].sum()
        st.bar_chart(summary)
        st.info(f"**{selected_month} 총 지출: {edited_df['금액'].sum():,}원**")
else:
    st.info(f"{selected_month}에 등록된 데이터가 없습니다.")