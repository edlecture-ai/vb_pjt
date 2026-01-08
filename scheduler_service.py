"""
스케줄러 서비스 모듈
- APScheduler를 이용한 정기적인 뉴스 스크랩 및 Notion 저장
- 스케줄 설정 저장/로드
"""

import os
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from crawler_service import fetch_google_news, crawl_all_articles, summarize_articles
from notion_service import send_articles_to_notion

# 스케줄 설정 파일
SCHEDULE_CONFIG_FILE = "schedules.json"

# 글로벌 스케줄러 인스턴스
scheduler = None


def init_scheduler():
    """
    스케줄러 초기화 (앱 시작 시 한 번만 호출)

    Returns:
        BackgroundScheduler: 초기화된 스케줄러 인스턴스
    """
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        scheduler.start()
        print("[Scheduler] 스케줄러 초기화 완료")
    return scheduler


def load_schedules():
    """
    저장된 스케줄 설정 로드

    Returns:
        list: 스케줄 설정 리스트
    """
    if os.path.exists(SCHEDULE_CONFIG_FILE):
        with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_schedules(schedules):
    """
    스케줄 설정 저장

    Args:
        schedules (list): 저장할 스케줄 설정 리스트
    """
    with open(SCHEDULE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)


def execute_scheduled_scraping(schedule_id, keyword):
    """
    스케줄된 뉴스 스크랩 실행

    Args:
        schedule_id (str): 스케줄 ID
        keyword (str): 검색 키워드
    """
    try:
        print(f"[Scheduler] 스케줄 실행 시작 - ID: {schedule_id}, 키워드: {keyword}")

        # 뉴스 검색
        articles = fetch_google_news(keyword)

        if articles:
            # 본문 크롤링
            crawl_all_articles(articles)

            # 요약 생성
            summaries = summarize_articles(articles)

            # 카드 데이터 생성
            cards = [
                {"title": a["title"], "summary": s, "link": a["link"]}
                for a, s in zip(articles, summaries)
            ]

            # Notion 저장
            user_request = f"[자동 스케줄] {keyword} 관련 기사"
            success, page_url = send_articles_to_notion(user_request, keyword, cards[:6])

            if success:
                print(f"[Scheduler] Notion 저장 성공 - URL: {page_url}")
                log_schedule_execution(schedule_id, keyword, "성공", page_url)
            else:
                print(f"[Scheduler] Notion 저장 실패")
                log_schedule_execution(schedule_id, keyword, "실패", None)
        else:
            print(f"[Scheduler] 검색 결과 없음 - 키워드: {keyword}")
            log_schedule_execution(schedule_id, keyword, "검색 결과 없음", None)

    except Exception as e:
        print(f"[Scheduler] 실행 중 오류: {e}")
        log_schedule_execution(schedule_id, keyword, f"오류: {str(e)}", None)


def log_schedule_execution(schedule_id, keyword, status, notion_url):
    """
    스케줄 실행 로그 저장

    Args:
        schedule_id (str): 스케줄 ID
        keyword (str): 검색 키워드
        status (str): 실행 상태
        notion_url (str): Notion 페이지 URL (성공 시)
    """
    log_file = "schedule_logs.json"
    logs = []

    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)

    log_entry = {
        "schedule_id": schedule_id,
        "keyword": keyword,
        "status": status,
        "notion_url": notion_url,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    logs.append(log_entry)

    # 최근 100개만 유지
    logs = logs[-100:]

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def add_schedule(keyword, hour, minute, days_of_week=None):
    """
    새로운 스케줄 추가

    Args:
        keyword (str): 검색 키워드
        hour (int): 실행 시간 (시)
        minute (int): 실행 시간 (분)
        days_of_week (str): 요일 설정 (cron 형식, 예: "mon,wed,fri" 또는 None=매일)

    Returns:
        dict: 추가된 스케줄 정보
    """
    global scheduler

    if scheduler is None:
        init_scheduler()

    # 스케줄 ID 생성
    schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Cron 트리거 생성
    if days_of_week:
        trigger = CronTrigger(
            day_of_week=days_of_week,
            hour=hour,
            minute=minute,
            timezone="Asia/Seoul"
        )
        frequency_text = f"매주 {days_of_week}"
    else:
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone="Asia/Seoul"
        )
        frequency_text = "매일"

    # 스케줄 등록
    scheduler.add_job(
        execute_scheduled_scraping,
        trigger=trigger,
        args=[schedule_id, keyword],
        id=schedule_id,
        name=f"{keyword} 뉴스 스크랩",
        replace_existing=True
    )

    # 스케줄 정보 저장
    schedule_info = {
        "id": schedule_id,
        "keyword": keyword,
        "hour": hour,
        "minute": minute,
        "days_of_week": days_of_week,
        "frequency_text": frequency_text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    schedules = load_schedules()
    schedules.append(schedule_info)
    save_schedules(schedules)

    print(f"[Scheduler] 스케줄 추가 완료 - ID: {schedule_id}, 키워드: {keyword}, 시간: {hour:02d}:{minute:02d}")

    return schedule_info


def remove_schedule(schedule_id):
    """
    스케줄 제거

    Args:
        schedule_id (str): 제거할 스케줄 ID

    Returns:
        bool: 제거 성공 여부
    """
    global scheduler

    try:
        # APScheduler에서 job 제거
        if scheduler:
            scheduler.remove_job(schedule_id)

        # 설정 파일에서 제거
        schedules = load_schedules()
        schedules = [s for s in schedules if s["id"] != schedule_id]
        save_schedules(schedules)

        print(f"[Scheduler] 스케줄 제거 완료 - ID: {schedule_id}")
        return True

    except Exception as e:
        print(f"[Scheduler] 스케줄 제거 실패: {e}")
        return False


def get_active_schedules():
    """
    활성화된 스케줄 목록 조회

    Returns:
        list: 스케줄 정보 리스트
    """
    return load_schedules()


def restore_schedules():
    """
    앱 시작 시 저장된 스케줄 복원
    """
    global scheduler

    if scheduler is None:
        init_scheduler()

    schedules = load_schedules()

    for schedule in schedules:
        try:
            # Cron 트리거 재생성
            if schedule.get("days_of_week"):
                trigger = CronTrigger(
                    day_of_week=schedule["days_of_week"],
                    hour=schedule["hour"],
                    minute=schedule["minute"],
                    timezone="Asia/Seoul"
                )
            else:
                trigger = CronTrigger(
                    hour=schedule["hour"],
                    minute=schedule["minute"],
                    timezone="Asia/Seoul"
                )

            # Job 재등록
            scheduler.add_job(
                execute_scheduled_scraping,
                trigger=trigger,
                args=[schedule["id"], schedule["keyword"]],
                id=schedule["id"],
                name=f"{schedule['keyword']} 뉴스 스크랩",
                replace_existing=True
            )

            print(f"[Scheduler] 스케줄 복원 완료 - ID: {schedule['id']}, 키워드: {schedule['keyword']}")

        except Exception as e:
            print(f"[Scheduler] 스케줄 복원 실패 ({schedule['id']}): {e}")

    print(f"[Scheduler] 총 {len(schedules)}개 스케줄 복원 완료")


def get_schedule_logs(limit=20):
    """
    스케줄 실행 로그 조회

    Args:
        limit (int): 조회할 최대 로그 개수

    Returns:
        list: 로그 리스트 (최신순)
    """
    log_file = "schedule_logs.json"

    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
            return logs[-limit:][::-1]  # 최신순으로 반환

    return []
