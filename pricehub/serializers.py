"""
pricehub/serializers.py

selling_price 필드 추가.
외부 카드 관리 프로그램이 이 값을 받아 바로 판매가로 사용.
"""
from rest_framework import serializers
from .models import Expansion, Card, CardPrice
from .models import OnePieceExpansion, OnePieceCard
from .models import DigimonExpansion, DigimonCard
from .models import PurchaseList, PurchaseListItem


# ── CardPrice ────────────────────────────────────────────────

class CardPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardPrice
        fields = ['id', 'price', 'source', 'raw_data', 'collected_at']


class CardPriceLatestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardPrice
        fields = ['price', 'source', 'collected_at']


# ── Card ─────────────────────────────────────────────────────

class CardListSerializer(serializers.ModelSerializer):
    """
    카드 목록용.
    selling_price: 관리자가 설정한 판매가 → 외부 프로그램에서 바로 사용.
    """
    latest_price = serializers.SerializerMethodField()
    expansion_code = serializers.CharField(source='expansion.code', read_only=True)
    expansion_name = serializers.CharField(source='expansion.name', read_only=True)

    class Meta:
        model = Card
        fields = [
            'id', 'card_number', 'name', 'rarity', 'is_teukil',
            'shop_product_code', 'image_url',
            'expansion_code', 'expansion_name',
            'selling_price',        # ← 관리자 설정 판매가
            'latest_price',         # ← 최신 시장가 (네이버)
        ]

    def get_latest_price(self, obj):
        prices = obj.prices.all()
        return CardPriceLatestSerializer(prices[0]).data if prices else None


class CardDetailSerializer(serializers.ModelSerializer):
    """
    카드 상세용.
    naver_price_history
    """
    expansion = serializers.SerializerMethodField()
    naver_price_history = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = [
            'id', 'card_number', 'name', 'rarity', 'is_teukil',
            'shop_product_code', 'image_url',
            'selling_price',        # ← 관리자 설정 판매가
            'created_at', 'updated_at',
            'expansion',
            'naver_price_history',
        ]

    def get_expansion(self, obj):
        return {'id': obj.expansion.id, 'code': obj.expansion.code, 'name': obj.expansion.name}

    def get_naver_price_history(self, obj):
        limit = self.context.get('price_limit', 30)
        return CardPriceSerializer(obj.prices.all()[:limit], many=True).data


# ── Expansion ────────────────────────────────────────────────

class ExpansionListSerializer(serializers.ModelSerializer):
    card_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Expansion
        fields = ['id', 'code', 'name', 'image_url', 'release_date', 'card_count']


class ExpansionDetailSerializer(serializers.ModelSerializer):
    card_count = serializers.IntegerField(read_only=True)
    price_stats = serializers.SerializerMethodField()

    class Meta:
        model = Expansion
        fields = [
            'id', 'code', 'name', 'image_url', 'release_date',
            'created_at', 'updated_at', 'card_count', 'price_stats',
        ]

    def get_price_stats(self, obj):
        from django.db.models import Min, Max, Avg, Count
        stats = CardPrice.objects.filter(card__expansion=obj).aggregate(
            min_price=Min('price'), max_price=Max('price'),
            avg_price=Avg('price'), total_records=Count('id'),
        )
        if stats['avg_price']:
            stats['avg_price'] = round(stats['avg_price'])
        return stats

class OnePieceExpansionListSerializer(serializers.ModelSerializer):
    card_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = OnePieceExpansion
        fields = ['code', 'name', 'release_date', 'card_count']

class OnePieceCardListSerializer(serializers.ModelSerializer):
    expansion = serializers.SerializerMethodField()
    class Meta:
        model = OnePieceCard
        fields = ['id', 'card_number', 'name', 'rarity', 'selling_price',
                  'shop_product_code', 'image_url', 'expansion']
    def get_expansion(self, obj):
        return {'code': obj.expansion.code, 'name': obj.expansion.name}


