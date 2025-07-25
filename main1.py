import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="과목 유형 검사", page_icon="📚", layout="centered")

@st.cache_data
def load_data(file_path):
    """CSV 파일을 로드하고 데이터를 정리하는 함수"""
    try:
        df = pd.read_csv(file_path, dtype={'번호': str})
        df.columns = df.columns.str.strip()
        
        # 데이터 클리닝
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

# 버전 선택에 따른 데이터 로드
st.title("📚 나의 과목 선호 유형 검사")
st.write("---")
version = st.radio(
    "**원하는 검사 버전을 선택해주세요.**",
    ('**라이트** (81문항)', '**기본** (115문항)'),
    index=None,
    horizontal=True
)

if version:
    file_to_load = 'lite_data.csv' if '라이트' in version else 'default_data.csv'
    df = load_data(file_to_load)
else:
    st.info("👆 위에서 검사 버전을 선택해주세요.")
    st.stop()

if df is None: st.stop()
required_columns = ['번호', '수정내용', '척도', '카테고리', '관련교과군']
if not all(col in df.columns for col in required_columns):
    st.error("CSV 파일의 컬럼명을 확인해주세요.")
    st.stop()

SUBJECT_ORDER = ['국어', '수학', '영어', '독일어', '중국어', '일본어', '물리', '화학', '생명과학', '지구과학', '일반사회', '역사', '윤리', '지리']
SECTION_ORDER = ['기초교과군', '제2외국어군', '과학군', '사회군']
section_list = [s for s in SECTION_ORDER if s in df['카테고리'].unique()]
if not section_list:
    st.error("CSV 파일의 '카테고리' 열 내용을 확인해주세요.")
    st.stop()

if 'version' not in st.session_state or st.session_state.version != version:
    st.session_state.version = version
    st.session_state.current_section = 0
    st.session_state.responses = {}

def display_survey():
    section_index = st.session_state.current_section
    current_section_name = section_list[section_index]
    questions_df = df[df['카테고리'] == current_section_name].astype({'번호': str})
    
    st.progress((section_index + 1) / len(section_list), text=f"{section_index + 1}/{len(section_list)} 단계 진행 중")
    
    # --- 2. 응답 옵션 설명 문구 추가 ---
    # 각 숫자에 해당하는 설명 문구를 딕셔너리로 정의
    options_map = {
        1: "1(전혀 아니다)",
        2: "2(아니다)",
        3: "3(보통이다)",
        4: "4(그렇다)",
        5: "5(매우 그렇다)"
    }
    
    with st.form(key=f"form_{version}_{section_index}"):
        st.header(f"섹션 {section_index + 1}: {current_section_name}")
        for _, row in questions_df.iterrows():
            st.markdown(f"**{row['번호']}. {row['수정내용']}**")
            # format_func를 이용해 숫자 대신 설명 문구를 버튼에 표시
            st.radio("선택", 
                     options=[1, 2, 3, 4, 5], 
                     key=f"q_{row['번호']}", 
                     format_func=lambda x: options_map[x],
                     horizontal=True, 
                     label_visibility="collapsed")
        
        button_label = "결과 분석하기" if (section_index == len(section_list) - 1) else "다음 섹션으로"
        if st.form_submit_button(button_label):
            for _, row in questions_df.iterrows():
                st.session_state.responses[str(row['번호'])] = st.session_state[f"q_{row['번호']}"]
            st.session_state.current_section += 1
            st.rerun()

def display_results():
    import plotly.express as px
    with st.spinner('결과를 분석하는 중입니다...'):
        question_counts = {subject: 0 for subject in SUBJECT_ORDER}
        for _, row in df.iterrows():
            for i in range(1, 4):
                subject_col = f'관련교과군{i}' if i > 1 else '관련교과군'
                if subject_col in row and pd.notna(row[subject_col]):
                    subject = row[subject_col]
                    if subject in question_counts:
                        question_counts[subject] += 1
        
        total_scores = {subject: 0 for subject in SUBJECT_ORDER}
        df_results = df.astype({'번호': str})
        for q_id, answer in st.session_state.responses.items():
            q_data_rows = df_results.loc[df_results['번호'] == q_id]
            if q_data_rows.empty: continue
            q_data = q_data_rows.iloc[0]
            for i in range(1, 4):
                subject_col = f'관련교과군{i}' if i > 1 else '관련교과군'
                scale_col = f'척도{i}' if i > 1 else '척도'
                if subject_col in q_data and pd.notna(q_data[subject_col]):
                    subject = q_data[subject_col]
                    scale = q_data[scale_col]
                    score = (6 - answer) if scale == '역' else answer
                    if subject in total_scores:
                        total_scores[subject] += score

        normalized_scores = {}
        for subject, total_score in total_scores.items():
            if question_counts.get(subject, 0) > 0:
                normalized_scores[subject] = total_score / question_counts[subject]
        
        sorted_scores = sorted(normalized_scores.items(), key=lambda item: item[1], reverse=True)

    st.balloons()
    st.header("📈 최종 분석 결과")

    if sorted_scores:
        st.subheader("💡 나의 상위 선호 과목 Top 8 (평균 점수 기준)")
        top_8_subjects = sorted_scores[:8]
        top_subjects_text = ", ".join([f"**{i+1}위**: {subject} ({score:.2f}점)" for i, (subject, score) in enumerate(top_8_subjects)])
        st.success(top_subjects_text)
        
        st.subheader("과목별 선호도 점수 (평균 점수)")
        scores_series = pd.Series(normalized_scores).reindex(SUBJECT_ORDER).fillna(0)
        chart_df = scores_series.reset_index()
        chart_df.columns = ['과목', '평균 점수']
        fig = px.bar(chart_df, x='과목', y='평균 점수', text_auto='.2f')
        fig.update_xaxes(tickangle=0)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("분석 결과가 없습니다.")

    st.write("---")
    # --- 1. 결과 페이지 안내 문구 추가 ---
    st.info("""
    이 검사는 개인의 흥미 유형을 알아보기 위한 간단한 검사이며, 결과는 참고용으로만 활용하시기 바랍니다. 
    검사자의 태도나 상황에 따라 정확도가 달라질 수 있으므로, 실제 교육과정 선택 시에는 다양한 요소를 함께 고려하시길 권장합니다.
    """)

    if st.button("검사 다시하기"):
        st.session_state.clear()
        st.rerun()

# --- 메인 로직 실행 ---
if 'current_section' in st.session_state and st.session_state.current_section < len(section_list):
    display_survey()
elif 'responses' in st.session_state and st.session_state.responses:
    display_results()
