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

# 구글 시트 연결 초기화
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 설정 및 데이터 처리 함수 ---
CATEGORIES = ["식료품", "의류", "가전", "교통비", "저축", "기타"]

def load_data(worksheet_name):
    """구글 시트에서 데이터를 불러오고 형식을 정리합니다."""
    try:
        # ttl=0 설정을 통해 실시간 데이터 로드
        df = conn.read(worksheet=worksheet_name, ttl=0)
        
        if df is not None and not df.empty:
            # [핵심 수정] 날짜를 문자열이 아닌 '날짜 객체'로 변환해야 st.data_editor의 DateColumn과 호환됩니다.
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
            # 금액 컬럼 숫자화
            df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception:
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
        target_month = f"{date_input.month}월"
        existing_df = load_data(target_month)
        
        # 새로운 데이터 행 (날짜를 문자열로 저장하기 위해 처리)
        new_row = pd.DataFrame([{
            "날짜": date_input.strftime("%Y-%m-%d"),
            "분류": category_input,
            "상품명": item_input,
            "금액": price_input
        }])
        
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)
        
        try:
            conn.update(worksheet=target_month, data=updated_df)
            st.success(f"✅ {target_month} 시트에 저장되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ '{target_month}' 시트를 찾을 수 없습니다. 구글 시트에 탭을 만들어주세요.")

# --- 4. 데이터 조회 및 편집 섹션 ---
st.divider()
st.subheader("🔍 내역 확인 및 편집")

selected_month = st.selectbox("조회할 월을 선택하세요", [f"{i}월" for i in range(1, 13)], index=now.month-1)

if st.button("🔄 데이터 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()

df_display = load_data(selected_month)

if df_display is not None and not df_display.empty:
    selected_cat = st.multiselect("분류 필터", CATEGORIES, default=CATEGORIES)
    # 필터링 적용
    filtered_df = df_display[df_display["분류"].isin(selected_cat)]

    st.info("💡 수정: 칸 더블클릭 / 삭제: 행 선택 후 Delete 키 / 완료 후 저장 버튼 클릭")
    
    # [수정된 부분] 데이터 에디터
    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "금액": st.column_config.NumberColumn(format="%d 원"),
            "날짜": st.column_config.DateColumn(format="YYYY-MM-DD") # 형식을 명시
        },
        key="main_editor"
    )

    if st.button("💾 변경사항 저장"):
        try:
            # 저장할 때는 날짜를 다시 문자열로 바꿔서 저장 (안정성)
            save_df = edited_df.copy()
            save_df['날짜'] = save_df['날짜'].astype(str)
            conn.update(worksheet=selected_month, data=save_df)
            st.success("✅ 구글 시트에 변경사항이 저장되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")

    # --- 5. 통계 요약 ---
    st.write("---")
    col_chart, col_stat = st.columns([2, 1])
    
    if not edited_df.empty:
        with col_chart:
            st.write(f"📊 {selected_month} 분류별 지출 비중")
            summary = edited_df.groupby("분류")["금액"].sum()
            st.bar_chart(summary)

        with col_stat:
            st.write(f"💰 {selected_month} 요약")
            total_sum = edited_df["금액"].sum()
            st.metric(label="총 지출", value=f"{total_sum:,} 원")
            for cat, val in summary.items():
                st.write(f"- {cat}: {val:,} 원")
else:
    st.warning(f"아직 {selected_month}에 입력된 데이터가 없습니다.")