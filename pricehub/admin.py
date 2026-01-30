# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Expansion, Card, CardPrice, TargetStorePrice


@admin.register(Expansion)
class ExpansionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'image_preview', 'release_date', 'card_count', 'created_at']
    list_filter = ['release_date', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at', 'image_preview_large']
    ordering = ['-release_date', '-created_at']
    list_per_page = 20
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'release_date')
        }),
        ('이미지', {
            'fields': ('image_url', 'image_preview_large')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 60px; max-height: 60px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.image_url
            )
        return '-'
    image_preview.short_description = '이미지'
    
    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />',
                obj.image_url
            )
        return '-'
    image_preview_large.short_description = '이미지 미리보기'
    
    def card_count(self, obj):
        count = obj.cards.count()
        return format_html(
            '<span style="display: inline-block; padding: 4px 8px; background-color: #e3f2fd; color: #1976d2; border-radius: 12px; font-weight: 500;">{}</span>',
            count
        )
    card_count.short_description = '카드 수'


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['card_number_display', 'name_display', 'rarity_badge', 'current_price', 'image_preview', 'created_at_display']
    list_filter = ['expansion', 'rarity', 'created_at']
    search_fields = ['card_number', 'name', 'shop_product_code']
    readonly_fields = ['created_at', 'updated_at', 'image_preview_large', 'price_history']
    autocomplete_fields = ['expansion']
    ordering = ['expansion', 'card_number']
    list_per_page = 50
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('expansion', 'card_number', 'name', 'rarity')
        }),
        ('상품 정보', {
            'fields': ('shop_product_code', 'image_url', 'image_preview_large')
        }),
        ('가격 정보', {
            'fields': ('price_history',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/custom_card_admin.css',)
        }
    
    def card_number_display(self, obj):
        return format_html(
            '<span style="font-family: monospace; font-weight: 600; color: #424242; background-color: #f5f5f5; padding: 3px 8px; border-radius: 4px;">{}</span>',
            obj.card_number
        )
    card_number_display.short_description = '카드번호'
    card_number_display.admin_order_field = 'card_number'
    
    def name_display(self, obj):
        return format_html(
            '<div style="font-weight: 500; color: #212121;">{}</div><div style="font-size: 11px; color: #757575; margin-top: 2px;">{}</div>',
            obj.name,
            obj.expansion.code if obj.expansion else '-'
        )
    name_display.short_description = '카드명'
    name_display.admin_order_field = 'name'
    
    def rarity_badge(self, obj):
        rarity_colors = {
            # 기본 레어도
            'C': '#9e9e9e',      # 회색 (Common)
            'U': '#4caf50',      # 초록 (Uncommon)
            'R': '#2196f3',      # 파랑 (Rare)
            'RR': '#9c27b0',     # 보라 (Double Rare)
            'RRR': '#f44336',    # 빨강 (Triple Rare)
            
            # 스페셜 레어도
            'SR': '#ff9800',     # 오렌지 (Super Rare)
            'SSR': '#ff6f00',    # 진한 오렌지 (Super Super Rare)
            'UR': '#ffd700',     # 금색 (Ultra Rare)
            'SAR': '#e91e63',    # 핑크 (Special Art Rare)
            'HR': '#ec407a',     # 분홍 (Hyper Rare)
            'CSR': '#ab47bc',    # 연보라 (Character Super Rare)
            'CHR': '#ba68c8',    # 밝은 보라 (Character Rare)
            
            # 특수 레어도
            'AR': '#00bcd4',     # 시안 (Art Rare)
            'MUR': '#ffb300',    # 황금 (Mystery Ultra Rare)
            'MA': '#ffa726',     # 주황 (Master Art)
            'BWR': '#78909c',    # 청회색 (Black & White Rare)
            
            # 미러/특수 버전
            '미러': '#b0bec5',           # 은색 (Mirror)
            '볼 미러': '#64b5f6',        # 파란 은색 (Ball Mirror)
            '타입 미러': '#81c784',      # 초록 은색 (Type Mirror)
            '로켓단 미러': '#e57373',    # 빨간 은색 (Rocket Mirror)
            '이로치': '#ce93d8',         # 연보라 (Shiny)
            
            # 볼 에디션
            '몬스터볼': '#ef5350',       # 빨강 (Monster Ball)
            '마스터볼': '#7e57c2',       # 보라 (Master Ball)
        }
        color = rarity_colors.get(obj.rarity, '#757575')
        
        return format_html(
            '<span style="display: inline-block; padding: 4px 10px; background-color: {}; color: white; border-radius: 4px; font-weight: 600; font-size: 11px; letter-spacing: 0.5px;">{}</span>',
            color,
            obj.rarity or '-'
        )
    rarity_badge.short_description = '레어도'
    rarity_badge.admin_order_field = 'rarity'
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width: 60px; height: 84px; object-fit: cover; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); border: 1px solid #e0e0e0;" />',
                obj.image_url
            )
        return format_html('<span style="color: #bdbdbd;">이미지 없음</span>')
    image_preview.short_description = '이미지'
    
    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 560px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />',
                obj.image_url
            )
        return '-'
    image_preview_large.short_description = '이미지 미리보기'
    
    def current_price(self, obj):
        latest_price = obj.prices.first()
        if latest_price:
            return format_html(
                '<div style="text-align: right;"><strong style="font-size: 14px; color: #d32f2f;">{}원</strong><br/><small style="color: #757575;">{}</small></div>',
                f'{latest_price.price:,}',
                latest_price.collected_at.strftime('%m/%d %H:%M')
            )
        return format_html('<span style="color: #bdbdbd;">-</span>')
    current_price.short_description = '현재가'
    
    def created_at_display(self, obj):
        return format_html(
            '<span style="color: #757575; font-size: 12px;">{}</span>',
            obj.created_at.strftime('%Y-%m-%d<br/>%H:%M')
        )
    created_at_display.short_description = '생성일시'
    created_at_display.admin_order_field = 'created_at'
    
    def price_history(self, obj):
        prices = obj.prices.order_by('-collected_at')[:10]
        if not prices:
            return format_html('<p style="color: #bdbdbd;">가격 정보가 없습니다.</p>')
        
        html = '<div style="background-color: #fafafa; padding: 15px; border-radius: 8px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background-color: #e0e0e0;"><th style="padding: 8px; text-align: left;">일시</th><th style="padding: 8px; text-align: right;">가격</th><th style="padding: 8px; text-align: center;">출처</th></tr></thead>'
        html += '<tbody>'
        
        for i, price in enumerate(prices):
            bg_color = '#ffffff' if i % 2 == 0 else '#f5f5f5'
            formatted_price = f'{price.price:,}'
            html += f'<tr style="background-color: {bg_color};"><td style="padding: 8px;">{price.collected_at.strftime("%Y-%m-%d %H:%M")}</td><td style="padding: 8px; text-align: right; font-weight: 600; color: #d32f2f;">{formatted_price}원</td><td style="padding: 8px; text-align: center;"><span style="background-color: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{price.source}</span></td></tr>'
        
        html += '</tbody></table></div>'
        return format_html(html)
    price_history.short_description = '가격 히스토리'


