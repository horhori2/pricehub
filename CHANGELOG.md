# Changelog

이 프로젝트의 주요 변경사항을 버전별로 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따릅니다.

## [0.7.2] - 2026-07-24

### Changed
- 등록용 스마트스토어 엑셀 파일 교체 (`_102905.xlsx` → `_105530.xlsx`,
  이미지 URL 포함된 최신본).

## [0.7.1] - 2026-07-24

### Added
- `스마트스토어상품_20260724_102905.xlsx` — `import_cards_from_excel.py`로
  서버에서도 원피스(EB03 "두웅") 카드를 등록할 수 있도록 원본 엑셀 파일을
  저장소에 포함.

## [0.7.0] - 2026-07-24

### Added
- `import_cards_from_excel.py`가 포켓몬 외 **원피스(OPC) 상품코드도 처리**하도록
  게임 종류(상품코드 접두사) 분기 추가. 원피스는 상품코드의 확장팩 표기(`EB03`)와
  DB `OnePieceExpansion.code` 표기(`EBK-03`)가 달라 직접 매칭이 안 되므로, 같은
  접두사를 쓰는 기존 카드를 찾아 그 확장팩을 그대로 사용하는 방식으로 해결.
  상품명도 상품코드로 이미 알고 있는 `{확장팩코드}-{카드번호}` 마커를 기준으로
  카드명/레어도를 분리 파싱.
- `OnePieceCard` 레어도에 `D`(카드번호 없이 덱 동봉되는 "두웅" 굿즈)와
  `P-D`(그 패러렐) 추가.

### Known Issues
- 디지몬(DGM) 상품코드는 이번 분기에서 아직 미지원 — 확장팩 접두사만으로는
  실제 확장팩을 안전하게 추론할 수 없는 상태라 별도 작업 필요.

## [0.6.7] - 2026-07-23

### Fixed
- `scripts/` 하위 폴더로 운영 스크립트를 정리하면서(0.6.3) 깨졌던
  `ModuleNotFoundError: No module named 'config'` — 스크립트가 두 단계
  깊이(`scripts/<분류>/*.py`)로 이동해 프로젝트 루트가 더 이상 `sys.path`에
  자동으로 잡히지 않던 것. `django.setup()` 이전에 프로젝트 루트를
  `sys.path`에 추가하도록 `django.setup()`을 쓰는 스크립트 21개 전체에
  동일하게 적용.

## [0.6.6] - 2026-07-23

### Added
- `PRICEHUB_API.md` — 다른 프로젝트가 pricehub 가격 API를 참고할 수 있는
  독립 마크다운 레퍼런스. Base URL, 인증, 게임별 엔드포인트, 카탈로그/가격
  응답 예시, pricesite의 실제 소비 패턴(카탈로그 로컬 캐싱 + 가격 실시간
  호출)까지 정리.

### Changed
- `/api-docs/` 페이지에 빠져 있던 포켓몬 일본판·디지몬 한글판 섹션과,
  4개 게임 전체의 가격 스냅샷·가격 이력 엔드포인트 문서를 추가해서 최신화.

## [0.6.5] - 2026-07-23

### Fixed
- 가격 상승 대기 페이지(`bulk_rise.html`)에서 수정 가격을 직접 입력해도
  입력창 색이 "이전 판매가 유지" 상태와 똑같이 표시되던 버그 — 하락 페이지
  쪽에서 복사할 때 편집 상태 분기(`--trend-down`)가 실수로 `--trend-up`으로
  잘못 복붙됐던 것. 이번에 템플릿을 통합하면서 자연스럽게 정상화됨.

### Changed
- **`bulk_drop.html`/`bulk_rise.html` 템플릿(각 380줄 내외)과 뷰
  (`_bulk_drop_view`/`_bulk_rise_view`, 각 107줄)를 하나로 통합.** 로직이
  하락/상승 방향(비교식·부호·아이콘)만 다르고 나머지는 거의 동일했음 —
  `dashboard/bulk_trend.html` 템플릿 하나 + `_bulk_trend_view(request,
  cfg_key, trend)` 공용 뷰로 합치고, 기존 `_bulk_drop_view`/`_bulk_rise_view`는
  얇은 래퍼로 남겨 URL 라우팅은 그대로 유지. 뷰 컨텍스트 키도
  `drop_cards`/`rise_cards`, `avg_drop_pct`/`avg_rise_pct` 등으로 갈라져
  있던 걸 `items`, `avg_pct` 등으로 일반화.

## [0.6.4] - 2026-07-23

### Changed
- `bulk_price.html`(우선순위 자동완성)과 `shop_stats.html`에 거의 동일한
  "우선순위 입력창 채우기/하이라이트/삭제" JS가 이름만 다르게
  (`addToPriority`/`addShopToPriority` 등) 각각 구현돼 있던 걸 하나로
  통합. 페이지별 차이(스크롤 여부, 삭제 시 localStorage 자동저장 여부)는
  옵션 파라미터로 유지.

