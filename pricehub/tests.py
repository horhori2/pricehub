import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client, SimpleTestCase, TestCase

from pricehub.bulk_api_views import _clean_supplied_items
from pricehub.models import Card, CardPrice, Expansion, PurchaseList, PurchaseListItem, round_to_100
from pricehub.utils import (
    _doong_item_is_valid,
    _doong_search_query,
    _is_excluded,
    filter_digimon_items,
    filter_onepiece_items,
    filter_pokemon_items,
    generate_onepiece_search_query,
)


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


class CleanSuppliedItemsTests(SimpleTestCase):
    """Windows Electron 앱(가격조정 보조프로그램)이 보낸 items 정리 — imageUrl 처리 위주"""

    def test_keeps_http_image_url(self):
        cleaned = _clean_supplied_items([
            {'title': '뚜벅쵸', 'mallName': 'A샵', 'lprice': 1000, 'imageUrl': 'https://shopping-phinf.pstatic.net/a.jpg'},
        ])
        self.assertEqual(cleaned[0]['imageUrl'], 'https://shopping-phinf.pstatic.net/a.jpg')

    def test_strips_non_http_image_url_scheme(self):
        cleaned = _clean_supplied_items([
            {'title': '뚜벅쵸', 'mallName': 'A샵', 'lprice': 1000, 'imageUrl': 'javascript:alert(1)'},
        ])
        self.assertEqual(cleaned[0]['imageUrl'], '')

    def test_missing_image_url_defaults_to_empty_string(self):
        cleaned = _clean_supplied_items([
            {'title': '뚜벅쵸', 'mallName': 'A샵', 'lprice': 1000},
        ])
        self.assertEqual(cleaned[0]['imageUrl'], '')

    def test_still_drops_items_missing_required_fields(self):
        cleaned = _clean_supplied_items([
            {'title': '', 'mallName': 'A샵', 'lprice': 1000, 'imageUrl': 'https://x.test/a.jpg'},
            {'title': '뚜벅쵸', 'mallName': 'A샵', 'lprice': 0, 'imageUrl': 'https://x.test/a.jpg'},
        ])
        self.assertEqual(cleaned, [])


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


def _onepiece_item(title, price, mall='테스트몰'):
    return {'title': title, 'lprice': str(price), 'mallName': mall}


class IsExcludedTests(SimpleTestCase):
    """공통 제외 조건(_is_excluded): 판매처·해외판 키워드는 3개 게임 필터가 공용으로 씀"""

    def test_excludes_kream_mall(self):
        self.assertTrue(_is_excluded(_onepiece_item('아무 카드', 1000, mall='KREAM')))

    def test_excludes_naver_and_coupang_malls(self):
        self.assertTrue(_is_excluded(_onepiece_item('아무 카드', 1000, mall='네이버')))
        self.assertTrue(_is_excluded(_onepiece_item('아무 카드', 1000, mall='쿠팡')))

    def test_does_not_exclude_normal_mall(self):
        self.assertFalse(_is_excluded(_onepiece_item('아무 카드', 1000, mall='코방구')))

    def test_excludes_overseas_version_keywords(self):
        for keyword in ('일본', '일본판', '일판', '일어판', 'JP', 'JPN', '영문', '영문판', '미국', '미국판', '영어'):
            with self.subTest(keyword=keyword):
                item = _onepiece_item(f'포켓몬카드 뚜벅쵸 {keyword}', 1000)
                self.assertTrue(_is_excluded(item), f'{keyword!r}가 포함된 제목은 제외돼야 함')

    def test_does_not_exclude_normal_korean_title(self):
        item = _onepiece_item('포켓몬카드 뚜벅쵸 한글판', 1000)
        self.assertFalse(_is_excluded(item))


