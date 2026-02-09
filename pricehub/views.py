# pricehub/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import (
    Prefetch, Count, OuterRef, Subquery, Q, 
    Case, When, Value, IntegerField
)
from .models import (
    # 포켓몬 한글판
    Expansion, Card, CardPrice, TargetStorePrice,
    # 원피스
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice,
    # 포켓몬 일본판
    JapanExpansion, JapanCard, JapanCardPrice
)
from datetime import datetime, timedelta

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
    from django.db.models import Case, When, Value, IntegerField
    
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
        # 카드번호순 (기본)
        cards = cards.order_by('card_number')
    elif sort_by == 'name':
        # 카드명순 (가나다순)
        cards = cards.order_by('name', 'card_number')
    elif sort_by == 'rarity':
        # 레어도순 (희귀한 순서)
        cards = cards.annotate(rarity_rank=rarity_order).order_by('rarity_rank', 'card_number')
    elif sort_by == 'general_high':
        # 일반 최저가 높은순
        cards = cards.order_by('-latest_general_price', 'card_number')
    elif sort_by == 'general_low':
        # 일반 최저가 낮은순
        cards = cards.order_by('latest_general_price', 'card_number')
    elif sort_by == 'tcg999_high':
        # TCG999 가격 높은순
        cards = cards.order_by('-latest_tcg999_price', 'card_number')
    elif sort_by == 'tcg999_low':
        # TCG999 가격 낮은순
        cards = cards.order_by('latest_tcg999_price', 'card_number')
    else:
        # 기본값: 카드번호순
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
    import json
    from datetime import timedelta
    from django.utils import timezone
    
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
    from .models import OnePieceExpansion
    
    expansions = OnePieceExpansion.objects.annotate(
        card_count=Count('cards')
    ).order_by('-release_date', '-created_at')
    
    context = {
        'expansions': expansions,
    }
    return render(request, 'pricehub/onepiece_expansion_list.html', context)


def onepiece_card_search(request):
    """원피스 카드 검색 결과 페이지"""
    from .models import OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice
    
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
    from .models import OnePieceExpansion, OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice
    
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
    from .models import OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice
    import json
    from datetime import timedelta
    from django.utils import timezone
    
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
    
    # 최신 가격 추가
    latest_price_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at').values('price')[:1]
    
    cards = cards.annotate(
        latest_price=Subquery(latest_price_subquery)
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
    
    # 최신 가격 서브쿼리
    latest_price_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at').values('price')[:1]
    
    cards = cards.annotate(
        latest_price=Subquery(latest_price_subquery)
    )
    
    # 정렬
    if sort_by == 'card_number':
        cards = cards.order_by('card_number', 'mirror_type')
    elif sort_by == 'name':
        cards = cards.order_by('name')
    elif sort_by == 'rarity':
        cards = cards.order_by('rarity', 'card_number')
    elif sort_by == 'price':
        cards = cards.order_by('-latest_price', 'card_number')
    
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
    """일본판 카드 상세"""
    card = get_object_or_404(
        JapanCard.objects.select_related('expansion'),
        id=card_id
    )
    
    # 기간 필터
    period = request.GET.get('period', '1month')
    
    # 기간 계산
    now = datetime.now()
    if period == '1week':
        start_date = now - timedelta(days=7)
        period_label = '1주일'
    elif period == '3months':
        start_date = now - timedelta(days=90)
        period_label = '3개월'
    elif period == 'all':
        start_date = None
        period_label = '전체'
    else:  # 1month
        start_date = now - timedelta(days=30)
        period_label = '1개월'
    
    # 가격 데이터
    if start_date:
        prices = JapanCardPrice.objects.filter(
            card=card,
            collected_at__gte=start_date
        ).order_by('collected_at')
    else:
        prices = JapanCardPrice.objects.filter(card=card).order_by('collected_at')
    
    # 통계
    price_stats = {
        'current': None,
        'min': None,
        'max': None,
        'avg': None,
        'count': prices.count()
    }
    
    if prices.exists():
        latest_price = prices.last()
        price_stats['current'] = latest_price.price
        
        price_values = [p.price for p in prices]
        price_stats['min'] = min(price_values)
        price_stats['max'] = max(price_values)
        price_stats['avg'] = sum(price_values) / len(price_values)
    
    # 차트 데이터
    chart_data = {
        'labels': [p.collected_at.strftime('%Y-%m-%d') for p in prices],
        'prices': [float(p.price) for p in prices]
    }
    
    context = {
        'card': card,
        'prices': prices,
        'price_stats': price_stats,
        'chart_data': chart_data,
        'period': period,
        'period_label': period_label,
        'page_title': f'{card.name} - 카드 상세'
    }
    return render(request, 'pricehub/japan_card_detail.html', context)