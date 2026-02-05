import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="스마트 구글시트 가계부", layout="wide", page_icon="💰")

# 디자인 커스텀 (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #FF4B4B; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 나의 스마트 가계부")

# 실시간 시간 표시
now = datetime.now()
st.write(f"📅 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 구글 시트 연결 초기화 (Secrets 설정 자동 로드)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 설정 및 데이터 처리 함수 ---
CATEGORIES = ["식료품", "의류", "가전", "교통비", "저축", "기타"]

def load_data(worksheet_name):
    """구글 시트에서 데이터를 불러오고 형식을 정리합니다."""
    try:
        # ttl=0 설정을 통해 캐시를 방지하고 실시간으로 데이터를 가져옵니다.
        df = conn.read(worksheet=worksheet_name, ttl=0)
        
        if df is not None and not df.empty:
            # 날짜 컬럼을 판다스 날짜형으로 변환 후 문자열로 통일 (에러 방지)
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
            df['날짜'] = df['날짜'].dt.strftime('%Y-%m-%d')
            # 금액 컬럼 숫자화
            df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0)
        return df
    except Exception:
        # 시트가 없거나 오류 발생 시 빈 양식 반환
        return pd.DataFrame(columns=["날짜", "분류", "상품명", "금액"])

# --- 3. 입력창 섹션 ---
st.subheader("📝 새로운 지출 기록")
with st.container():
    with st.form("input_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            date_input = st.date_input("날짜", value=now)
        with col2:
            category_input = st.selectbox("분류", CATEGORIES)
        with col3:
            item_input = st.text_input("상품명", placeholder="어디에 쓰셨나요?")
        with col4:
            price_input = st.number_input("금액", min_value=0, step=100)
        
        submit = st.form_submit_button("기록하기")

# 데이터 기록 로직
if submit:
    if not item_input:
        st.error("상품명을 입력해주세요!")
    else:
        # 입력한 날짜의 '월'을 시트 이름으로 결정 (예: 2월)
        target_month = f"{date_input.month}월"
        
        existing_df = load_data(target_month)
        
        new_row = pd.DataFrame([{
            "날짜": date_input.strftime("%Y-%m-%d"),
            "분류": category_input,
            "상품명": item_input,
            "금액": price_input
        }])
        
        # 합치기
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)
        
        try:
            # 구글 시트에 실시간 업데이트
            conn.update(worksheet=target_month, data=updated_df)
            st.success(f"✅ {target_month} 시트에 저장되었습니다!")
            st.rerun() # 화면 새로고침하여 데이터 반영
        except Exception as e:
            st.error(f"⚠️ '{target_month}' 시트를 찾을 수 없습니다.")
            st.info(f"구글 시트 하단에 '{target_month}'라는 이름의 탭을 직접 만들어주세요.")

# --- 4. 데이터 조회 및 편집(삭제/수정) 섹션 ---
st.divider()
st.subheader("🔍 내역 확인 및 편집")

# 조회할 월 선택
selected_month = st.selectbox("조회할 월을 선택하세요", [f"{i}월" for i in range(1, 13)], index=now.month-1)

# 새로고침 버튼
if st.button("🔄 데이터 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()

df_display = load_data(selected_month)

if df_display is not None and not df_display.empty:
    # 필터링 기능
    selected_cat = st.multiselect("분류 필터", CATEGORIES, default=CATEGORIES)
    filtered_df = df_display[df_display["분류"].isin(selected_cat)]

    # 수정 및 삭제가 가능한 데이터 에디터
    st.info("💡 수정: 칸을 더블클릭 / 삭제: 행 선택 후 Delete 키 / 완료 후 반드시 저장 버튼 클릭")
    
    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        num_rows="dynamic", # 행 추가/삭제 활성화
        column_config={
            "금액": st.column_config.NumberColumn(format="%d 원"),
            "날짜": st.column_config.DateColumn()
        },
        key="main_editor"
    )

    # 변경사항 저장 버튼
    if st.button("💾 변경사항 저장"):
        try:
            # 수정한 데이터를 해당 월 시트에 덮어쓰기
            conn.update(worksheet=selected_month, data=edited_df)
            st.success("✅ 구글 시트에 변경사항이 저장되었습니다!")
            st.rerun()
        except Exception as e:
            st.error("저장 중 오류가 발생했습니다. 시트 권한을 확인해주세요.")

    # --- 5. 통계 요약 ---
    st.write("---")
    col_chart, col_stat = st.columns([2, 1])
    
    with col_chart:
        st.write(f"📊 {selected_month} 분류별 지출 비중")
        if not edited_df.empty:
            summary = edited_df.groupby("분류")["금액"].sum()
            st.bar_chart(summary)

    with col_stat:
        st.write(f"💰 {selected_month} 요약")
        total_sum = edited_df["금액"].sum()
        st.metric(label="총 지출", value=f"{total_sum:,} 원")
        
        # 상세 내역 텍스트 표시
        if not edited_df.empty:
            for cat, val in summary.items():
                st.write(f"- {cat}: {val:,} 원")
else:
    st.warning(f"아직 {selected_month}에 입력된 데이터가 없습니다.")