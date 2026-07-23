"""
pricesite/management/commands/sync_catalog.py

pricehub API에서 확장팩/카드 카탈로그(메타데이터)를 가져와 로컬 DB에 upsert.
카드명·레어도·이미지 등은 신규 세트 발매 때만 바뀌는 정적 데이터라 여기서
동기화해두고, 목록/검색/필터/페이지네이션은 로컬 DB로 빠르게 처리한다.

가격 정보(판매처별 분포, 가격 이력)는 여기서 동기화하지 않는다 — 카드 상세
페이지에서 pricehub API를 실시간으로 호출한다(pricesite/api_client.py).
단, 카드 목록의 "시장 최저가" 컬럼은 카탈로그와 함께 캐시해서 목록 페이지를
빠르게 보여준다(최신값이 아니라 이 동기화 시점 기준 스냅샷 — cron으로
주기적으로 이 커맨드를 돌려서 신선도를 유지).

사용:
    python manage.py sync_catalog
    python manage.py sync_catalog --game pokemon_kr
"""
from django.core.management.base import BaseCommand, CommandError

from pricesite.api_client import PricehubAPIError, fetch_cards, fetch_expansions
from pricesite.models import Card, Expansion

GAME_KEYS = ['pokemon_kr', 'pokemon_jp', 'onepiece_kr', 'digimon_kr']


class Command(BaseCommand):
    help = 'pricehub API에서 확장팩/카드 카탈로그(메타데이터)를 동기화한다.'

    def add_arguments(self, parser):
        parser.add_argument('--game', choices=GAME_KEYS, help='특정 게임만 동기화')

    def handle(self, *args, **options):
        games = [options['game']] if options.get('game') else GAME_KEYS
        for game_key in games:
            self._sync_game(game_key)

    def _sync_game(self, game_key):
        self.stdout.write(f'[{game_key}] 확장팩 동기화 중...')
        try:
            expansions = fetch_expansions(game_key)
        except PricehubAPIError as e:
            raise CommandError(str(e))

        synced_codes = set()
        synced_source_ids = set()

        for exp in expansions:
            expansion, _ = Expansion.objects.update_or_create(
                game_type=game_key, code=exp['code'],
                defaults={
                    'name': exp['name'],
                    'image_url': exp.get('image_url') or '',
                    'release_date': exp.get('release_date'),
                    'card_count': exp.get('card_count') or 0,
                },
            )
            synced_codes.add(exp['code'])
            synced_source_ids |= self._sync_cards(game_key, expansion)

        deleted_exp, _ = (
            Expansion.objects.filter(game_type=game_key).exclude(code__in=synced_codes).delete()
        )
        deleted_card, _ = (
            Card.objects.filter(game_type=game_key)
            .exclude(source_id__in=synced_source_ids).delete()
        )

        self.stdout.write(self.style.SUCCESS(
            f'[{game_key}] 확장팩 {len(expansions)}개 동기화 완료'
            f' (삭제: 확장팩 {deleted_exp}, 카드 {deleted_card})'
        ))

    def _sync_cards(self, game_key, expansion):
        try:
            cards = fetch_cards(game_key, expansion.code)
        except PricehubAPIError as e:
            self.stderr.write(self.style.WARNING(f'  {expansion.code}: 카드 조회 실패 ({e})'))
            return set()

        source_ids = set()
        for c in cards:
            Card.objects.update_or_create(
                game_type=game_key, source_id=c['id'],
                defaults={
                    'expansion': expansion,
                    'card_number': c['card_number'],
                    'name': c['name'],
                    'rarity': c.get('rarity') or '',
                    'image_url': c.get('image_url') or '',
                    'is_mirror': c.get('is_mirror') or False,
                    'latest_market_price': c.get('latest_market_price'),
                },
            )
            source_ids.add(c['id'])
        return source_ids
