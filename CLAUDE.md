# CLAUDE.md

Claude Code가 이 저장소에서 작업할 때 따라야 하는 지침.

## 전체 시스템 구조 (연관 레포 4개)

pricehub는 카드 가격·매장 관리 시스템 전체 중 "가격 수집·관리" 축을 담당하는 레포다.
연관 레포는 아래 4개(코드베이스 5개) — 새 기능이 이 경계를 넘나드는 작업이면 항상 이 그림을
먼저 참고해서 방향을 정한다.

| 레포 | 경로 | 역할 | 작업자 |
|---|---|---|---|
| **pricehub** (이 레포) | `12. 자동가격수집기/pricehub` | 개별 카드·가격 정보 수집·관리 — 가격 데이터의 SSOT | 가격 관리자 |
| **price_adjust** | `27.price_adjust_win` | 네이버 쇼핑 오픈API 종료로 수동 수집한 가격을 pricehub DB에 저장(Electron, 매크로) | 가격 수집 아르바이트 |
| **card-controltower** | `23.offlinestore-naver-control-back/card-controltower`(백엔드, Spring)<br>`22. 네이버 스마트스토어 매장 관리 front/card-controltower-front`(프론트, React) | 매장별 카드 가격·재고·네이버스토어 연동 관리 — 매장 운영 데이터의 SSOT | 매장 관리자 |
| **purchasing-customers** | `24.purchasing-customers-flutter` | 매장 손님용 매입 접수 태블릿 앱 | 손님 |

### 데이터 흐름 (단방향, 순환 없음 — 2026-08-06 실제 코드 확인 기준)

```
price_adjust  ──(가격 수집 결과 write)──▶  pricehub  ◀──(판매가/매입가 read)──  card-controltower 백엔드
                                                                                      │ (자체 API, JWT)
                                                                                      ▼
                                                                          card-controltower-front (매장 관리자)
                                                                                      ▲
                                                                     /api/buybacks/* (공개, X-Store-Code)
                                                                                      │
                                                                     purchasing-customers (손님, 태블릿)
```

- `price_adjust → pricehub`: **쓰기 전용** (`/api/{game}/bulk-price/collect-card/{id}/`)
- `card-controltower → pricehub`: **읽기 전용** (`PriceHubClient`) — pricehub에는 아무것도 쓰지 않음.
  pricehub가 느려지거나 rate limit에 걸려도 매입가는 `null` 폴백(직원 수기 입력)이라 죽지는 않음.
- **태블릿(purchasing-customers)은 pricehub를 직접 호출하지 않는다** — 항상 card-controltower의
  `/api/buybacks/*`만 거친다. 이 경계를 깨는 변경(태블릿→pricehub 직접 호출, pricehub→
  card-controltower 쓰기 등)은 설계 의도에서 벗어나므로 하지 않는다.
- pricehub의 "매입리스트"(가격 관리자가 정하는 매입 대상/추천가 정책)와 card-controltower의
  "Buyback"(손님이 실제로 들고 온 매입 건)은 이름은 비슷하지만 서로 다른 개념이다 — 헷갈리지 말 것.

### ⚠️ 임시 예외: `card_controltower_client.py` (pricehub → card-controltower 역방향 읽기)

`pricehub/card_controltower_client.py`/`store_price_check*.py`(스토어 가격 비교 페이지)는
위 원칙과 반대로 **pricehub가 card-controltower를 호출**해서 매장 카드 목록·실제 네이버
판매가·판매상태를 읽어온다(2026-08-06 추가). 카드 정보 수정·스토어 상품의 pricehub 초기
가격 설정 작업 때문에 **임시로** 만들어둔 것 — 원래 설계 방향(card-controltower만 pricehub를
읽는 단방향)에 대한 예외이며, 나중에 비활성화(주석 처리)하고 긴급 상황에서만 다시 켜서 쓸
예정이다. 새 기능을 이 파일 위에 계속 쌓지 말 것 — 정식으로 필요해지면 "일시적 예외"가
아니라 위 데이터 흐름 자체를 다시 설계해야 한다는 신호로 볼 것.

## 디자인 시스템 지침

이 앱은 Django 서버 렌더링 템플릿(`pricehub/templates/*.html`) + 순수 CSS(`static/dashboard/`,
`static/admin/`) 구조라 React 쪽(`card-controltower-front`)처럼 컴포넌트/토큰 함수는 없지만,
같은 원칙을 CSS 커스텀 프로퍼티(`var(--token)`)로 적용한다.

> **핵심 원칙: 색·폰트 크기·간격(gap/padding/margin)·radius는 전부 `var(--token)`으로 쓴다.
> 새 CSS·새 템플릿의 `style="..."`에 hex 색상이나 raw px를 직접 넣지 않는다.**

### 토큰 위치

