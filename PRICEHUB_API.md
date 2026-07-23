# PriceHub 가격 조회 API

트레이딩카드(포켓몬 한글판/일본판, 원피스 한글판, 디지몬 한글판) 시세 조회용 REST API.
pricehub가 매일 자동 수집한 가격 데이터를 제공한다. 이 문서는 **다른 프로젝트에서
pricehub의 가격/카탈로그 데이터를 가져다 쓰기 위한 참고 자료**다.

## Base URL

```
http://<서버 주소>/api/pokemon/kr/    # 포켓몬 한글판
http://<서버 주소>/api/pokemon/jp/    # 포켓몬 일본판
http://<서버 주소>/api/onepiece/kr/   # 원피스 한글판
http://<서버 주소>/api/digimon/kr/    # 디지몬 한글판
```

아직 도메인/HTTPS가 없어 `http://<EC2 IP>:...` 형태다 (CLAUDE.md 참고). 도메인이 생기면
이 문서의 Base URL만 바꾸면 된다.

## 인증

모든 요청에 `Authorization: Api-Key <key>` 헤더가 필요하다.

```
Authorization: Api-Key YOUR_API_KEY
Accept: application/json
```

키는 pricehub 서버에서 발급한다 (관리자에게 요청하거나 직접 발급):

```bash
python manage.py shell -c "from pricehub.models import APIKey; _, k = APIKey.create_key(name='소비 프로젝트명'); print(k)"
```

키 값은 발급 시 한 번만 출력되며 DB에는 해시만 저장되므로 다시 조회할 수 없다.
소비하는 프로젝트마다 별도 키를 발급하는 걸 권장한다(이름으로 구분, 필요시 개별 비활성화 가능).

요청 빈도 제한(rate limit)이 API 키 단위로 걸려 있다(기본 300/min, 서버 `.env`의
`API_THROTTLE_RATE`로 조정 가능).

## 엔드포인트 개요

4개 게임 모두 아래와 같은 패턴을 공유한다 (`{base}`는 위 Base URL 중 하나).
카드/확장팩 메타데이터(이름·레어도·이미지 등)와, **매일 갱신되는 가격 데이터**를
분리해서 생각하면 된다 — 가격은 절대 DB에 캐시하지 말고 매번 이 API를 직접 호출할 것
(pricehub 자체가 매일 수집을 다시 하므로, 캐시하면 금방 stale해짐).

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `{base}/expansions/` | 확장팩 목록 |
| GET | `{base}/expansions/{code}/` | 확장팩 상세 |
| GET | `{base}/expansions/{code}/cards/` | 확장팩별 카드 목록 (카탈로그) |
| GET | `{base}/cards/search/` | 카드 검색 (카탈로그) |
| GET | `{base}/cards/by-product-code/{code}/` | 상품코드로 카드 조회 |
| GET | `{base}/cards/{id}/price-snapshot/` | **카드 최신 가격 스냅샷** (실시간) |
| GET | `{base}/cards/{id}/price-history/?range=week\|month\|year` | **가격 변화 이력** (실시간) |
| GET | `{base}/cards/{id}/` | 카드 상세 (포켓몬 한글판만 지원) |

`price-snapshot`/`price-history`의 `{id}`는 위 카탈로그 엔드포인트(`expansions/{code}/cards/`,
`cards/search/`, `cards/by-product-code/{code}/`)가 돌려주는 카드의 `id` 필드다.

## 카탈로그 응답 예시

### `GET /expansions/`

```json
[
  { "id": 12, "code": "M2A", "name": "MEGA드림ex", "image_url": "https://...", "release_date": "2026-01-01", "card_count": 250 }
]
```

### `GET /expansions/{code}/cards/`

```json
[
  {
    "id": 7655,
    "card_number": "001",
    "name": "뿔충이",
    "rarity": "C",
    "shop_product_code": "PKM-M2A-001-K",
    "image_url": "https://...",
    "expansion_code": "M2A",
    "expansion_name": "MEGA드림ex",
    "selling_price": 200,
    "latest_price": { "price": 200, "source": "트레이너스", "collected_at": "2026-07-22T16:38:42+09:00" },
    "latest_market_price": 200
  }
]
```

