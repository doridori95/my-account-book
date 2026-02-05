import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 설정 및 데이터 로드 ---
FILE_NAME = "my_account_book.xlsx"
CATEGORIES = ["식료품", "의류", "가전", "교통비", "저축", "기타"]

def load_data():
    if os.path.exists(FILE_NAME):
        return pd.read_excel(FILE_NAME, sheet_name=None)
    return {}

def save_data(all_sheets):
    with pd.ExcelWriter(FILE_NAME, engine='openpyxl') as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

# --- UI 구성 ---
st.set_page_config(page_title="나의 스마트 가계부", layout="wide")
st.title("💰 나의 스마트 가계부")

# 1) 실시간 시간 기능
now = datetime.now()
st.write(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 데이터 불러오기
all_data = load_data()

# --- 3) 입력창 섹션 ---
st.subheader("📝 새로운 지출 입력")
with st.form("input_form", clear_on_submit=True):
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

# --- 4) 데이터 처리 (자동 월별 분류) ---
if submit:
    month_name = f"{date.year}년_{date.month}월"
    new_data = pd.DataFrame([[date, category, item, price]], 
                            columns=["날짜", "분류", "상품명", "금액"])
    
    if month_name in all_data:
        all_data[month_name] = pd.concat([all_data[month_name], new_data], ignore_index=True)
    else:
        all_data[month_name] = new_data
    
    save_data(all_data)
    st.success(f"{month_name} 시트에 저장되었습니다!")

# --- 5) 월별 데이터 조회 및 6) 필터/통계 ---
st.divider()
st.subheader("📊 월별 지출 내역")

if all_data:
    selected_month = st.selectbox("조회할 월 선택", list(all_data.keys())[::-1])
    df_display = all_data[selected_month]
    
    # 필터 기능
    selected_cat = st.multiselect("분류 필터", CATEGORIES, default=CATEGORIES)
    filtered_df = df_display[df_display["분류"].isin(selected_cat)]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if not filtered_df.empty:
            display_df = filtered_df.copy()
    
            # 1. 날짜 컬럼 처리
            if "날짜" in display_df.columns:
                # 먼저 날짜 형식으로 강제 변환 (문자열이나 다른 타입일 경우 대비)
                display_df["날짜"] = pd.to_datetime(display_df["날짜"], errors='coerce')
                
                # 날짜 변환에 성공한 데이터만 문자열(YYYY-MM-DD)로 변환
                # 변환 실패(NaT)인 경우는 'Invalid Date' 등으로 표시되거나 유지됨
                display_df["날짜"] = display_df["날짜"].dt.strftime('%Y-%m-%d').fillna("데이터 오류")
            
            # 2. 금액 컬럼 처리 (이전과 동일)
            if "금액" in display_df.columns:
                display_df["금액"] = pd.to_numeric(display_df["금액"], errors='coerce').fillna(0)

            # 3. 화면에 출력
            st.dataframe(display_df, use_container_width=True)
                
    with col2:
        # 6) 분류별 합계 요약
        st.write(f"### {selected_month} 요약")
        summary = filtered_df.groupby("분류")["금액"].sum()
        st.write(summary)
        st.info(f"**총 지출: {filtered_df['금액'].sum():,}원**")

    # 7) 추가 유용한 기능: 간단한 차트
    if not filtered_df.empty:
        st.bar_chart(summary)
else:
    st.info("데이터가 없습니다. 첫 지출을 입력해보세요!")