## [0.6.3] - 2026-07-23

### Fixed
- **카드 목록 페이지 "판매가 초기화" 버튼이 동작하지 않던 버그** —
  `dashboard.js`에 `showResetModal`이라는 이름의 함수가 두 번 정의돼 있어서
  (카드 목록용: 인자 없음, 확장팩 목록용: `(code, name)`) 나중에 정의된
  쪽이 항상 앞의 정의를 덮어썼음. 카드 목록 페이지에서 버튼을 누르면
  "undefined의 모든 카드..." 메시지가 뜨고 확인 시 `RESET_URL_PREFIX`
  미정의로 JS 에러가 나며 아무 것도 초기화되지 않았음. 카드 목록용 함수를
  `showResetThisExpansionModal`로 이름을 분리해서 해결.

### Changed
- 어디서도 참조되지 않던 `pricehub/templates/dashboard/_pre_consolidation_backup/`
  (예전 리팩터링 잔여물 템플릿 4개) 삭제.
- 포켓몬 일본판 "출처×등급별 최신 가격" 집계 로직이 관리자 상세 페이지
  (`views.py`)와 공개 API(`api_views.py`)에 각각 따로 구현돼 있던 걸
  `_jp_latest_prices()` 공용 헬퍼로 통합.

## [0.6.2] - 2026-07-23

### Changed
- **루트에 흩어져 있던 운영 스크립트 25개를 `scripts/` 하위 목적별 폴더로 정리**
  (`collect/` 가격 수집, `japan_sync/` 일본판 export·import, `catalog/` 신작
  카드 크롤링, `maintenance/` 이미지·엑셀 업데이트, `cleanup/` 데이터 초기화,
  `archive/` 완료된 1회성 스크립트). 스크립트 내부 로직은 그대로, 위치만
  이동(`git mv`로 히스토리 보존) — `run_collect_*.sh`가 부르는 경로만 함께
  수정해서 서버 crontab은 변경 불필요.

## [0.6.1] - 2026-07-23

### Added
- 커스텀 404/500 에러 페이지 — DEBUG=False일 때 노출되던 빈 기본 페이지 대신
  다크 테마의 안내 페이지 표시 (`pricehub/templates/404.html`, `500.html`).
- `robots.txt` — 공개 가격 검색 사이트(`/prices/`)만 크롤링 허용, 나머지
  (관리자/API)는 전부 비공개 처리.
- pricesite 테스트 코드 20개 추가 — 뷰(카탈로그 조회, 가격 API 연동, 읽기
  전용 강제), api_client 캐싱, sync_catalog 커맨드의 upsert/정리 로직 검증.
  지금까지 pricesite 쪽엔 테스트가 전혀 없었음.

## [0.6.0] - 2026-07-23

### Added
- **DB 백업 cron 스크립트** (`run_db_backup.sh`) — mysqldump로 매일 전체
  백업 후 gzip 압축, 14일 넘은 백업은 자동 삭제. 지금까지 백업이 전혀
  없어서 서버 장애 시 전체 데이터 유실 위험이 있었음.
- **pricesite 가격 응답 캐싱** — 카드 상세 페이지의 price-snapshot/
  price-history 응답을 10분간 캐시(기존 rate limit용 FileBasedCache
  재사용). 가격은 하루 1번만 갱신되므로 신선도 손해는 거의 없이, 트래픽/
  봇이 몰릴 때 pricehub API·DB에 가는 부하를 크게 줄임.
- **관리자 로그인 무차별 대입 방어** — 같은 아이디로 15분 내 5회 이상
  로그인 실패하면 일시 차단. IP가 아니라 시도한 아이디 기준으로 잠가서
  (nginx가 클라이언트 IP를 제대로 넘겨주는지 확인 안 된 상태라) 리버스
  프록시 설정과 무관하게 안전하게 동작함.

## [0.5.4] - 2026-07-23

### Added
- `run_sync_catalog.sh` — pricesite 카탈로그 동기화용 cron 래퍼 스크립트
  (기존 `run_collect_*.sh`와 동일한 형식). 가격 수집이 다 끝난 뒤 돌아야
  그날 수집된 시장가가 카탈로그 캐시에 반영되므로, 마지막 가격 수집
  cron(04:00 디지몬) 이후 시간대에 등록.

## [0.5.3] - 2026-07-23

### Fixed
- `sync_catalog`의 확장팩별 카드 조회 API 타임아웃(15초)이 카드 수가 많은
  확장팩에서 실제 서버 환경(느린 인스턴스)에 부족했던 문제 — 사용자 응답이
  아니라 백그라운드 동기화라 완주가 더 중요하므로 60초로 상향.

## [0.5.2] - 2026-07-23

