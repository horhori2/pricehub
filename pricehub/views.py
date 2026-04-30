# pricehub/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import (
    Prefetch, Count, OuterRef, Subquery, Q, 
    Case, When, Value, IntegerField, Avg, Min, Max
)
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import json

from .models import (
    # 포켓몬 한글판
    Expansion, Card, CardPrice, TargetStorePrice,
    # 원피스
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice,
    # 포켓몬 일본판
    JapanExpansion, JapanCard, JapanCardPrice
)


# ==================== 포켓몬 카드 뷰 ====================

def expansion_list(request):
    """확장팩 목록 페이지"""
    expansions = Expansion.objects.annotate(
        card_count=Count('cards')
    ).order_by('-release_date', '-created_at')
    
    context = {
        'expansions': expansions,
    }
    return render(request, 'pricehub/expansion_list.html', context)


def card_search(request):
    """카드 검색 결과 페이지"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        context = {
            'query': query,
            'cards': [],
            'count': 0,
        }
        return render(request, 'pricehub/search_results.html', context)
    
    # Subquery로 최신 가격 가져오기
    latest_general_subquery = CardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    latest_tcg999_subquery = TargetStorePrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    # 카드명으로 검색 (대소문자 구분 없이)
    cards = Card.objects.filter(
        Q(name__icontains=query) |  # 카드명에 포함
        Q(card_number__icontains=query)  # 카드번호에 포함
    ).select_related('expansion').annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
        latest_tcg999_price=Subquery(latest_tcg999_subquery.values('price')[:1]),
        latest_tcg999_store=Subquery(latest_tcg999_subquery.values('store_name')[:1]),
    ).order_by('expansion__code', 'card_number')
    
    context = {
        'query': query,
        'cards': cards,
        'count': cards.count(),
    }
    return render(request, 'pricehub/search_results.html', context)


def card_list(request, expansion_code):
    """확장팩 내 카드 목록 페이지 (검색 및 정렬 기능 포함)"""
    expansion = get_object_or_404(Expansion, code=expansion_code)
    
    # 검색어 가져오기
    query = request.GET.get('q', '').strip()
    
    # 정렬 옵션 가져오기 (기본값: 카드번호순)
    sort_by = request.GET.get('sort', 'number')
    
    # Subquery로 최신 가격 가져오기
    latest_general_subquery = CardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    latest_tcg999_subquery = TargetStorePrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    # 기본 쿼리셋 (해당 확장팩의 카드만)
    cards = Card.objects.filter(expansion=expansion)
    
    # 검색어가 있으면 필터링
    if query:
        cards = cards.filter(
            Q(name__icontains=query) |
            Q(card_number__icontains=query)
        )
    
    # 최신 가격 정보 추가
    cards = cards.annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
        latest_tcg999_price=Subquery(latest_tcg999_subquery.values('price')[:1]),
        latest_tcg999_store=Subquery(latest_tcg999_subquery.values('store_name')[:1]),
    )
    
    # 레어도 순서 정의 (희귀한 순서대로)
    rarity_order = Case(
        When(rarity='MUR', then=Value(1)),
        When(rarity='BWR', then=Value(2)),
        When(rarity='SAR', then=Value(3)),
        When(rarity='UR', then=Value(4)),
        When(rarity='SSR', then=Value(5)),
        When(rarity='SR', then=Value(6)),
        When(rarity='HR', then=Value(7)),
        When(rarity='CSR', then=Value(8)),
        When(rarity='CHR', then=Value(9)),
        When(rarity='AR', then=Value(10)),
        When(rarity='마스터볼', then=Value(11)),
        When(rarity='몬스터볼', then=Value(12)),
        When(rarity='이로치', then=Value(13)),
        When(rarity='미러', then=Value(14)),
        When(rarity='RRR', then=Value(15)),
        When(rarity='RR', then=Value(16)),
        When(rarity='R', then=Value(17)),
        When(rarity='U', then=Value(18)),
        When(rarity='C', then=Value(19)),
        default=Value(99),
        output_field=IntegerField(),
    )
    
    # 정렬 적용
    if sort_by == 'number':
        cards = cards.order_by('card_number')
    elif sort_by == 'name':
        cards = cards.order_by('name', 'card_number')
    elif sort_by == 'rarity':
        cards = cards.annotate(rarity_rank=rarity_order).order_by('rarity_rank', 'card_number')
    elif sort_by == 'general_high':
        cards = cards.order_by('-latest_general_price', 'card_number')
    elif sort_by == 'general_low':
        cards = cards.order_by('latest_general_price', 'card_number')
    elif sort_by == 'tcg999_high':
        cards = cards.order_by('-latest_tcg999_price', 'card_number')
    elif sort_by == 'tcg999_low':
        cards = cards.order_by('latest_tcg999_price', 'card_number')
    else:
        cards = cards.order_by('card_number')
    
    context = {
        'expansion': expansion,
        'cards': cards,
        'query': query,
        'sort_by': sort_by,
        'total_count': Card.objects.filter(expansion=expansion).count(),
    }
    return render(request, 'pricehub/card_list.html', context)


def card_detail(request, card_id):
    """카드 상세 페이지 (가격 그래프)"""
    card = get_object_or_404(Card.objects.select_related('expansion'), id=card_id)
    
    # 기간 필터 (기본값: 30일)
    period = request.GET.get('period', '30')
    
    # 기간에 따른 날짜 계산
    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        date_format = '%m-%d'
    elif period == '30':
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'
    elif period == '90':
        start_date = now - timedelta(days=90)
        date_format = '%m-%d'
    elif period == 'all':
        start_date = None
        date_format = '%Y-%m-%d'
    else:
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'
    
    # 가격 데이터 (기간 필터 적용)
    if start_date:
        general_prices = CardPrice.objects.filter(
            card=card, 
            collected_at__gte=start_date
        ).order_by('collected_at')
        tcg999_prices = TargetStorePrice.objects.filter(
            card=card,
            collected_at__gte=start_date
        ).order_by('collected_at')
    else:
        general_prices = CardPrice.objects.filter(card=card).order_by('collected_at')
        tcg999_prices = TargetStorePrice.objects.filter(card=card).order_by('collected_at')
    
    # 최신 가격
    latest_general = CardPrice.objects.filter(card=card).order_by('-collected_at').first()
    latest_tcg999 = TargetStorePrice.objects.filter(card=card).order_by('-collected_at').first()
    
    # 통계 계산
    stats = {
        'general': {
            'min': min([p.price for p in general_prices]) if general_prices else None,
            'max': max([p.price for p in general_prices]) if general_prices else None,
            'avg': sum([p.price for p in general_prices]) / len(general_prices) if general_prices else None,
        },
        'tcg999': {
            'min': min([p.price for p in tcg999_prices]) if tcg999_prices else None,
            'max': max([p.price for p in tcg999_prices]) if tcg999_prices else None,
            'avg': sum([p.price for p in tcg999_prices]) / len(tcg999_prices) if tcg999_prices else None,
        }
    }
    
    # 차트 데이터 준비
    general_chart_data = {
        'labels': json.dumps([p.collected_at.strftime(date_format) for p in general_prices]),
        'data': json.dumps([float(p.price) for p in general_prices])
    }
    
    tcg999_chart_data = {
        'labels': json.dumps([p.collected_at.strftime(date_format) for p in tcg999_prices]),
        'data': json.dumps([float(p.price) for p in tcg999_prices])
    }
    
    context = {
        'card': card,
        'latest_general': latest_general,
        'latest_tcg999': latest_tcg999,
        'general_chart_data': general_chart_data,
        'tcg999_chart_data': tcg999_chart_data,
        'period': period,
        'stats': stats,
    }
    return render(request, 'pricehub/card_detail.html', context)


# ==================== 원피스 카드 뷰 ====================

def onepiece_expansion_list(request):
    """원피스 확장팩 목록 페이지"""
    expansions = OnePieceExpansion.objects.annotate(
        card_count=Count('cards')
    ).order_by('-release_date', '-created_at')
    
    context = {
        'expansions': expansions,
    }
    return render(request, 'pricehub/onepiece_expansion_list.html', context)


def onepiece_card_search(request):
    """원피스 카드 검색 결과 페이지"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        context = {
            'query': query,
            'cards': [],
            'count': 0,
        }
        return render(request, 'pricehub/onepiece_search_results.html', context)
    
    # Subquery로 최신 가격 가져오기
    latest_general_subquery = OnePieceCardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    latest_tcg999_subquery = OnePieceTargetStorePrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    # 카드명으로 검색
    cards = OnePieceCard.objects.filter(
        Q(name__icontains=query) |
        Q(card_number__icontains=query)
    ).select_related('expansion').annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
        latest_tcg999_price=Subquery(latest_tcg999_subquery.values('price')[:1]),
        latest_tcg999_store=Subquery(latest_tcg999_subquery.values('store_name')[:1]),
    ).order_by('expansion__code', 'card_number')
    
    context = {
        'query': query,
        'cards': cards,
        'count': cards.count(),
    }
    return render(request, 'pricehub/onepiece_search_results.html', context)


