# update_expansion_images.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Expansion

# 확장팩 이미지 URL 매핑
# 여기에 추가 확장팩 이미지 URL을 입력하세요
# 'CODE': 'IMAGE_URL',
EXPANSION_IMAGES = {
    'M2A': 'https://data1.pokemonkorea.co.kr/2025/12/2025-12-30_11-00-50-12772-1767060050.png',
    'M2': 'https://data1.pokemonkorea.co.kr/2025/11/2025-11-05_14-18-14-89295-1762319894.png',
    'M1S': 'https://data1.pokemonkorea.co.kr/2025/09/2025-09-04_19-09-25-19256-1756980565.png',
    'M1L':'https://data1.pokemonkorea.co.kr/2025/09/2025-09-04_19-10-23-72498-1756980623.png',
    'SV11W':'https://data1.pokemonkorea.co.kr/2025/07/2025-07-10_16-51-40-50682-1752133900.png',
    'SV11B':'https://data1.pokemonkorea.co.kr/2025/07/2025-07-10_16-51-13-13534-1752133873.png',
    'SV10':'https://data1.pokemonkorea.co.kr/2025/05/2025-05-28_17-24-50-69720-1748420690.png',
    'SV9A':'https://data1.pokemonkorea.co.kr/2025/04/2025-04-16_17-03-55-83045-1744790635.png',
    'SV9':'https://data1.pokemonkorea.co.kr/2025/02/2025-02-19_14-48-06-72993-1739944086.png',
    'SV8A':'https://data1.pokemonkorea.co.kr/2025/01/2025-01-06_10-32-05-76621-1736127125.png',
    'SV8':'https://data1.pokemonkorea.co.kr/2024/11/2024-11-08_18-12-04-80523-1731057124.png',
    'SV7A':'https://data1.pokemonkorea.co.kr/2024/10/2024-10-08_16-37-12-71372-1728373032.png',
    'SV7':'https://data1.pokemonkorea.co.kr/2024/08/2024-08-23_10-19-28-23364-1724375968.png',
    'SV6A':'https://data1.pokemonkorea.co.kr/2024/07/2024-07-19_18-38-46-20537-1721381926.png',
    'SV6':'https://data1.pokemonkorea.co.kr/2024/06/2024-06-05_18-31-47-27996-1717579907.png',
    'SV5A':'https://data1.pokemonkorea.co.kr/2024/06/2024-06-05_18-31-47-27996-1717579907.png',
    'SV5M':'https://data1.pokemonkorea.co.kr/2024/02/2024-02-21_17-45-14-54933-1708505114.png',
    'SV5K':'https://data1.pokemonkorea.co.kr/2024/02/2024-02-21_17-50-13-57832-1708505413.png',
    'SV4A':'https://data1.pokemonkorea.co.kr/2024/01/2024-01-16_09-54-41-42969-1705366481.png',
    'SV4M':'https://data1.pokemonkorea.co.kr/2023/11/2023-11-17_18-30-43-72211-1700213443.png',
    'SV4K':'https://data1.pokemonkorea.co.kr/2023/11/2023-11-20_10-30-47-46597-1700443847.png',
    'SV3A':'https://data1.pokemonkorea.co.kr/2023/10/2023-10-10_19-38-31-50929-1696934311.png',
    'SV3':'https://data1.pokemonkorea.co.kr/2023/08/2023-08-17_16-12-59-33370-1692256379.png',
    'SV2A':'https://data1.pokemonkorea.co.kr/2023/07/2023-07-24_19-49-34-75204-1690195774.png',
    'SV2D':'https://data1.pokemonkorea.co.kr/2023/06/2023-06-07_14-03-41-77039-1686114221.png',
    'SV2P':'https://data1.pokemonkorea.co.kr/2025/03/2025-03-28_15-16-28-22396-1743142588.png',
    'SV1A':'https://data1.pokemonkorea.co.kr/2023/04/2023-04-21_15-16-01-13152-1682057761.png',
    'SV1V':'https://data1.pokemonkorea.co.kr/2023/03/2023-03-20_13-45-25-84143-1679287525.png',
    'SV1S':'https://data1.pokemonkorea.co.kr/2023/03/2023-03-20_13-45-32-57955-1679287532.png',
    'S12A':'https://data1.pokemonkorea.co.kr/2023/01/2023-01-02_09-19-35-27619-1672618775.png',
    'S12':'https://data1.pokemonkorea.co.kr/2022/11/2022-11-22_15-43-09-17892-1669099389.png',
    'S11A':'https://data1.pokemonkorea.co.kr/2022/10/2022-10-06_18-14-27-98043-1665047667.png',
    'S11':'https://data1.pokemonkorea.co.kr/2022/08/2022-08-26_18-33-40-36466-1661506420.png',
    'S10A':'https://data1.pokemonkorea.co.kr/2022/07/2022-07-18_14-26-37-61722-1658121997.png',
    'S10B':'https://data1.pokemonkorea.co.kr/2022/06/2022-06-09_17-20-14-11650-1654762814.png',
    'S10P':'https://data1.pokemonkorea.co.kr/2022/05/2022-05-19_17-12-13-51411-1652947933.png',
    'S10D':'https://data1.pokemonkorea.co.kr/2022/05/2022-05-19_17-21-18-82300-1652948478.png',
    'S9A':'https://data1.pokemonkorea.co.kr/2022/04/2022-04-21_16-42-42-37997-1650526962.png',
    'S9':'https://data1.pokemonkorea.co.kr/2022/02/2022-02-18_15-17-47-21906-1645165067.png',
    'S8B':'https://data1.pokemonkorea.co.kr/2022/01/2022-01-14_17-03-30-66162-1642147410.png',
    'S8':'https://data1.pokemonkorea.co.kr/2021/11/2021-11-19_18-00-03-99266-1637312403.png',
    'S8A':'https://data1.pokemonkorea.co.kr/2021/10/2021-10-15_16-01-01-13015-1634281261.png',
    'S7R':'https://data1.pokemonkorea.co.kr/2021/08/2021-08-31_11-20-11-76653-1630376411.png',
    'S7D':'https://data1.pokemonkorea.co.kr/2021/08/2021-08-31_11-22-21-59233-1630376541.png',
    'S6A':'https://data1.pokemonkorea.co.kr/2021/07/2021-07-22_11-54-15-63258-1626922455.png',
    'S6K':'https://data1.pokemonkorea.co.kr/2021/05/2021-05-12_15-02-00-25111-1620799320.png',
    'S6H':'https://data1.pokemonkorea.co.kr/2021/05/2021-05-12_15-03-18-80959-1620799398.png',
    'S5A':'https://data1.pokemonkorea.co.kr/2021/04/2021-04-06_17-45-17-83293-1617698717.png',
    'S5R':'https://data1.pokemonkorea.co.kr/2021/01/2021-01-28_14-56-56-52460-1611813416.png',
    'S5I':'https://data1.pokemonkorea.co.kr/2021/01/2021-01-28_15-19-19-81846-1611814759.png',
    'S4A':'https://data1.pokemonkorea.co.kr/2020/11/2020-11-26_18-20-13-99929-1606382413.png',
    'S4':'https://data1.pokemonkorea.co.kr/2020/10/2020-10-07_18-03-37-36741-1602061417.png',
    'S3A':'https://data1.pokemonkorea.co.kr/2020/09/2020-09-09_11-56-00-27651-1599620160.png',
    'S3':'https://data1.pokemonkorea.co.kr/2020/07/2020-07-10_18-14-20-33148-1594372460.png',
    'S2A':'https://data1.pokemonkorea.co.kr/2020/06/2020-06-03_09-51-03-72811-1591145463.png',
    'S2':'https://data1.pokemonkorea.co.kr/2020/04/2020-04-09_15-43-53-72986-1586414633.png',
    'S1A':'https://data1.pokemonkorea.co.kr/2020/03/2020-03-10_10-13-14-18944-1583802794.png',
    'S1H':'https://data1.pokemonkorea.co.kr/2020/01/2020-01-21_18-29-43-51796-1579598983.gif',
    'S1W':'https://data1.pokemonkorea.co.kr/2020/01/2020-01-21_18-29-43-51796-1579598983.gif',
}