| 파일 | 역할 |
|------|------|
| `static/dashboard/dashboard.css`의 `:root` | 색상 + 타이포그래피/간격/radius 스케일. 대시보드 전 페이지가 로드. |
| `static/dashboard/login.css`의 `:root` | 로그인 페이지 전용 — 로그인 전이라 `dashboard.css`를 로드할 수 없어 **같은 값을 별도로 복제**한다. 토큰을 추가·변경하면 두 파일 다 고칠 것. |
| `static/admin/css/custom_card_admin.css` | Django Admin(라이트 테마) 전용 — 대시보드는 다크 테마라 위 색상 토큰과 톤이 근본적으로 다르다. **의도적으로 분리되어 있으며 대시보드 토큰을 끌어오지 않는다.** |

### 색상 (기존)

```css
--bg / --surface / --surface2 / --surface3   /* 배경 레이어 (어두운 순) */
--border / --border2                          /* 테두리 */
--accent / --accent2                          /* 액센트 */
--success / --warning / --danger              /* 액션 결과 */
--text / --text-muted / --text-dim            /* 텍스트 */
--trend-down* / --trend-up*                   /* 가격 방향 표시 전용(액션 결과와 의미가 다름) */
--favorite / --rank-silver / --rank-bronze    /* 즐겨찾기·순위뱃지 전용 */
```

### 타이포그래피 / 간격 / radius (2026-08-07 도입)

```css
--fs-xs: 11px;  --fs-sm: 13px;  --fs-md: 14px;  --fs-lg: 16px;
--fs-xl: 20px;  --fs-2xl: 24px; --fs-3xl: 32px;

--space-2xs: 4px; --space-xs: 6px;  --space-sm: 8px;  --space-md: 12px;
--space-lg: 16px; --space-xl: 20px; --space-2xl: 24px; --space-3xl: 28px;

--radius-xs: 4px; --radius-sm: 6px; --radius-md: 8px;
--radius-lg: 12px; --radius-xl: 16px; --radius-pill: 999px;  /* 완전한 원/필 모양 전용 */
```

### ✅ / ❌

```css
/* ✅ */
.card-badge {
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: var(--fs-sm);
  color: var(--danger);
}

/* ❌ — 하드코딩 색/크기/간격 */
.card-badge { padding: 4px 8px; border-radius: 6px; font-size: 13px; color: #f06060; }
```

템플릿의 인라인 `style=""`도 동일하게 적용한다: `style="padding: var(--space-sm); color: var(--accent);"`
처럼 값 자리에 `var(--token)`을 쓴다. 인라인 스타일이 여러 줄 반복되면(같은 배지·버튼이
템플릿마다 되풀이되는 경우) CSS 클래스로 뽑아 `dashboard.css`에 추가하는 쪽을 우선 검토한다 —
인라인 스타일은 그 한 곳에서만 쓰는 값에만 쓴다.

### 적용 범위 — 기존 코드는 전면 마이그레이션하지 않는다

`dashboard.css`(약 700줄)·`custom_card_admin.css`·`templates/*.html`의 기존 코드는 대부분
이 스케일 도입 이전에 raw px로 작성되어 있고(폰트 크기만 19종 난립), 위험 대비 이득이 낮아
한 번에 다시 쓰지 않았다. 규칙은 다음과 같다:

- **새 CSS 규칙·새 템플릿은 반드시 토큰만 쓴다.**
- **기존 규칙을 고칠 일이 생기면(버그 수정 등으로 손대는 김에) 그 규칙만 토큰으로 옮긴다** —
  파일 전체를 갈아엎지 않는다. `login.css`가 그 예시다(2026-08-07에 정확히 스케일 값과
  일치하는 부분만 토큰으로 바꾸고, `48px`/`36px`/`15px`처럼 스케일에 없는 값은 시각적 회귀
  위험 때문에 그대로 남겨 주석으로 표시해뒀다).
- 값이 스케일에 정확히 없으면(예: `48px`) 억지로 반올림하지 말고, 먼저 그 값이 정말
  필요한 고유 크기인지(로그인 박스 패딩처럼) 판단한다 — 필요하면 스케일에 없는 값 그대로
  두고 주석으로 "레거시 값"임을 표시한다.

### 검증

수정한 CSS/템플릿 파일에서 아래가 검색되면(주석·레거시로 표시해둔 줄 제외) 토큰화가
빠진 것이다:

```bash
grep -nE "#[0-9a-fA-F]{3,6}\b|font-size:\s*[0-9]|padding:\s*[0-9]|margin[a-z-]*:\s*[0-9]|gap:\s*[0-9]|border-radius:\s*[0-9]" <바꾼 파일>
```
(`custom_card_admin.css`는 위 표 참고 — 대시보드 토큰 대상이 아니므로 이 검증에서 제외한다.)

## 커밋 시 CHANGELOG.md 갱신

사용자가 최종적으로 커밋을 요청하면, 커밋에 포함되는 변경사항을 `CHANGELOG.md`에 반드시 기록한다.