def onepiece_card_list(request, expansion_code):
    """원피스 확장팩 내 카드 목록 페이지"""
    expansion = get_object_or_404(OnePieceExpansion, code=expansion_code)
    
    # 검색어 가져오기
    query = request.GET.get('q', '').strip()
    
    # 정렬 옵션
    sort_by = request.GET.get('sort', 'number')
    
    # Subquery로 최신 가격 가져오기
    latest_general_subquery = OnePieceCardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')

    latest_cardkingdom_subquery = OnePieceTargetStorePrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')
    
    # 기본 쿼리셋
    cards = OnePieceCard.objects.filter(expansion=expansion)
    
    # 검색어가 있으면 필터링
    if query:
        cards = cards.filter(
            Q(name__icontains=query) |
            Q(card_number__icontains=query)
        )
    
    # 최신 가격 정보 추가
    cards = cards.annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
        latest_cardkingdom_price=Subquery(latest_cardkingdom_subquery.values('price')[:1]),
        latest_cardkingdom_store=Subquery(latest_cardkingdom_subquery.values('store_name')[:1]),
    )
    
    # 레어도 순서 정의
    rarity_order = Case(
        When(rarity='SEC', then=Value(1)),
        When(rarity='SP-SEC', then=Value(2)),
        When(rarity='P-SEC', then=Value(3)),
        When(rarity='SL', then=Value(4)),
        When(rarity='SP-SL', then=Value(5)),
        When(rarity='P-SL', then=Value(6)),
        When(rarity='SR', then=Value(7)),
        When(rarity='SP-SR', then=Value(8)),
        When(rarity='P-SR', then=Value(9)),
        When(rarity='SP', then=Value(10)),
        When(rarity='L', then=Value(11)),
        When(rarity='P-L', then=Value(12)),
        When(rarity='R', then=Value(13)),
        When(rarity='P-R', then=Value(14)),
        When(rarity='UC', then=Value(15)),
        When(rarity='P-UC', then=Value(16)),
        When(rarity='C', then=Value(17)),
        When(rarity='P-C', then=Value(18)),
        When(rarity='P', then=Value(19)),
        default=Value(99),
        output_field=IntegerField(),
    )
    
    # 정렬 적용
    if sort_by == 'number':
        cards = cards.order_by('card_number')
    elif sort_by == 'name':
        cards = cards.order_by('name', 'card_number')
    elif sort_by == 'rarity':
        cards = cards.annotate(rarity_rank=rarity_order).order_by('rarity_rank', 'card_number')
    elif sort_by == 'general_high':
        cards = cards.order_by('-latest_general_price', 'card_number')
    elif sort_by == 'general_low':
        cards = cards.order_by('latest_general_price', 'card_number')
    elif sort_by == 'tcg999_high':
        cards = cards.order_by('-latest_tcg999_price', 'card_number')
    elif sort_by == 'tcg999_low':
        cards = cards.order_by('latest_tcg999_price', 'card_number')
    else:
        cards = cards.order_by('card_number')
    
    context = {
        'expansion': expansion,
        'cards': cards,
        'query': query,
        'sort_by': sort_by,
        'total_count': OnePieceCard.objects.filter(expansion=expansion).count(),
    }
    return render(request, 'pricehub/onepiece_card_list.html', context)


