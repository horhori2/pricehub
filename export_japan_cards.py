# export_japan_cards.py
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanExpansion, JapanCard

print("일본판 카드 데이터 내보내기...")

data = {
    'expansions': [],
    'cards': []
}

# 확장팩 데이터
for expansion in JapanExpansion.objects.all():
    data['expansions'].append({
        'code': expansion.code,
        'name': expansion.name,
        'release_date': expansion.release_date.isoformat() if expansion.release_date else None,
        'image_url': expansion.image_url,
    })

# 카드 데이터
for card in JapanCard.objects.select_related('expansion').all():
    data['cards'].append({
        'expansion_code': card.expansion.code,
        'shop_product_code': card.shop_product_code,
        'card_number': card.card_number,
        'name': card.name,
        'rarity': card.rarity,
        'is_mirror': card.is_mirror,
        'mirror_type': card.mirror_type,
        'image_url': card.image_url,
    })

# JSON 파일로 저장
with open('japan_cards_export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ 완료!")
print(f"확장팩: {len(data['expansions'])}개")
print(f"카드: {len(data['cards'])}개")
print(f"파일: japan_cards_export.json")