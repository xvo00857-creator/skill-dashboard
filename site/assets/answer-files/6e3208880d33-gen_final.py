#!/usr/bin/env python3
"""基于 v1 生成 v2 最终版（修复全部问题的批量订单接口）。仅新增端点与 schema，不改动现有契约。"""
import json, copy, pathlib

base = pathlib.Path(__file__).parent
v1 = json.loads((base / "openapi-v1.json").read_text(encoding="utf-8"))
d = copy.deepcopy(v1)

# 版本号提升（次版本，纯新增功能）
d["info"]["version"] = "1.1.0"
d["info"]["description"] = (
    "订单服务 REST API，提供订单的查询、单个创建与批量创建能力。"
    "所有接口均需 Bearer Token 认证，返回 JSON；批量接口支持 Idempotency-Key 幂等。"
)

# 新增批量结果相关 schema
d["components"]["schemas"]["BatchOrderResultItem"] = {
    "type": "object",
    "description": "批量创建中单条订单的处理结果",
    "required": ["index", "status"],
    "properties": {
        "index": {
            "type": "integer",
            "minimum": 0,
            "description": "该订单在请求数组中的下标，从 0 开始",
            "example": 0
        },
        "orderId": {
            "type": "integer",
            "format": "int64",
            "nullable": True,
            "description": "创建成功时的订单 ID；失败时为 null",
            "example": 1001
        },
        "status": {
            "type": "string",
            "enum": ["created", "failed", "conflict"],
            "description": "本条处理结果：created 成功、failed 失败、conflict 幂等冲突",
            "example": "created"
        },
        "error": {
            "type": "object",
            "nullable": True,
            "description": "失败时的错误信息；成功时为 null",
            "properties": {
                "code": {"type": "string", "description": "机器可读错误码", "example": "VALIDATION_ERROR"},
                "message": {"type": "string", "description": "人类可读错误描述", "example": "items 不能为空"}
            }
        },
        "links": {
            "type": "object",
            "description": "HATEOAS 导航链接",
            "properties": {
                "self": {
                    "type": "object",
                    "properties": {"href": {"type": "string", "example": "/orders/1001"}}
                }
            }
        }
    }
}

d["components"]["schemas"]["BatchOrderCreateRequest"] = {
    "type": "array",
    "description": "批量创建订单的请求体：订单创建对象数组，最少 1 条，最多 100 条。超过 100 条请改用异步批量导入。",
    "minItems": 1,
    "maxItems": 100,
    "items": {"$ref": "#/components/schemas/OrderCreateRequest"}
}

