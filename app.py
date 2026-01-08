import os
import json
from datetime import datetime
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# 서비스 모듈 임포트
from notion_service import send_articles_to_notion, check_notion_config
from crawler_service import (
    is_article_request,
    fetch_google_news,
    crawl_all_articles,
    summarize_articles
)
from scheduler_service import (
    init_scheduler,
    restore_schedules,
    add_schedule,
    remove_schedule,
    get_active_schedules,
    get_schedule_logs
)

# =========================
# 환경 변수 로드
# =========================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("환경 변수 OPENAI_API_KEY가 설정되어 있지 않습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Notion 설정 확인
check_notion_config()

# 스케줄러 초기화 및 복원
init_scheduler()
if "scheduler_restored" not in st.session_state:
    restore_schedules()
    st.session_state.scheduler_restored = True

# =========================
# Streamlit 설정 및 상태
# =========================
st.set_page_config(page_title="Chatbot + News + Notion", layout="wide")
CHAT_HISTORY_FILE = "chat_history.json"

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat_history(messages):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

if "show_scheduler" not in st.session_state:
    st.session_state.show_scheduler = False

# =========================
# 헬퍼 함수
# =========================
def get_openai_messages(messages):
    return [m for m in messages if m["role"] in ("user", "assistant", "system")]

