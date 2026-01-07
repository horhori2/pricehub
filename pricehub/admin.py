# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Expansion, Card, CardPrice, TargetStorePrice


@admin.register(Expansion)
class ExpansionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'image_preview', 'release_date', 'card_count', 'created_at']
    list_filter = ['release_date', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    ordering = ['-release_date', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'release_date')
        }),
        ('이미지', {
            'fields': ('image_url', 'image_preview')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.image_url
            )
        return '-'
    image_preview.short_description = '이미지 미리보기'
    
    def card_count(self, obj):
        return obj.cards.count()
    card_count.short_description = '카드 수'


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'name', 'expansion', 'rarity', 'current_price', 'image_preview', 'created_at']
    list_filter = ['expansion', 'rarity', 'created_at']
    search_fields = ['card_number', 'name', 'shop_product_code']
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'current_price']
    autocomplete_fields = ['expansion']
    ordering = ['expansion', 'card_number']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('expansion', 'card_number', 'name', 'rarity')
        }),
        ('상품 정보', {
            'fields': ('shop_product_code', 'image_url', 'image_preview')
        }),
        ('가격 정보', {
            'fields': ('current_price',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.image_url
            )
        return '-'
    image_preview.short_description = '이미지'
    
    def current_price(self, obj):
        latest_price = obj.prices.first()
        if latest_price:
            return format_html(
                '<strong>{}원</strong><br/><small>{}</small>',
                f'{latest_price.price:,}',
                latest_price.collected_at.strftime('%Y-%m-%d %H:%M')
            )
        return '-'
    current_price.short_description = '현재가'


@admin.register(CardPrice)
class CardPriceAdmin(admin.ModelAdmin):
    list_display = ['card_info', 'price_display', 'source', 'collected_at']
    list_filter = ['source', 'collected_at']
    search_fields = ['card__name', 'card__card_number']
    readonly_fields = ['collected_at']
    date_hierarchy = 'collected_at'
    ordering = ['-collected_at']
    
    fieldsets = (
        ('가격 정보', {
            'fields': ('card', 'price', 'source', 'collected_at')
        }),
    )
    
    def card_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{} ({})</small>',
            obj.card.name,
            obj.card.card_number,
            obj.card.expansion.code
        )
    card_info.short_description = '카드 정보'
    
    def price_display(self, obj):
        return format_html('<strong style="color: #0066cc;">{:,}원</strong>', obj.price)
    price_display.short_description = '판매가'
    
    def has_add_permission(self, request):
        # 가격은 자동 수집되므로 수동 추가 방지
        return False
    
@admin.register(TargetStorePrice)
class TargetStorePriceAdmin(admin.ModelAdmin):
    list_display = ['card_info', 'store_name', 'price_display', 'collected_at']
    list_filter = ['store_name', 'collected_at']
    search_fields = ['card__name', 'card__card_number', 'store_name']
    readonly_fields = ['collected_at']
    date_hierarchy = 'collected_at'
    ordering = ['-collected_at']
    
    fieldsets = (
        ('가격 정보', {
            'fields': ('card', 'price', 'store_name', 'collected_at')
        }),
    )
    
    def card_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{} ({})</small>',
            obj.card.name,
            obj.card.card_number,
            obj.card.expansion.code
        )
    card_info.short_description = '카드 정보'
    
    def price_display(self, obj):
        return format_html('<strong style="color: #0066cc;">{:,}원</strong>', obj.price)
    price_display.short_description = '판매가'
    
    def has_add_permission(self, request):
        return False


# Admin 사이트 커스터마이징
admin.site.site_header = '포켓몬 카드 가격 관리'
admin.site.site_title = '포켓몬 카드 관리자'
admin.site.index_title = '대시보드'

