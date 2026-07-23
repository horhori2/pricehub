# import_japan_cards.py
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanExpansion, JapanCard

print("일본판 카드 데이터 가져오기...")

# JSON 파일 읽기
with open('japan_cards_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 확장팩 생성
expansion_map = {}
for exp_data in data['expansions']:
    expansion, created = JapanExpansion.objects.update_or_create(
        code=exp_data['code'],
        defaults={
            'name': exp_data['name'],
            'release_date': datetime.fromisoformat(exp_data['release_date']) if exp_data['release_date'] else None,
            'image_url': exp_data['image_url'],
        }
    )
    expansion_map[exp_data['code']] = expansion
    status = "생성" if created else "업데이트"
    print(f"{status}: {expansion.name}")

# 카드 생성
created_count = 0
updated_count = 0

for card_data in data['cards']:
    expansion = expansion_map[card_data['expansion_code']]
    
    card, created = JapanCard.objects.update_or_create(
        shop_product_code=card_data['shop_product_code'],
        defaults={
            'expansion': expansion,
            'card_number': card_data['card_number'],
            'name': card_data['name'],
            'rarity': card_data['rarity'],
            'is_mirror': card_data['is_mirror'],
            'mirror_type': card_data['mirror_type'],
            'image_url': card_data['image_url'],
        }
    )
    
    if created:
        created_count += 1
    else:
        updated_count += 1

print(f"\n✅ 완료!")
print(f"확장팩: {len(data['expansions'])}개")
print(f"카드 생성: {created_count}개")
print(f"카드 업데이트: {updated_count}개")