# pricehub/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import (
    Prefetch, Count, OuterRef, Subquery, Q, 
    Case, When, Value, IntegerField
)
from .models import (
    # 포켓몬
    Expansion, Card, CardPrice, TargetStorePrice,
    # 원피스
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice
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


def card_list(request, code):
    """확장팩 내 카드 목록 페이지 (검색 및 정렬 기능 포함)"""
    from django.db.models import Case, When, Value, IntegerField
    
    expansion = get_object_or_404(Expansion, code=code)
    
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


def onepiece_card_list(request, code):
    """원피스 확장팩 내 카드 목록 페이지"""
    from .models import OnePieceExpansion, OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice
    
    expansion = get_object_or_404(OnePieceExpansion, code=code)
    
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