class FilterOnePieceItemsTests(SimpleTestCase):
    """원피스 필터링: 카드번호 매칭 + 망가/스페셜/패러렐/일반/기타 레어도"""

    def test_base_number_must_be_in_title(self):
        items = [_onepiece_item('원피스카드 다른번호 EB03-999', 1000)]
        price, count, mall, valid = filter_onepiece_items(items, '나미', 'C', '확장팩', 'EB03-062')
        self.assertEqual(count, 0)

    def test_manga_requires_keyword_and_high_price(self):
        items = [
            _onepiece_item('원피스카드 나미 망가 EB03-062', 1600000),
            _onepiece_item('원피스카드 나미 망가 EB03-062', 100000),   # 20만원 미만 → 제외
            _onepiece_item('원피스카드 나미 EB03-062', 1600000),        # 망가 키워드 없음 → 제외
        ]
        price, count, mall, valid = filter_onepiece_items(items, '나미', 'MANGA', '확장팩', 'EB03-062')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '1600000')

    def test_special_requires_sp_keyword(self):
        items = [
            _onepiece_item('원피스카드 나미 SP EB03-062', 30000),
            _onepiece_item('원피스카드 나미 EB03-062', 5000),
        ]
        price, count, mall, valid = filter_onepiece_items(items, '나미', 'SP', '확장팩', 'EB03-062')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '30000')

    def test_parallel_rarity_requires_parallel_keyword(self):
        items = [
            _onepiece_item('원피스카드 나미 패러렐 EB03-062', 20000),
            _onepiece_item('원피스카드 나미 EB03-062', 5000),
        ]
        price, count, mall, valid = filter_onepiece_items(items, '나미', 'P-SR', '확장팩', 'EB03-062')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '20000')

    def test_general_rarity_excludes_parallel_and_special(self):
        items = [
            _onepiece_item('원피스카드 나미 EB03-062', 5000),
            _onepiece_item('원피스카드 나미 패러렐 EB03-062', 20000),
            _onepiece_item('원피스카드 나미 SP EB03-062', 30000),
        ]
        price, count, mall, valid = filter_onepiece_items(items, '나미', 'C', '확장팩', 'EB03-062')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '5000')

    def test_other_rarity_only_excludes_parallel(self):
        items = [
            _onepiece_item('원피스카드 나미 EB03-062', 5000),
            _onepiece_item('원피스카드 나미 패러렐 EB03-062', 20000),
        ]
        price, count, mall, valid = filter_onepiece_items(items, '나미', 'L', '확장팩', 'EB03-062')
        self.assertEqual(count, 1)
        self.assertEqual(valid[0]['lprice'], '5000')


class GenerateOnePieceSearchQueryTests(SimpleTestCase):
    """원피스 검색어 생성: 레어도별 접두사 + 두웅(D/P-D) 특수 케이스 위임"""

    def test_plain_rarity_returns_base_number(self):
        query = generate_onepiece_search_query('나미', 'C', '확장팩', 'EB03-062')
        self.assertEqual(query, 'EB03-062')

    def test_manga_prefixes_query(self):
        query = generate_onepiece_search_query('나미', 'MANGA', '확장팩', 'EB03-062_P2')
        self.assertEqual(query, '망가 EB03-062')

    def test_special_prefixes_query(self):
        query = generate_onepiece_search_query('나미', 'SP', '확장팩', 'EB03-062')
        self.assertEqual(query, '스페셜 EB03-062')

    def test_parallel_prefixes_query(self):
        query = generate_onepiece_search_query('나미', 'P-SR', '확장팩', 'EB03-062')
        self.assertEqual(query, '패러렐 EB03-062')

    def test_starter_deck_prefixes_with_onepiece(self):
        query = generate_onepiece_search_query('나미', 'C', '확장팩', 'ST01-004')
        self.assertEqual(query, '원피스 ST01-004')

    def test_doong_rarity_delegates_to_doong_search_query(self):
        query = generate_onepiece_search_query(
            '금 두웅 (나미)', 'P-D', '확장팩', 'D4', shop_product_code='OPC-EB03-D4-K-V1',
        )
        self.assertEqual(query, 'EB03 금 두웅 나미')


class DoongSearchQueryTests(SimpleTestCase):
    """두웅(EB03/OP13 등 덱 동봉 굿즈) 전용 검색어 생성"""

    def test_extracts_expansion_code_and_flattens_parens(self):
        query = _doong_search_query('OPC-EB03-D4-K-V1', '금 두웅 (나미)')
        self.assertEqual(query, 'EB03 금 두웅 나미')

    def test_works_without_parens_in_name(self):
        query = _doong_search_query('OPC-OP13-D1-K-V1', '금 두웅')
        self.assertEqual(query, 'OP13 금 두웅')

    def test_missing_expansion_segment_falls_back_to_empty(self):
        query = _doong_search_query('OPC', '두웅 (히로인즈)')
        self.assertEqual(query, '두웅 히로인즈')


