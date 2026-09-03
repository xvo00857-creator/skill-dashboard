"""order_validator 的单元测试。"""
import unittest

from order_validator import validate_order_amount


class TestValidateOrderAmount(unittest.TestCase):
    """基线：金额必须为正数。"""

    def test_positive_amount_passes(self):
        self.assertIsNone(validate_order_amount(100))

    def test_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_amount(0)

    def test_negative_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_amount(-1)

    def test_non_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_amount("100")

    def test_amount_at_max_limit_passes(self):
        # 边界值：1,000,000（含）应通过
        self.assertIsNone(validate_order_amount(1_000_000))

    def test_amount_over_max_limit_is_rejected(self):
        # 超出上限：1,000,000.01 应拒绝
        with self.assertRaises(ValueError):
            validate_order_amount(1_000_000.01)


if __name__ == "__main__":
    unittest.main()
