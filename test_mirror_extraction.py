# test_mirror_extraction.py
import re

def extract_mirror_type(card_name: str) -> str:
    """미러 타입 추출"""
    print(f"\n[테스트] 카드명: {card_name}")
    
    # (타입/ミラー仕様) 또는 (타입/ミ) 패턴에서 타입 추출
    match = re.search(r'\((.+?)(?:/ミラー仕様|/ミ)\)', card_name)
    if match:
        mirror_type = match.group(1).strip()
        print(f"[결과] 미러 타입: '{mirror_type}'")
        return mirror_type
    
    # (ミラー仕様) 만 있는 경우
    if 'ミラー仕様' in card_name or 'ミラー' in card_name:
        print(f"[결과] 기본 미러")
        return "基本ミラー"
    
    print(f"[결과] 미러 아님")
    return ""


def generate_japan_product_code(expansion_code: str, card_number: str, is_mirror: bool = False, mirror_type: str = "") -> str:
    """상품코드 생성"""
    product_code = f"PKM-{expansion_code}-{card_number}-J"
    
    if is_mirror:
        product_code += "-M"
        
        if mirror_type:
            if 'エネルギー' in mirror_type or 'エネルギーマーク' in mirror_type:
                product_code += "-ENERGY"
            elif 'マスターボール' in mirror_type:
                product_code += "-MASTERBALL"
            elif 'モンスターボール' in mirror_type:
                product_code += "-MONSTERBALL"
            elif 'ボール柄' in mirror_type:
                product_code += "-BALL"
            elif '基本' in mirror_type or mirror_type == "基本ミラー":
                product_code += "-BASIC"
            else:
                import hashlib
                type_hash = hashlib.md5(mirror_type.encode()).hexdigest()[:4].upper()
                product_code += f"-{type_hash}"
    
    print(f"[상품코드] {product_code}\n")
    return product_code


# 테스트 케이스
test_cases = [
    "イイネイヌ",
    "イイネイヌ(エネルギーマーク柄/ミラー仕様)",
    "イイネイヌ(ボール柄/ミラー仕様)",
    "キリキザン(モンスターボール柄/ミラー仕様)",
    "キリキザン(マスターボール柄/ミラー仕様)",
    "ホップのウールー(エネルギーマーク柄/ミ)",  # 짧은 표기
]

print("=" * 80)
print("미러 타입 추출 테스트")
print("=" * 80)

for card_name in test_cases:
    mirror_type = extract_mirror_type(card_name)
    is_mirror = bool(mirror_type)
    generate_japan_product_code("SV1V", "098", is_mirror, mirror_type)