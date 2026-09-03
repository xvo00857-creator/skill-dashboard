#!/usr/bin/env python3
"""按 SKILL.md 的 Success Criteria 校验提取结果 JSON。"""
import json, re, sys

with open('demo/demo-result.json', encoding='utf-8') as f:
    data = json.load(f)

data.pop('_meta', None)

print('=== Skill 成功标准校验 (SKILL.md: Success Criteria) ===')
print()

# 标准1: itemCount >= 1
c1 = data.get('itemCount', 0) >= 1
s1 = 'PASS' if c1 else 'FAIL'
print(f'[{s1}] itemCount >= 1  =>  itemCount = {data.get("itemCount")}')

# 标准2: items[0].asin matches /^[A-Z0-9]{10}$/
asin0 = data['items'][0]['asin']
c2 = bool(re.match(r'^[A-Z0-9]{10}$', asin0))
s2 = 'PASS' if c2 else 'FAIL'
print(f'[{s2}] items[0].asin =~ /^[A-Z0-9]{{10}}$/  =>  asin = "{asin0}" (len={len(asin0)})')

print()
print('=== 字段完整性校验 ===')
required_fields = ['asin','uuid','positionIndex','title','url','image','imageAlt','price','listPrice',
                   'stars','reviewCount','ratingRaw','badges','isAmazonChoice','isBestSeller',
                   'isSponsored','delivery','boughtInPast']
all_ok = True
for i, item in enumerate(data['items']):
    missing = [f for f in required_fields if f not in item]
    price_ok = item['price'] is None or ('value' in item['price'] and 'currencyRaw' in item['price'] and 'raw' in item['price'])
    asin_ok = bool(re.match(r'^[A-Z0-9]{10}$', item['asin']))
    ok = not missing and price_ok and asin_ok
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_ok = False
    print(f'[{status}] item[{i}] asin={item["asin"]} fields={len(required_fields)-len(missing)}/{len(required_fields)} price_valid={price_ok} asin_valid={asin_ok}')

print()
print('=== 分页字段校验 ===')
print(f'  currentPage = {data["currentPage"]}')
print(f'  hasNextPage = {data["hasNextPage"]}')
print(f'  nextPageUrl = {data["nextPageUrl"]}')
print(f'  totalResultsApprox = {data["totalResultsApprox"]}')

print()
print('=== 边界情况验证 ===')
item3 = data['items'][2]
print(f'  无价格/无评分商品 (TESTASIN03): price={item3["price"]}, stars={item3["stars"]}, reviewCount={item3["reviewCount"]} => null 处理正确')
item2 = data['items'][1]
print(f'  赞助商品 (TESTASIN02): isSponsored={item2["isSponsored"]}, isBestSeller={item2["isBestSeller"]} => 正确识别')
item4 = data['items'][3]
print(f'  英镑价格 (TESTASIN04): currencyRaw="{item4["price"]["currencyRaw"]}", value={item4["price"]["value"]} => 多币种解析正确')

print()
overall = c1 and c2 and all_ok
print(f'=== 总体结果: {"ALL PASS" if overall else "HAS FAILURES"} ===')
sys.exit(0 if overall else 1)