class DoongItemIsValidTests(SimpleTestCase):
    """두웅 상품 유효성 판정: 캐릭터명/금/패러렐 키워드 OR 조건"""

    def test_requires_doong_keyword_in_title(self):
        self.assertFalse(_doong_item_is_valid('원피스카드 나미 EB03-062', '두웅 (나미)', is_parallel=False))

    def test_plain_doong_requires_character_name_when_present(self):
        self.assertTrue(_doong_item_is_valid('두웅 (나미) EB03-D4', '두웅 (나미)', is_parallel=False))
        self.assertFalse(_doong_item_is_valid('두웅 (우타) EB03-D3', '두웅 (나미)', is_parallel=False))

    def test_plain_doong_without_character_name_only_needs_doong_keyword(self):
        self.assertTrue(_doong_item_is_valid('두웅 히로인즈 세트', '두웅 (히로인즈)', is_parallel=False))

    def test_parallel_doong_accepts_gold_keyword(self):
        self.assertTrue(_doong_item_is_valid('금 두웅 (나미) EB03-D4', '금 두웅 (나미)', is_parallel=True))

    def test_parallel_doong_accepts_generic_parallel_keyword(self):
        self.assertTrue(_doong_item_is_valid('패러렐 두웅 나미 EB03-D4', '금 두웅 (나미)', is_parallel=True))

    def test_parallel_doong_accepts_character_name_alone(self):
        self.assertTrue(_doong_item_is_valid('두웅 나미 특별판 EB03-D4', '금 두웅 (나미)', is_parallel=True))

    def test_parallel_doong_rejects_when_none_of_the_signals_present(self):
        self.assertFalse(_doong_item_is_valid('두웅 우타 EB03-D3', '금 두웅 (나미)', is_parallel=True))


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


class UnderpricedReviewWorkflowTests(TestCase):
    """
    저가 경고(판매가 < 시장 최저가) 목록이 "하루치 확인하면 0건" 워크플로로
    동작하는지 검증. 필터링으로 못 거르는 오매칭 등은 작업자가 판매처
    목록을 보고 직접 판매가를 확정하면, 같은 시장가로는 다시 안 떠야 하고
    시장가 자체가 바뀌면 다시 떠야 한다 (reviewed_market_price 메커니즘).
    """

    UNDERPRICED_URL = '/pokemon/kr/bulk-price/underpriced/'
    EDIT_URL        = '/pokemon/kr/bulk-price/edit/'
    APPROVE_URL     = '/pokemon/kr/bulk-price/approve/'

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'staff_tester2', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        self.expansion = Expansion.objects.create(
            code='TEST2', name='테스트팩2', image_url='https://example.com/exp.png',
        )
        self.card = Card.objects.create(
            expansion=self.expansion, card_number='001', name='쫀도기', rarity='C',
            shop_product_code='TEST2-001', image_url='https://example.com/card.png',
            selling_price=200, latest_market_price=10000,
        )

    def _card_ids_in_underpriced_list(self):
        res = self.client.get(self.UNDERPRICED_URL)
        return {d['card'].id for d in res.context['under_cards']}

    def test_underpriced_card_appears_when_never_reviewed(self):
        self.assertIn(self.card.id, self._card_ids_in_underpriced_list())

    def test_manual_save_at_same_market_price_removes_from_list(self):
        """작업자가 판매처 목록 보고 200원으로 확정 저장(시장가 10000은 오매칭) → 목록에서 빠짐"""
        res = self.client.post(
            self.EDIT_URL,
            data=json.dumps({'card_id': self.card.id, 'price': 200}),
            content_type='application/json',
        )
        self.assertTrue(res.json()['success'])
        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 200)
        self.assertEqual(self.card.reviewed_market_price, 10000)
        self.assertNotIn(self.card.id, self._card_ids_in_underpriced_list())

    def test_card_reappears_after_market_price_changes(self):
        """리뷰 후에도, 다음 수집에서 시장가 자체가 달라지면 다시 노출"""
        self.client.post(
            self.EDIT_URL,
            data=json.dumps({'card_id': self.card.id, 'price': 200}),
            content_type='application/json',
        )
        self.card.latest_market_price = 250  # 다음날 수집에서 정상 가격으로 정정됨
        self.card.save(update_fields=['latest_market_price'])
        self.assertIn(self.card.id, self._card_ids_in_underpriced_list())

    def test_approve_falls_back_to_market_price_when_no_modified_price(self):
        """저가 경고 카드는 modified_price가 비어 있어도 '체크된 카드 저장'이 시장가를 반영해야 함"""
        self.assertFalse(self.card.modified_price)
        res = self.client.post(
            self.APPROVE_URL,
            data=json.dumps({'card_id': self.card.id}),
            content_type='application/json',
        )
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_price'], 10000)
        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 10000)
        self.assertEqual(self.card.reviewed_market_price, 10000)
        self.assertNotIn(self.card.id, self._card_ids_in_underpriced_list())

    def test_set_price_endpoint_also_marks_reviewed(self):
        """카드 목록 페이지의 인라인 저장(set-price)도 동일하게 확인 완료 처리해야 함"""
        res = self.client.post(
            f'/pokemon/kr/cards/{self.card.id}/set-price/',
            data=json.dumps({'selling_price': 200}),
            content_type='application/json',
        )
        self.assertTrue(res.json()['success'])
        self.card.refresh_from_db()
        self.assertEqual(self.card.reviewed_market_price, 10000)
        self.assertNotIn(self.card.id, self._card_ids_in_underpriced_list())