### Fixed
- 포켓몬 한글판 카드 목록/검색/상세 API가 "최신 가격" 하나를 계산하려고
  카드당 가격 이력 전체(수백 건, raw_data 포함)를 prefetch하고 있던 성능
  버그 수정 — 카드당 최신 1건만 인덱스(`card`, `-collected_at`)로 조회하도록
  변경. 확장팩 전체 순회 시(예: `sync_catalog`, 외부 카드관리프로그램) 매우
  느렸던 원인이었음. 로컬 벤치마크 기준 확장팩 64개 전체 직렬화가 약 21초
  → 9.5초로 개선.

## [0.5.1] - 2026-07-23

### Fixed
- pricesite 카드 상세 페이지의 판매처 목록이 항목 수(0~20개+)에 따라
  페이지 전체 높이가 들쭉날쭉해지고, 많을 땐 페이지를 쭉 내려야 하는
  문제 — 목록에 최대 높이(560px) + 내부 스크롤을 적용해 판매처가
  많아도 페이지 레이아웃이 늘어나지 않도록 함.

## [0.5.0] - 2026-07-23

### Added
- **pricesite를 pricehub DB 직접 조회 → REST API 기반 구조로 전환.**
  pricesite가 나중에 별도 프로젝트/도메인으로 분리될 것을 염두에 두고,
  더 이상 `pricehub.models`를 직접 import하지 않는다. 확장팩/카드 메타
  데이터(이름·레어도·이미지 등, 신규 세트 발매 때만 바뀌는 정적 데이터)는
  새 관리 커맨드 `sync_catalog`가 pricehub API를 통해 주기적으로 로컬
  캐시(`pricesite` 앱의 신규 Expansion/Card 모델)에 채워두고, 목록·검색·
  필터·페이지네이션은 이 로컬 캐시로 빠르게 처리한다. 반대로 매일 갱신
  되는 핵심 가격 정보(판매처별 가격 분포, 가격 변화 이력)는 절대 로컬에
  중복 저장하지 않고 카드 상세 페이지에서 매 요청마다 pricehub API를
  실시간으로 호출해서 보여준다(`pricesite/api_client.py`). pricehub API에
  없던 포켓몬 일본판 엔드포인트 및 게임별 가격 스냅샷/이력 엔드포인트를
  새로 추가했고, API 호출은 서버 간 API Key로 인증(공개 사용자에게는
  노출되지 않음). pricehub가 앞으로 다른 사이트에도 API로 정보를 제공할
  수 있도록 하는 기반이기도 함.

## [0.4.0] - 2026-07-23

### Added
- **일반 사용자용 가격 검색 사이트 신설** (`/prices/`). 완전 공개(로그인
  불필요), 읽기 전용 — 관리자 대시보드는 카드 목록에 판매가 수정 입력창이
  항상 있어 공개하기 위험했음. 새 Django 앱 `pricesite`로 분리해서 쓰기
  기능을 아예 포함하지 않음(모든 뷰에 `@require_GET`, POST는 405).
  홈(게임 선택) → 확장팩 목록 → 카드 목록(검색/레어도 필터) → 카드 상세
  (판매처별 가격 분포, 판매처 목록, 1주/1개월/1년 가격 변화 그래프)
  4단계 구성. 판매가 설정 UI는 전혀 없음. 관리자 대시보드와 같은 다크
  테마(dashboard.css/js) 재사용, 카드 상세의 가격 변화 그래프는 최근에
  만든 컴포넌트를 그대로 재사용. 추후 별도 프로젝트/도메인으로 분리할
  것을 염두에 두고 pricehub 앱과의 결합은 모델 + 순수 조회 헬퍼로 최소화.

## [0.3.15] - 2026-07-22

### Changed
- 매입리스트 관리 페이지 — 게임별로 리스트가 쌓일수록(주기적으로 새
  리스트를 만들거나 게임 종류가 늘수록) 화면이 길어지던 문제 개선.
  이제 게임당 가장 최근 리스트만 "최신" 배지와 함께 상단에 바로 보여주고,
  나머지는 "이전 리스트 보기 (N개)"로 접어둠(클릭하면 펼쳐짐).

## [0.3.14] - 2026-07-22

### Fixed
- 매입리스트 상세 화면 레이아웃 안정성 개선.
  - 검색 결과 영역이 검색 전엔 접혀있다가 검색하면 갑자기 펼쳐지면서
    아래 등록 카드 목록이 훅 내려가던 문제 — 검색 전에도 고정 높이(320px,
    내부 스크롤)로 미리 공간을 확보해두도록 변경.
  - 카드를 추가하면 페이지 전체를 새로고침해서 검색 결과 그리드가
    사라지던 문제 — 이제 새로고침 없이 등록 카드 목록에 행만 추가하고
    검색 그리드의 해당 카드에 "추가됨" 표시만 남김(카드 삭제도 동일하게
    새로고침 없이 처리).

## [0.3.13] - 2026-07-22