@admin.register(CardPrice)
class CardPriceAdmin(admin.ModelAdmin):
    list_display = ['id_display', 'card_info', 'price_display', 'source_badge', 'collected_at_display']
    list_filter = ['source', 'collected_at']
    search_fields = ['card__name', 'card__card_number']
    readonly_fields = ['collected_at']
    date_hierarchy = 'collected_at'
    ordering = ['-collected_at']
    list_per_page = 100
    
    fieldsets = (
        ('가격 정보', {
            'fields': ('card', 'price', 'source', 'collected_at')
        }),
    )
    
    def id_display(self, obj):
        return format_html(
            '<span style="font-family: monospace; color: #757575; font-size: 11px;">#{}</span>',
            obj.id
        )
    id_display.short_description = 'ID'
    id_display.admin_order_field = 'id'
    
    def card_info(self, obj):
        return format_html(
            '<div style="line-height: 1.5;"><strong style="color: #212121;">{}</strong><br/><span style="font-size: 11px; color: #757575; font-family: monospace;">{}</span> <span style="font-size: 11px; color: #9e9e9e;">({})</span></div>',
            obj.card.name,
            obj.card.card_number,
            obj.card.expansion.code
        )
    card_info.short_description = '카드 정보'
    
    def price_display(self, obj):
        return format_html(
            '<strong style="color: #d32f2f; font-size: 14px; white-space: nowrap;">{}원</strong>',
            f'{obj.price:,}'
        )
    price_display.short_description = '판매가'
    price_display.admin_order_field = 'price'
    
    def source_badge(self, obj):
        return format_html(
            '<span style="background-color: #e3f2fd; color: #1976d2; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            obj.source
        )
    source_badge.short_description = '출처'
    source_badge.admin_order_field = 'source'
    
    def collected_at_display(self, obj):
        return format_html(
            '<span style="color: #757575; font-size: 12px; white-space: nowrap;">{}</span>',
            obj.collected_at.strftime('%Y-%m-%d %H:%M')
        )
    collected_at_display.short_description = '수집일시'
    collected_at_display.admin_order_field = 'collected_at'
    
    def has_add_permission(self, request):
        # 가격은 자동 수집되므로 수동 추가 방지
        return False


