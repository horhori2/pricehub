# delete_japan_card_prices.py
import os
import django
from pricehub.models import JapanCardPrice

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')
django.setup()



def delete_japan_card_prices():
    """japan_card_price 테이블의 모든 데이터를 삭제"""
    
    # 삭제 전 데이터 개수 확인
    count = JapanCardPrice.objects.count()
    print(f"삭제 전 데이터 개수: {count}개")
    
    if count == 0:
        print("삭제할 데이터가 없습니다.")
        return
    
    # 사용자 확인
    confirm = input(f"\n정말로 {count}개의 데이터를 삭제하시겠습니까? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # 모든 데이터 삭제
        deleted_count, _ = JapanCardPrice.objects.all().delete()
        print(f"\n✓ {deleted_count}개의 데이터가 삭제되었습니다.")
    else:
        print("\n삭제가 취소되었습니다.")

if __name__ == '__main__':
    delete_japan_card_prices()