1. `CHANGELOG.md` 최상단(가장 최근 버전) 항목을 확인한다.
2. 이번 커밋 내용에 맞춰 버전을 올린다 ([Semantic Versioning](https://semver.org/lang/ko/) 기준, 0.x 단계):
   - 새 기능 추가 → MINOR 버전 (`0.1.0` → `0.2.0`)
   - 버그 수정 / 보안 수정 / 문서·설정 정리 → PATCH 버전 (`0.1.0` → `0.1.1`)
   - 기존 동작을 깨는 변경 → MAJOR 버전 (`0.x.x` → `1.0.0`), 애매하면 사용자에게 먼저 확인
3. 새 버전 섹션을 파일 최상단(기존 항목들 위)에 추가한다. 날짜는 `YYYY-MM-DD`.
4. 기존 항목의 스타일을 따른다 — [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/) 형식,
   `### Added` / `### Fixed` / `### Security` / `### Known Issues` 등으로 구분.
   한 줄 요약 + 필요하면 이유(왜 바꿨는지)를 짧게.
5. `git commit` 시 `CHANGELOG.md`도 함께 스테이징해서 같은 커밋에 포함한다.
6. 커밋 메시지 요약 정도로 너무 상세하게 쓰지 않는다 — 사용자나 나중에 코드를 보는 사람이
   "무엇이 왜 바뀌었는지" 빠르게 파악할 수 있는 수준이면 충분하다.
7. **git 태그(`git tag`)는 `dev`에서 커밋할 때마다 만들지 않는다** — `master`로 병합해
   실제 release가 되는 시점에만 태그를 단다. `dev`에서는 CHANGELOG.md 버전만 올려둔다.

버전이 애매하거나(사소한 수정인지 새 기능인지 판단이 안 설 때) 사용자에게 먼저 물어보고 진행한다.

## 브랜치 전략

- `master` — 최종 release 브랜치. **서버(운영 환경)는 항상 `master`에서만 pull 받는다.**
  직접 실험적인 커밋을 쌓거나 검증 안 된 변경을 바로 올리지 않는다.
- `dev` — 로컬 작업/테스트용 브랜치. 새 기능·리팩토링 작업은 기본적으로 여기서 진행한다.
- 작업 흐름: `dev`에서 작업 → 충분히 확인됐을 때 사용자 승인 하에 `dev`를 `master`로 병합.
  병합 시점에 CHANGELOG.md 버전도 함께 갱신한다 (위 규칙 참고).
- `master`에 대한 `push`(특히 origin으로) 는 서버가 바로 pull 받는 대상이므로,
  사용자가 명시적으로 병합/배포를 요청했을 때만 수행한다. 다른 모든 git 작업과 마찬가지로
  브랜치를 삭제하거나 강제로 이력을 바꾸는 작업은 하지 않는다.

## 배포 환경 (서버)

- AWS EC2(Ubuntu), `~/pricehub`에 저장소가 체크아웃되어 있고 `master` 브랜치만 pull 받는다.
- 프로세스 관리는 pm2 (`pm2 list`에서 이름 `django-app`). 재시작: `pm2 restart django-app`.
- gunicorn `-w 4`(워커 4개)로 `0.0.0.0:8000`에 바인딩, nginx가 80번 포트에서 리버스 프록시.
- **아직 도메인/TLS 미적용, HTTP로만 서비스 중.** `.env`의 `USE_HTTPS`는 도메인+인증서를
  붙이기 전까지 켜면 안 됨 — 켜면 `SECURE_SSL_REDIRECT`가 없는 HTTPS로 강제 리다이렉트해서
  사이트가 먹통이 된다. 나중에 도메인 적용되면 `USE_HTTPS=True` 추가할 것.
- `staticfiles/`(collectstatic 산출물), `django_cache/`(rate limit용 파일 캐시), `logs/`(에러 로그)는
  전부 런타임에 자동 생성되는 산출물이라 git에 커밋하지 않는다(`.gitignore` 처리됨) —
  실수로 다시 add하지 말 것.
- 공유 캐시(rate limit 등)가 필요하면 Redis 등 별도 인프라가 서버에 없으므로
  `FileBasedCache`(파일시스템 기반, 워커 간 공유됨) 사용을 우선 고려한다.
- `master` 병합 후 서버 배포 절차:
  ```bash
  cd ~/pricehub && source venv/bin/activate
  git pull origin master
  pip install -r requirements.txt
  python manage.py collectstatic --noinput --clear
  python manage.py migrate
  pm2 restart django-app
  ```
  **`pip install` / `collectstatic --clear` / `migrate` 세 개는 이번에 뭐가 바뀌었는지와
  무관하게 매 배포마다 항상 실행한다.** "이번엔 정적 파일만/DB만 바뀌었으니 이 단계는
  건너뛰어도 되겠다"는 판단을 하지 말 것 — nginx가 `staticfiles/`(git에 없는 산출물)를
  서빙하는데 `collectstatic`을 건너뛰면 며칠 전 정적 파일이 그대로 서빙되면서 새 JS/CSS가
  반영 안 된 채로 눈치채기 힘든 버그처럼 보이는 사고가 실제로 있었다(`--clear`로 옛 파일
  잔존까지 방지). `git pull`만 하고 `pm2 restart`로 끝내는 식의 축약 배포는 하지 않는다.
