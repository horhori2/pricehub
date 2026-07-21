# pricehub/migrations/0033_hash_existing_api_keys.py
"""
기존에 평문으로 저장돼 있던 APIKey.key 값을 SHA-256 해시로 변환한다.

DB 스키마는 그대로다 (key 필드는 max_length=64라 해시 hex digest가 그대로 들어감).
클라이언트가 들고 있는 원본 키 값은 바뀌지 않으므로, 배포 후에도 기존
Authorization: Api-Key <원본키> 요청은 그대로 인증된다 (서버가 들어온 키를
해시해서 비교하는 방식으로 바뀌었을 뿐).

되돌릴 수 없는 단방향 해시라 reverse 마이그레이션으로 원본을 복원할 수는 없다.
"""
import hashlib

from django.db import migrations


def hash_existing_keys(apps, schema_editor):
    APIKey = apps.get_model('pricehub', 'APIKey')
    for row in APIKey.objects.all():
        # 이미 64자리 hex(해시)면 재적용하지 않음 — 마이그레이션 재실행/부분 적용 대비
        if len(row.key) == 64 and all(c in '0123456789abcdef' for c in row.key.lower()):
            continue
        row.key = hashlib.sha256(row.key.encode()).hexdigest()
        row.save(update_fields=['key'])


def noop_reverse(apps, schema_editor):
    # 단방향 해시라 원본 키를 복원할 수 없다. 되돌릴 수 없음을 명시하기 위한 no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0032_purchaselist_purchaselistitem'),
    ]

    operations = [
        migrations.RunPython(hash_existing_keys, noop_reverse),
    ]
