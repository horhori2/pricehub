import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client, SimpleTestCase, TestCase

from pricehub.models import Card, CardPrice, Expansion, PurchaseList, PurchaseListItem, round_to_100
from pricehub.utils import filter_digimon_items, filter_pokemon_items


def _item(title, price, mall='테스트몰'):
    """네이버 쇼핑 API 응답 아이템 형태를 흉내낸 테스트용 헬퍼."""
    return {'title': title, 'lprice': str(price), 'mallName': mall}


class FilterPokemonItemsNameMatchTests(SimpleTestCase):
    """카드명 매칭 (공백/대소문자 무시) 및 기본 제외 조건"""

    def test_matches_when_title_has_extra_spaces(self):
        items = [_item('포켓몬카드 뚜 벅쵸 U', 1000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(count, 1)
        self.assertEqual(valid, items)

    def test_excludes_when_card_name_not_in_title(self):
        items = [_item('포켓몬카드 다른카드 U', 1000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertIsNone(price)
        self.assertEqual(count, 0)
        self.assertEqual(valid, [])

    def test_excludes_naver_and_coupang_malls(self):
        items = [
            _item('포켓몬카드 뚜벅쵸 U', 1000, mall='네이버'),
            _item('포켓몬카드 뚜벅쵸 U', 2000, mall='쿠팡'),
        ]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(count, 0)

    def test_excludes_japanese_version_keywords(self):
        items = [_item('포켓몬카드 뚜벅쵸 U 일본판', 1000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(count, 0)


class FilterPokemonItemsTeukilTests(SimpleTestCase):
    """특일 컬럼 필터링: is_teukil=True/False 각각의 포함·제외 규칙"""

    def test_teukil_card_requires_teukil_or_special_keyword(self):
        items = [
            _item('포켓몬카드 뚜벅쵸 U 특일', 1000),
            _item('포켓몬카드 뚜벅쵸 U 특별', 1200),
            _item('포켓몬카드 뚜벅쵸 U', 900),  # 특일/특별 키워드 없음 → 제외
        ]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U', is_teukil=True)
        self.assertEqual(count, 2)
        self.assertEqual({v['lprice'] for v in valid}, {'1000', '1200'})

    def test_non_teukil_card_excludes_teukil_or_special_titles(self):
        items = [
            _item('포켓몬카드 뚜벅쵸 U 특일', 1000),
            _item('포켓몬카드 뚜벅쵸 U 특별', 1200),
            _item('포켓몬카드 뚜벅쵸 U', 900),
        ]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U', is_teukil=False)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '900')


class FilterPokemonItemsGeneralRarityTests(SimpleTestCase):
    """일반 레어도(U/C/R/RR/RRR): 고레어 키워드·상위 레어도 오매칭 제외"""

    def test_includes_plain_general_rarity_title(self):
        items = [_item('포켓몬카드 뚜벅쵸 U', 1000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(count, 1)

    def test_excludes_high_rarity_keyword_in_title(self):
        # SR은 HIGH_RARITY_KEYWORDS 에 포함 — U 카드 검색인데 SR 상품이 섞여 들어오는 오매칭 방지
        items = [_item('포켓몬카드 뚜벅쵸 SR', 5000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(count, 0)

    def test_excludes_higher_rarity_listed_for_this_rarity(self):
        # RR은 HIGH_RARITY_KEYWORDS엔 없지만 HIGHER_RARITIES['U']에 있음
        items = [_item('포켓몬카드 뚜벅쵸 RR', 3000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(count, 0)


class FilterPokemonItemsMirrorRarityTests(SimpleTestCase):
    """미러 계열 레어도: 레어도별 필수 키워드 매칭"""

    def test_monster_ball_requires_keyword(self):
        items = [
            _item('포켓몬카드 뚜벅쵸 몬스터볼', 4000),
            _item('포켓몬카드 뚜벅쵸 마스터볼', 4500),  # 다른 미러 키워드 → 제외
        ]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', '몬스터볼')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '4000')

    def test_type_mirror_matches_any_of_list_keywords(self):
        # MIRROR_KEYWORDS['타입 미러'] = ['타입', '에너지'] — 둘 중 하나만 있어도 통과
        items = [_item('포켓몬카드 뚜벅쵸 에너지 미러', 4000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', '타입 미러')
        self.assertEqual(count, 1)


class FilterPokemonItemsIrochiTests(SimpleTestCase):
    """이로치: 이로치 키워드 또는 단독 s/S 중 하나 이상 포함"""

    def test_matches_irochi_keyword(self):
        items = [_item('포켓몬카드 뚜벅쵸 이로치', 6000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', '이로치')
        self.assertEqual(count, 1)

    def test_matches_standalone_s(self):
        items = [_item('포켓몬카드 뚜벅쵸 S', 6000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', '이로치')
        self.assertEqual(count, 1)

    def test_excludes_s_that_is_part_of_another_word(self):
        # SSR의 s는 단독 s가 아니므로(양옆에 알파벳) 이로치 조건을 만족하지 못함
        items = [_item('포켓몬카드 뚜벅쵸 SSR', 6000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', '이로치')
        self.assertEqual(count, 0)


class FilterPokemonItemsMurAndSpecificRarityTests(SimpleTestCase):
    """MUR / 그 외 특정 레어도(SR 등) 매칭"""

    def test_mur_matches_case_insensitively(self):
        items = [_item('포켓몬카드 뚜벅쵸 mur', 7000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'MUR')
        self.assertEqual(count, 1)

    def test_mur_excludes_when_missing(self):
        items = [_item('포켓몬카드 뚜벅쵸', 7000)]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'MUR')
        self.assertEqual(count, 0)

    def test_specific_rarity_requires_word_boundary(self):
        items = [
            _item('포켓몬카드 뚜벅쵸 SR', 8000),   # 단독 SR → 포함
            _item('포켓몬카드 뚜벅쵸 SRR', 8500),  # SR 뒤에 R이 붙어있어 단어 경계 불만족 → 제외
        ]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'SR')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '8000')


class FilterPokemonItemsPriceResultTests(SimpleTestCase):
    """필터를 통과한 상품들 중 최저가 계산"""

    def test_picks_lowest_price_among_valid_items(self):
        items = [
            _item('포켓몬카드 뚜벅쵸 U', 3000, mall='A샵'),
            _item('포켓몬카드 뚜벅쵸 U', 1000, mall='B샵'),
            _item('포켓몬카드 뚜벅쵸 U', 2000, mall='C샵'),
        ]
        price, count, mall, valid = filter_pokemon_items(items, '뚜벅쵸', 'U')
        self.assertEqual(price, 1000.0)
        self.assertEqual(count, 3)
        self.assertEqual(mall, 'B샵')


def _digimon_item(title, price, mall='테스트몰'):
    return {'title': title, 'lprice': str(price), 'mallName': mall}


class FilterDigimonItemsTests(SimpleTestCase):
    """디지몬 필터링: 희소/패러렐/스페셜 모두 양방향(있어야 함/있으면 제외)으로 검사"""

    def test_card_number_must_be_in_title(self):
        items = [_digimon_item('디지몬카드 다른번호', 1000)]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01')
        self.assertEqual(count, 0)

    def test_scarce_card_requires_keyword(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 희소', 3000),
            _digimon_item('디지몬카드 ST1-01', 1000),  # 희소 키워드 없음 → 제외
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_scarce=True)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '3000')

    def test_non_scarce_card_excludes_scarce_titles(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 희소', 3000),  # 희소 상품 섞임 → 제외
            _digimon_item('디지몬카드 ST1-01', 1000),
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_scarce=False)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '1000')

    def test_parallel_card_requires_keyword(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 패러렐', 3000),
            _digimon_item('디지몬카드 ST1-01', 1000),
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_parallel=True)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '3000')

    def test_non_parallel_card_excludes_parallel_titles(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 패러렐', 3000),
            _digimon_item('디지몬카드 ST1-01', 1000),
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_parallel=False)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '1000')

    def test_special_card_matches_special_keyword_or_sp(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 스페셜', 3000),
            _digimon_item('디지몬카드 ST1-01 SP', 3200),
            _digimon_item('디지몬카드 ST1-01', 1000),  # 둘 다 없음 → 제외
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_special=True)
        self.assertEqual(count, 2)
        self.assertEqual({v['lprice'] for v in valid}, {'3000', '3200'})

    def test_non_special_card_excludes_special_or_sp_titles(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 스페셜', 3000),
            _digimon_item('디지몬카드 ST1-01 SP', 3200),
            _digimon_item('디지몬카드 ST1-01', 1000),
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_special=False)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '1000')

    def test_sp_keyword_is_case_insensitive_but_word_bounded(self):
        items = [
            _digimon_item('디지몬카드 ST1-01 sp버전', 1500),   # 소문자 sp도 매칭
            _digimon_item('디지몬카드 ST1-01 DISPLAY', 1600),  # 'sp'가 단어 일부 → 매칭 안 됨
        ]
        price, count, mall, valid = filter_digimon_items(items, 'ST1-01', is_special=True)
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '1500')


class RoundTo100Tests(SimpleTestCase):
    """100원 단위 반올림 (반올림 기준: .5는 올림)"""

    def test_rounds_down_when_under_half(self):
        self.assertEqual(round_to_100(149), 100)

    def test_rounds_up_at_exact_half(self):
        self.assertEqual(round_to_100(150), 200)

    def test_rounds_up_when_over_half(self):
        self.assertEqual(round_to_100(151), 200)

    def test_exact_hundred_stays_same(self):
        self.assertEqual(round_to_100(200), 200)

    def test_zero_stays_zero(self):
        self.assertEqual(round_to_100(0), 0)


class BulkRunViewTests(TestCase):
    """
    _bulk_run_view (POST /pokemon/kr/bulk-price/run/) 의 신규/유지/상승/하락 분기.
    상승은 자동 반영되지 않고 modified_price에만 저장되어 관리자 확인을 거쳐야 한다.
    """

    RUN_URL = '/pokemon/kr/bulk-price/run/'

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'staff_tester', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        self.expansion = Expansion.objects.create(
            code='TEST', name='테스트팩', image_url='https://example.com/exp.png',
        )

    def _make_card(self, selling_price=0, card_number='001'):
        return Card.objects.create(
            expansion=self.expansion, card_number=card_number, name='테스트카드',
            rarity='U', shop_product_code=f'TEST-{card_number}',
            image_url='https://example.com/card.png', selling_price=selling_price,
        )

    def _make_price(self, card, mall, price):
        CardPrice.objects.create(
            card=card, price=price, source=mall,
            raw_data=[{'mallName': mall, 'lprice': str(price)}],
        )

    def _run(self, **overrides):
        body = {'priorities': ['테스트몰'], 'skip_priced': False}
        body.update(overrides)
        return self.client.post(
            self.RUN_URL, data=json.dumps(body), content_type='application/json',
        )

    def test_new_card_applies_immediately(self):
        card = self._make_card(selling_price=0)
        self._make_price(card, '테스트몰', 5000)

        res = self._run()
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 5000)
        self.assertEqual(card.modified_price, 5000)
        self.assertEqual(data['detail']['new'], 1)
        self.assertEqual(data['rise_count'], 0)
        self.assertEqual(data['drop_count'], 0)

    def test_price_increase_waits_for_review_instead_of_auto_applying(self):
        card = self._make_card(selling_price=2000)
        self._make_price(card, '테스트몰', 5000)

        res = self._run()
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 2000)   # 자동 반영되지 않음
        self.assertEqual(card.modified_price, 5000)   # 상승 대기 상태로 저장
        self.assertEqual(data['rise_count'], 1)
        self.assertEqual(data['drop_count'], 0)
        self.assertIn(card.id, data['rise_ids'])

    def test_price_decrease_waits_for_review(self):
        card = self._make_card(selling_price=5000)
        self._make_price(card, '테스트몰', 2000)

        res = self._run()
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 5000)   # 자동 반영되지 않음
        self.assertEqual(card.modified_price, 2000)   # 하락 대기 상태로 저장
        self.assertEqual(data['drop_count'], 1)
        self.assertEqual(data['rise_count'], 0)
        self.assertIn(card.id, data['drop_ids'])

    def test_same_price_is_applied_directly(self):
        card = self._make_card(selling_price=3000)
        self._make_price(card, '테스트몰', 3000)

        res = self._run()
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 3000)
        self.assertEqual(data['detail']['same_or_up'], 1)
        self.assertEqual(data['rise_count'], 0)
        self.assertEqual(data['drop_count'], 0)

    def test_overwrite_forces_immediate_apply_even_on_decrease(self):
        card = self._make_card(selling_price=5000)
        self._make_price(card, '테스트몰', 2000)

        res = self._run(overwrite=True)
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 2000)   # overwrite=True라 즉시 반영됨
        self.assertEqual(data['drop_count'], 0)

    def test_skip_priced_leaves_already_priced_cards_untouched(self):
        card = self._make_card(selling_price=5000)
        self._make_price(card, '테스트몰', 9000)

        res = self._run(skip_priced=True)
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 5000)
        self.assertEqual(card.modified_price, None)
        self.assertEqual(data['skipped_count'], 1)

    def test_no_matching_mall_marks_needs_review(self):
        card = self._make_card(selling_price=0)
        self._make_price(card, '다른몰', 9000)  # priorities에 없는 몰

        res = self._run()
        data = res.json()
        card.refresh_from_db()

        self.assertEqual(card.selling_price, 0)
        self.assertEqual(data['needs_review_count'], 1)
        self.assertIn(card.id, data['needs_review_ids'])


class PurchaseListItemComputeRecommendedPriceTests(SimpleTestCase):
    """PurchaseListItem.compute_recommended_price — DB 저장 없이 순수 계산만 검증"""

    def test_fifty_percent_of_snapshot(self):
        item = PurchaseListItem(selling_price_snapshot=1000, purchase_ratio=50)
        self.assertEqual(item.compute_recommended_price(), 500)

    def test_rounds_to_nearest_100(self):
        # 149 * 50% = 74.5 → 100원 단위로 반올림하면 100
        item = PurchaseListItem(selling_price_snapshot=149, purchase_ratio=50)
        self.assertEqual(item.compute_recommended_price(), 100)

    def test_defaults_to_50_percent_when_ratio_is_none(self):
        item = PurchaseListItem(selling_price_snapshot=10000, purchase_ratio=None)
        self.assertEqual(item.compute_recommended_price(), 5000)

    def test_custom_ratio(self):
        item = PurchaseListItem(selling_price_snapshot=10000, purchase_ratio=30)
        self.assertEqual(item.compute_recommended_price(), 3000)

    def test_zero_snapshot_gives_zero(self):
        item = PurchaseListItem(selling_price_snapshot=0, purchase_ratio=50)
        self.assertEqual(item.compute_recommended_price(), 0)


class PurchaseListItemModelTests(TestCase):
    """PurchaseListItem 저장 시 추천 매입가 자동 계산 및 부가 프로퍼티"""

    def setUp(self):
        expansion = Expansion.objects.create(
            code='TEST', name='테스트팩', image_url='https://example.com/exp.png',
        )
        self.card = Card.objects.create(
            expansion=expansion, card_number='001', name='테스트카드', rarity='U',
            shop_product_code='TEST-001', image_url='https://example.com/card.png',
            selling_price=10000,
        )
        self.plist = PurchaseList.objects.create(
            name='테스트 매입리스트', game_type='pokemon_kr', default_purchase_ratio=50,
        )
        self.content_type = ContentType.objects.get_for_model(Card)

    def _make_item(self, **overrides):
        defaults = {
            'purchase_list': self.plist, 'content_type': self.content_type,
            'object_id': self.card.id, 'selling_price_snapshot': 10000, 'purchase_ratio': 50,
        }
        defaults.update(overrides)
        return PurchaseListItem.objects.create(**defaults)

    def test_save_computes_recommended_price(self):
        item = self._make_item()
        self.assertEqual(item.recommended_purchase_price, 5000)

    def test_save_recomputes_when_ratio_changes(self):
        item = self._make_item()
        item.purchase_ratio = 30
        item.save()
        self.assertEqual(item.recommended_purchase_price, 3000)

    def test_is_decided_reflects_purchase_price(self):
        item = self._make_item()
        self.assertFalse(item.is_decided)
        item.purchase_price = 4500
        item.save()
        self.assertTrue(item.is_decided)

    def test_final_purchase_price_falls_back_to_recommended(self):
        item = self._make_item()
        self.assertEqual(item.final_purchase_price, item.recommended_purchase_price)
        item.purchase_price = 4500
        item.save()
        self.assertEqual(item.final_purchase_price, 4500)


class PurchaseListViewsTests(TestCase):
    """매입리스트 대시보드 뷰(검색/추가/상세/가격결정/삭제) 통합 테스트"""

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'purchase_staff', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        self.expansion = Expansion.objects.create(
            code='TEST', name='테스트팩', image_url='https://example.com/exp.png',
        )
        self.card = Card.objects.create(
            expansion=self.expansion, card_number='001', name='테스트카드', rarity='U',
            shop_product_code='TEST-001', image_url='https://example.com/card.png',
            selling_price=10000,
        )
        self.plist = PurchaseList.objects.create(
            name='테스트 매입리스트', game_type='pokemon_kr', default_purchase_ratio=50,
        )
        self.content_type = ContentType.objects.get_for_model(Card)

    def test_add_card_snapshots_current_selling_price(self):
        res = self.client.post(
            f'/purchase-lists/detail/{self.plist.id}/add-card/',
            data=json.dumps({'card_id': self.card.id}), content_type='application/json',
        )
        data = res.json()
        self.assertTrue(data['success'])

        item = PurchaseListItem.objects.get(purchase_list=self.plist, object_id=self.card.id)
        self.assertEqual(item.selling_price_snapshot, 10000)
        self.assertEqual(item.recommended_purchase_price, 5000)

    def test_add_card_twice_fails_second_time(self):
        add_url = f'/purchase-lists/detail/{self.plist.id}/add-card/'
        body = json.dumps({'card_id': self.card.id})
        self.client.post(add_url, data=body, content_type='application/json')
        res = self.client.post(add_url, data=body, content_type='application/json')

        self.assertFalse(res.json()['success'])
        self.assertEqual(
            PurchaseListItem.objects.filter(purchase_list=self.plist).count(), 1,
        )

    def test_detail_view_refreshes_snapshot_to_current_selling_price(self):
        item = PurchaseListItem.objects.create(
            purchase_list=self.plist, content_type=self.content_type,
            object_id=self.card.id, selling_price_snapshot=10000, purchase_ratio=50,
        )
        self.card.selling_price = 20000
        self.card.save(update_fields=['selling_price'])

        res = self.client.get(f'/purchase-lists/detail/{self.plist.id}/')
        self.assertEqual(res.status_code, 200)

        item.refresh_from_db()
        self.assertEqual(item.selling_price_snapshot, 20000)
        self.assertEqual(item.recommended_purchase_price, 10000)

    def test_search_cards_returns_rounded_recommended_price(self):
        res = self.client.get(
            f'/purchase-lists/detail/{self.plist.id}/search-cards/?q=테스트카드'
        )
        data = res.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['selling_price'], 10000)
        self.assertEqual(data['results'][0]['recommended_purchase_price'], 5000)

    def test_set_price_confirms_purchase_price(self):
        item = PurchaseListItem.objects.create(
            purchase_list=self.plist, content_type=self.content_type,
            object_id=self.card.id, selling_price_snapshot=10000, purchase_ratio=50,
        )
        res = self.client.post(
            f'/purchase-lists/items/{item.id}/set-price/',
            data=json.dumps({'purchase_price': 6000}), content_type='application/json',
        )
        self.assertTrue(res.json()['success'])

        item.refresh_from_db()
        self.assertEqual(item.purchase_price, 6000)
        self.assertIsNotNone(item.decided_at)

    def test_set_price_ratio_change_recomputes_recommended_price(self):
        item = PurchaseListItem.objects.create(
            purchase_list=self.plist, content_type=self.content_type,
            object_id=self.card.id, selling_price_snapshot=10000, purchase_ratio=50,
        )
        res = self.client.post(
            f'/purchase-lists/items/{item.id}/set-price/',
            data=json.dumps({'purchase_ratio': 30}), content_type='application/json',
        )
        self.assertTrue(res.json()['success'])

        item.refresh_from_db()
        self.assertEqual(item.recommended_purchase_price, 3000)

    def test_set_price_clear_resets_to_recommended(self):
        item = PurchaseListItem.objects.create(
            purchase_list=self.plist, content_type=self.content_type,
            object_id=self.card.id, selling_price_snapshot=10000, purchase_ratio=50,
            purchase_price=6000,
        )
        res = self.client.post(
            f'/purchase-lists/items/{item.id}/set-price/',
            data=json.dumps({'clear': True}), content_type='application/json',
        )
        self.assertTrue(res.json()['success'])

        item.refresh_from_db()
        self.assertIsNone(item.purchase_price)
        self.assertIsNone(item.decided_at)

    def test_remove_item_deletes_it(self):
        item = PurchaseListItem.objects.create(
            purchase_list=self.plist, content_type=self.content_type,
            object_id=self.card.id, selling_price_snapshot=10000, purchase_ratio=50,
        )
        res = self.client.post(f'/purchase-lists/items/{item.id}/remove/')

        self.assertTrue(res.json()['success'])
        self.assertFalse(PurchaseListItem.objects.filter(id=item.id).exists())


class BulkRiseViewTests(TestCase):
    """GET /pokemon/kr/bulk-price/rise/ — 상승 대기 목록 필터링·정렬·집계"""

    RISE_URL = '/pokemon/kr/bulk-price/rise/'

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'rise_staff', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        self.expansion = Expansion.objects.create(
            code='TEST', name='테스트팩', image_url='https://example.com/exp.png',
        )

    def _make_card(self, *, selling_price, modified_price, card_number, rarity='U'):
        return Card.objects.create(
            expansion=self.expansion, card_number=card_number, name='테스트카드',
            rarity=rarity, shop_product_code=f'TEST-{card_number}',
            image_url='https://example.com/card.png',
            selling_price=selling_price, modified_price=modified_price,
        )

    def test_only_lists_cards_where_modified_exceeds_selling(self):
        rising = self._make_card(selling_price=1000, modified_price=2000, card_number='001')
        # 하락 대기 카드 (modified < selling) — 상승 목록에 나오면 안 됨
        self._make_card(selling_price=5000, modified_price=2000, card_number='002')
        # 변화 없음 — 상승 목록에 나오면 안 됨
        self._make_card(selling_price=3000, modified_price=3000, card_number='003')

        res = self.client.get(self.RISE_URL)
        self.assertEqual(res.status_code, 200)
        rise_cards = res.context['rise_cards']

        self.assertEqual(len(rise_cards), 1)
        self.assertEqual(rise_cards[0]['card'].id, rising.id)
        self.assertEqual(rise_cards[0]['rise_amt'], 1000)
        self.assertEqual(rise_cards[0]['rise_pct'], 100.0)

    def test_sort_by_rise_amt_descending(self):
        small = self._make_card(selling_price=10000, modified_price=11000, card_number='001')  # +1000
        big = self._make_card(selling_price=1000, modified_price=5000, card_number='002')      # +4000

        res = self.client.get(self.RISE_URL, {'sort': 'rise_amt'})
        rise_cards = res.context['rise_cards']

        self.assertEqual([c['card'].id for c in rise_cards], [big.id, small.id])

    def test_expansion_filter_narrows_results(self):
        other_expansion = Expansion.objects.create(
            code='OTHER', name='다른팩', image_url='https://example.com/exp2.png',
        )
        self._make_card(selling_price=1000, modified_price=2000, card_number='001')
        Card.objects.create(
            expansion=other_expansion, card_number='999', name='다른카드', rarity='U',
            shop_product_code='TEST-999', image_url='https://example.com/card.png',
            selling_price=1000, modified_price=2000,
        )

        res = self.client.get(self.RISE_URL, {'expansion': 'OTHER'})
        rise_cards = res.context['rise_cards']

        self.assertEqual(len(rise_cards), 1)
        self.assertEqual(rise_cards[0]['card'].expansion.code, 'OTHER')

    def test_empty_when_no_cards_rising(self):
        res = self.client.get(self.RISE_URL)
        self.assertEqual(res.context['total_count'], 0)
        self.assertEqual(res.context['avg_rise_pct'], 0)
        self.assertContains(res, '가격 상승 대기 카드가 없습니다')


class BulkApproveAndEditViewTests(TestCase):
    """
    상승/하락 대기 카드를 실제로 반영하는 두 엔드포인트:
    - approve: modified_price를 그대로 selling_price에 반영
    - edit: 관리자가 직접 입력한 가격으로 반영
    둘 다 반영 후 modified_price는 0으로 초기화된다.
    """

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'approve_staff', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        expansion = Expansion.objects.create(
            code='TEST', name='테스트팩', image_url='https://example.com/exp.png',
        )
        self.card = Card.objects.create(
            expansion=expansion, card_number='001', name='테스트카드', rarity='U',
            shop_product_code='TEST-001', image_url='https://example.com/card.png',
            selling_price=2000, modified_price=5000,
        )

    def test_approve_applies_modified_price_and_resets_it(self):
        res = self.client.post(
            '/pokemon/kr/bulk-price/approve/',
            data=json.dumps({'card_id': self.card.id}), content_type='application/json',
        )
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['old_price'], 2000)
        self.assertEqual(data['new_price'], 5000)

        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 5000)
        self.assertEqual(self.card.modified_price, 0)

    def test_approve_fails_without_modified_price(self):
        self.card.modified_price = 0
        self.card.save(update_fields=['modified_price'])

        res = self.client.post(
            '/pokemon/kr/bulk-price/approve/',
            data=json.dumps({'card_id': self.card.id}), content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)

    def test_edit_sets_custom_price_and_resets_modified(self):
        res = self.client.post(
            '/pokemon/kr/bulk-price/edit/',
            data=json.dumps({'card_id': self.card.id, 'price': 3500}),
            content_type='application/json',
        )
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_price'], 3500)

        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 3500)
        self.assertEqual(self.card.modified_price, 0)

    def test_edit_rejects_non_positive_price(self):
        res = self.client.post(
            '/pokemon/kr/bulk-price/edit/',
            data=json.dumps({'card_id': self.card.id, 'price': 0}),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)
        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 2000)  # 변경되지 않음


class CsrfFailureViewTests(TestCase):
    """CSRF 검증 실패 시 기본 403 디버그 화면 대신 로그인 페이지로 안내되는지 (settings.CSRF_FAILURE_VIEW)"""

    def test_csrf_failure_redirects_to_login_with_friendly_message(self):
        client = Client(enforce_csrf_checks=True)
        res = client.post('/login/', data={'username': 'nouser', 'password': 'x'})

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res['Location'].startswith('/login/?'))

        follow = client.get(res['Location'])
        self.assertEqual(follow.status_code, 200)
        self.assertContains(follow, '세션이 만료')


