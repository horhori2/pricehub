"""
pricesite/tests.py

pricesite는 pricehub DB를 직접 참조하지 않고 전부 api_client(HTTP)를 거쳐
데이터를 받아오므로, 뷰 테스트는 api_client 함수를 mock으로 대체해
실제 네트워크 호출 없이 검증한다. 카탈로그(확장팩/카드) 쪽은 pricesite
자체 로컬 모델이라 일반 Django TestCase 픽스처로 바로 만든다.
"""
from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from . import api_client
from .models import Card, Expansion


def _make_expansion(game_type='pokemon_kr', code='SV1', name='최초의 벚꽃', **kwargs):
    return Expansion.objects.create(
        game_type=game_type, code=code, name=name,
        release_date=kwargs.pop('release_date', date(2024, 1, 1)),
        **kwargs,
    )


def _make_card(expansion, source_id, card_number='001', name='이상해씨', rarity='C', **kwargs):
    return Card.objects.create(
        game_type=expansion.game_type, expansion=expansion, source_id=source_id,
        card_number=card_number, name=name, rarity=rarity, **kwargs,
    )


class HomeViewTests(TestCase):
    def test_home_lists_all_games(self):
        resp = self.client.get(reverse('pricesite:home'))
        self.assertEqual(resp.status_code, 200)
        for label in ['포켓몬 한글판', '포켓몬 일본판', '원피스 한글판', '디지몬 한글판']:
            self.assertContains(resp, label)

    def test_post_not_allowed(self):
        resp = self.client.post(reverse('pricesite:home'))
        self.assertEqual(resp.status_code, 405)


class ExpansionListViewTests(TestCase):
    def test_unknown_game_404(self):
        resp = self.client.get(reverse('pricesite:expansion-list', args=['not_a_game']))
        self.assertEqual(resp.status_code, 404)

    def test_lists_only_expansions_for_this_game(self):
        _make_expansion(game_type='pokemon_kr', code='SV1', name='포켓몬 확장팩')
        _make_expansion(game_type='onepiece_kr', code='OP01', name='원피스 확장팩')

        resp = self.client.get(reverse('pricesite:expansion-list', args=['pokemon_kr']))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '포켓몬 확장팩')
        self.assertNotContains(resp, '원피스 확장팩')


class CardListViewTests(TestCase):
    def setUp(self):
        self.expansion = _make_expansion()
        self.card1 = _make_card(self.expansion, source_id=1, card_number='001', name='이상해씨', rarity='C')
        self.card2 = _make_card(self.expansion, source_id=2, card_number='002', name='피카츄', rarity='R')

    def _url(self, **params):
        url = reverse('pricesite:card-list', args=['pokemon_kr', self.expansion.code])
        if params:
            from urllib.parse import urlencode
            url += '?' + urlencode(params, doseq=True)
        return url

    def test_lists_all_cards(self):
        resp = self.client.get(self._url())
        self.assertContains(resp, '이상해씨')
        self.assertContains(resp, '피카츄')

    def test_search_by_name(self):
        resp = self.client.get(self._url(q='피카'))
        self.assertNotContains(resp, '이상해씨')
        self.assertContains(resp, '피카츄')

    def test_filter_by_rarity(self):
        resp = self.client.get(self._url(rarities=['R']))
        self.assertNotContains(resp, '이상해씨')
        self.assertContains(resp, '피카츄')

    def test_wrong_game_key_404s_expansion(self):
        # 이 expansion은 pokemon_kr 소속이라 다른 게임 경로로는 못 찾아야 함
        resp = self.client.get(
            reverse('pricesite:card-list', args=['onepiece_kr', self.expansion.code])
        )
        self.assertEqual(resp.status_code, 404)


class CardDetailViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.expansion = _make_expansion()
        self.card = _make_card(self.expansion, source_id=42, name='이상해씨')

    def tearDown(self):
        cache.clear()

    # views.py가 `from .api_client import fetch_price_snapshot, ...`로 이름을
    # 직접 가져다 쓰므로, api_client 모듈이 아니라 views 모듈에 바인딩된
    # 이름을 patch해야 한다(안 그러면 mock이 적용 안 되고 실제 함수가 호출됨).
    @patch('pricesite.views.fetch_price_history')
    @patch('pricesite.views.fetch_price_snapshot')
    def test_renders_market_items_for_kr_card(self, mock_snapshot, mock_history):
        mock_snapshot.return_value = {
            'market_items': [{'mallName': '테스트몰', 'price_int': 1000, 'clean_title': '이상해씨', 'link': '', 'image': ''}],
            'stats': {'min': 1000, 'max': 1000, 'avg': 1000, 'median': 1000, 'count': 1},
        }
        mock_history.return_value = {'range': 'week', 'history': []}

        resp = self.client.get(reverse('pricesite:card-detail', args=['pokemon_kr', self.card.pk]))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '테스트몰')
        self.assertIsNone(resp.context['api_error'])
        # 원본 pricehub PK(source_id)가 아니라 이 카드의 로컬 pk로 호출해야 함
        mock_snapshot.assert_called_once_with('pokemon_kr', self.card.source_id)

    @patch('pricesite.views.fetch_price_history')
    @patch('pricesite.views.fetch_price_snapshot')
    def test_api_failure_degrades_gracefully_instead_of_500(self, mock_snapshot, mock_history):
        mock_snapshot.side_effect = api_client.PricehubAPIError('boom')
        mock_history.side_effect = api_client.PricehubAPIError('boom')

        resp = self.client.get(reverse('pricesite:card-detail', args=['pokemon_kr', self.card.pk]))

        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context['api_error'])
        self.assertEqual(resp.context['market_items'], [])

    @patch('pricesite.views.fetch_price_history')
    @patch('pricesite.views.fetch_price_snapshot')
    def test_japan_card_uses_latest_prices_not_market_items(self, mock_snapshot, mock_history):
        jp_expansion = _make_expansion(game_type='pokemon_jp', code='SVJ', name='일본판 확장팩')
        jp_card = _make_card(jp_expansion, source_id=99, name='이로치 리자몽')
        mock_snapshot.return_value = {
            'latest_prices': [{'source': '유유테이', 'condition': 'S', 'price': 5000}],
            'stats': {'min': 5000, 'max': 5000, 'avg': 5000, 'median': 5000, 'count': 1},
        }
        mock_history.return_value = {'range': 'week', 'history': []}

        resp = self.client.get(reverse('pricesite:card-detail', args=['pokemon_jp', jp_card.pk]))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '유유테이')
        self.assertNotIn('market_items', resp.context)

    def test_unknown_card_pk_404s(self):
        resp = self.client.get(reverse('pricesite:card-detail', args=['pokemon_kr', 999999]))
        self.assertEqual(resp.status_code, 404)

    def test_no_price_editing_ui_present(self):
        with patch('pricesite.views.fetch_price_snapshot', return_value={'market_items': [], 'stats': {}}), \
             patch('pricesite.views.fetch_price_history', return_value={'range': 'week', 'history': []}):
            resp = self.client.get(reverse('pricesite:card-detail', args=['pokemon_kr', self.card.pk]))
        html = resp.content.decode('utf-8')
        for forbidden in ['판매가 설정', 'price-input', 'save-btn', 'setPrice(']:
            self.assertNotIn(forbidden, html)


class PriceHistoryAjaxViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.expansion = _make_expansion()
        self.card = _make_card(self.expansion, source_id=7)

    def tearDown(self):
        cache.clear()

    @patch('pricesite.views.fetch_price_history')
    def test_returns_history_json(self, mock_history):
        mock_history.return_value = {'range': 'month', 'history': [{'date': '01/01', 'prices': []}]}
        resp = self.client.get(
            reverse('pricesite:price-history', args=['pokemon_kr', self.card.pk]), {'range': 'month'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['range'], 'month')
        mock_history.assert_called_once_with('pokemon_kr', self.card.source_id, 'month')

    @patch('pricesite.views.fetch_price_history')
    def test_api_failure_returns_empty_history_not_500(self, mock_history):
        mock_history.side_effect = api_client.PricehubAPIError('boom')
        resp = self.client.get(
            reverse('pricesite:price-history', args=['pokemon_kr', self.card.pk]), {'range': 'week'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['history'], [])


class ApiClientCachingTests(TestCase):
    """가격 응답 캐싱 — 짧은 시간 안에 같은 카드를 여러 번 조회해도 pricehub를 한 번만 호출."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch.object(api_client, '_get')
    def test_price_snapshot_is_cached_per_card(self, mock_get):
        mock_get.return_value = {'market_items': [], 'stats': {}}

        api_client.fetch_price_snapshot('pokemon_kr', 1)
        api_client.fetch_price_snapshot('pokemon_kr', 1)
        self.assertEqual(mock_get.call_count, 1)

        api_client.fetch_price_snapshot('pokemon_kr', 2)
        self.assertEqual(mock_get.call_count, 2)

    @patch.object(api_client, '_get')
    def test_price_history_cache_key_includes_range(self, mock_get):
        mock_get.return_value = {'range': 'week', 'history': []}

        api_client.fetch_price_history('pokemon_kr', 1, 'week')
        api_client.fetch_price_history('pokemon_kr', 1, 'month')
        self.assertEqual(mock_get.call_count, 2)

        api_client.fetch_price_history('pokemon_kr', 1, 'week')
        self.assertEqual(mock_get.call_count, 2)

    @patch('pricesite.api_client.requests.get')
    def test_request_exception_raises_pricehub_api_error_and_is_not_cached(self, mock_requests_get):
        import requests
        mock_requests_get.side_effect = requests.Timeout('timed out')

        with self.assertRaises(api_client.PricehubAPIError):
            api_client.fetch_price_snapshot('pokemon_kr', 5)

        # 실패는 캐시되지 않아야 함 — 재요청 시 다시 pricehub를 호출
        mock_requests_get.side_effect = requests.Timeout('timed out')
        with self.assertRaises(api_client.PricehubAPIError):
            api_client.fetch_price_snapshot('pokemon_kr', 5)
        self.assertEqual(mock_requests_get.call_count, 2)


class SyncCatalogCommandTests(TestCase):
    """카탈로그 동기화 커맨드 — pricehub API를 mock으로 대체해 upsert/삭제 로직만 검증."""

    @patch('pricesite.management.commands.sync_catalog.fetch_cards')
    @patch('pricesite.management.commands.sync_catalog.fetch_expansions')
    def test_creates_expansions_and_cards(self, mock_expansions, mock_cards):
        from io import StringIO

        from django.core.management import call_command

        mock_expansions.return_value = [
            {'code': 'SV1', 'name': '최초의 벚꽃', 'image_url': '', 'release_date': '2024-01-01', 'card_count': 1},
        ]
        mock_cards.return_value = [
            {'id': 10, 'card_number': '001', 'name': '이상해씨', 'rarity': 'C', 'image_url': '', 'latest_market_price': 500},
        ]

        call_command('sync_catalog', '--game', 'pokemon_kr', stdout=StringIO())

        expansion = Expansion.objects.get(game_type='pokemon_kr', code='SV1')
        card = Card.objects.get(game_type='pokemon_kr', source_id=10)
        self.assertEqual(expansion.name, '최초의 벚꽃')
        self.assertEqual(card.name, '이상해씨')
        self.assertEqual(card.latest_market_price, 500)
        self.assertEqual(card.expansion, expansion)

    @patch('pricesite.management.commands.sync_catalog.fetch_cards')
    @patch('pricesite.management.commands.sync_catalog.fetch_expansions')
    def test_removes_expansions_no_longer_returned_by_api(self, mock_expansions, mock_cards):
        from io import StringIO

        from django.core.management import call_command

        stale = _make_expansion(game_type='pokemon_kr', code='OLD', name='단종된 확장팩')
        _make_card(stale, source_id=1)

        mock_expansions.return_value = []
        mock_cards.return_value = []

        call_command('sync_catalog', '--game', 'pokemon_kr', stdout=StringIO())

        self.assertFalse(Expansion.objects.filter(pk=stale.pk).exists())
        self.assertFalse(Card.objects.filter(expansion_id=stale.pk).exists())