def update_expansion_images(dry_run=True):
    """확장팩 이미지 URL 업데이트"""
    
    mode_text = "테스트 모드 (실제 저장 안 함)" if dry_run else "실제 저장 모드"
    
    print("\n" + "=" * 80)
    print(f"🖼️  확장팩 이미지 URL 업데이트 - {mode_text}")
    print("=" * 80)
    
    updated_count = 0
    not_found_count = 0
    skipped_count = 0
    
    for code, image_url in EXPANSION_IMAGES.items():
        try:
            expansion = Expansion.objects.get(code=code)
            
            # 이미 이미지가 있는 경우
            if expansion.image_url and expansion.image_url.strip():
                print(f"[건너뜀] {code} ({expansion.name}) - 이미 이미지 URL 존재")
                print(f"         기존: {expansion.image_url}")
                skipped_count += 1
                continue
            
            print(f"[업데이트] {code} ({expansion.name})")
            print(f"          URL: {image_url}")
            
            if not dry_run:
                expansion.image_url = image_url
                expansion.save()
                print(f"          ✅ 저장 완료")
            
            updated_count += 1
            
        except Expansion.DoesNotExist:
            print(f"[미발견] {code} - DB에 존재하지 않는 확장팩")
            not_found_count += 1
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 업데이트 완료")
    print("=" * 80)
    print(f"✅ 업데이트됨: {updated_count}개")
    print(f"⏭️  건너뜀: {skipped_count}개 (이미 이미지 존재)")
    print(f"❌ 미발견: {not_found_count}개")