def onepiece_card_detail(request, card_id):
    """원피스 카드 상세 페이지"""
    card = get_object_or_404(OnePieceCard.objects.select_related('expansion'), id=card_id)
    
    # 기간 필터
    period = request.GET.get('period', '30')
    
    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        date_format = '%m-%d'
    elif period == '30':
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'
    elif period == '90':
        start_date = now - timedelta(days=90)
        date_format = '%m-%d'
    elif period == 'all':
        start_date = None
        date_format = '%Y-%m-%d'
    else:
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'
    
    # 가격 데이터
    if start_date:
        general_prices = OnePieceCardPrice.objects.filter(
            card=card, 
            collected_at__gte=start_date
        ).order_by('collected_at')
        tcg999_prices = OnePieceTargetStorePrice.objects.filter(
            card=card,
            collected_at__gte=start_date
        ).order_by('collected_at')
    else:
        general_prices = OnePieceCardPrice.objects.filter(card=card).order_by('collected_at')
        tcg999_prices = OnePieceTargetStorePrice.objects.filter(card=card).order_by('collected_at')
    
    # 최신 가격
    latest_general = OnePieceCardPrice.objects.filter(card=card).order_by('-collected_at').first()
    latest_tcg999 = OnePieceTargetStorePrice.objects.filter(card=card).order_by('-collected_at').first()
    
    # 통계 계산
    stats = {
        'general': {
            'min': min([p.price for p in general_prices]) if general_prices else None,
            'max': max([p.price for p in general_prices]) if general_prices else None,
            'avg': sum([p.price for p in general_prices]) / len(general_prices) if general_prices else None,
        },
        'tcg999': {
            'min': min([p.price for p in tcg999_prices]) if tcg999_prices else None,
            'max': max([p.price for p in tcg999_prices]) if tcg999_prices else None,
            'avg': sum([p.price for p in tcg999_prices]) / len(tcg999_prices) if tcg999_prices else None,
        }
    }
    
    # 차트 데이터
    general_chart_data = {
        'labels': json.dumps([p.collected_at.strftime(date_format) for p in general_prices]),
        'data': json.dumps([float(p.price) for p in general_prices])
    }
    
    tcg999_chart_data = {
        'labels': json.dumps([p.collected_at.strftime(date_format) for p in tcg999_prices]),
        'data': json.dumps([float(p.price) for p in tcg999_prices])
    }
    
    context = {
        'card': card,
        'latest_general': latest_general,
        'latest_tcg999': latest_tcg999,
        'general_chart_data': general_chart_data,
        'tcg999_chart_data': tcg999_chart_data,
        'period': period,
        'stats': stats,
    }
    return render(request, 'pricehub/onepiece_card_detail.html', context)


