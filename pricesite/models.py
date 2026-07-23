"""
pricesite/models.py

pricehub API에서 주기적으로 동기화해오는 카탈로그 캐시(확장팩/카드 메타데이터).
카드명·레어도·이미지·카드번호 등은 신규 세트 발매 때만 바뀌는 정적 데이터라
로컬 DB에 캐시해서 목록/검색/필터/페이지네이션을 빠르게 처리한다.

반대로 가격 정보(판매처별 분포, 가격 이력)는 매일 갱신되므로 여기 저장하지
않고 카드 상세 페이지에서 매번 pricehub API를 실시간으로 호출한다
(management command `sync_catalog` 및 `pricesite/api_client.py` 참고).
"""
from django.db import models

GAME_CHOICES = [
    ('pokemon_kr', '포켓몬 한글판'),
    ('pokemon_jp', '포켓몬 일본판'),
    ('onepiece_kr', '원피스 한글판'),
    ('digimon_kr', '디지몬 한글판'),
]


class Expansion(models.Model):
    game_type = models.CharField(max_length=20, choices=GAME_CHOICES, db_index=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    image_url = models.URLField(max_length=500, blank=True)
    release_date = models.DateField(null=True, blank=True)
    card_count = models.PositiveIntegerField(default=0)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pricesite_expansion'
        unique_together = [['game_type', 'code']]
        ordering = ['-release_date']

    def __str__(self):
        return f'{self.name} ({self.code})'


class Card(models.Model):
    game_type = models.CharField(max_length=20, choices=GAME_CHOICES, db_index=True)
    expansion = models.ForeignKey(Expansion, on_delete=models.CASCADE, related_name='cards')
    source_id = models.PositiveIntegerField(help_text='pricehub 원본 Card PK — 가격 API 조회에 사용')
    card_number = models.CharField(max_length=20)
    name = models.CharField(max_length=200, db_index=True)
    rarity = models.CharField(max_length=50, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_mirror = models.BooleanField(default=False, help_text='포켓몬 일본판 미러 카드 여부')
    latest_market_price = models.PositiveIntegerField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pricesite_card'
        unique_together = [['game_type', 'source_id']]
        indexes = [models.Index(fields=['game_type', 'expansion', 'card_number'])]
        ordering = ['card_number']

    def __str__(self):
        return f'{self.name} ({self.card_number})'
