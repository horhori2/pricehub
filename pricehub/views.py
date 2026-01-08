# pricehub/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch, Count
from .models import Expansion, Card, CardPrice, TargetStorePrice


def expansion_list(request):
    """확장팩 목록 페이지"""
    expansions = Expansion.objects.annotate(
        card_count=Count('cards')
    ).order_by('-release_date', '-created_at')
    
    context = {
        'expansions': expansions,
    }
    return render(request, 'pricehub/expansion_list.html', context)


def card_list(request, code):
    """확장팩 내 카드 목록 페이지"""
    expansion = get_object_or_404(Expansion, code=code)
    
    # 카드 목록 (최신 가격 포함)
    cards = Card.objects.filter(expansion=expansion).prefetch_related(
        Prefetch('prices', queryset=CardPrice.objects.order_by('-collected_at')[:1]),
        Prefetch('target_prices', queryset=TargetStorePrice.objects.order_by('-collected_at')[:1])
    ).order_by('card_number')
    
    context = {
        'expansion': expansion,
        'cards': cards,
    }
    return render(request, 'pricehub/card_list.html', context)


def card_detail(request, card_id):
    """카드 상세 페이지 (가격 그래프)"""
    import json
    
    card = get_object_or_404(Card.objects.select_related('expansion'), id=card_id)
    
    # 최근 30일 가격 데이터
    general_prices = CardPrice.objects.filter(card=card).order_by('collected_at')
    tcg999_prices = TargetStorePrice.objects.filter(card=card).order_by('collected_at')
    
    # 최신 가격
    latest_general = general_prices.last()
    latest_tcg999 = tcg999_prices.last()
    
    # 차트 데이터 준비 (JSON 문자열로)
    general_chart_data = {
        'labels': json.dumps([p.collected_at.strftime('%Y-%m-%d') for p in general_prices]),
        'data': json.dumps([float(p.price) for p in general_prices])
    }
    
    tcg999_chart_data = {
        'labels': json.dumps([p.collected_at.strftime('%Y-%m-%d') for p in tcg999_prices]),
        'data': json.dumps([float(p.price) for p in tcg999_prices])
    }
    
    context = {
        'card': card,
        'latest_general': latest_general,
        'latest_tcg999': latest_tcg999,
        'general_chart_data': general_chart_data,
        'tcg999_chart_data': tcg999_chart_data,
    }
    return render(request, 'pricehub/card_detail.html', context)