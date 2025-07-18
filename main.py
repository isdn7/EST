import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="과목 유형 검사", page_icon="📚", layout="centered")

@st.cache_data
def load_data(file_path):
    """CSV 파일을 로드하고 데이터를 정리하는 함수"""
    try:
        df = pd.read_csv(file_path, dtype={'번호': str})
        df.columns = df.columns.str.strip()
        
        # 데이터 클리닝 (여러 과목 열에 대해 반복)
        for col in ['관련교과군', '관련교과군2', '관련교과군3']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

        # 과목명 축약어 변환
        name_map = {'생명': '생명과학', '지구': '지구과학', '일사': '일반사회'}
        for col in ['관련교과군', '관련교과군2', '관련교과군3']:
            if col in df.columns:
                df[col] = df[col].replace(name_map)
                
        return df
    except Exception as e:
        st.error(f"파일 로드 중 오류: {e}")
        return None

# --- 1. 버전 선택 UI ---
st.title("📚 나의 과목 선호 유형 검사")
st.write("---")

version = st.radio(
    "**원하는 검사 버전을 선택해주세요.**",
    ('**라이트** (81문항)', '**기본** (115문항)'),
    index=None,
    horizontal=True
)

# 버전에 따라 다른 데이터 파일 로드
if version:
    file_to_load = 'lite_data.csv' if '라이트' in version else 'default_data.csv'
    df = load_data(file_to_load)
else:
    st.info("👆 위에서 검사 버전을 선택해주세요.")
    st.stop()

# 데이터 로드 실패 시 중지
if df is None:
    st.stop()

# 필수 컬럼 확인
required_columns = ['번호', '수정내용', '척도', '카테고리', '관련교과군']
if not all(col in df.columns for col in required_columns):
    st.error("CSV 파일의 컬럼명을 확인해주세요.")
    st.stop()

# --- 이하 코드는 이전과 거의 동일, 일부 로직만 수정 ---

# 과목 및 섹션 순서 정의
SUBJECT_ORDER = ['국어', '수학', '영어', '독일어', '중국어', '일본어', '물리', '화학', '생명과학', '지구과학', '일반사회', '역사', '윤리', '지리']
SECTION_ORDER = ['기초교과군', '제2외국어군', '과학군', '사회군']
section_list = [s for s in SECTION_ORDER if s in df['카테고리'].unique()]
if not section_list:
    st.error("CSV 파일의 '카테고리' 열 내용을 확인해주세요.")
    st.stop()

# 세션 상태 초기화
if 'version' not in st.session_state or st.session_state.version != version:
    st.session_state.version = version
    st.session_state.current_section = 0
    st.session_state.responses = {}

def display_survey():
    section_index = st.session_state.current_section
    current_section_name = section_list[section_index]
    questions_df = df[df['카테고리'] == current_section_name].astype({'번호': str})
    
    st.progress((section_index + 1) / len(section_list), text=f"{section_index + 1}/{len(section_list)} 단계 진행 중")
    
    with st.form(key=f"form_{version}_{section_index}"):
        st.header(f"섹션 {section_index + 1}: {current_section_name}")
        for _, row in questions_df.iterrows():
            st.markdown(f"**{row['번호']}. {row['수정내용']}**")
            st.radio("선택", [1, 2, 3, 4, 5], key=f"q_{row['번호']}", horizontal=True, label_visibility="collapsed")
        
        button_label = "결과 분석하기" if (section_index == len(section_list) - 1) else "다음 섹션으로"
        if st.form_submit_button(button_label):
            for _, row in questions_df.iterrows():
                st.session_state.responses[str(row['번호'])] = st.session_state[f"q_{row['번호']}"]
            st.session_state.current_section += 1
            st.rerun()

def display_results():
    import plotly.express as px
    with st.spinner('결과를 분석하는 중입니다...'):
        all_subjects = pd.concat([df[col] for col in ['관련교과군', '관련교과군2', '관련교과군3'] if col in df.columns]).dropna().unique()
        scores = {subject: 0 for subject in all_subjects}
        
        df_results = df.astype({'번호': str})

        for q_id, answer in st.session_state.responses.items():
            q_data_rows = df_results.loc[df_results['번호'] == q_id]
            if q_data_rows.empty: continue
            q_data = q_data_rows.iloc[0]

            # --- 2. 복합 문항 처리 로직 ---
            for i in range(1, 4):
                subject_col = f'관련교과군{i}' if i > 1 else '관련교과군'
                scale_col = f'척도{i}' if i > 1 else '척도'

                if subject_col in q_data and pd.notna(q_data[subject_col]):
                    subject = q_data[subject_col]
                    scale = q_data[scale_col]
                    score = (6 - answer) if scale == '역' else answer
                    if subject in scores:
                        scores[subject] += score

        final_scores = {s: v for s, v in scores.items() if v > 0}
        sorted_scores = sorted(final_scores.items(), key=lambda item: item[1], reverse=True)

    st.balloons()
    st.header("📈 최종 분석 결과")

    if sorted_scores:
        st.subheader("💡 나의 상위 선호 과목 Top 8")
        top_8_subjects = sorted_scores[:8]
        top_subjects_text = ", ".join([f"**{i+1}위**: {subject}" for i, (subject, score) in enumerate(top_8_subjects)])
        st.success(top_subjects_text)
        st.subheader("과목별 선호도 점수")
        
        scores_series = pd.Series(final_scores).reindex(SUBJECT_ORDER).fillna(0)
        chart_df = scores_series.reset_index()
        chart_df.columns = ['과목', '점수']

        fig = px.bar(chart_df, x='과목', y='점수', text_auto=True)
        fig.update_xaxes(tickangle=0)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("분석 결과가 없습니다.")

    if st.button("검사 다시하기"):
        st.session_state.clear()
        st.rerun()

# --- 메인 로직 실행 ---
if 'current_section' in st.session_state and st.session_state.current_section < len(section_list):
    display_survey()
elif 'responses' in st.session_state and st.session_state.responses:
    display_results()
