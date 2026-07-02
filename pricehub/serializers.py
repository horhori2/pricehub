"""
pricehub/serializers.py

selling_price 필드 추가.
외부 카드 관리 프로그램이 이 값을 받아 바로 판매가로 사용.
"""
from rest_framework import serializers
from .models import Expansion, Card, CardPrice
from .models import OnePieceExpansion, OnePieceCard
from .models import DigimonExpansion, DigimonCard


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