# ==================== 포켓몬 일본판 뷰 ====================

def japan_expansion_list(request):
    """일본판 확장팩 목록"""
    expansions = JapanExpansion.objects.all().order_by('-release_date', '-created_at')
    
    # 각 확장팩별 카드 수 및 최신 가격 추가
    for expansion in expansions:
        expansion.card_count = JapanCard.objects.filter(expansion=expansion).count()
        
        # 최신 가격이 있는 카드 수
        latest_prices = JapanCardPrice.objects.filter(
            card__expansion=expansion
        ).values('card').distinct()
        expansion.price_count = latest_prices.count()
    
    context = {
        'expansions': expansions,
        'page_title': '포켓몬 일본판 확장팩 목록'
    }
    return render(request, 'pricehub/japan_expansion_list.html', context)


def japan_card_search(request):
    """일본판 카드 검색"""
    query = request.GET.get('q', '')
    
    if not query:
        return render(request, 'pricehub/japan_search_results.html', {
            'cards': [],
            'query': query,
            'page_title': '포켓몬 일본판 카드 검색'
        })
    
    # 카드 검색
    cards = JapanCard.objects.filter(
        Q(name__icontains=query) | 
        Q(card_number__icontains=query) |
        Q(shop_product_code__icontains=query)
    ).select_related('expansion').order_by('expansion', 'card_number')
    
    # 최신 가격 추가 (유유테이 S급)
    latest_yuyu_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'),
        source='유유테이'
    ).order_by('-collected_at').values('price')[:1]
    
    # 최신 가격 추가 (카드러쉬 S급)
    latest_cardrush_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'),
        source='카드러쉬',
        condition='S'
    ).order_by('-collected_at').values('price')[:1]
    
    cards = cards.annotate(
        latest_yuyu_price=Subquery(latest_yuyu_subquery),
        latest_cardrush_price=Subquery(latest_cardrush_subquery)
    )
    
    context = {
        'cards': cards,
        'query': query,
        'page_title': f'포켓몬 일본판 검색: {query}'
    }
    return render(request, 'pricehub/japan_search_results.html', context)


