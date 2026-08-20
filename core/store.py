"""
core/store.py
──────────────
GitHub 저장소를 단일 소스로 삼는 경량 JSON 저장소.
로컬 파일은 캐시 겸 GitHub 미설정 환경(로컬 개발) 폴백으로 사용한다.
app.py(Streamlit)와 generate_report.py(GitHub Actions)가 함께 사용한다.
"""
import json
import logging
import os

from github import Github

logger = logging.getLogger(__name__)


def _get_repo(github_token, repo_name):
    return Github(github_token).get_repo(repo_name)


def read_json(filename, default, github_token=None, repo_name=None):
    if github_token and repo_name:
        try:
            repo = _get_repo(github_token, repo_name)
            contents = repo.get_contents(filename)
            return json.loads(contents.decoded_content.decode("utf-8"))
        except Exception as e:
            logger.warning(f"GitHub 읽기 실패 [{filename}]: {e}")
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"로컬 읽기 실패 [{filename}]: {e}")
    return default


def write_json(filename, data, github_token=None, repo_name=None):
    content_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content_str)
    except Exception as e:
        logger.warning(f"로컬 저장 실패 [{filename}]: {e}")

    if not (github_token and repo_name):
        return False
    try:
        repo = _get_repo(github_token, repo_name)
        try:
            existing = repo.get_contents(filename)
            repo.update_file(existing.path, f"[Auto] Update {filename}", content_str, existing.sha)
        except Exception:
            repo.create_file(filename, f"[Auto] Create {filename}", content_str)
        return True
    except Exception as e:
        logger.warning(f"GitHub 저장 실패 [{filename}]: {e}")
        return False