### Changed
- 매입리스트 상세 화면 재설계. 등록/미등록 전체 카드를 필터+페이지네이션으로
  보여주던 큰 목록 테이블을 제거 — 실제로는 인기 카드만 검색해서 등록하는
  용도라 불필요했음. 대신 검색 결과를 작은 드롭다운 목록 대신 페이지 폭의
  큰 이미지 카드 그리드로 보여주도록 개편(카드번호/썸네일 34px → 160px).
  같은 이름인데 이미지(확장팩)가 다른 카드가 많아(예: "카르본" 19장) 작은
  텍스트 목록보다 큰 이미지로 확인하는 게 중요했음. 검색 결과도 이름순
  정렬해 동명 카드끼리 모아서 비교하기 쉽게 함, 결과 수도 20 → 60으로 확대.
  매입리스트에 담긴(등록된) 카드 목록은 기존처럼 표로 유지.

## [0.3.12] - 2026-07-22

### Fixed
- 매입리스트 관리 페이지 상단 바 일관성 수정. 다른 모든 페이지는 왼쪽에
  뒤로가기+현재 위치, 오른쪽에 로그아웃만 두는데 이 페이지만 로고 스타일
  제목을 쓰면서 뒤로가기를 로그아웃 옆(오른쪽)에 배치하고 있었음. 다른
  페이지와 동일한 배치(왼쪽 뒤로가기)로 통일. 나머지 페이지는 점검 결과
  이미 일관돼 있어 변경 없음.

## [0.3.11] - 2026-07-22

### Fixed
- 정적 파일(`dashboard.css`/`dashboard.js`/`login.css`) 캐시 무효화 추가 —
  배포해도 브라우저가 예전 버전을 계속 쓰는 바람에 화면이 깨져 보이는
  문제가 있었음(실제로 그래프 기능 배포 직후 발생). 새 템플릿 태그
  `{% static_v %}`(`pricehub/templatetags/cache_bust.py`)가 파일 수정
  시각을 `?v=` 쿼리스트링으로 붙여서, 파일이 바뀌면 URL도 바뀌어 브라우저가
  새로 받아가게 함. `git pull`로 파일이 갱신되면 mtime도 같이 바뀌므로
  배포 때마다 자동 적용됨 — 별도 조치 불필요. 정적 파일을 쓰는 템플릿
  15개 전체 적용.

## [0.3.10] - 2026-07-22

### Fixed
- 일본판 카드 상세 페이지의 "출처별 최신 가격" 목록이 스타일 없이 텍스트만
  줄줄이 나열되던 문제 수정 — 템플릿이 쓰는 `.jp-price-grid`/`.jp-price-item`
  등 클래스가 `dashboard.css`에 정의된 적이 없었음(`.badge-mirror`도 동일).
  카드형 그리드 레이아웃 추가, 등급(S/A-/B/C)별로 금·은·동 톤 배지 색상
  적용(레어도 고정가 기능에서 쓰던 `--rank-silver`/`--rank-bronze` 토큰 재사용).

## [0.3.9] - 2026-07-22

### Added
- 카드/확장팩 이미지 로드 실패 시 브라우저 기본 "깨진 이미지" 아이콘 대신
  🃏 플레이스홀더로 자동 대체(`cardImgFallback()`). 포켓몬코리아 등 외부
  이미지 서버 장애 시에도 화면이 깨져 보이지 않도록 함. 카드 이미지가
  나오는 모든 화면(카드 상세/목록, 확장팩 목록, 하락·상승·미설정·저가경고
  목록, 검색 결과, 일괄검증, 매입리스트)에 적용.

## [0.3.8] - 2026-07-22

### Fixed
- 가격 변화 그래프 날짜 라벨에서 시:분 제거 — 한글판 1주 구간만 `MM/DD HH:MM`
  형식이라 1개월/1년(`MM/DD`)과 형식이 달랐음. 시각은 의미가 없고 날짜만
  중요하므로 전체 구간을 `MM/DD`로 통일(일본판은 이미 날짜만 쓰고 있었음).

## [0.3.7] - 2026-07-22

### Added
- 포켓몬 일본판 카드 상세 페이지에도 가격 변화 그래프 추가 — 한글판과
  동일하게 페이지 최상단에 배치, 1주/1개월/1년 전환 지원. 일본판은
  `JapanCardPrice`가 출처/등급/가격을 바로 필드로 갖고 있어(한글판의
  raw_data 파싱 불필요) 출처+등급 조합(예: "카드러쉬 A-급")별로 선을
  그림 — 각 출처가 서로 다른 시각에 수집될 수 있어 날짜(일) 단위로
  묶어서 정렬. 그래프 컴포넌트(dashboard.js)는 한글판과 동일한 것을
  재사용.

## [0.3.6] - 2026-07-22

