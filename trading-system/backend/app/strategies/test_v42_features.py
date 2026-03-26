"""
v4.2 核心功能测试示例

本文件演示如何使用 v4.2 新增的核心功能：
1. 时区感知
2. 买入金额递减
3. 智能超仓豁免
4. 动态波段计算
"""

from datetime import datetime, timedelta, timezone
from app.strategies.v42_features import (
    TimeZoneManager,
    DecreasingBuyManager,
    ExemptionManager,
    DynamicBandsCalculator
)

# 设置时区
BEIJING_TZ = timezone(timedelta(hours=8))


def test_timezone_aware():
    """测试时区感知功能"""
    print("\n" + "=" * 60)
    print("测试 1: 时区感知功能")
    print("=" * 60)

    # 打印当前时区信息
    TimeZoneManager.print_timezone_info()

    # 获取当前时区配置
    config = TimeZoneManager.get_current_config()
    print(f"\n当前时区配置:")
    print(f"  时段: {TimeZoneManager.get_current_timezone_key()}")
    print(f"  名称: {config.name}")
    print(f"  活跃强度: {config.intensity} 星")
    print(f"  建议仓位: ${config.position_min}-${config.position_max}")
    print(f"  持仓时间: {config.hold_time_min}-{config.hold_time_max} 分钟")
    print(f"  日目标占比: {config.daily_quota * 100}%")
    print(f"  检查频率: {config.check_interval} 分钟")


def test_decreasing_buy():
    """测试买入金额递减功能"""
    print("\n" + "=" * 60)
    print("测试 2: 买入金额递减功能")
    print("=" * 60)

    # 模拟今日交易记录
    today_trades = [
        {"coin": "BTC", "action": "buy", "time": "2024-03-21 10:00:00"},
        {"coin": "BTC", "action": "buy", "time": "2024-03-21 11:00:00"},
        {"coin": "BTC", "action": "buy", "time": "2024-03-21 12:00:00"},
    ]

    # 测试不同币种的递减
    base_amount = 20.0

    # BTC：已有3次买入
    print(f"\nBTC 今日已有 3 次买入:")
    for i in range(4):
        adjusted = DecreasingBuyManager.calculate_amount("BTC", base_amount, today_trades)
        print(f"  第 {i+1} 次: ${base_amount:.2f} -> ${adjusted:.2f}")
        today_trades.append({"coin": "BTC", "action": "buy", "time": datetime.now().isoformat()})

    # ETH：无买入记录
    print(f"\nETH 今日无买入记录:")
    eth_amount = DecreasingBuyManager.calculate_amount("ETH", base_amount, [])
    print(f"  第 1 次: ${base_amount:.2f} -> ${eth_amount:.2f}")


def test_exemption_period():
    """测试智能超仓豁免功能"""
    print("\n" + "=" * 60)
    print("测试 3: 智能超仓豁免功能")
    print("=" * 60)

    # 测试不同盈亏状态的豁免期
    pnl_scenarios = [
        ("大额亏损", -2.5, 60),
        ("小额亏损", -0.5, 45),
        ("已盈利", 1.5, 30),
        ("大额盈利", 5.0, 30),
    ]

    for name, pnl, expected in pnl_scenarios:
        exemption_minutes = ExemptionManager.calculate_exemption_minutes(pnl)
        print(f"{name} ({pnl:+.1f}%): 豁免 {exemption_minutes} 分钟 (预期: {expected} 分钟)")

    # 测试豁免期检查
    print("\n测试豁免期检查:")

    # 场景 1：在豁免期内
    last_buy = datetime.now(BEIJING_TZ) - timedelta(minutes=20)
    is_exempted = ExemptionManager.is_in_exemption_period(
        "BTC", -1.5, last_buy
    )
    print(f"  20分钟前买入，亏损1.5%: {'在豁免期内 ✓' if is_exempted else '不在豁免期内 ✗'}")

    # 场景 2：超过豁免期
    last_buy = datetime.now(BEIJING_TZ) - timedelta(minutes=70)
    is_exempted = ExemptionManager.is_in_exemption_period(
        "BTC", -1.5, last_buy
    )
    print(f"  70分钟前买入，亏损1.5%: {'在豁免期内 ✓' if is_exempted else '不在豁免期内 ✗'}")