class PurchaseListCrudViewsTests(TestCase):
    """매입리스트 생성/활성토글/삭제"""

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'plist_crud_staff', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)

    def test_create_clamps_ratio_into_0_100_range(self):
        res = self.client.post('/purchase-lists/pokemon_kr/create/', data={
            'name': '테스트 리스트', 'default_purchase_ratio': '150',
        })
        self.assertEqual(res.status_code, 302)

        plist = PurchaseList.objects.get(name='테스트 리스트')
        self.assertEqual(plist.game_type, 'pokemon_kr')
        self.assertEqual(int(plist.default_purchase_ratio), 100)

    def test_create_rejects_unknown_game_type(self):
        res = self.client.post('/purchase-lists/not_a_game/create/', data={'name': '테스트'})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(PurchaseList.objects.filter(name='테스트').exists())

    def test_toggle_active_flips_flag(self):
        plist = PurchaseList.objects.create(name='토글용', game_type='pokemon_kr', is_active=True)

        res = self.client.post(f'/purchase-lists/detail/{plist.id}/toggle-active/')
        data = res.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['is_active'])

        plist.refresh_from_db()
        self.assertFalse(plist.is_active)

    def test_delete_removes_list(self):
        plist = PurchaseList.objects.create(name='삭제용', game_type='pokemon_kr')

        res = self.client.post(f'/purchase-lists/detail/{plist.id}/delete/')
        data = res.json()
        self.assertTrue(data['success'])
        self.assertFalse(PurchaseList.objects.filter(id=plist.id).exists())
