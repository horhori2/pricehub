from django.contrib import admin
from .models import (
    # 포켓몬 한글판
    Expansion, Card, CardPrice,
    # 원피스
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice,
    # 포켓몬 일본판
    JapanExpansion, JapanCard, JapanCardPrice
)

# ==================== 포켓몬 ====================

@admin.register(Expansion)
class ExpansionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'release_date', 'created_at']
    search_fields = ['code', 'name']
    ordering = ['-release_date']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['name', 'card_number', 'expansion', 'rarity', 'created_at']
    list_filter = ['expansion', 'rarity']
    search_fields = ['name', 'card_number']
    ordering = ['expansion', 'card_number']


@admin.register(CardPrice)
class CardPriceAdmin(admin.ModelAdmin):
    list_display = ['card', 'price', 'source', 'collected_at']
    list_filter = ['source', 'collected_at']
    search_fields = ['card__name']
    ordering = ['-collected_at']


# ==================== 원피스 ====================

@admin.register(OnePieceExpansion)
class OnePieceExpansionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'release_date', 'created_at']
    search_fields = ['code', 'name']
    ordering = ['-release_date']


@admin.register(OnePieceCard)
class OnePieceCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'card_number', 'expansion', 'rarity', 'is_manga', 'created_at']
    list_filter = ['expansion', 'rarity', 'is_manga']
    search_fields = ['name', 'card_number']
    ordering = ['expansion', 'card_number']


@admin.register(OnePieceCardPrice)
class OnePieceCardPriceAdmin(admin.ModelAdmin):
    list_display = ['card', 'price', 'source', 'collected_at']
    list_filter = ['source', 'collected_at']
    search_fields = ['card__name']
    ordering = ['-collected_at']


# ==================== 포켓몬 일본판 ====================

@admin.register(JapanExpansion)
class JapanExpansionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'release_date', 'created_at']
    search_fields = ['code', 'name']
    ordering = ['-release_date', '-created_at']


@admin.register(JapanCard)
class JapanCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'card_number', 'expansion', 'rarity', 'is_mirror', 'created_at']
    list_filter = ['expansion', 'rarity', 'is_mirror']
    search_fields = ['name', 'card_number', 'shop_product_code']
    ordering = ['expansion', 'card_number']


@admin.register(JapanCardPrice)
class JapanCardPriceAdmin(admin.ModelAdmin):
    list_display = ['card', 'price', 'source', 'collected_at']
    list_filter = ['source', 'collected_at']
    search_fields = ['card__name', 'card__card_number']
    ordering = ['-collected_at']