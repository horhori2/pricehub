# Changelog

이 프로젝트의 주요 변경사항을 버전별로 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따릅니다.

## [0.1.2] - 2026-07-21

리팩토링 1차 정리 — 죽은 코드/깨진 스크립트 제거, `card_detail` 뷰 중복 제거.

### Removed
- 1회성 디버깅 스크립트 7개 삭제 (`test_cardrush_crawl.py`, `test_cardrush_expantion_data.py`, `test_filtering_pokemon.py`, `test_mirror_extraction.py`, `test_single_card.py`, `test_time_insert.py`, `test_yuyu_structure.py`). 전부 자동 테스트 러너에 물려있지 않은 print 기반 수동 확인용 스크립트였고, 일부는 실제 필터링 로직(`pricehub/utils.py`)과 이미 어긋나 있었음. 실제 테스트 스위트(`pricehub/tests.py`)는 그대로 유지.
- 존재하지 않는 파이썬 파일(`collect_prices.py`, `collect_tcg999_prices.py`)을 호출하던 죽은 크론 스크립트 3개 삭제 (`run_collect_prices.sh`, `run_all_collections.sh`, `run_collect_tcg999.sh`).
- 어디서도 import되지 않던 고아 모듈 `japan_utils.py` 삭제 (안의 크롤링 로직도 `save_japan_cards_to_db.py`의 실제 로직과 이미 어긋난 상태였음).

### Fixed
- `delete_onepiece_data.py`, `delete_japan_data.py`가 마이그레이션 `0019`에서 이미 삭제된 `OnePieceTargetStorePrice`/`JapanTargetStorePrice` 모델을 import하고 있어 실행하면 바로 `ImportError`가 나던 문제 수정.

### Changed
- `pricehub/views.py`: `pokemon_kr_card_detail`/`onepiece_kr_card_detail`/`digimon_kr_card_detail`에 복붙돼 있던 동일한 로직(~25줄×3)을 `_card_detail_view(request, cfg_key, pk)` 공용 함수로 통합. 이 파일의 다른 뷰들과 동일한 패턴으로 정리됨. 렌더링 컨텍스트는 리팩토링 전후 동일.

### Known Issues
- `test_single_card.py`(이번에 삭제)에 네이버 API 키가 평문으로 박혀 있었고, 이미 GitHub에 푸시된 커밋 히스토리에 남아있음. 파일 삭제만으로는 히스토리에서 지워지지 않으므로 **네이버 개발자센터에서 키 재발급 필요** (별도 조치, 아직 미완료).

## [0.1.1] - 2026-07-21

### Added
- `README.md` 추가 — 지원 게임/카테고리, 주요 기능(가격 자동 수집, 판매가 관리, 저가 경고, 매입리스트, 외부 API 등) 정리.
- `CLAUDE.md` 추가 — 커밋 시 CHANGELOG.md를 갱신하는 작업 지침 명시.

### Fixed
- `requirements.txt`가 실제 사용 중인 의존성(djangorestframework, django-filter, requests, beautifulsoup4, openpyxl, python-dotenv 등)을 누락하고 있던 문제 수정. Django 버전도 실제 설치본(5.2.4)에 맞게 정정 (기존엔 5.2.10으로 잘못 적혀 있었음). 새 가상환경에서 `pip install -r requirements.txt`만으로 서버가 뜨는지 확인 완료.

## [0.1.0] - 2026-07-21

첫 번째 기록 버전. 이 시점부터 버전을 태깅하고 변경사항을 정리합니다.

### Added
- **저가 경고 기능**: 판매가가 시장 최저가보다 낮은 카드를 자동으로 감지.
  - 포켓몬/원피스/디지몬 한글판 각각에 `/bulk-price/underpriced/` 목록 페이지 추가 (일본판은 시장가가 엔화라 통화 단위가 달라 제외).
  - 확장팩 목록 화면에 "🔻 저가 경고" 통계 카드, 일괄 판매가 설정 화면에 경고 배너 추가.
  - 카드 목록 화면에 저가 경고 필터 탭 + 해당 행 강조 표시.

### Fixed
- **시장 최저가 계산에서 자기 매장 누락 수정**: 우리 매장(화성스토어-TCG-, 카드 베이스) 항목이 "시장 최저가" 계산에 섞여 들어가던 문제 수정. 이제 경쟁사 최저가만 시장가로 집계 (경쟁사가 없을 때만 예외적으로 자체 매장가 사용). 판매처 목록 표시용 원본 데이터(raw_data)에는 그대로 우리 매장 항목 유지.

### Security
- **XSS 수정**: 템플릿에 `json.dumps(...) | safe`로 심던 값들이 `<`, `>`, `&`를 이스케이프하지 않아 스크립트 태그를 조기 종료시킬 수 있던 문제 수정 (`safe_json_dumps()` 헬퍼 도입). 네이버 쇼핑 판매자명/상품명뿐 아니라 URL 쿼리스트링(`?rarities=`)을 통한 반사형 XSS 경로도 함께 차단.
- `pokemon_jp_expansion_list` 뷰에 누락돼 있던 로그인 요건(`@staff_required`) 추가.
- **API Key 평문 저장 제거**: `APIKey.key`를 SHA-256 해시로 저장하도록 변경. 기존에 발급된 키는 데이터 마이그레이션으로 자동 전환되며, 클라이언트 쪽 원본 키 값은 그대로 유효.
- Naver 쇼핑 API 호출에 타임아웃(15초) 추가 — 응답이 없을 때 수집 크론이 무한 대기하는 문제 방지.
- 외부 연동 API(Api-Key 인증)에 API Key당 요청 빈도 제한(rate limiting) 추가 — 기본 300회/분, `.env`의 `API_THROTTLE_RATE`로 조절 가능.
- HTTPS 배포용 보안 설정 추가 (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS 등) — `.env`에 `USE_HTTPS=True`로 활성화.
- `/api-docs/` 페이지에 로그인 요건 추가 (기존엔 비로그인 상태에서도 API 구조가 노출됨). 중복 등록돼 있던 라우트도 정리.
- 사용되지 않고 연결도 안 돼 있던 `api_key_auth/` 앱 삭제.

### Known Issues
- `pokemon_jp_card_detail` 뷰가 참조하는 `dashboard/card_detail_jp.html` 템플릿이 없어 일본판 카드 상세 페이지가 500 에러를 반환함 (이번 작업 범위 밖, 별도 확인 필요).
