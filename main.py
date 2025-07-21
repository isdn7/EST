import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_marquee import streamlit_marquee # marquee 라이브러리 다시 사용

# 페이지 기본 설정
st.set_page_config(page_title="과목 유형 검사", page_icon="📚", layout="centered")

@st.cache_data
def load_data(file_path):
    """CSV 파일을 로드하고 데이터를 정리하는 함수"""
    try:
        df = pd.read_csv(file_path, dtype={'번호': str})
        df.columns = df.columns.str.strip()
        
        for col in ['관련교과군', '관련교과군2', '관련교과군3']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

        name_map = {'생명': '생명과학', '지구': '지구과학', '일사': '일반사회'}
        for col in ['관련교과군', '관련교과군2', '관련교과군3']:
            if col in df.columns:
                df[col] = df[col].replace(name_map)
                
        return df
    except Exception as e:
        st.error(f"데이터 파일 로드 중 오류: {e}")
        return None

# --- UI 시작 ---
st.title("📚 SETI 선택과목 유형검사")

# 버전 선택 UI
version = st.radio(
    "**원하는 검사 버전을 선택해주세요.**",
    ('**라이트** (81문항)', '**기본** (115문항)'),
    index=None,
    horizontal=True
)

# --- 1. 속도 조절된 전광판 기능 (marquee 사용) ---
if version:
    try:
        advice_df = pd.read_csv('advice_data.csv', header=None)
        advice_list = advice_df[0].dropna().tolist()
        marquee_content = " ★★★ ".join(advice_list)
        
        streamlit_marquee(
            content=marquee_content,
            velocity=-10,  # 속도 조절 (숫자가 작을수록 느려짐)
            loop=0,
            background="#222222",
            font_size="18px",
        )
    except Exception:
        pass

st.write("---")

if not version:
    st.info("👆 위에서 검사 버전을 선택해주세요.")
    st.stop()

# (이하 나머지 코드는 이전과 동일합니다)
file_to_load = 'lite_data.csv' if '라이트' in version else 'default_data.csv'
df = load_data(file_to_load)
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

total_questions = len(df)
answered_questions = len(st.session_state.responses)
st.progress(answered_questions / total_questions, text=f"진행률: {answered_questions} / {total_questions} 문항")

def display_survey():
    section_index = st.session_state.current_section
    current_section_name = section_list[section_index]
    questions_df = df[df['카테고리'] == current_section_name].astype({'번호': str})
    
    st.subheader(f"섹션 {section_index + 1}: {current_section_name}")
    options_map = {1: "1(전혀 아니다)", 2: "2(아니다)", 3: "3(보통이다)", 4: "4(그렇다)", 5: "5(매우 그렇다)"}
    
    with st.form(key=f"form_{version}_{section_index}"):
        for _, row in questions_df.iterrows():
            st.markdown(f"**{row['번호']}. {row['수정내용']}**")
            st.radio("선택", [1, 2, 3, 4, 5], key=f"q_{row['번호']}", 
                     format_func=lambda x: options_map[x], 
                     horizontal=True, 
                     label_visibility="collapsed",
                     index=None)
        
        button_label = "결과 분석하기" if (section_index == len(section_list) - 1) else "다음 섹션으로"
        if st.form_submit_button(button_label):
            all_answered = True
            for _, row in questions_df.iterrows():
                if st.session_state[f"q_{row['번호']}"] is None:
                    all_answered = False
                    break
            
            if not all_answered:
                st.warning("모든 문항에 답변해주세요!")
            else:
                for _, row in questions_df.iterrows():
                    st.session_state.responses[str(row['번호'])] = st.session_state[f"q_{row['번호']}"]
                st.session_state.current_section += 1
                st.rerun()

def display_results():
    all_answers = list(st.session_state.responses.values())
    if len(set(all_answers)) == 1:
        st.warning(f"모든 문항에 '{all_answers[0]}'번으로만 응답하셨습니다. 보다 정확한 결과를 위해 다양한 선택을 해보시길 권장합니다.")

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
        
        sorted_scores_dict = dict(sorted(normalized_scores.items(), key=lambda item: item[1], reverse=True))

    st.balloons()
    st.header("📈 최종 분석 결과")

    if sorted_scores_dict:
        st.subheader("💡 나의 상위 선호 과목 (교과군별)")
        subject_to_group_map = df.drop_duplicates(subset=['관련교과군']).set_index('관련교과군')['카테고리'].to_dict()
        for group_name in SECTION_ORDER:
            group_subjects = [s for s in SUBJECT_ORDER if subject_to_group_map.get(s) == group_name and s in sorted_scores_dict]
            group_subjects.sort(key=lambda s: sorted_scores_dict.get(s, 0), reverse=True)
            if group_subjects:
                st.markdown(f"**▌ {group_name}**")
                cols = st.columns(len(group_subjects))
                for i, subject in enumerate(group_subjects):
                    with cols[i]:
                        st.metric(label=subject, value=f"{sorted_scores_dict[subject]:.2f}점")
        
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
    st.info("이 검사는 개인의 흥미 유형을 알아보기 위한 간단한 검사이며, 결과는 참고용으로만 활용하시기 바랍니다. 검사자의 태도나 상황에 따라 정확도가 달라질 수 있으므로, 실제 교육과정 선택 시에는 다양한 요소를 함께 고려하시길 권장합니다.")

    if st.button("검사 다시하기"):
        st.session_state.clear()
        st.rerun()

if 'current_section' in st.session_state and st.session_state.current_section < len(section_list):
    display_survey()
elif 'responses' in st.session_state and st.session_state.responses:
    display_results()