# 新增批量端点：名词子资源 /orders/batch，顶层 array 请求体，幂等头，完整错误响应
d["paths"]["/orders/batch"] = {
    "post": {
        "tags": ["Orders"],
        "summary": "批量创建订单",
        "description": (
            "在一次请求中创建最多 100 笔订单。请求体为订单创建对象数组（与 POST /orders 结构一致）。"
            "必须携带 Idempotency-Key 头：相同键+相同请求体在 24 小时内返回首次结果；"
            "相同键+不同请求体返回 409。全部成功返回 201；部分失败返回 200，逐笔给出结果。"
        ),
        "operationId": "batchCreateOrders",
        "parameters": [
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "description": "幂等键，UUID。服务端在 24 小时内对相同键+相同体返回首次结果；同键不同体返回 409。",
                "schema": {"type": "string", "format": "uuid"},
                "example": "a3bb189e-8bf9-3888-9912-ace4e6543002"
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "description": "订单创建对象数组，最少 1 条，最多 100 条。超过 100 条请改用异步批量导入。",
                        "minItems": 1,
                        "maxItems": 100,
                        "items": {"$ref": "#/components/schemas/OrderCreateRequest"}
                    },
                    "example": [
                        {
                            "customerId": "cust_001",
                            "currency": "CNY",
                            "items": [{"skuId": "sku_100", "quantity": 2, "unitPrice": 99.95}]
                        },
                        {
                            "customerId": "cust_002",
                            "currency": "CNY",
                            "items": [{"skuId": "sku_200", "quantity": 1, "unitPrice": 50.0}]
                        }
                    ]
                }
            }
        },
        "responses": {
            "201": {
                "description": "全部订单创建成功",
                "headers": {
                    "Location": {
                        "description": "批量结果资源路径（可用于查询本次批量结果）",
                        "schema": {"type": "string", "example": "/orders/batch/results/a3bb189e"}
                    }
                },
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["data", "meta"],
                            "properties": {
                                "data": {
                                    "type": "object",
                                    "required": ["results", "successCount", "failureCount", "hasFailures"],
                                    "properties": {
                                        "results": {
                                            "type": "array",
                                            "description": "逐笔处理结果",
                                            "items": {"$ref": "#/components/schemas/BatchOrderResultItem"}
                                        },
                                        "successCount": {"type": "integer", "description": "成功笔数", "example": 2},
                                        "failureCount": {"type": "integer", "description": "失败笔数", "example": 0},
                                        "hasFailures": {"type": "boolean", "description": "是否存在失败", "example": False}
                                    }
                                },
                                "meta": {"$ref": "#/components/schemas/Meta"},
                                "links": {
                                    "type": "object",
                                    "description": "HATEOAS 导航链接",
                                    "properties": {
                                        "self": {"type": "object", "properties": {"href": {"type": "string", "example": "/orders/batch"}}},
                                        "orders": {"type": "object", "properties": {"href": {"type": "string", "example": "/orders"}}}
                                    }
                                }
                            }
                        },
                        "example": {
                            "data": {
                                "results": [
                                    {"index": 0, "orderId": 1001, "status": "created", "error": None,
                                     "links": {"self": {"href": "/orders/1001"}}},
                                    {"index": 1, "orderId": 1002, "status": "created", "error": None,
                                     "links": {"self": {"href": "/orders/1002"}}}
                                ],
                                "successCount": 2,
                                "failureCount": 0,
                                "hasFailures": False
                            },
                            "meta": {"timestamp": "2026-08-12T10:00:00Z", "requestId": "req-batch-001"},
                            "links": {"self": {"href": "/orders/batch"}, "orders": {"href": "/orders"}}
                        }
                    }
                }
            },
            "200": {
                "description": "批量请求已处理，但存在部分失败",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["data", "meta"],
                            "properties": {
                                "data": {
                                    "type": "object",
                                    "required": ["results", "successCount", "failureCount", "hasFailures"],
                                    "properties": {
                                        "results": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/BatchOrderResultItem"}
                                        },
                                        "successCount": {"type": "integer", "example": 1},
                                        "failureCount": {"type": "integer", "example": 1},
                                        "hasFailures": {"type": "boolean", "example": True}
                                    }
                                },
                                "meta": {"$ref": "#/components/schemas/Meta"}
                            }
                        },
                        "example": {
                            "data": {
                                "results": [
                                    {"index": 0, "orderId": 1001, "status": "created", "error": None,
                                     "links": {"self": {"href": "/orders/1001"}}},
                                    {"index": 1, "orderId": None, "status": "failed",
                                     "error": {"code": "VALIDATION_ERROR", "message": "items 不能为空"}}
                                ],
                                "successCount": 1,
                                "failureCount": 1,
                                "hasFailures": True
                            },
                            "meta": {"timestamp": "2026-08-12T10:00:00Z", "requestId": "req-batch-002"}
                        }
                    }
                }
            },
            "400": {"description": "请求体不是数组或超过 100 条等结构错误", "$ref": "#/components/responses/BadRequest"},
            "401": {"description": "未认证或令牌无效", "$ref": "#/components/responses/Unauthorized"},
            "403": {"description": "已认证但无批量创建权限", "$ref": "#/components/responses/Forbidden"},
            "409": {"description": "Idempotency-Key 冲突：同键不同体", "$ref": "#/components/responses/Conflict"},
            "422": {"description": "全部条目语义校验失败，未创建任何订单", "$ref": "#/components/responses/Unprocessable"},
            "429": {"description": "触发限流，请按 Retry-After 退避", "$ref": "#/components/responses/RateLimited"},
            "500": {"description": "服务端内部错误", "$ref": "#/components/responses/InternalError"}
        }
    }
}

(base / "openapi-v2-final.json").write_text(
    json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("written openapi-v2-final.json")
