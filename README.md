# 📰 AI 뉴스 어시스턴트 챗봇

실시간 뉴스 검색, 요약 및 Notion 저장 기능을 제공하는 Streamlit 기반 AI 챗봇입니다.

## 주요 기능

- **AI 챗봇**: OpenAI GPT를 활용한 대화형 인터페이스
- **뉴스 검색**: Google News RSS를 통한 실시간 뉴스 검색
- **자동 크롤링**: Playwright를 이용한 기사 본문 크롤링
- **AI 요약**: OpenAI를 활용한 기사 자동 요약
- **Notion 연동**: 검색된 뉴스를 Notion 데이터베이스에 자동 저장
- **스케줄러**: 정기적인 뉴스 수집 및 저장 자동화

## 기술 스택

- **프론트엔드**: Streamlit
- **AI/ML**: OpenAI GPT-4
- **크롤링**: Playwright, Feedparser
- **스케줄링**: APScheduler
- **데이터베이스**: Notion API
- **환경 관리**: Python-dotenv

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd my_chatbot_project
```

### 2. Python 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. Playwright 브라우저 설치

```bash
playwright install chromium
```

### 5. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 입력하세요.

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` 파일을 열어 다음 값들을 설정하세요:

```env
OPENAI_API_KEY=your-openai-api-key-here
NOTION_API_KEY=your-notion-integration-token-here
NOTION_DATABASE_ID=your-notion-database-id-here
```

## API 키 발급 방법

### OpenAI API Key

1. [OpenAI Platform](https://platform.openai.com/)에 접속
2. 로그인 후 API Keys 메뉴로 이동
3. "Create new secret key" 클릭하여 키 생성
4. 생성된 키를 `.env` 파일의 `OPENAI_API_KEY`에 입력

### Notion Integration

1. [Notion Integrations](https://www.notion.so/my-integrations) 페이지 접속
2. "New integration" 클릭
3. Integration 이름 입력 후 생성
4. "Internal Integration Token" 복사하여 `.env` 파일의 `NOTION_API_KEY`에 입력

### Notion Database ID

1. Notion에서 뉴스를 저장할 데이터베이스 페이지 생성
2. 데이터베이스에 다음 속성 추가:
   - `Title` (제목 타입)
   - `Keyword` (텍스트 타입)
   - `Date` (날짜 타입)
3. 데이터베이스를 Integration에 연결 (Share → Invite → 생성한 Integration 선택)
4. 데이터베이스 URL에서 ID 추출:
   ```
   https://www.notion.so/workspace/DATABASE_ID?v=...
   ```
   `DATABASE_ID` 부분을 `.env` 파일의 `NOTION_DATABASE_ID`에 입력

## 실행 방법

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 앱에 접속할 수 있습니다.

## 사용 방법

### 1. 일반 채팅

채팅 입력창에 질문을 입력하면 AI가 답변합니다.

```
사용자: 안녕하세요!
AI: 안녕하세요! 어떻게 도와드릴까요?
```

### 2. 뉴스 검색

뉴스 관련 키워드로 질문하면 자동으로 뉴스를 검색하고 요약합니다.

```
사용자: 삼성전자 최신 뉴스 찾아줘
AI: 관련 기사들을 찾아서 정리했어요. [Notion 페이지 열기](...)
```

### 3. 뉴스 스케줄러

1. 우측 상단의 "📅 뉴스 수집 스케줄러" 버튼 클릭
2. 사이드바에서 키워드, 시간, 주기 설정
3. "스케줄 추가" 버튼 클릭
4. 설정된 시간에 자동으로 뉴스 수집 및 Notion 저장

## 프로젝트 구조

```
my_chatbot_project/
├── app.py                    # 메인 Streamlit 애플리케이션
├── crawler_service.py        # 뉴스 크롤링 서비스
├── notion_service.py         # Notion API 연동
├── scheduler_service.py      # 스케줄링 서비스
├── requirements.txt          # Python 패키지 의존성
├── .env                      # 환경 변수 (Git 제외)
├── .env.example             # 환경 변수 예시
├── .gitignore               # Git 제외 파일 목록
├── chat_history.json        # 채팅 기록 (자동 생성)
├── schedules.json           # 스케줄 설정 (자동 생성)
└── schedule_logs.json       # 스케줄 실행 로그 (자동 생성)
```

## 주요 파일 설명

- **app.py**: Streamlit UI 및 메인 로직
- **crawler_service.py**: Google News RSS 검색, Playwright 크롤링, AI 요약
- **notion_service.py**: Notion API를 통한 뉴스 저장
- **scheduler_service.py**: APScheduler를 이용한 정기적 뉴스 수집

## 문제 해결

### Playwright 관련 오류

```bash
# 브라우저 재설치
playwright install chromium

# 시스템 의존성 설치 (Linux)
playwright install-deps
```

### 환경 변수 인식 오류

- `.env` 파일이 프로젝트 루트에 있는지 확인
- API 키에 공백이나 따옴표가 없는지 확인
- 앱을 재시작

### Notion 연동 오류

- Integration이 데이터베이스에 연결되어 있는지 확인
- Database ID가 올바른지 확인 (URL에서 추출)
- Notion API Key가 유효한지 확인

## 개발 환경

- Python 3.8 이상
- Windows / macOS / Linux

## 라이선스

MIT License

## 기여

이슈와 PR은 언제나 환영합니다!

## 연락처

문의사항이 있으시면 이슈를 생성해주세요.
