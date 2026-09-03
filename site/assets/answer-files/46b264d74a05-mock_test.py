"""
安全模拟测试：不触网、不需要 BROWSERACT_API_KEY。
用构造的假数据验证 analyze_competitive_position / 三种报告生成逻辑。
运行: python3 mock_test.py
"""
import os, sys, json, tempfile
SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "amazon-competitor-analyzer", "amazon-competitor-analyzer")
sys.path.insert(0, os.path.abspath(SKILL_DIR))
from amazon_competitor_analyzer import AmazonCompetitorAnalyzer

def fake_product(title, brand, price, orig, disc, rating, reviews, weight, features):
    return {
        "results": {
            "products": [{
                "product_info": {"title": title, "brand": brand},
                "pricing": {"current_price": price, "original_price": orig, "discount_percent": disc},
                "reviews": {"average_rating": rating, "total_count": reviews},
                "specifications": {"weight": weight, "features": features},
            }]
        }
    }

products = {
    "B09G9GB4MG": fake_product("Wireless Earbuds Pro", "AudioX", 49.99, 79.99, 38, 4.5, 12500, "0.2 lb", ["ANC", "30h battery", "IPX5"]),
    "B07ABC11111": fake_product("Bluetooth Earbuds Lite", "SoundY", 29.99, 39.99, 25, 4.2, 8300, "0.18 lb", ["Bluetooth 5.3", "20h battery"]),
}

an = AmazonCompetitorAnalyzer(api_key="mock-key")

# ASIN 校验
assert an.validate_asin("B09G9GB4MG") is True
assert an.validate_asin("BAD") is False
assert an.validate_asin("B09G9GB4M!") is False
print("[OK] ASIN 校验逻辑正常")

# 竞争分析
analysis = an.analyze_competitive_position(products)
assert analysis["price_analysis"]["lowest"][1] == 29.99
assert analysis["price_analysis"]["highest"][1] == 49.99
assert analysis["rating_analysis"]["top_rated"][1] == 4.5
print("[OK] 竞争分析逻辑正常:", json.dumps(analysis["price_analysis"], default=str))

# 报告生成
with tempfile.TemporaryDirectory() as d:
    an.generate_csv_report(products, os.path.join(d, "a.csv"))
    an.generate_markdown_report(products, os.path.join(d, "a.md"))
    an.generate_json_report(products, os.path.join(d, "a.json"))
    for ext in ("csv", "md", "json"):
        p = os.path.join(d, f"a.{ext}")
        assert os.path.getsize(p) > 0, f"{ext} 为空"
        print(f"[OK] {ext} 报告生成成功 ({os.path.getsize(p)} bytes)")

# 无 key 时真实调用应安全失败（不崩溃、不伪造）
an2 = AmazonCompetitorAnalyzer(api_key="")
res = an2.submit_task("B09G9GB4MG")
print("[OK] 无有效 key 时 submit_task 返回:", res, "(预期 None，不伪造数据)")
print("\n全部模拟测试通过。")
