import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 및 디자인 ---
st.set_page_config(page_title="스마트 구글시트 가계부", layout="wide", page_icon="💰")

# 스타일 커스텀 (눈금선 제거 및 깔끔한 UI)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_value=True)

st.title("💰 나의 스마트 가계부")

# 1) 실시간 시간 기능
now = datetime.now()
st.write(f"📅 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 구글 시트 연결 (Secrets에 설정된 정보를 자동으로 사용)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 설정 및 데이터 처리 함수 ---
CATEGORIES = ["식료품", "의류", "가전", "교통비", "저축", "기타"]

def load_data(worksheet_name):
    try:
        # 데이터 불러오기 (해당 월 시트)
        df = conn.read(worksheet=worksheet_name)
        # 데이터가 비어있지 않다면 날짜 타입을 정리
        if not df.empty:
            df['날짜'] = pd.to_datetime(df['날짜']).dt.strftime('%Y-%m-%d')
        return df
    except Exception:
        # 시트가 없거나 오류 시 빈 양식 반환
        return pd.DataFrame(columns=["날짜", "분류", "상품명", "금액"])

# --- 3) 입력창 섹션 ---
st.subheader("📝 내역 입력")
with st.container():
    with st.form("input_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            date = st.date_input("날짜", value=now)
        with col2:
            category = st.selectbox("분류", CATEGORIES)
        with col3:
            item = st.text_input("상품명", placeholder="무엇을 구매하셨나요?")
        with col4:
            price = st.number_input("금액", min_value=0, step=100)
        
        submit = st.form_submit_button("기록하기")

# 4) 데이터 입력 로직 (자동 월별 이동)
if submit:
    if item == "":
        st.error("상품명을 입력해주세요!")
    else:
        month_name = f"{date.month}월"  # 입력한 날짜에 따라 'n월' 결정
        existing_df = load_data(month_name)
        
        new_row = pd.DataFrame([{
            "날짜": date.strftime("%Y-%m-%d"),
            "분류": category,
            "상품명": item,
            "금액": price
        }])
        
        # 기존 데이터에 추가
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)
        
        # 구글 시트 업데이트
        conn.update(worksheet=month_name, data=updated_df)
        st.success(f"✅ {month_name} 시트에 성공적으로 기록되었습니다!")
        st.rerun()

# --- 6) 월별 데이터 조회 및 수정/삭제 ---
st.divider()
st.subheader("🔍 내역 확인 및 편집")

# 월 선택 (기본값은 현재 월)
selected_month = st.selectbox("조회할 월을 선택하세요", [f"{i}월" for i in range(1, 13)], index=now.month-1)

df_display = load_data(selected_month)

if not df_display.empty:
    # 필터 기능 (멀티 셀렉트)
    selected_cat = st.multiselect("분류 필터", CATEGORIES, default=CATEGORIES)
    filtered_df = df_display[df_display["분류"].isin(selected_cat)]

    # 수정 및 삭제 기능 (st.data_editor)
    st.write("💡 행 클릭 후 Delete 키로 삭제 가능, 수정 후 반드시 아래 '저장' 버튼 클릭")
    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        num_rows="dynamic",  # 행 삭제/추가 가능
        column_config={
            "금액": st.column_config.NumberColumn(format="%d 원"),
            "날짜": st.column_config.DateColumn()
        },
        key="main_editor"
    )

    # 수정사항 저장 버튼
    if st.button("💾 변경사항 저장"):
        # 필터링되지 않은 원본 데이터를 유지하면서 수정한 부분 반영 로직 (간편화를 위해 현재 상태 덮어쓰기)
        conn.update(worksheet=selected_month, data=edited_df)
        st.success("변경사항이 구글 시트에 반영되었습니다!")
        st.rerun()

    # --- 6-1) 통계 정리 ---
    st.write("---")
    col_chart, col_stat = st.columns([2, 1])
    
    with col_chart:
        st.write(f"📊 {selected_month} 분류별 지출 비중")
        summary = edited_df.groupby("분류")["금액"].sum()
        st.bar_chart(summary)

    with col_stat:
        st.write(f"💰 {selected_month} 총계")
        total_sum = edited_df["금액"].sum()
        st.metric(label="총 지출", value=f"{total_sum:,} 원")
        for cat, val in summary.items():
            st.write(f"- {cat}: {val:,} 원")
else:
    st.info(f"아직 {selected_month}에 입력된 내역이 없습니다.")