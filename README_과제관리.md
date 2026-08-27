# 과제관리 대시보드 — 설치 및 연결 안내

회의록 텍스트를 과제/정보로 자동 분류하고 진척을 이력 관리하는 Streamlit 페이지입니다.
데이터는 이 저장소의 `tasks_data.json`에 저장됩니다.

| 파일 | 역할 |
|---|---|
| `pages/1_과제관리.py` | Streamlit 페이지 (GitHub 연동) |
| `tasks_data.json` | 과제·정보·이력 데이터 |
| `task_dashboard.html` | 오프라인 단일 파일 버전 (인터넷 없이 브라우저에서 실행) |

기존 `app.py`(Semi-Insight Hub)는 그대로 메인 페이지이고, 과제관리는 사이드바에서
선택하는 하위 페이지로 추가됩니다.

---

## 1. Streamlit Cloud 배포

1. https://share.streamlit.io 에서 **New app** 선택
2. 저장소 `SamLee-Kr0001/semi_info`, 브랜치, Main file path `app.py` 지정
3. **Advanced settings → Secrets** 에 아래를 입력

```toml
GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"
REPO_NAME    = "SamLee-Kr0001/semi_info"

# 기존 Daily Report 기능을 함께 쓰는 경우에만 추가
GEMINI_API_KEY = "..."
```

4. Deploy 후 사이드바에서 **과제관리** 선택

`GITHUB_TOKEN`은 GitHub → Settings → Developer settings → Personal access tokens에서
발급하며, **이 저장소에 대한 Contents: Read and write 권한**이 필요합니다.
토큰은 Secrets에만 넣고 코드나 커밋에 포함하지 마세요.

## 2. 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

Secrets 없이 실행하면 GitHub 대신 로컬 `tasks_data.json`을 읽고 쓰며,
사이드바에 "GitHub 미연결" 경고가 표시됩니다.
저장소에 반영하려면 `.streamlit/secrets.toml`에 위 값을 넣으세요
(이 파일은 절대 커밋하지 마세요).

---

## 3. 사용 방법

### 회의록 입력
회의록을 그대로 붙여넣고 **분석하기**를 누릅니다.

- `2026. 08. 27 (팀장 현안회의)` 형태의 **날짜 헤더**를 인식해 항목별로 나눕니다
- `-->`, `+`, 들여쓰기로 이어지는 줄은 앞 항목에 병합됩니다
- **실행이 필요한 항목은 과제**로, **단순 사실·수치·인물 정보는 정보 저장소**로 분류합니다
- 기존 과제와 같은 주제면 신규 등록 대신 **해당 과제의 진척 이력으로 갱신**합니다
  (측정 사실과 조치가 따로 등록되지 않도록 한 과제로 통합)

분류·매칭은 모두 규칙 기반이라 **AI API 키가 필요 없습니다.**

### 담당 · 납기 · 진척율
세 항목은 **자동으로 채우지 않습니다.** 텍스트에서 발견한 값은 `제안 담당` / `제안 납기`
열에만 표시되며, **제안값 일괄 적용** 버튼을 눌러야 반영됩니다.
과제 목록 탭의 표에서 칸을 클릭해 직접 입력할 수도 있습니다.

### 저장
편집 내용은 먼저 화면(세션)에만 반영되고, 사이드바의 **💾 GitHub에 저장**을 눌러야
저장소에 커밋됩니다. 저장되지 않은 변경이 있으면 사이드바에 경고가 표시됩니다.
회의록 **확정 저장**은 즉시 GitHub에 커밋합니다.

> Streamlit Cloud는 컨테이너가 재시작되면 로컬 파일이 초기화됩니다.
> 반드시 GitHub에 저장해야 데이터가 유지됩니다.

---

## 4. 데이터 구조

```jsonc
{
  "tasks": [{
    "id": "T001",
    "title": "과제명", "goal": "목표",
    "category": "품질",              // 소재개발/품질/R&D기술/설비·인프라/조직·인력/수급·SCM/AI·DX/환경/경영현안
    "owner": "", "deadline": "",     // 미입력은 빈 문자열
    "status": "진행중",              // 접수/진행중/완료/보류
    "progress": 0,                   // 0~100
    "created": "2026-08-12", "updated": "2026-08-12",
    "history": [{ "date": "...", "meeting": "...", "note": "...", "status": "...", "progress": 0 }]
  }],
  "info": [{
    "id": "I001",
    "category": "소재",              // 소재/System/운영/인물/기술
    "title": "...", "content": "...", "date": "...", "meeting": "...", "tags": []
  }]
}
```

초기 데이터는 2026.08.12~08.27 회의록 기준 **과제 45건 · 정보 28건 · 진척 이력 51건**입니다.
진척율은 근거가 없는 추정을 넣지 않기 위해 0으로 두었고, 회의록에 "완료"로 명시된
1건만 100입니다. 담당 6건 · 납기 5건도 회의록에 명시된 값만 채워져 있습니다.
