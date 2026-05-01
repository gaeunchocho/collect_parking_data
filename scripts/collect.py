"""
부산시설공단 공영주차장 실시간 주차현황 수집 스크립트
- GitHub Actions가 30분마다 실행
- 전체 주차장 데이터를 하나의 CSV에 누적
"""
import csv
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ============================================================
# 설정
# ============================================================
API_URL = "https://apis.data.go.kr/B552587/ParkingInfoService/getParkingInfoList"
API_KEY = os.environ["API_KEY"]  # GitHub Secrets에서 주입됨

PARAMS = {
    "serviceKey": API_KEY,
    "numOfRows": 200,  # 부산시설공단 공영주차장 전체 받기에 충분
    "pageNo": 1,
}

CSV_PATH = Path("data/parking.csv")
KST = timezone(timedelta(hours=9))

# CSV 컬럼 (한글 헤더로 분석 시 편의성 ↑)
CSV_COLUMNS = [
    "수집시각",
    "주차장코드",
    "주차장명",
    "총주차면",
    "현재주차대수",
    "잔여면수",
    "점유율",
    "최종업데이트",
]


def fetch_xml() -> str:
    """API 호출해서 XML 텍스트 받아오기"""
    try:
        resp = requests.get(API_URL, params=PARAMS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)


def parse_items(xml_text: str) -> list[dict]:
    """XML에서 <item> 태그들을 dict 리스트로 변환"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"[ERROR] XML 파싱 실패: {e}", file=sys.stderr)
        print(f"응답 앞부분: {xml_text[:500]}", file=sys.stderr)
        sys.exit(1)

    # 응답 코드 체크
    result_code = root.findtext(".//resultCode")
    if result_code and result_code != "00":
        result_msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        print(f"[ERROR] API 에러 응답: {result_code} - {result_msg}", file=sys.stderr)
        sys.exit(1)

    items = root.findall(".//item")
    if not items:
        print("[WARN] item이 하나도 없음. 응답 앞부분:", file=sys.stderr)
        print(xml_text[:500], file=sys.stderr)
        return []

    collected_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for item in items:
        # 숫자 필드는 안전하게 변환 (None, 빈 문자열 처리)
        try:
            total = int((item.findtext("maxcnt") or "0").strip() or "0")
        except ValueError:
            total = 0
        try:
            cur = int((item.findtext("parkingcnt") or "0").strip() or "0")
        except ValueError:
            cur = 0
        try:
            remain = int((item.findtext("curravacnt") or "0").strip() or "0")
        except ValueError:
            remain = 0

        # 점유율 계산
        occupancy = round(cur / total * 100, 1) if total > 0 else 0.0

        rows.append({
            "수집시각": collected_at,
            "주차장코드": (item.findtext("parkgcd") or "").strip(),
            "주차장명": (item.findtext("parknm") or "").strip(),
            "총주차면": total,
            "현재주차대수": cur,
            "잔여면수": remain,
            "점유율": occupancy,
            "최종업데이트": (item.findtext("lastupdatetime") or "").strip(),
        })

    return rows


def append_to_csv(rows: list[dict]) -> None:
    """CSV에 누적 저장. 파일 없으면 헤더부터 생성"""
    if not rows:
        print("[INFO] 저장할 데이터 없음")
        return

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists()

    # utf-8-sig: 엑셀에서 한글 안 깨지게
    with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] {len(rows)}개 주차장 데이터 추가됨 → {CSV_PATH}")


def main():
    print(f"[START] 수집 시작 - {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} KST")
    xml_text = fetch_xml()
    rows = parse_items(xml_text)
    append_to_csv(rows)
    print("[END] 수집 완료")


if __name__ == "__main__":
    main()
