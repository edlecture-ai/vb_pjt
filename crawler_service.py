"""
뉴스 검색 및 크롤링 관련 서비스 모듈
- Google News RSS 검색
- Playwright를 이용한 기사 본문 크롤링 (ref_codes 방식 적용)
- OpenAI를 이용한 기사 요약
"""

import os
import sys
import asyncio
import feedparser
from urllib.parse import quote
from openai import OpenAI
import streamlit as st
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Windows에서 ProactorEventLoop 설정 (ref_codes 방식)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def is_article_request(text: str) -> bool:
    """
    사용자 입력이 기사 검색 요청인지 확인

    Args:
        text (str): 사용자 입력 텍스트

    Returns:
        bool: 기사 검색 키워드가 포함되어 있으면 True
    """
    if not text:
        return False
    keywords = ["기사", "뉴스", "요약"]
    return any(k in text for k in keywords)


def fetch_google_news(keyword: str):
    """
    Google News RSS를 통해 기사 검색

    Args:
        keyword (str): 검색 키워드

    Returns:
        list: 기사 정보 리스트 (title, link 포함), 최대 6개
    """
    if not keyword:
        return []
    encoded = quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:6]:
        articles.append({"title": entry.title, "link": entry.link})
    return articles


async def _crawl_article_async(url: str):
    """
    비동기 기사 본문 크롤링 (ref_codes 방식)

    Args:
        url (str): 기사 URL

    Returns:
        str: 크롤링된 본문 텍스트 (실패 시 빈 문자열)
    """
    try:
        async with async_playwright() as p:
            # Windows 환경에서 안정적인 브라우저 설정 (ref_codes 방식)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',                      # 샌드박스 비활성화
                    '--disable-setuid-sandbox',          # setuid 샌드박스 비활성화
                    '--disable-dev-shm-usage',           # /dev/shm 사용 안 함
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu'                      # GPU 비활성화
                ]
            )

            page = await browser.new_page()
            await page.goto(url, timeout=15000)

            # 본문 추출
            paragraphs = await page.query_selector_all("p")
            text_list = [await p_el.inner_text() for p_el in paragraphs]

            await browser.close()
            return "\n".join(text_list).strip()
    except Exception as e:
        return ""


async def _crawl_all_articles_async(articles):
    """
    여러 기사의 본문을 병렬로 크롤링 (비동기)

    Args:
        articles (list): 기사 정보 리스트 (link 필드 필요)

    Returns:
        None: articles 리스트에 'body' 필드 추가
    """
    tasks = [_crawl_article_async(article['link']) for article in articles]
    bodies = await asyncio.gather(*tasks)

    for article, body in zip(articles, bodies):
        article['body'] = body


def crawl_all_articles(articles):
    """
    여러 기사의 본문을 병렬로 크롤링 (ref_codes 방식 적용)

    Windows + Streamlit 환경에서 안전하게 동작

    Args:
        articles (list): 기사 정보 리스트 (link 필드 필요)

    Returns:
        None: articles 리스트에 'body' 필드 추가
    """
    try:
        # Streamlit 스레드 환경에서 이벤트 루프 생성 (ref_codes 방식)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 현재 스레드에 이벤트 루프가 없는 경우 새로 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 이벤트 루프가 실행 중인지 확인
        if loop.is_running():
            # 이미 실행 중인 경우 새 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_crawl_all_articles_async(articles))
        else:
            # 실행 중이 아닌 경우 그대로 사용
            loop.run_until_complete(_crawl_all_articles_async(articles))

    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {e}")
        # 실패 시 빈 본문으로 설정
        for article in articles:
            article['body'] = ""


def summarize_articles(articles):
    """
    OpenAI를 이용하여 기사 요약

    Args:
        articles (list): 기사 정보 리스트 (title, body 필드 필요)

    Returns:
        list: 각 기사의 요약 텍스트 리스트
    """
    summaries = []
    for article in articles:
        prompt = f"다음 기사를 중립적이고 짧게 요약하세요.\n제목: {article['title']}\n본문: {article.get('body', '')}"
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            summaries.append(response.choices[0].message.content)
        except Exception as e:
            st.warning(f"OpenAI 오류 발생: {e}")
            summaries.append("요약을 생성할 수 없습니다.")
    return summaries
