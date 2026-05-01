"""
공공데이터포털 주차장 데이터 수집 스크립트
- XML 응답을 파싱해서 하나의 CSV에 누적
- 30분마다 GitHub Actions가 실행
"""
import csv
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ============================================================
# 설정 - 본인 API에 맞게 수정하세요
# ============================================================
API_URL = "https://apis.data.go.kr/여기에_본인_엔드포인트"  # TODO: 변경
API_KEY = os.environ["API_KEY"]  # GitHub Secrets에서 주입됨

# API 호출 파라미터 (공공데이터포털 가이드 문서 참고해서 수정)
PARAMS = {
    "serviceKey": API_KEY,
    "pageNo": 1,
    "numOfRows": 1000,
    "type": "xml",
}

# CSV로 저장할 필드 (XML 태그명에 맞춰 수정)
# 예시: 주차장명, 주차구획수, 현재주차차량수 등
FIELDS_TO_EXTRACT = [
    "prkplceNm",      # 주차장명 (예시)
    "prkcmprt",       # 주차구획수
    "curParking",     # 현재 주차 차량 수
    "lat",            # 위도
    "lot",            # 경도
]

CSV_PATH = Path("data/parking.csv")
KST = timezone(timedelta(hours=9))


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

    # 공공데이터포털 표준 응답: response > body > items > item
    items = root.findall(".//item")
    if not items:
        # 에러 메시지일 가능성 체크
        result_msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg")
        if result_msg:
            print(f"[ERROR] API 에러 응답: {result_msg}", file=sys.stderr)
            sys.exit(1)
        print("[WARN] item이 하나도 없음", file=sys.stderr)
        return []

    rows = []
    collected_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    for item in items:
        row = {"collected_at": collected_at}
        for field in FIELDS_TO_EXTRACT:
            row[field] = (item.findtext(field) or "").strip()
        rows.append(row)
    return rows


def append_to_csv(rows: list[dict]) -> None:
    """CSV에 누적 저장. 파일 없으면 헤더부터 생성"""
    if not rows:
        print("저장할 데이터 없음")
        return

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists()
    fieldnames = ["collected_at"] + FIELDS_TO_EXTRACT

    with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] {len(rows)}개 행 추가됨 → {CSV_PATH}")


def main():
    xml_text = fetch_xml()
    rows = parse_items(xml_text)
    append_to_csv(rows)


if __name__ == "__main__":
    main()