### Changed
- 카드 상세 페이지(포켓몬/원피스/디지몬 한글판) 레이아웃 개편 — 가격 변화
  그래프를 페이지 최상단으로 이동해 판매처 목록이 길어도 스크롤 없이 바로
  보이도록 함. 판매처별 가격 분포·판매처 목록은 그 아래 기존 2단 레이아웃
  유지.

### Added
- 가격 변화 그래프에 **1주/1개월/1년** 기간 전환 버튼 추가. 1주치는 페이지
  로드 시 함께 내려받고, 1개월/1년은 클릭 시 새 API
  (`/pokemon/kr/cards/<id>/price-history/?range=`)로 조회(캐싱해서 같은
  기간 재클릭 시 재요청 안 함). 그래프 데이터는 판매처명+가격만 담은 경량
  포맷으로 바꿔 1년치도 가볍게 조회되도록 함(제목/이미지/링크 등은 최신
  스냅샷에만 필요해 제외). 점이 많은 구간(1개월/1년)은 포인트 마커를 숨겨
  선이 지저분해지지 않게 함.

## [0.3.5] - 2026-07-22

### Added
- `/api-docs/`에 매입리스트 API 문서화 — 목록/상세/카드 목록/상품코드 매입가
  조회(lookup) 4개 엔드포인트. 파라미터, 실제 응답 예시(페이지네이션 미적용
  확인), 오류 케이스 포함. 이전 버전에서 "Known Issues"로 남겨뒀던 문서 공백
  해소.

## [0.3.4] - 2026-07-22

### Added
- 오프라인 매장 연동용 매입가 조회 API 추가:
  `GET /api/purchase-lists/lookup/?game_type=<>&shop_product_code=<>`.
  기존 매입리스트 API는 개별 등록된 카드만 조회 가능했는데, 실제로는
  매장에서 스캔하는 아무 카드나(인기 카드든 일반 카드든) 매입가를 받아야
  해서 신설. 조회 순서: ① 해당 게임에서 가장 최근에 만든 활성 매입리스트에
  개별 등록돼 있으면 그 확정/추천가, ② 없으면 레어도별 매입 고정가
  (설정된 경우, 일본판 제외), ③ 둘 다 없으면 null. API Key 인증 필요
  (기존 카드 조회 API와 동일한 방식).

### Known Issues
- 매입리스트 관련 API(list/detail/items/lookup)가 `/api-docs/` 문서
  페이지에 아직 반영 안 됨 — 별도 작업 필요.

## [0.3.3] - 2026-07-22

### Added
- 매입리스트 복사 기능. 매입리스트 관리 화면의 각 리스트 행에 "복사" 버튼을
  추가 — 담긴 카드와 매입가(확정가/추천가 포함)를 그대로 복사한 새 리스트를
  만든다. 매입 주기마다 이전 리스트를 시작점으로 필요한 카드만 조정하는
  용도.

## [0.3.2] - 2026-07-22

### Fixed
- 포켓몬 일본판 카드 상세 페이지(`/pokemon/jp/cards/<id>/`) 500 에러 수정.
  `card_detail.html`은 이미 일본판까지 지원하도록 만들어져 있었는데,
  `pokemon_jp_card_detail` 뷰가 존재하지 않는 `card_detail_jp.html`을
  가리키고 있었고 `card_type` 컨텍스트도 빠져있었음(리팩토링 중 남은
  이전 세션에서 발견된 미해결 이슈). 올바른 템플릿 + `card_type='pokemon_jp'`로
  수정. 가격 이력 없는 카드/미러 카드 포함해 재검증 완료.

## [0.3.1] - 2026-07-22

### Changed
- 레어도별 일괄 매입가를 "시장 최저가 × 비율(%)" 계산 방식에서 레어도별
  **고정 금액**으로 변경(아직 배포 전인 0.3.0 기능 수정). `RarityPurchaseRatio`
  → `RarityPurchasePrice`로 모델명 변경, 관리 화면 경로도
  `/purchase-lists/rarity-ratios/` → `/purchase-lists/rarity-prices/`로 변경.
  시장가 유무와 무관하게 레어도만으로 고정가가 정해짐.

## [0.3.0] - 2026-07-22

### Added
- **레어도별 일괄 매입가**: 매입리스트에 모든 카드를 개별 등록할 수 없는 문제 해결.
  인기 카드만 개별 등록해 매입가를 정하고, 나머지 카드는 게임 종류별로 설정한
  "레어도 → 비율(%)"를 시장 최저가에 곱해 화면에서 즉석 계산해 보여줌(DB에
  별도 행을 만들지 않음). 새 관리 화면(`/purchase-lists/rarity-ratios/<game_type>/`)에서
  레어도별 비율 설정. 일본판은 판매가가 엔화라 통화 단위가 달라 대상에서 제외
  (포켓몬/원피스/디지몬 한글판만 지원).
- 매입리스트 상세 화면을 "개별 등록한 카드만" 보여주던 것에서, 등록/미등록
  카드를 확장팩·레어도 필터 + 페이지네이션과 함께 한 화면에서 보도록 개편.
  미등록 카드는 "개별 등록" 버튼으로 바로 승격 가능.