def show_all_expansions():
    """모든 확장팩 목록 출력 (이미지 URL 상태 포함)"""
    print("\n" + "=" * 80)
    print("📦 모든 확장팩 목록")
    print("=" * 80)
    
    expansions = Expansion.objects.all().order_by('code')
    
    has_image_count = 0
    no_image_count = 0
    
    for expansion in expansions:
        has_image = expansion.image_url and expansion.image_url.strip()
        status = "✅ 있음" if has_image else "❌ 없음"
        
        print(f"\n코드: {expansion.code}")
        print(f"이름: {expansion.name}")
        print(f"이미지: {status}")
        
        if has_image:
            print(f"URL: {expansion.image_url}")
            has_image_count += 1
        else:
            no_image_count += 1
    
    print("\n" + "=" * 80)
    print(f"이미지 있음: {has_image_count}개")
    print(f"이미지 없음: {no_image_count}개")
    print(f"총: {expansions.count()}개")


def force_update_expansion_images():
    """기존 이미지 URL이 있어도 강제로 업데이트"""
    
    print("\n" + "=" * 80)
    print("🖼️  확장팩 이미지 URL 강제 업데이트")
    print("=" * 80)
    print("⚠️  이 작업은 기존 이미지 URL을 덮어씁니다!")
    
    confirm = input("\n계속하시겠습니까? (yes/no): ")
    if confirm.lower() != 'yes':
        print("취소되었습니다.")
        return
    
    updated_count = 0
    not_found_count = 0
    
    for code, image_url in EXPANSION_IMAGES.items():
        try:
            expansion = Expansion.objects.get(code=code)
            
            old_url = expansion.image_url
            print(f"\n[강제 업데이트] {code} ({expansion.name})")
            
            if old_url and old_url.strip():
                print(f"              기존: {old_url}")
            
            print(f"              새로: {image_url}")
            
            expansion.image_url = image_url
            expansion.save()
            print(f"              ✅ 저장 완료")
            
            updated_count += 1
            
        except Expansion.DoesNotExist:
            print(f"\n[미발견] {code} - DB에 존재하지 않는 확장팩")
            not_found_count += 1
    
    print("\n" + "=" * 80)
    print("✅ 강제 업데이트 완료")
    print(f"업데이트됨: {updated_count}개")
    print(f"미발견: {not_found_count}개")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🖼️  확장팩 이미지 URL 관리 도구")
    print("=" * 80)
    
    print("\n선택하세요:")
    print("  1. 테스트 모드 (이미지가 없는 확장팩만 업데이트 - 실제 저장 안 함)")
    print("  2. 실제 저장 모드 (이미지가 없는 확장팩만 업데이트)")
    print("  3. 강제 업데이트 (기존 이미지 URL 덮어쓰기)")
    print("  4. 모든 확장팩 목록 보기")
    print("  5. 종료")
    
    choice = input("\n선택 (1/2/3/4/5): ").strip()
    
    if choice == '1':
        print("\n⚠️  테스트 모드로 실행합니다. 실제로 DB에 저장되지 않습니다.\n")
        update_expansion_images(dry_run=True)
    
    elif choice == '2':
        confirm = input("\n⚠️  실제로 DB에 저장하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            update_expansion_images(dry_run=False)
        else:
            print("취소되었습니다.")
    
    elif choice == '3':
        force_update_expansion_images()
    
    elif choice == '4':
        show_all_expansions()
    
    elif choice == '5':
        print("종료합니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")