# =========================
# CSS 스타일
# =========================
st.markdown("""
<style>
    /* 헤더 전체 Wrapper - 헤더+버튼을 묶는 컨테이너 */
    .header-wrapper {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: white;
        z-index: 1000;
        padding: 1rem 3rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    /* 헤더 컨테이너 */
    .header-container {
        padding: 0;
        margin-bottom: 0.5rem;
    }

    /* 헤더 스타일 */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem 1rem 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        margin: 0.3rem 0 0.8rem 0;
        font-size: 0.9rem;
    }

    /* 헤더 내부 버튼 컨테이너 - fixed 위치 (헤더 높이 + 84px, 우측) */
    .st-key-scheduler-toggle-btn {
        position: fixed;
        top: calc(1rem + 1.5rem + 1rem + 0.3rem + 0.8rem + 1rem + 84px);
        right: 3rem;
        z-index: 1001;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 헤더 내부 버튼 스타일 - 색상 있는 버튼 */
    .st-key-scheduler-toggle-btn button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.6rem 1.2rem !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
    }
    .st-key-scheduler-toggle-btn button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
        transform: translateY(-2px) scale(1.05) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    }
    .st-key-scheduler-toggle-btn button:active {
        transform: translateY(0) scale(1.02) !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4) !important;
    }

    /* 헤더 버튼 스타일 */
    .header-button {
        background-color: rgba(255, 255, 255, 0.2);
        border: 2px solid rgba(255, 255, 255, 0.5);
        color: white;
        font-size: 1rem;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        white-space: nowrap;
        text-align: center;
    }
    .header-button:hover {
        background-color: rgba(255, 255, 255, 0.3);
        border-color: rgba(255, 255, 255, 0.8);
        transform: scale(1.05);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }


    /* 버튼 스타일 개선 */
    .stButton button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }

    /* 채팅 메시지 스타일 */
    .stChatMessage {
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    /* 다크모드 대응 */
    [data-testid="stAppViewContainer"] {
        padding-top: 0 !important;
    }

    /* Fixed 헤더로 인한 콘텐츠 여백 */
    .main .block-container {
        padding-top: 13rem !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# 페이지 헤더 - 버튼 포함
# =========================
# 헤더와 버튼을 하나의 컨테이너로 묶음
st.markdown("""
<div class="header-wrapper">
    <div class="header-container">
        <div class="main-header">
            <h1>📰 AI 뉴스 어시스턴트 챗봇</h1>
            <p>실시간 뉴스 검색, 요약 및 Notion 저장 | 자동 스케줄링 지원</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# 스케줄러 토글 버튼 (헤더 wrapper 내부)
button_text = "✕ 스케쥴러 닫기" if st.session_state.show_scheduler else "📅 뉴스 수집 스케줄러"
if st.button(button_text, key="scheduler-toggle-btn"):
    st.session_state.show_scheduler = not st.session_state.show_scheduler
    st.rerun()

# header-wrapper 닫기
st.markdown("""
</div>
""", unsafe_allow_html=True)

# =========================
# 사이드바: 스케줄 관리 UI (조건부 표시)
# =========================
if st.session_state.show_scheduler:
    with st.sidebar:
        st.header("⏰ 자동 뉴스 스크랩 스케줄")

        # 스케줄 추가 섹션
        with st.expander("➕ 새 스케줄 추가", expanded=False):
            # 폼 외부에서 실행 주기 선택 (즉시 반영)
            frequency_type = st.radio(
                "실행 주기",
                options=["매일", "특정 요일"],
                horizontal=True,
                key="frequency_type_radio"
            )

            with st.form("add_schedule_form"):
                keyword_input = st.text_input("검색 키워드", placeholder="예: AI, 삼성전자, 경제")

                col1, col2 = st.columns(2)
                with col1:
                    hour_input = st.number_input("시간 (시)", min_value=0, max_value=23, value=9)
                with col2:
                    minute_input = st.number_input("시간 (분)", min_value=0, max_value=59, value=0, step=15)

                # 특정 요일 선택 시에만 표시
                days_selected = []
                if frequency_type == "특정 요일":
                    days_selected = st.multiselect(
                        "실행 요일 선택",
                        options=["월", "화", "수", "목", "금", "토", "일"],
                        default=["월", "수", "금"]
                    )

                submitted = st.form_submit_button("스케줄 추가")

                if submitted:
                    if keyword_input.strip():
                        try:
                            # 요일 변환
                            days_of_week_input = None
                            if frequency_type == "특정 요일":
                                if days_selected:
                                    day_map = {"월": "mon", "화": "tue", "수": "wed", "목": "thu", "금": "fri", "토": "sat", "일": "sun"}
                                    days_of_week_input = ",".join([day_map[d] for d in days_selected])
                                else:
                                    st.warning("실행할 요일을 선택해주세요.")
                                    st.stop()

                            schedule_info = add_schedule(
                                keyword=keyword_input.strip(),
                                hour=hour_input,
                                minute=minute_input,
                                days_of_week=days_of_week_input
                            )
                            st.success(f"✅ 스케줄 추가 완료: {keyword_input} ({hour_input:02d}:{minute_input:02d})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"스케줄 추가 실패: {e}")
                    else:
                        st.warning("키워드를 입력해주세요.")

        # 활성 스케줄 목록
        st.subheader("📋 활성 스케줄")
        active_schedules = get_active_schedules()

        if active_schedules:
            for schedule in active_schedules:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{schedule['keyword']}**")
                        st.caption(f"{schedule['frequency_text']} {schedule['hour']:02d}:{schedule['minute']:02d}")
                    with col2:
                        if st.button("🗑️", key=f"del_{schedule['id']}"):
                            if remove_schedule(schedule['id']):
                                st.success("삭제 완료")
                                st.rerun()
                            else:
                                st.error("삭제 실패")
                    st.divider()
        else:
            st.info("등록된 스케줄이 없습니다.")

        # 실행 로그 확인
        st.divider()
        with st.expander("📜 실행 로그 (최근 10개)", expanded=True):
            logs = get_schedule_logs(limit=10)
            if logs:
                for log in logs:
                    status_icon = "✅" if log["status"] == "성공" else "❌"
                    with st.container():
                        st.markdown(f"{status_icon} **{log['keyword']}** - {log['status']}")
                        st.caption(f"⏰ {log['timestamp']}")
                        if log.get('notion_url'):
                            st.markdown(f"🔗 [Notion 페이지 열기]({log['notion_url']})")
                        st.divider()
            else:
                st.info("아직 실행 로그가 없습니다. 스케줄이 실행되면 여기에 표시됩니다.")

# =========================
# 기존 메시지 출력
# =========================
for msg in st.session_state.messages:
    if msg.get("role") == "news_cards":
        st.markdown("### 📰 기사 요약 카드뉴스")
        cols = st.columns(2)
        for idx, item in enumerate(msg["content"][:6]):
            with cols[idx % 2]:
                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd; padding:15px;
                                border-radius:8px; margin-bottom:10px;">
                        <h4>{item['title']}</h4>
                        <p>{item['summary']}</p>
                        <a href="{item['link']}" target="_blank">원문 보기</a>
                    </div>
                    """, unsafe_allow_html=True
                )
    else:
        with st.chat_message(msg["role"]):
            # 타임스탬프가 있으면 표시
            if "timestamp" in msg:
                st.caption(msg["timestamp"])
            st.markdown(msg["content"])

# =========================
# 사용자 입력 처리
# =========================

user_input = st.chat_input("메시지를 입력하세요")

if user_input and isinstance(user_input, str) and user_input.strip():
    cleaned_input = user_input.strip()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.messages.append({"role":"user","content":cleaned_input,"timestamp":current_time})

    if is_article_request(cleaned_input):
        # 이전 카드뉴스 제거
        st.session_state.messages = [m for m in st.session_state.messages if m.get("role")!="news_cards"]

        # 키워드 추출 개선: 불필요한 단어들 제거
        exclude_words = [
            "기사", "뉴스", "요약", "검색", "찾아", "찾아줘", "보여", "보여줘",
            "알려", "알려줘", "관련", "최신", "오늘", "최근", "관한", "대한",
            "해줘", "주세요", "해주세요", "원해", "원합니다", "보고", "싶어",
            "싶습니다", "해", "줘", "을", "를", "의", "에", "대해", "대하여"
        ]

        words = cleaned_input.split()
        keyword_words = [w for w in words if w not in exclude_words]
        keyword = " ".join(keyword_words).strip()

        # 사용자 메시지 먼저 표시
        with st.chat_message("user"):
            st.markdown(cleaned_input)

        # 키워드가 있으면 표시, 없으면 기본 메시지
        spinner_message = f"'{keyword}' 기사를 검색 및 요약하고 있습니다..." if keyword else "기사를 검색 및 요약하고 있습니다..."

        with st.spinner(spinner_message):
            articles = fetch_google_news(keyword)
            if articles:
                # Playwright 비동기 본문 크롤링 (이제 동기 함수로 호출)
                crawl_all_articles(articles)
                # OpenAI 요약
                summaries = summarize_articles(articles)
                cards = [{"title":a["title"],"summary":s,"link":a["link"]} for a,s in zip(articles,summaries)]

                # Notion 저장
                success, page_url = send_articles_to_notion(cleaned_input, keyword, cards[:6])

                # 챗봇 안내 메시지 + Notion 버튼
                assistant_content = "관련 기사들을 찾아서 정리했어요."
                if success and page_url:
                    # Streamlit 버튼을 markdown 링크로 표현
                    assistant_content += f' [Notion 페이지 열기]({page_url})'
                else:
                    assistant_content += " (Notion 저장 실패, 로그 확인 가능)"

                assistant_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.messages.append({"role":"assistant","content":assistant_content,"timestamp":assistant_time})
                st.session_state.messages.append({"role":"news_cards","content":cards[:6]})
            else:
                no_result_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.messages.append({"role":"assistant","content":"해당 키워드로는 최근 기사를 찾지 못했어요.","timestamp":no_result_time})

    else:
        # 일반 챗봇
        # 사용자 메시지 먼저 표시
        with st.chat_message("user"):
            st.markdown(cleaned_input)

        openai_messages = get_openai_messages(st.session_state.messages)
        try:
            with st.spinner("응답 생성 중..."):
                response = client.chat.completions.create(model="gpt-4o-mini", messages=openai_messages)
                response_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.messages.append({"role":"assistant","content":response.choices[0].message.content,"timestamp":response_time})
        except Exception as e:
            st.warning(f"OpenAI 오류 발생: {e}")
            error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.messages.append({"role":"assistant","content":"요청 처리 중 오류가 발생했습니다.","timestamp":error_time})

    save_chat_history(st.session_state.messages)
    st.rerun()

# =========================
# Notion 로그 확인 UI (실패 시에만 표시)
# =========================
if "notion_logs" in st.session_state and st.session_state.notion_logs:
    # 로그 중 오류 메시지가 있는지 확인
    has_error = any("오류" in log or "실패" in log for log in st.session_state.notion_logs)

    if has_error:
        with st.expander("⚠️ Notion 전송 로그 확인 (오류 발생)", expanded=True):
            for log in st.session_state.notion_logs[-5:]:
                if "오류" in log or "실패" in log:
                    st.error(log)
                else:
                    st.write(log)