def japan_card_list(request, expansion_code):
    """일본판 확장팩 내 카드 목록"""
    expansion = get_object_or_404(JapanExpansion, code=expansion_code)
    
    # 검색 및 필터
    query = request.GET.get('q', '')
    rarity_filter = request.GET.get('rarity', '')
    mirror_filter = request.GET.get('mirror', '')
    sort_by = request.GET.get('sort', 'card_number')
    
    # 기본 쿼리
    cards = JapanCard.objects.filter(expansion=expansion).select_related('expansion')
    
    # 검색
    if query:
        cards = cards.filter(
            Q(name__icontains=query) | 
            Q(card_number__icontains=query)
        )
    
    # 레어도 필터
    if rarity_filter:
        cards = cards.filter(rarity=rarity_filter)
    
    # 미러 필터
    if mirror_filter == 'mirror':
        cards = cards.filter(is_mirror=True)
    elif mirror_filter == 'normal':
        cards = cards.filter(is_mirror=False)
    
    # 최신 가격 서브쿼리 (유유테이 S급)
    latest_yuyu_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'),
        source='유유테이'
    ).order_by('-collected_at').values('price')[:1]
    
    # 최신 가격 서브쿼리 (카드러쉬 S급)
    latest_cardrush_s_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'),
        source='카드러쉬',
        condition='S'
    ).order_by('-collected_at').values('price')[:1]
    
    # 최신 가격 서브쿼리 (카드러쉬 A-급)
    latest_cardrush_a_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'),
        source='카드러쉬',
        condition='A-'
    ).order_by('-collected_at').values('price')[:1]
    
    cards = cards.annotate(
        latest_yuyu_price=Subquery(latest_yuyu_subquery),
        latest_cardrush_s_price=Subquery(latest_cardrush_s_subquery),
        latest_cardrush_a_price=Subquery(latest_cardrush_a_subquery)
    )
    
    # 정렬
    if sort_by == 'card_number':
        cards = cards.order_by('card_number', 'mirror_type')
    elif sort_by == 'name':
        cards = cards.order_by('name')
    elif sort_by == 'rarity':
        cards = cards.order_by('rarity', 'card_number')
    elif sort_by == 'yuyu_price':
        cards = cards.order_by('-latest_yuyu_price', 'card_number')
    elif sort_by == 'cardrush_price':
        cards = cards.order_by('-latest_cardrush_s_price', 'card_number')
    
    # 레어도 목록 (필터용)
    rarities = JapanCard.objects.filter(expansion=expansion).values_list('rarity', flat=True).distinct().order_by('rarity')
    
    context = {
        'expansion': expansion,
        'cards': cards,
        'rarities': rarities,
        'query': query,
        'rarity_filter': rarity_filter,
        'mirror_filter': mirror_filter,
        'sort_by': sort_by,
        'page_title': f'{expansion.name} - 카드 목록'
    }
    return render(request, 'pricehub/japan_card_list.html', context)


