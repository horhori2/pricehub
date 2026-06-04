from django.db import migrations, models

def manga_to_rarity(apps, schema_editor):
    OnePieceCard = apps.get_model('pricehub', 'OnePieceCard')
    updated = OnePieceCard.objects.filter(is_manga=True).update(rarity='MANGA')
    print(f"\n  ✅ 망가 카드 레어도 변환: {updated}개 → MANGA")

def reverse_manga(apps, schema_editor):
    OnePieceCard = apps.get_model('pricehub', 'OnePieceCard')
    OnePieceCard.objects.filter(rarity='MANGA').update(is_manga=True)

class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0023_normalize_onepiece_sp_rarity'),
    ]

    operations = [
        # 1. is_manga=True인 카드를 rarity='MANGA'로 변환
        migrations.RunPython(manga_to_rarity, reverse_manga),
        # 2. is_manga 컬럼 삭제
        migrations.RemoveField(
            model_name='onepiececard',
            name='is_manga',
        ),
    ]