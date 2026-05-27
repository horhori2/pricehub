# API Key 인증 설정 가이드

## 파일 배치

```
pricehub/
├── authentication.py    ← 복사
├── permissions.py       ← 복사
├── models.py            ← APIKey 모델 내용 추가
├── serializers.py       ← 교체 (selling_price 추가)
├── views.py             ← 교체 (API Key 인증 적용)
└── migrations/
    └── 0016_apikey.py   ← 복사
```

---

## 적용 순서

### 1. 마이그레이션
```bash
python manage.py migrate
```

### 2. API Key 발급
```bash
python manage.py shell
```
```python
from pricehub.models import APIKey

instance, raw_key = APIKey.create_key(name='카드관리프로그램')
print(f"발급된 키: {raw_key}")
# 발급된 키: abc123xyz...  ← 이 값을 외부 프로그램에 전달
```

### 3. 키 목록 확인
```python
APIKey.objects.all().values('name', 'is_active', 'last_used_at')
```

### 4. 키 비활성화
```python
APIKey.objects.filter(name='카드관리프로그램').update(is_active=False)
```

---

## API 호출 방법

### 헤더
```
Authorization: Api-Key <발급받은 키>
```

### Python (외부 카드 관리 프로그램)
```python
import requests

API_KEY = 'abc123xyz...'
BASE_URL = 'https://your-server.com'

headers = {'Authorization': f'Api-Key {API_KEY}'}

# 확장팩 목록
res = requests.get(f'{BASE_URL}/api/pokemon/kr/expansions/', headers=headers)
expansions = res.json()

# 특정 확장팩 카드 목록 (selling_price 포함)
res = requests.get(f'{BASE_URL}/api/pokemon/kr/expansions/m2/cards/', headers=headers)
cards = res.json()

for card in cards['results']:
    print(card['name'], card['selling_price'])  # 관리자 설정 판매가

# 카드 상세
res = requests.get(f'{BASE_URL}/api/pokemon/kr/cards/101/', headers=headers)
card = res.json()
print(card['selling_price'])  # 판매가
```

---

## 응답 예시

### 카드 목록 (`/api/pokemon/kr/expansions/m2/cards/`)
```json
{
  "count": 165,
  "results": [
    {
      "id": 101,
      "card_number": "079",
      "name": "리자몽 ex",
      "rarity": "RR",
      "shop_product_code": "PKM-m2-079-K",
      "image_url": "https://...",
      "expansion_code": "m2",
      "expansion_name": "인페르노X",
      "selling_price": 3500,        ← 관리자가 설정한 판매가
      "latest_price": {
        "price": 3200,
        "source": "카드디씨",
        "collected_at": "2025-01-15T10:30:00Z"
      },
    }
  ]
}
```

### 인증 실패 응답
```json
{
  "detail": "유효하지 않은 API Key입니다."
}
```
HTTP 403

---

## settings.py DRF 설정

기존 DRF 설정에서 기본 인증은 그대로 두고,
각 뷰에서 개별 설정하므로 전역 변경 불필요.

```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
```
