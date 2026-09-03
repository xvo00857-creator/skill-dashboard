"""订单金额校验模块。"""

# 单笔订单金额上限（含）
MAX_ORDER_AMOUNT = 1_000_000


def validate_order_amount(amount):
    """校验订单金额是否合法。

    合法条件：金额必须为正数（大于 0），且不超过 MAX_ORDER_AMOUNT。
    合法返回 None；不合法抛出 ValueError。
    """
    if not isinstance(amount, (int, float)):
        raise ValueError("金额必须为数字")
    if amount <= 0:
        raise ValueError("金额必须大于 0")
    if amount > MAX_ORDER_AMOUNT:
        raise ValueError("金额超过单笔上限")
    return None