class DigimonExpansionListSerializer(serializers.ModelSerializer):
    card_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = DigimonExpansion
        fields = ['code', 'name', 'release_date', 'card_count']


class DigimonCardListSerializer(serializers.ModelSerializer):
    expansion = serializers.SerializerMethodField()
    class Meta:
        model = DigimonCard
        fields = [
            'id', 'card_number', 'name', 'rarity', 'card_type', 'card_level',
            'is_parallel', 'is_scarce', 'selling_price', 'shop_product_code',
            'image_url', 'expansion',
        ]
    def get_expansion(self, obj):
        return {'code': obj.expansion.code, 'name': obj.expansion.name}


# ── 매입리스트 ───────────────────────────────────────────────
# 외부 프로그램이 카드 목록/이미지/카드 정보/매입가를 받아갈 때 사용.

class PurchaseListItemSerializer(serializers.ModelSerializer):
    """
    매입리스트 항목 — 외부 연동용.
    카드 정보(이름/번호/레어도/이미지/확장팩), 판매가, 매입가를 함께 제공한다.
    """
    card_id = serializers.SerializerMethodField()
    card_name = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    rarity = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    shop_product_code = serializers.SerializerMethodField()
    expansion = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()
    is_decided = serializers.BooleanField(read_only=True)
    final_purchase_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseListItem
        fields = [
            'id', 'card_id', 'card_name', 'card_number', 'rarity',
            'image_url', 'shop_product_code', 'expansion',
            'selling_price', 'purchase_ratio', 'recommended_purchase_price',
            'purchase_price', 'is_decided', 'final_purchase_price',
            'memo', 'added_at', 'decided_at',
        ]

    def _card(self, obj):
        # purchase_config.attach_cards() 로 미리 채워둔 캐시가 있으면 그것을 사용 (N+1 방지)
        return obj.cached_card

    def get_card_id(self, obj):
        c = self._card(obj)
        return c.id if c else None

    def get_card_name(self, obj):
        c = self._card(obj)
        return c.name if c else '(삭제된 카드)'

    def get_card_number(self, obj):
        c = self._card(obj)
        return getattr(c, 'card_number', None) if c else None

    def get_rarity(self, obj):
        c = self._card(obj)
        return getattr(c, 'rarity', None) if c else None

    def get_image_url(self, obj):
        c = self._card(obj)
        return getattr(c, 'image_url', None) if c else None

    def get_shop_product_code(self, obj):
        c = self._card(obj)
        return getattr(c, 'shop_product_code', None) if c else None

    def get_expansion(self, obj):
        c = self._card(obj)
        exp = getattr(c, 'expansion', None) if c else None
        if not exp:
            return None
        return {'code': exp.code, 'name': exp.name}

    def get_selling_price(self, obj):
        c = self._card(obj)
        price = getattr(c, 'selling_price', None) if c else None
        return price if price else None


class PurchaseListSerializer(serializers.ModelSerializer):
    game_type_label = serializers.CharField(source='get_game_type_display', read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    decided_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseList
        fields = [
            'id', 'name', 'game_type', 'game_type_label', 'description',
            'default_purchase_ratio', 'is_active',
            'item_count', 'decided_count',
            'created_at', 'updated_at',
        ]


class PurchaseListDetailSerializer(PurchaseListSerializer):
    """매입리스트 상세 — 카드 목록(이미지/카드정보/매입가 포함) 포함"""
    items = serializers.SerializerMethodField()

    class Meta(PurchaseListSerializer.Meta):
        fields = PurchaseListSerializer.Meta.fields + ['items']

    def get_items(self, obj):
        from .purchase_config import attach_cards  # 순환 import 방지용 지연 import

        items = getattr(obj, '_prefetched_items', None)
        if items is None:
            items = list(obj.items.select_related('content_type').order_by('-added_at'))
            attach_cards(items)
        return PurchaseListItemSerializer(items, many=True).data