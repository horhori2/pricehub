from django.db import migrations

def normalize_sp_rarity(apps, schema_editor):
    OnePieceCard = apps.get_model('pricehub', 'OnePieceCard')
    updated = OnePieceCard.objects.filter(
        rarity__startswith='SP-'
    ).update(rarity='SP')
    print(f"\n  ✅ SP 레어도 정규화: {updated}개 업데이트")

def reverse_normalize(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0022_alter_card_selling_price_and_more'),  # ← 수정
    ]

    operations = [
        migrations.RunPython(normalize_sp_rarity, reverse_normalize),
    ]