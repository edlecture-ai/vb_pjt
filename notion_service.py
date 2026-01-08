"""
Notion API 관련 서비스 모듈
- Notion 데이터베이스에 기사 저장
- Notion API와의 통신 처리
"""

import os
import datetime
import requests
import streamlit as st
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_PUBLIC_DOMAIN = "https://dolomite-lyric-c5d.notion.site"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def convert_to_public_url(notion_url: str) -> str:
    """
    Notion API에서 반환된 URL을 public 도메인으로 변환

    Args:
        notion_url (str): Notion API에서 반환된 URL (예: https://www.notion.so/xxx-yyy)

    Returns:
        str: Public 도메인 URL (예: https://dolomite-lyric-c5d.notion.site/xxx-yyy)
    """
    if not notion_url:
        return notion_url

    # notion.so 도메인을 public 도메인으로 교체
    if "notion.so" in notion_url:
        # URL에서 페이지 ID 부분 추출
        page_path = notion_url.split("notion.so/")[-1]
        return f"{NOTION_PUBLIC_DOMAIN}/{page_path}"

    return notion_url


def send_articles_to_notion(user_request: str, keyword: str, articles: list):
    """
    Notion Page에 Markdown 형태로 기사 저장

    Args:
        user_request (str): 사용자의 원본 요청 메시지
        keyword (str): 검색 키워드
        articles (list): 기사 정보 리스트 (title, summary, link 포함)

    Returns:
        tuple: (success: bool, page_url: str or None)
    """
    if "notion_logs" not in st.session_state:
        st.session_state.notion_logs = []

    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        msg = "Notion API Key 또는 Database ID가 없습니다."
        st.error(msg)
        st.session_state.notion_logs.append(msg)
        return False, None

    # children 블록 생성
    children = []
    for idx, article in enumerate(articles[:6], 1):
        # 제목
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": f'{idx}. {article["title"]}'}}]
            }
        })
        # 요약
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": article["summary"]}}]
            }
        })
        # 링크
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text",
                     "text": {
                         "content": "기사 바로가기",
                         "link": {"url": article["link"]}
                     }}
                ]
            }
        })

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": user_request}}]},
            "Keyword": {"rich_text": [{"text": {"content": keyword}}]},
            "Date": {"date": {"start": datetime.date.today().isoformat()}}
        },
        "children": children
    }

    try:
        response = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload)
        if response.status_code in (200, 201):
            st.session_state.notion_logs.append("Notion 저장 완료")
            # Notion page URL 가져오기 및 public 도메인으로 변환
            page_url = response.json().get("url")
            public_url = convert_to_public_url(page_url)
            return True, public_url
        else:
            msg = f"Notion 전송 오류: {response.status_code} {response.text}"
            st.error(msg)
            st.session_state.notion_logs.append(msg)
            return False, None
    except Exception as e:
        msg = f"Notion 전송 예외 발생: {e}"
        st.error(msg)
        st.session_state.notion_logs.append(msg)
        return False, None


def check_notion_config():
    """
    Notion API 설정이 올바른지 확인

    Returns:
        bool: 설정이 올바르면 True
    """
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        st.warning("Notion API Key 또는 Database ID가 설정되어 있지 않습니다.")
        return False
    return True