## [0.2.14] - 2026-07-22

### Added
- `CLAUDE.md`에 "배포 환경 (서버)" 섹션 추가 — 오늘 서버 점검하며 확인한
  구성(pm2/gunicorn -w 4/nginx, 아직 HTTP 전용이라 USE_HTTPS 켜면 안 됨,
  staticfiles/django_cache/logs는 git 추적 안 함, 배포 절차)을 문서화.

## [0.2.13] - 2026-07-22

### Fixed
- API Key rate limit이 gunicorn 워커별로(운영 중 `-w 4`) 따로 카운트되던
  문제 수정 — 기본 `LocMemCache`가 프로세스 로컬이라 설정한 한도(예:
  300/min)가 실제로는 워커 수만큼(최대 4배) 새고 있었음. Redis 없이
  `FileBasedCache`(`django_cache/`)로 교체해 워커 간 카운트를 공유하도록
  수정. 별도 프로세스 두 개로 캐시 쓰기/읽기가 실제로 공유되는지 확인함.

## [0.2.12] - 2026-07-22

### Fixed
- `staticfiles/`(collectstatic 산출물, Django 관리자 페이지 기본 CSS/JS 128개
  포함)가 git에 그대로 추적되고 있던 문제 수정. 서버에서 `collectstatic` 돌릴
  때마다 이 파일들이 "수정됨"으로 떠서 `git status`/`git pull`을 방해하고
  있었음. `.gitignore`에 추가하고 git 추적에서 제거(로컬 파일 자체는 유지 —
  다음 `collectstatic` 실행 시 정상적으로 다시 채워짐).

## [0.2.11] - 2026-07-22

### Added
- `requirements.txt`에 운영 WSGI 서버 `gunicorn` 추가 — 지금까지 프로덕션
  서버 구성요소가 requirements.txt에 없었음. 서버에 이미 다른 버전이 떠
  있다면 그 버전에 맞춰 조정 필요.

## [0.2.10] - 2026-07-22

### Security
- 로컬 `.env.local`의 `SECRET_KEY`가 과거 git 히스토리(2026-01)에 평문으로
  커밋된 적이 있는 값과 동일해서 새 값으로 교체(파일 자체는 `.gitignore` 대상이라
  이번 커밋엔 포함 안 됨). 운영 서버 `.env`도 같은 값을 쓰고 있었다면 반드시
  교체 필요 — git 히스토리 자체에서 지우려면 별도의 history rewrite가 필요하며
  이건 원격 force-push가 필요한 작업이라 진행 전 확인 필요.

### Added
- 운영 환경(`DEBUG=False`) 에러 로깅 추가. 기존엔 `ADMINS` 설정이 없어서 500
  에러가 콘솔에도 파일에도 안 남고 그냥 사라졌음 — `logs/django.log`에 10MB
  단위로 로테이션되는 파일 핸들러 추가(`django`/`django.request` 로거,
  WARNING 이상). `*.log`는 이미 `.gitignore` 대상.

## [0.2.9] - 2026-07-22

### Fixed
- `dashboard.css`에 같은 클래스가 두 번 정의되어 있어(파일 뒤쪽 규칙이 조용히
  이기는 구조) 의도와 다르게 렌더링되던 항목 정리: `.page-sub`(부제 크기/여백),
  `.section`(card_detail 패널), `.progress-bar`류(확장팩 진행률 바),
  `.price-cancel-btn`(인라인 가격취소 버튼 — 유일하게 실제 화면이 바뀜: 알약
  버튼 → 원래 의도한 테두리 없는 "×" 아이콘으로 복원).

### Changed
- 순위 뱃지(1/2/3위 최저가 샵) 색상을 `card_detail.html`(`.rank-1~3`)과
  `bulk_price.html` 랭킹 테이블(`.r1~3`)에서 공유하도록 통합.
  `--rank-silver`/`--rank-bronze` 토큰 추가, 금색 배경도 `--warning` 실제
  RGB와 맞춤 — 두 화면에서 미묘하게 다르게 보이던 색을 통일.

## [0.2.8] - 2026-07-22

### Fixed
- 비동기로 옮긴 뒤에도 저가 경고 관련 집계가 여전히 느리던 근본 원인 수정.
  `_underpriced_count`/`_card_list_view`/`_underpriced_view`가 카드마다
  `card_price` 히스토리 테이블을 서브쿼리로 뒤지는 구조라, 히스토리가
  쌓일수록 계속 느려지는 문제였음. `Card`/`OnePieceCard`/`DigimonCard`에
  `latest_market_price` 캐시 컬럼을 추가해 가격 수집 시(`collect_*_prices.py`)
  갱신하도록 하고, 위 3개 조회 지점 모두 히스토리 서브쿼리 대신 이 캐시
  컬럼을 직접 필터링/정렬하도록 교체. 기존 데이터는 데이터 마이그레이션으로
  최근 수집 가격 기준 백필.

