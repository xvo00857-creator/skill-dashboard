#!/usr/bin/env python3
"""基于 v1 生成 v2 草稿（含问题的批量订单接口设计）。仅用于构造审查对象，不修改 Skill 文件。"""
import json, copy, pathlib

base = pathlib.Path(__file__).parent
v1 = json.loads((base / "openapi-v1.json").read_text(encoding="utf-8"))
d = copy.deepcopy(v1)

# 版本号提升
d["info"]["version"] = "1.1.0"

# 破坏性变更：把现有 Order 响应 schema 中的 totalAmount 改名为 total_amount（snake_case）
order_props = d["components"]["schemas"]["Order"]["properties"]
order_req = d["components"]["schemas"]["Order"]["required"]
del order_props["totalAmount"]
order_req.remove("totalAmount")
order_props["total_amount"] = {
    "type": "number",
    "description": "订单总金额"
}
order_req.append("total_amount")

# 新增有问题的批量创建 schema（snake_case 字段 + 敏感字段未保护）
d["components"]["schemas"]["BatchOrderItem"] = {
    "type": "object",
    "properties": {
        "customer_id": {"type": "string"},
        "product_list": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sku_id": {"type": "string"},
                    "qty": {"type": "integer"},
                    "price": {"type": "number"}
                }
            }
        },
        "total_price": {"type": "number"},
        "currency": {"type": "string"},
        "webhook_secret": {"type": "string", "description": "回调签名密钥，创建后原样返回"},
        "card_last_four": {"type": "string"},
        "internal_note": {"type": "string"}
    }
}

d["components"]["schemas"]["BatchCreateRequest"] = {
    "type": "object",
    "properties": {
        "order_list": {
            "type": "array",
            "items": {"$ref": "#/components/schemas/BatchOrderItem"}
        },
        "idempotency_key": {"type": "string", "description": "幂等键放在请求体里"}
    }
}

# 新增有问题的批量端点：动词式 snake_case 路径、无幂等头、无错误响应、无文档、响应结构不一致
d["paths"]["/orders/batch_create"] = {
    "post": {
        "tags": ["Orders"],
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/BatchCreateRequest"}
                }
            }
        },
        "responses": {
            "200": {
                "description": "successful operation",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "result": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/BatchOrderItem"}
                                },
                                "count": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        }
    }
}

(base / "openapi-v2-draft.json").write_text(
    json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("written openapi-v2-draft.json")