- `latest_market_price` — 매일 가격 수집 시 갱신되는 **시장 최저가 캐시 컬럼**. 목록/미리보기용으로는
  이 값을 써도 되지만(카탈로그와 같이 캐싱해도 무방, 최대 하루 지연), 카드 상세 화면처럼 정확한
  최신값이 필요하면 `price-snapshot`을 호출할 것.
- 일본판(`pokemon/jp`)은 `is_mirror`/`mirror_type` 필드가 추가로 있고 `latest_market_price`가 없다
  (판매처별 최저가 개념이 아니라 출처×등급별 가격이라 아래 price-snapshot 형식이 다름).
- 원피스/디지몬은 위와 거의 동일하되 게임 고유 필드가 조금씩 추가된다(디지몬: `card_type`,
  `card_level`, `is_parallel`, `is_scarce`).

### `GET /cards/by-product-code/{shop_product_code}/`

```json
{
  "id": 7655, "card_number": "001", "name": "뿔충이", "rarity": "C",
  "selling_price": 200, "shop_product_code": "PKM-M2A-001-K",
  "expansion": { "code": "M2A", "name": "MEGA드림ex" }
}
```

## 가격 응답 (핵심 — 항상 실시간 호출)

### `GET /cards/{id}/price-snapshot/`

한글판(포켓몬/원피스/디지몬) — 판매처별 가격 분포:

```json
{
  "market_items": [
    { "mallName": "트레이너스", "price_int": 200, "clean_title": "포켓몬카드 뿔충이 C", "link": "https://...", "image": "https://..." }
  ],
  "stats": { "min": 200, "max": 350, "avg": 275, "median": 260, "count": 4 }
}
```

일본판(`pokemon/jp`) — 출처×등급별 최신가:

```json
{
  "latest_prices": [
    { "source": "카드러쉬", "condition": "S", "price": 30 },
    { "source": "카드러쉬", "condition": "A-", "price": 70 }
  ],
  "stats": { "min": 30, "max": 70, "avg": 50, "median": 30, "count": 2 }
}
```

### `GET /cards/{id}/price-history/?range=week`

`range`는 `week`(7일) / `month`(30일, 기본값) / `year`(365일).

```json
{
  "range": "week",
  "history": [
    { "date": "07/20", "prices": [{ "mallName": "트레이너스", "price": 200 }] },
    { "date": "07/21", "prices": [{ "mallName": "트레이너스", "price": 210 }] }
  ]
}
```

일본판도 동일한 `{date, prices: [{mallName, price}]}` 형태를 쓰되, `mallName` 자리에
`"카드러쉬 S급"`처럼 `출처 등급급` 라벨이 들어간다(출처마다 수집 시각이 달라 날짜
단위로 묶어서 반환하기 때문).

## Python 예시

```python
import requests

API_KEY = "your-api-key"
BASE = "http://your-server/api/pokemon/kr"
headers = {"Authorization": f"Api-Key {API_KEY}"}

# 확장팩의 카드 목록
cards = requests.get(f"{BASE}/expansions/M2A/cards/", headers=headers).json()

# 카드 하나의 실시간 가격
card_id = cards[0]["id"]
snapshot = requests.get(f"{BASE}/cards/{card_id}/price-snapshot/", headers=headers).json()
print(snapshot["stats"]["min"])
```

## 참고: pricesite의 사용 패턴

이 프로젝트 안에 있는 `pricesite`(공개 가격 검색 사이트, `/prices/`)가 이 API의
실제 소비자 예시다 — `pricesite/api_client.py`를 보면 요청/에러 처리/캐싱 패턴을
그대로 참고할 수 있다. 핵심 설계:

- 확장팩/카드 **카탈로그**는 소비 프로젝트 쪽 로컬 DB에 주기적으로 동기화해서(예:
  `pricesite/management/commands/sync_catalog.py`) 캐싱 — 검색/필터/페이지네이션을
  빠르게 하기 위함. 자주 안 바뀌는 데이터라 하루 몇 번 동기화해도 충분.
- **가격**(price-snapshot/price-history)은 절대 로컬 DB에 영구 저장하지 않고 매
  요청마다 이 API를 실시간 호출. 다만 짧은 시간(수 분) 내 중복 호출을 줄이려면
  응답을 짧게(예: 10분) 캐시하는 정도는 괜찮다 — `pricesite/api_client.py`의
  `_PRICE_CACHE_TTL` 참고.