## [0.2.7] - 2026-07-21

### Fixed
- 일괄 판매가 설정 페이지(`/pokemon/kr/bulk-price/` 등)도 확장팩 목록과 같은 문제로
  느렸음 — `needs_review`(하락/상승/신규 대기 합계)와 `underpriced_pending`을
  페이지 렌더링 전에 동기로 계산하고 있었음. 이미 비동기로 불러오던
  `bulk-price/stats/` 엔드포인트(샵 통계용)에 같이 얹어서, 페이지는 먼저 뜨고
  "점검이 필요한 카드"/"저가 경고" 배너는 나중에 채워지도록 함. 배너는 카운트가
  0보다 클 때만 표시(기존과 동일한 동작).

## [0.2.6] - 2026-07-21

### Fixed
- 확장팩 목록 페이지가 N+1 쿼리를 고쳤는데도 여전히 느리던 문제 추가 수정.
  "가격 하락 대기"/"저가 경고" 카운트가 카드 가격 히스토리 전체를 훑는 무거운
  집계라(특히 `_underpriced_count`의 카드별 최신가 서브쿼리는 `card_price`
  테이블이 쌓일수록 느려짐) 페이지 렌더링을 막고 있었음. 이제 확장팩
  목록·전체 카드 수·판매가 미설정 수(전부 가벼운 단일 쿼리)만 즉시 렌더링하고,
  하락 대기/저가 경고 카운트는 `expansions/stats/` 엔드포인트로 분리해서
  페이지가 뜬 뒤 비동기로 채움(뱃지에 "···" 표시 후 도착하면 채워짐).

## [0.2.5] - 2026-07-21

### Fixed
- 확장팩 목록 페이지(`/pokemon/kr/expansions/` 등)가 확장팩이 늘어날수록 점점 느려지던 문제 수정.
  확장팩마다 `e.cards.count()` / `e.cards.filter(selling_price=0).count()`를 반복 호출하는
  N+1 쿼리였음(확장팩 80개면 쿼리 160개+). `Count(..., filter=Q(...))` 어노테이션으로
  단일 쿼리(LEFT JOIN + GROUP BY)로 교체. 포켓몬/원피스/디지몬 한글판·포켓몬 일본판
  확장팩 목록 전부 이 함수를 공유해서 한 번에 적용됨.

## [0.2.4] - 2026-07-21

디자인 시스템 정리 3차 — 레거시 버튼 클래스를 .btn 시스템으로 통합.

### Changed
- `back-btn`/`logout-btn`/`quick-btn`/`quick-chip-btn`/`again-btn`/`action-btn`/`rank-filter-btn`/
  `filter-btn`/`inline-tab`/`set-btn`/`issue-save-btn`/`pg-btn`/`pg-num`(고스트 계열),
  `bulk-btn`/`reset-btn`/`exp-reset-btn`/`fav-tab-btn`/`action-btn.success`(틴트 계열),
  `save-btn`/`search-btn`/`modal-confirm`(솔리드 계열) — 총 20개 레거시 버튼 클래스를
  그룹 셀렉터로 `.btn-ghost`/`.btn-soft`/`.btn-solid`에 합류시켜 CSS 선언을 한 곳으로 모음.
  마크업(템플릿 class=)은 전혀 안 건드림 — 클래스 이름은 그대로, CSS 내부 선언만 정리.
  `.run-btn`/`.revert-btn`/`.star-toggle`/`.modal-cancel` 등 호버 효과가 이미 있거나
  구조가 근본적으로 다른 것들은 대상에서 제외.

  **일관성을 위해 의도적으로 통일한 작은 시각적 차이**(기능/레이아웃 영향 없음, 호버 색상 수준):
  - `back-btn`/`again-btn`/`quick-chip-btn`의 호버 색이 제각각(`--accent`+`--text` 등)이던 걸 `--accent2`로 통일
  - `logout-btn`에 없던 호버 피드백 추가
  - `issue-save-btn`/`pg-btn`/`pg-num`에 호버 시 배경 틴트 추가(`set-btn`엔 이미 있었음)
  - `exp-reset-btn`의 틴트 alpha를 `reset-btn`과 동일하게 정규화(0.06/0.15 → 0.08/0.18)
  - `save-btn`/`search-btn`/`modal-confirm`의 호버를 `filter: brightness(1.1)`로 통일
    (기존: `brightness(1.15)`, 하드코딩 `#6b5aee`, `opacity(0.85)` 각각 달랐음)

## [0.2.3] - 2026-07-21

디자인 시스템 정리 2차 — 버튼 컴포넌트 베이스 추가.

