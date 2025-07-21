import streamlit as st
import pandas as pd
import plotly.express as px
import random

# 페이지 기본 설정
st.set_page_config(page_title="과목 유형 검사", page_icon="📚", layout="wide")

# CSS 주입
st.markdown(
    """
    <style>
    .st-emotion-cache-18ni7ap { padding-top: 6rem; }
    </style>
    """,
    unsafe_allow_html=True
)

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

# --- 세션 상태 초기화 ---
if 'dev_authenticated' not in st.session_state:
    st.session_state.dev_authenticated = False
if 'show_dev_results' not in st.session_state:
    st.session_state.show_dev_results = False

# --- 핵심 수정: URL 파라미터로 개발자 모드 접근 제어 ---
# URL에 ?dev=true가 있을 때만 사이드바 로직 실행
if st.query_params.get("dev") == "true":
    with st.sidebar:
        st.header("개발자용")
        
        if st.session_state.dev_authenticated:
            st.success("인증 성공")
            if st.button("결과 페이지 바로보기 (기본 버전)"):
                st.session_state.show_dev_results = True
                st.rerun()
            if st.button("로그아웃"):
                st.session_state.dev_authenticated = False
                st.session_state.show_dev_results = False
                st.rerun()
        else:
            with st.form("login_form"):
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인")
                if submitted:
                    if "passwords" in st.secrets and password == st.secrets.passwords.dev_mode_password:
                        st.session_state.dev_authenticated = True
                        st.rerun()
                    else:
                        st.error("비밀번호가 틀렸습니다.")

# --- UI 및 메인 로직 ---
with st.container():
    try:
        advice_df = pd.read_csv('advice_data.csv', header=None)
        advice_list = advice_df[0].dropna().tolist()
        marquee_content = " ★★★ ".join(advice_list)
        marquee_speed_seconds = 240
        st.markdown(
            f"""
            <style>
            .marquee-container {{
                position: fixed; top: 55px; left: 0; width: 100%; z-index: 998;
                background-color: #222222; color: white; padding: 10px 0;
                overflow: hidden; box-sizing: border-box;
            }}
            .marquee-text {{
                display: inline-block; padding-left: 100%;
                animation: marquee {marquee_speed_seconds}s linear infinite;
                white-space: nowrap; font-size: 18px;
            }}
            @keyframes marquee {{
                0%   {{ transform: translateX(0); }}
                100% {{ transform: translateX(-100%); }}
            }}
            </style>
            <div class="marquee-container">
                <div class="marquee-text">{marquee_content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass

st.title("📚 SETI 선택과목 유형검사")

def display_survey(df):
    version = st.session_state.get('version')
    section_list = [s for s in SECTION_ORDER if s in df['카테고리'].unique()]

    if 'current_section' not in st.session_state:
        st.session_state.current_section = 0

    total_questions = len(df)
    answered_questions = len(st.session_state.get('responses', {}))
    st.progress(answered_questions / total_questions, text=f"진행률: {answered_questions} / {total_questions} 문항")
    
    section_index = st.session_state.current_section
    if section_index < len(section_list):
        current_section_name = section_list[section_index]
        questions_df = df[df['카테고리'] == current_section_name].sample(frac=1).reset_index(drop=True)
        st.subheader(f"섹션 {section_index + 1}: {current_section_name}")
        options_map = {1: "1(전혀 아니다)", 2: "2(아니다)", 3: "3(보통이다)", 4: "4(그렇다)", 5: "5(매우 그렇다)"}
        
        with st.form(key=f"form_{version}_{section_index}"):
            for _, row in questions_df.iterrows():
                st.markdown(f"**{row['수정내용']}**")
                st.radio("선택", [1, 2, 3, 4, 5], key=f"q_{row['번호']}", 
                         format_func=lambda x: options_map[x], 
                         horizontal=True, 
                         label_visibility="collapsed",
                         index=None)
            
            button_label = "결과 분석하기" if (section_index == len(section_list) - 1) else "다음 섹션으로"
            if st.form_submit_button(button_label):
                all_answered = True
                for _, row in questions_df.iterrows():
                    if st.session_state.get(f"q_{row['번호']}") is None:
                        all_answered = False
                        break
                
                if not all_answered:
                    st.warning("모든 문항에 답변해주세요!")
                else:
                    if 'responses' not in st.session_state:
                        st.session_state.responses = {}
                    for _, row in questions_df.iterrows():
                        st.session_state.responses[str(row['번호'])] = st.session_state[f"q_{row['번호']}"]
                    st.session_state.current_section += 1
                    st.rerun()
    else:
        st.session_state.show_results = True
        st.rerun()

def display_results(df, is_dev_mode=False):
    responses = st.session_state.get('responses', {})
    if not is_dev_mode:
        all_answers = list(responses.values())
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
        for q_id, answer in responses.items():
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
        top_8_subjects_list = list(sorted_scores_dict.keys())[:8]
        sorted_top_subjects = []
        for group_name in SECTION_ORDER:
            for subject in top_8_subjects_list:
                if subject_to_group_map.get(subject) == group_name:
                    sorted_top_subjects.append(subject)

        if sorted_top_subjects:
            cols = st.columns(4)
            for i in range(len(sorted_top_subjects)):
                subject = sorted_top_subjects[i]
                with cols[i % 4]:
                    st.metric(label=f"**{subject_to_group_map.get(subject)}** | {subject}", 
                              value=f"{sorted_scores_dict[subject]:.2f}점")
        
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

# --- 메인 로직 분기 ---
SUBJECT_ORDER = ['국어', '수학', '영어', '독일어', '중국어', '일본어', '물리', '화학', '생명과학', '지구과학', '일반사회', '역사', '윤리', '지리']
SECTION_ORDER = ['기초교과군', '제2외국어군', '과학군', '사회군']

if st.session_state.show_dev_results:
    st.warning("개발자 모드가 활성화되었습니다. 랜덤 응답으로 결과 페이지를 표시합니다.")
    df_dev = load_data('default_data.csv')
    if df_dev is not None:
        st.session_state.responses = {str(q_id): random.randint(1, 5) for q_id in df_dev['번호']}
        display_results(df_dev, is_dev_mode=True)
    else:
        st.error("개발자 모드를 위해 default_data.csv 파일이 필요합니다.")
else:
    version = st.radio(
        "**원하는 검사 버전을 선택해주세요.**",
        ('**라이트** (81문항)', '**기본** (115문항)'),
        index=None,
        horizontal=True
    )

    if version:
        if 'version' not in st.session_state or st.session_state.version != version:
            st.session_state.version = version
            st.session_state.current_section = 0
            st.session_state.responses = {}
            st.session_state.show_results = False

        file_to_load = 'lite_data.csv' if '라이트' in version else 'default_data.csv'
        df = load_data(file_to_load)
        if df is not None:
            if st.session_state.get('show_results', False):
                 display_results(df)
            else:
                 display_survey(df)
    else:
        st.info("👆 위에서 검사 버전을 선택해주세요.")