class UnpricedWorkflowTests(TestCase):
    """
    작업 1: 판매가 미설정 — 신제품 발매 등으로 새로 등록된, 판매가가 아직
    없는(selling_price=0) 카드를 작업자가 처음 설정하는 흐름.
    """

    UNPRICED_URL = '/pokemon/kr/bulk-price/unpriced/'
    EDIT_URL     = '/pokemon/kr/bulk-price/edit/'

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'staff_tester3', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        self.expansion = Expansion.objects.create(
            code='TEST3', name='테스트팩3', image_url='https://example.com/exp.png',
        )
        self.card = Card.objects.create(
            expansion=self.expansion, card_number='001', name='신규카드', rarity='C',
            shop_product_code='TEST3-001', image_url='https://example.com/card.png',
            selling_price=0,
        )

    def _card_ids_in_unpriced_list(self):
        res = self.client.get(self.UNPRICED_URL)
        return {c.id for c in res.context['cards']}

    def test_unset_card_appears_in_list(self):
        self.assertIn(self.card.id, self._card_ids_in_unpriced_list())

    def test_setting_price_removes_from_list(self):
        res = self.client.post(
            self.EDIT_URL,
            data=json.dumps({'card_id': self.card.id, 'price': 300}),
            content_type='application/json',
        )
        self.assertTrue(res.json()['success'])
        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 300)
        self.assertNotIn(self.card.id, self._card_ids_in_unpriced_list())

    def test_bulk_set_price_endpoint_also_removes_from_list(self):
        """판매가 미설정 페이지의 일괄 적용 버튼은 카드 목록과 같은 set-price 엔드포인트를 씀"""
        res = self.client.post(
            f'/pokemon/kr/cards/{self.card.id}/set-price/',
            data=json.dumps({'selling_price': 300}),
            content_type='application/json',
        )
        self.assertTrue(res.json()['success'])
        self.assertNotIn(self.card.id, self._card_ids_in_unpriced_list())

    def test_clearing_price_back_to_zero_does_not_crash(self):
        """카드 목록에서 판매가를 0(미설정)으로 되돌려도 500 없이 저장되고, 다시 미설정 목록에 떠야 함.

        selling_price는 null=True 없는 PositiveIntegerField라, 0을 None으로
        바꿔 저장하면 NOT NULL 제약 위반(IntegrityError)이 났었다.
        """
        self.card.selling_price = 500
        self.card.save(update_fields=['selling_price'])

        res = self.client.post(
            f'/pokemon/kr/cards/{self.card.id}/set-price/',
            data=json.dumps({'selling_price': 0}),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['success'])
        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 0)
        self.assertIn(self.card.id, self._card_ids_in_unpriced_list())