### Added
- `dashboard.css`에 `.btn` 베이스 + 변형 클래스(`.btn-ghost`/`.btn-soft`/`.btn-solid`,
  `.btn-danger`/`.btn-success`/`.btn-favorite`, `.btn-sm`/`.btn-lg`) 추가.
  기존 21개 "-btn" 레거시 클래스를 하나하나 대조해보니 호버 색상 등이 미묘하게
  제각각이라(예: `.action-btn`은 호버 시 `--accent2`, `.back-btn`은 `--accent`+`--text`)
  마크업 없이 그룹 셀렉터로 합치면 시각적 변경이 될 수 있어 이번엔 새 시스템만
  추가하고 기존 클래스는 그대로 둠. 새 버튼은 앞으로 이 `.btn` 시스템을 사용.
  기존 템플릿 마크업은 전혀 변경하지 않아 시각적 영향 없음.

## [0.2.2] - 2026-07-21

디자인 시스템 정리 1차 — 색상 토큰 통합 (시각적 변화 없음, 순수 리팩토링).

### Changed
- `dashboard.css`에 `--trend-down`/`--trend-down-strong`(가격 하락), `--trend-up`/`--trend-up-mid`/`--trend-up-strong`(가격 상승),
  `--favorite`(즐겨찾기) 색상 토큰 추가. 기존 `--danger`/`--success`와 톤이 달라 별도 토큰으로 분리(의미도 다름: 액션 결과 vs 가격 방향).
  `dashboard.css`·`bulk_drop/rise/unpriced/underpriced/price.html`·`card_list.html`에 흩어져 있던 하드코딩 hex(`#e86060`, `#4ade80`, `#ffc700` 등)
  34곳을 전부 토큰 참조로 교체. Chart.js 캔버스 색상은 `var()`가 안정적으로 해석 안 돼서 대상에서 제외.
- `login.css`의 `:root` 색상값을 `dashboard.css`와 동일한 값으로 정렬 — 로그인 전이라 파일은 분리돼 있지만 팔레트는 이제 완전히 동일.
- `bulk_price.html`의 죽은 `var(--danger,#e86060)` fallback을 `var(--danger)`로 정리.

## [0.2.1] - 2026-07-21

### Added
- `CLAUDE.md`에 브랜치 전략 문서화 — `master`는 서버가 pull 받는 최종 release 브랜치,
  `dev`는 로컬 작업/테스트용 브랜치. `dev → master` 병합은 사용자 승인 하에만 진행.
  기존에 방치돼 있던 `develop` 브랜치(로컬/원격, master보다 많이 뒤처진 상태)는 삭제하고
  `master` 기준으로 새 `dev` 브랜치를 생성함.
- 같은 문서에 git 태그 규칙 추가 — 태그는 `dev`에서 커밋할 때마다 달지 않고,
  `master`로 병합해 실제 release가 되는 시점에만 단다.

## [0.2.0] - 2026-07-21

리팩토링 2차 정리 — 게임별 위임 뷰 팩토리화, 판매가 관리 템플릿 4종 공통화, 저가 경고 페이지 인라인 편집 추가.

### Added
- **저가 경고 페이지에서 판매가 바로 수정 가능**: 그동안은 "카드 열기"로 카드 상세 페이지까지 이동해야 판매가를 고칠 수 있었는데, 이제 다른 일괄 관리 페이지(하락 대기/상승 대기)와 동일하게 목록에서 바로 수정 가격을 입력(시장 최저가로 자동 채움)하고 개별/일괄 저장할 수 있다. 행 클릭 시 판매처 목록 사이드패널도 함께 뜬다.

### Changed
- `pricehub/views.py`: `pokemon_kr_bulk_price`처럼 게임(포켓몬/원피스/디지몬 한글판)별로 `cfg_key`만 다르고 나머지는 동일했던 위임 뷰 39개(bulk_* 12종 + card_detail × 3게임)를 `_make_game_view` 팩토리 + `game_views(cfg_key)` 함수로 대체. `urls.py`에서 `**v.game_views('pokemon_kr')`로 병합. 기존 `@staff_required`/`@require_POST` 데코레이터 순서(인증 체크가 바깥쪽)를 그대로 유지해 동작은 완전히 동일. `views.py`+`urls.py` 합쳐서 188줄 감소.
- `pricehub/templates/dashboard/bulk_drop.html`/`bulk_rise.html`/`bulk_unpriced.html`/`bulk_underpriced.html`: 4개 페이지에서 100% 동일했던 헤더·모드탭·확장팩/레어도 필터·페이지네이션을 `templates/dashboard/partials/`의 공용 partial 4개로 분리. 가격 입력/저장/승인 로직 등 페이지마다 실제로 다른 부분(및 실제 판매가에 영향을 주는 부분)은 그대로 각 파일에 남겨둠 — 렌더링 결과가 리팩토링 전후 동일한지 fixture 데이터로 diff 검증함. 리팩토링 전 원본은 `templates/dashboard/_pre_consolidation_backup/`에 보관.

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