def japan_card_detail(request, card_id):
    """일본판 카드 상세 (상태별 가격 포함)"""
    card = get_object_or_404(
        JapanCard.objects.select_related('expansion'),
        id=card_id
    )
    
    # 기간 필터
    period = request.GET.get('period', '30')
    
    # 기간 계산
    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        period_label = '1주일'
        date_format = '%m-%d'
    elif period == '90':
        start_date = now - timedelta(days=90)
        period_label = '3개월'
        date_format = '%m-%d'
    elif period == 'all':
        start_date = None
        period_label = '전체'
        date_format = '%Y-%m-%d'
    else:  # 30
        start_date = now - timedelta(days=30)
        period_label = '1개월'
        date_format = '%m-%d'
    
    # 유유테이 가격 데이터 (항상 S급)
    if start_date:
        yuyu_prices = JapanCardPrice.objects.filter(
            card=card,
            source='유유테이',
            collected_at__gte=start_date
        ).order_by('collected_at')
    else:
        yuyu_prices = JapanCardPrice.objects.filter(
            card=card,
            source='유유테이'
        ).order_by('collected_at')
    
    # 카드러쉬 가격 데이터 (모든 상태)
    if start_date:
        cardrush_prices = JapanCardPrice.objects.filter(
            card=card,
            source='카드러쉬',
            collected_at__gte=start_date
        ).order_by('collected_at')
    else:
        cardrush_prices = JapanCardPrice.objects.filter(
            card=card,
            source='카드러쉬'
        ).order_by('collected_at')
    
    # 상태별로 그룹화
    cardrush_by_condition = {}
    for price in cardrush_prices:
        condition = price.condition
        if condition not in cardrush_by_condition:
            cardrush_by_condition[condition] = []
        cardrush_by_condition[condition].append(price)
    
    # 최신 가격
    latest_yuyu = yuyu_prices.last() if yuyu_prices.exists() else None
    
    # 카드러쉬 상태별 최신 가격
    latest_cardrush_by_condition = {}
    for condition, prices in cardrush_by_condition.items():
        if prices:
            latest_cardrush_by_condition[condition] = prices[-1]
    
    # 최저가 계산 (S급 기준)
    latest_cardrush_s = latest_cardrush_by_condition.get('S')
    
    lowest_price = None
    lowest_source = None
    
    if latest_yuyu and latest_cardrush_s:
        if latest_yuyu.price <= latest_cardrush_s.price:
            lowest_price = float(latest_yuyu.price)
            lowest_source = '유유테이'
        else:
            lowest_price = float(latest_cardrush_s.price)
            lowest_source = '카드러쉬'
    elif latest_yuyu:
        lowest_price = float(latest_yuyu.price)
        lowest_source = '유유테이'
    elif latest_cardrush_s:
        lowest_price = float(latest_cardrush_s.price)
        lowest_source = '카드러쉬'
    
    # 통계
    price_stats = {
        'yuyu': {
            'current': float(latest_yuyu.price) if latest_yuyu else None,
            'min': float(min([p.price for p in yuyu_prices])) if yuyu_prices.exists() else None,
            'max': float(max([p.price for p in yuyu_prices])) if yuyu_prices.exists() else None,
            'avg': float(sum([p.price for p in yuyu_prices]) / len(yuyu_prices)) if yuyu_prices.exists() else None,
        },
        'cardrush': {},
        'lowest': {
            'price': lowest_price,
            'source': lowest_source
        } if lowest_price else None
    }
    
    # 카드러쉬 상태별 통계 (모든 상태 포함)
    for condition, prices in cardrush_by_condition.items():
        if prices:
            price_stats['cardrush'][condition] = {
                'current': float(prices[-1].price),
                'min': float(min([p.price for p in prices])),
                'max': float(max([p.price for p in prices])),
                'avg': float(sum([p.price for p in prices]) / len(prices)),
            }
    
    # 차트 데이터
    chart_data = {
        'yuyu': {
            'labels': json.dumps([p.collected_at.strftime(date_format) for p in yuyu_prices]),
            'prices': json.dumps([float(p.price) for p in yuyu_prices])
        },
        'cardrush': {}
    }
    
    # 카드러쉬 상태별 차트 데이터 (모든 상태)
    for condition, prices in cardrush_by_condition.items():
        chart_data['cardrush'][condition] = {
            'labels': json.dumps([p.collected_at.strftime(date_format) for p in prices]),
            'prices': json.dumps([float(p.price) for p in prices])
        }
    
    # 사용 가능한 상태 목록 (정렬: S, A-, B, C 순서)
    condition_order = ['S', 'A-', 'B', 'C']
    available_conditions = sorted(
        cardrush_by_condition.keys(),
        key=lambda x: condition_order.index(x) if x in condition_order else 99
    )
    
    # 상태 라벨
    condition_labels = {
        'S': 'S급 (신품)',
        'A-': 'A-급',
        'B': 'B급',
        'C': 'C급'
    }
    
    context = {
        'card': card,
        'latest_yuyu': latest_yuyu,
        'latest_cardrush_by_condition': latest_cardrush_by_condition,
        'available_conditions': available_conditions,
        'condition_labels': condition_labels,
        'price_stats': price_stats,
        'chart_data': chart_data,
        'period': period,
        'period_label': period_label,
        'page_title': f'{card.name} - 카드 상세'
    }
    return render(request, 'pricehub/japan_card_detail.html', context)


# ============================================================================
# 포켓몬 일본판 API (REST API)
# ============================================================================

class JapanExpansionListAPIView(APIView):
    """일본판 확장팩 목록 API"""
    def get(self, request):
        expansions = JapanExpansion.objects.all().order_by('-created_at')
        data = [
            {
                'id': exp.id,
                'code': exp.code,
                'name': exp.name,
                'card_count': JapanCard.objects.filter(expansion=exp).count()
            }
            for exp in expansions
        ]
        return Response(data)


