# 주차장 데이터 수집기

GitHub Actions로 30분마다 공공데이터포털 API를 호출해서 `data/parking.csv`에 누적 저장.

## 셋업 (5분이면 끝)

### 1. 새 레포 생성
GitHub에 프라이빗/퍼블릭 레포 만들고 이 파일들 그대로 올리기.

### 2. API 키를 Secrets에 등록
레포 페이지 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`
- Name: `API_KEY`
- Secret: 공공데이터포털에서 받은 일반 인증키 (Encoding 말고 **Decoding** 키 사용)

### 3. `scripts/collect.py` 수정
- `API_URL`: 본인이 신청한 API의 엔드포인트로 변경
- `PARAMS`: API 가이드 문서 참고해서 필요한 파라미터 추가
- `FIELDS_TO_EXTRACT`: 실제 XML 응답에 있는 태그명으로 변경

> **팁**: 공공데이터포털 마이페이지 → 활용신청 현황 → 해당 API → "상세설명"에서 샘플 응답 XML 확인 가능

### 4. 첫 실행 테스트
- `Actions` 탭 → `Collect Parking Data` → `Run workflow` 버튼으로 수동 실행
- 성공하면 `data/parking.csv` 생성됨

### 5. 자동 실행 시작
push만 하면 cron 자동 등록. 30분마다 알아서 돌아감.

## 로컬에서 테스트하기

```bash
pip install requests
export API_KEY="여기에_디코딩된_키"
python scripts/collect.py
```

## 주의사항

- **cron이 정확히 30분마다 안 돌 수 있음**: GitHub 부하에 따라 5~15분 밀림. 그래서 `collected_at` 필드를 같이 저장해둠.
- **60일 무활동 시 cron 비활성화**: 봇 커밋은 활동으로 안 쳐주니, 가끔 README 수정 같은 사람 푸시 한 번씩 해주기.
- **CSV가 너무 커지면**: 1년쯤 쌓이면 수백 MB 갈 수 있음. 그땐 월별 파일로 쪼개거나 Parquet로 바꾸거나 Supabase/S3로 옮기기.
- **API 키 절대 코드에 직접 쓰지 말기**: 반드시 Secrets 사용.

## 파일 구조

```
.
├── .github/workflows/collect.yml   # 30분 cron 워크플로우
├── scripts/collect.py              # 수집 스크립트
├── data/parking.csv                # 누적 데이터 (자동 생성)
└── README.md
```
