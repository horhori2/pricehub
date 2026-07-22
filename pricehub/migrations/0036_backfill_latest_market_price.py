# Generated manually — backfills the latest_market_price 캐시 컬럼
# for existing rows from each card's most recent CardPrice.

from django.db import migrations


# (card 테이블, card_price 테이블) 쌍 — db_table 이름 그대로 사용.
_TABLE_PAIRS = [
    ('card', 'card_price'),
    ('onepiece_card', 'onepiece_card_price'),
    ('digimon_card', 'digimon_card_price'),
]

# card_price 테이블에 이미 있는 (card_id, -collected_at) 인덱스를 타도록
# GROUP BY로 최신 collected_at을 먼저 구하고, 그 값으로 다시 조인해서
# price를 가져온다. 카드 수만큼 서브쿼리를 반복하는 방식(예전 뷰 로직)보다
# 훨씬 빠르다.
_BACKFILL_SQL = """
UPDATE `{card_table}` c
JOIN (
    SELECT card_id, MAX(collected_at) AS max_collected_at
    FROM `{price_table}`
    GROUP BY card_id
) m ON m.card_id = c.id
JOIN `{price_table}` cp ON cp.card_id = m.card_id AND cp.collected_at = m.max_collected_at
SET c.latest_market_price = cp.price
"""


def backfill(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for card_table, price_table in _TABLE_PAIRS:
            cursor.execute(_BACKFILL_SQL.format(card_table=card_table, price_table=price_table))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0035_card_latest_market_price_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