@admin.register(TargetStorePrice)
class TargetStorePriceAdmin(admin.ModelAdmin):
    list_display = ['id_display', 'card_info', 'store_name_badge', 'price_display', 'collected_at_display']
    list_filter = ['store_name', 'collected_at']
    search_fields = ['card__name', 'card__card_number', 'store_name']
    readonly_fields = ['collected_at']
    date_hierarchy = 'collected_at'
    ordering = ['-collected_at']
    list_per_page = 100
    
    fieldsets = (
        ('가격 정보', {
            'fields': ('card', 'price', 'store_name', 'collected_at')
        }),
    )
    
    def id_display(self, obj):
        return format_html(
            '<span style="font-family: monospace; color: #757575; font-size: 11px;">#{}</span>',
            obj.id
        )
    id_display.short_description = 'ID'
    id_display.admin_order_field = 'id'
    
    def card_info(self, obj):
        return format_html(
            '<div style="line-height: 1.5;"><strong style="color: #212121;">{}</strong><br/><span style="font-size: 11px; color: #757575; font-family: monospace;">{}</span> <span style="font-size: 11px; color: #9e9e9e;">({})</span></div>',
            obj.card.name,
            obj.card.card_number,
            obj.card.expansion.code
        )
    card_info.short_description = '카드 정보'
    
    def store_name_badge(self, obj):
        return format_html(
            '<span style="background-color: #fff3e0; color: #f57c00; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            obj.store_name
        )
    store_name_badge.short_description = '판매처'
    store_name_badge.admin_order_field = 'store_name'
    
    def price_display(self, obj):
        return format_html(
            '<strong style="color: #d32f2f; font-size: 14px; white-space: nowrap;">{}원</strong>',
            f'{obj.price:,}'
        )
    price_display.short_description = '판매가'
    price_display.admin_order_field = 'price'
    
    def collected_at_display(self, obj):
        return format_html(
            '<span style="color: #757575; font-size: 12px; white-space: nowrap;">{}</span>',
            obj.collected_at.strftime('%Y-%m-%d %H:%M')
        )
    collected_at_display.short_description = '수집일시'
    collected_at_display.admin_order_field = 'collected_at'
    
    def has_add_permission(self, request):
        return False


# Admin 사이트 커스터마이징
admin.site.site_header = '🎴 포켓몬 카드 가격 관리 시스템'
admin.site.site_title = '포켓몬 카드 관리자'
admin.site.index_title = '관리 대시보드'