class JapanCardListAPIView(APIView):
    """일본판 카드 목록 API (확장팩별)"""
    def get(self, request, expansion_code):
        try:
            expansion = JapanExpansion.objects.get(code=expansion_code)
        except JapanExpansion.DoesNotExist:
            return Response({'error': '확장팩을 찾을 수 없습니다'}, status=404)
        
        cards = JapanCard.objects.filter(expansion=expansion).order_by('card_number')
        
        # 각 카드의 최신 가격 정보 포함
        data = []
        for card in cards:
            # 유유테이 최신 가격 (S급)
            latest_yuyu = JapanCardPrice.objects.filter(
                card=card,
                source='유유테이'
            ).order_by('-collected_at').first()
            
            # 카드러쉬 최신 가격 (S급)
            latest_cardrush = JapanCardPrice.objects.filter(
                card=card,
                source='카드러쉬',
                condition='S'
            ).order_by('-collected_at').first()
            
            data.append({
                'id': card.id,
                'name': card.name,
                'card_number': card.card_number,
                'rarity': card.rarity,
                'latest_price': {
                    'yuyu_tei': float(latest_yuyu.price) if latest_yuyu else None,
                    'cardrush': float(latest_cardrush.price) if latest_cardrush else None
                }
            })
        
        return Response({
            'expansion': {
                'code': expansion.code,
                'name': expansion.name
            },
            'cards': data
        })


class JapanCardDetailAPIView(APIView):
    """일본판 카드 상세 정보 API (상태별 가격 포함)"""
    def get(self, request, card_id):
        try:
            card = JapanCard.objects.select_related('expansion').get(id=card_id)
        except JapanCard.DoesNotExist:
            return Response({'error': '카드를 찾을 수 없습니다'}, status=404)
        
        # 최근 7일 가격 데이터
        week_ago = timezone.now() - timedelta(days=7)
        
        # 유유테이 가격 (항상 S급)
        yuyu_prices = JapanCardPrice.objects.filter(
            card=card,
            source='유유테이',
            collected_at__gte=week_ago
        ).order_by('-collected_at')
        
        # 카드러쉬 가격 (상태별)
        cardrush_prices = JapanCardPrice.objects.filter(
            card=card,
            source='카드러쉬',
            collected_at__gte=week_ago
        ).order_by('condition', '-collected_at')
        
        # 상태별로 그룹화
        cardrush_by_condition = {}
        for price in cardrush_prices:
            condition = price.condition
            if condition not in cardrush_by_condition:
                cardrush_by_condition[condition] = []
            cardrush_by_condition[condition].append({
                'price': float(price.price),
                'collected_at': price.collected_at.isoformat()
            })
        
        # 최저가 계산 (S급 기준)
        latest_yuyu = yuyu_prices.first()
        latest_cardrush_s = JapanCardPrice.objects.filter(
            card=card,
            source='카드러쉬',
            condition='S'
        ).order_by('-collected_at').first()
        
        lowest_price = None
        lowest_source = None
        
        if latest_yuyu and latest_cardrush_s:
            if latest_yuyu.price <= latest_cardrush_s.price:
                lowest_price = float(latest_yuyu.price)
                lowest_source = '유유테이'
            else:
                lowest_price = float(latest_cardrush_s.price)
                lowest_source = '카드러쉬'
        elif latest_yuyu:
            lowest_price = float(latest_yuyu.price)
            lowest_source = '유유테이'
        elif latest_cardrush_s:
            lowest_price = float(latest_cardrush_s.price)
            lowest_source = '카드러쉬'
        
        response_data = {
            'id': card.id,
            'name': card.name,
            'card_number': card.card_number,
            'rarity': card.rarity,
            'mirror_type': card.mirror_type,
            'expansion': {
                'code': card.expansion.code,
                'name': card.expansion.name
            },
            'prices': {
                'yuyu_tei': [
                    {
                        'price': float(p.price),
                        'collected_at': p.collected_at.isoformat()
                    } for p in yuyu_prices
                ],
                'cardrush': cardrush_by_condition,
                'lowest': {
                    'price': lowest_price,
                    'source': lowest_source
                } if lowest_price else None
            }
        }
        
        return Response(response_data)