class TrendResolveWorkflowTests(TestCase):
    """
    작업 2·3: 가격 하락/상승 대기 — 매일 수집한 가격 중 일괄 실행으로 잡힌
    modified_price를 작업자가 판매처 목록 보고 확인 후 반영하면 목록에서
    빠지는지 검증. (분류 로직 자체는 BulkRunViewTests에서 이미 검증하므로,
    여기선 "목록 노출 → 저장 → 목록에서 빠짐" 사이클만 확인한다.)
    """

    EDIT_URL = '/pokemon/kr/bulk-price/edit/'

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            'staff_tester4', password='pw', is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)
        self.expansion = Expansion.objects.create(
            code='TEST4', name='테스트팩4', image_url='https://example.com/exp.png',
        )

    def _make_card(self, selling_price, modified_price, card_number='001'):
        return Card.objects.create(
            expansion=self.expansion, card_number=card_number, name='테스트카드',
            rarity='U', shop_product_code=f'TEST4-{card_number}',
            image_url='https://example.com/card.png',
            selling_price=selling_price, modified_price=modified_price,
        )

    def _card_ids_in_trend_list(self, trend):
        res = self.client.get(f'/pokemon/kr/bulk-price/{trend}/')
        return {d['card'].id for d in res.context['items']}

    def test_drop_card_appears_only_in_drop_list(self):
        card = self._make_card(selling_price=10000, modified_price=3000)
        self.assertIn(card.id, self._card_ids_in_trend_list('drop'))
        self.assertNotIn(card.id, self._card_ids_in_trend_list('rise'))

    def test_rise_card_appears_only_in_rise_list(self):
        card = self._make_card(selling_price=3000, modified_price=10000, card_number='002')
        self.assertIn(card.id, self._card_ids_in_trend_list('rise'))
        self.assertNotIn(card.id, self._card_ids_in_trend_list('drop'))

    def test_saving_resolves_drop_card_and_it_leaves_the_list(self):
        card = self._make_card(selling_price=10000, modified_price=3000, card_number='003')
        res = self.client.post(
            self.EDIT_URL,
            data=json.dumps({'card_id': card.id, 'price': 10000}),  # 오매칭으로 판단, 기존가 유지
            content_type='application/json',
        )
        self.assertTrue(res.json()['success'])
        card.refresh_from_db()
        self.assertEqual(int(card.modified_price), 0)
        self.assertNotIn(card.id, self._card_ids_in_trend_list('drop'))

    def test_saving_resolves_rise_card_and_it_leaves_the_list(self):
        card = self._make_card(selling_price=3000, modified_price=10000, card_number='004')
        res = self.client.post(
            self.EDIT_URL,
            data=json.dumps({'card_id': card.id, 'price': 10000}),  # 상승 확인 후 반영
            content_type='application/json',
        )
        self.assertTrue(res.json()['success'])
        card.refresh_from_db()
        self.assertEqual(int(card.modified_price), 0)
        self.assertNotIn(card.id, self._card_ids_in_trend_list('rise'))


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
        items = res.context['items']

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['card'].id, rising.id)
        self.assertEqual(items[0]['amt'], 1000)
        self.assertEqual(items[0]['pct'], 100.0)

    def test_sort_by_amt_descending(self):
        small = self._make_card(selling_price=10000, modified_price=11000, card_number='001')  # +1000
        big = self._make_card(selling_price=1000, modified_price=5000, card_number='002')      # +4000

        res = self.client.get(self.RISE_URL, {'sort': 'amt'})
        items = res.context['items']

        self.assertEqual([c['card'].id for c in items], [big.id, small.id])

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
        items = res.context['items']

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['card'].expansion.code, 'OTHER')

    def test_empty_when_no_cards_rising(self):
        res = self.client.get(self.RISE_URL)
        self.assertEqual(res.context['total_count'], 0)
        self.assertEqual(res.context['avg_pct'], 0)
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

    def test_approve_prefers_client_supplied_price_over_modified_price(self):
        """"≤N% 일괄 반영"이 화면에 표시된(작업자가 고친) 값을 무시하고 DB의
        modified_price를 그대로 저장했던 문제 — price를 같이 보내면 그 값이 이겨야 함."""
        res = self.client.post(
            '/pokemon/kr/bulk-price/approve/',
            data=json.dumps({'card_id': self.card.id, 'price': 4200}),
            content_type='application/json',
        )
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_price'], 4200)

        self.card.refresh_from_db()
        self.assertEqual(self.card.selling_price, 4200)
        self.assertEqual(self.card.modified_price, 0)

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


class RobotsTxtTests(SimpleTestCase):
    def test_disallows_everything_except_prices(self):
        res = self.client.get('/robots.txt')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/plain')
        self.assertIn('Disallow: /', res.content.decode('utf-8'))
        self.assertIn('Allow: /prices/', res.content.decode('utf-8'))


class CustomErrorPageTests(TestCase):
    def test_404_uses_custom_template_not_default_django_page(self):
        with self.settings(DEBUG=False):
            res = self.client.get('/this-path-does-not-exist/')
        self.assertEqual(res.status_code, 404)
        self.assertIn('404', res.content.decode('utf-8'))

    def test_500_handler_renders_without_request_context(self):
        # Django는 500.html을 request/컨텍스트 없이 렌더링하므로({% url %}/
        # {% static %}만 안전) 그 상태 그대로 렌더 가능한지 확인한다.
        from django.test import RequestFactory
        from django.views.defaults import server_error

        request = RequestFactory().get('/whatever/')
        res = server_error(request)
        self.assertEqual(res.status_code, 500)
        self.assertIn('500', res.content.decode('utf-8'))