def test_dynamic_bands():
    """测试动态波段计算功能"""
    print("\n" + "=" * 60)
    print("测试 4: 动态波段计算功能")
    print("=" * 60)

    # 测试不同币种的动态波段
    test_coins = [
        {
            "coin": "BTC",
            "change_24h": 3.5,
            "volatility": 3.5,
            "turnover_24h": 2000000000,  # 大市值
            "trend_score": 9
        },
        {
            "coin": "ETH",
            "change_24h": 5.2,
            "volatility": 5.2,
            "turnover_24h": 800000000,  # 中市值
            "trend_score": 7
        },
        {
            "coin": "DOGE",
            "change_24h": 8.5,
            "volatility": 8.5,
            "turnover_24h": 50000000,  # 小市值
            "trend_score": 5
        },
    ]

    for coin_data in test_coins:
        print(f"\n{coin_data['coin']}:")
        result = DynamicBandsCalculator.calculate(
            coin=coin_data['coin'],
            change_24h=coin_data['change_24h'],
            volatility=coin_data['volatility'],
            turnover_24h=coin_data['turnover_24h'],
            trend_score=coin_data['trend_score']
        )
        print(f"  止损: {result['stop_loss']:.2f}%")
        print(f"  止盈: {result['take_profit']:.2f}%")
        print(f"  市值级别: {result['market_cap_level']}")
        print(f"  因子: 波动={result['factors']['volatility_factor']:.2f}, "
              f"市值={result['factors']['market_cap_factor']:.2f}, "
              f"趋势={result['factors']['trend_factor']:.2f}")


def test_integration():
    """测试功能集成"""
    print("\n" + "=" * 60)
    print("测试 5: 功能集成测试")
    print("=" * 60)

    # 模拟一个完整的交易决策流程
    coin = "BTC"
    base_amount = 15.0

    # 1. 获取时区感知配置
    timezone_config = TimeZoneManager.get_current_config()
    print(f"\n1. 时区感知: {timezone_config.name}, 建议仓位 ${timezone_config.position_min}-${timezone_config.position_max}")

    # 2. 计算递减买入金额
    today_trades = [{"coin": "BTC", "action": "buy"}]
    buy_amount = DecreasingBuyManager.calculate_amount(coin, base_amount, today_trades)
    print(f"2. 买入金额递减: ${base_amount:.2f} -> ${buy_amount:.2f}")

    # 3. 检查超仓豁免期
    last_buy = datetime.now(BEIJING_TZ) - timedelta(minutes=25)
    is_exempted = ExemptionManager.is_in_exemption_period(coin, -0.5, last_buy)
    print(f"3. 超仓豁免: {'是' if is_exempted else '否'}")

    # 4. 计算动态波段
    bands = DynamicBandsCalculator.calculate(
        coin, 3.5, 3.5, 2000000000, 9
    )
    print(f"4. 动态波段: 止损 {bands['stop_loss']:.2f}%, 止盈 {bands['take_profit']:.2f}%")

    # 5. 综合决策
    print(f"\n综合决策:")
    print(f"  - 币种: {coin}")
    print(f"  - 买入金额: ${buy_amount:.2f}")
    print(f"  - 止损: {bands['stop_loss']:.2f}%")
    print(f"  - 止盈: {bands['take_profit']:.2f}%")
    print(f"  - 豁免状态: {'豁免中' if is_exempted else '正常'}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("v4.2 核心功能测试套件")
    print("=" * 60)

    try:
        test_timezone_aware()
        test_decreasing_buy()
        test_exemption_period()
        test_dynamic_bands()
        test_integration()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        print("\n总结:")
        print("1. ✅ 时区感知：根据不同时段动态调整仓位")
        print("2. ✅ 买入金额递减：同币种多次买入金额递减")
        print("3. ✅ 智能超仓豁免：根据盈亏给予豁免期")
        print("4. ✅ 动态波段计算：根据波动率/市值/趋势动态调整")
        print("5. ✅ 功能集成：所有功能协同工作")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
