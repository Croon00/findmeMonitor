import os
import json
from config import STATE_FILE
from logger_setup import setup_logger

log = setup_logger()

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        log.info(f"state 없음 -> 새로 시작 (파일: {STATE_FILE})")
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"state 로드 완료: {len(data)}개")
        return data
    except Exception as e:
        log.exception(f"state 로드 실패: {e}")
        return {}

def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log.info(f"state 저장 완료: {len(state)}개 (파일: {STATE_FILE})")
    except Exception as e:
        log.exception(f"state 저장 실패: {e}")