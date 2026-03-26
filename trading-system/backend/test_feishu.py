#!/usr/bin/env python3
"""
飞书通知测试脚本
"""
import asyncio
import os
from dotenv import load_dotenv
from app.services.notification_agent import FeishuNotifier

load_dotenv()


async def test_feishu_notification():
    """测试飞书通知功能"""
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    chat_id = os.getenv("FEISHU_CHAT_ID", "")

    print(f"App ID: {'已配置' if app_id else '未配置'}")
    print(f"App Secret: {'已配置' if app_secret else '未配置'}")
    print(f"Chat ID: {chat_id if chat_id else '未配置'}")

    if not app_id or not app_secret:
        print("❌ 错误：请在 .env 文件中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return

    # 创建通知器实例（chat_id 会自动从环境变量读取）
    notifier = FeishuNotifier()
    notifier.configure(
        app_id=app_id,
        app_secret=app_secret,
        enabled=True,
        chat_id=chat_id
    )

    print("\n🚀 开始发送测试消息...\n")

    # 测试 1: 买入通知
    print("测试 1: 买入通知")
    result = await notifier.notify_trade(
        action="buy",
        coin="BTC",
        price=65000.50,
        amount=100.00,
        pnl_percent=0,
        reason="趋势评分8分，突破MA20"
    )
    print(f"  结果: {'✅ 成功' if result else '❌ 失败'}\n")
    await asyncio.sleep(1)

    # 测试 2: 卖出通知
    print("测试 2: 卖出通知")
    result = await notifier.notify_trade(
        action="sell",
        coin="ETH",
        price=3200.75,
        amount=50.00,
        pnl_percent=5.5,
        reason="达到止盈目标"
    )
    print(f"  结果: {'✅ 成功' if result else '❌ 失败'}\n")
    await asyncio.sleep(1)

    # 测试 3: 金字塔加仓通知
    print("测试 3: 金字塔加仓通知")
    result = await notifier.notify_trade(
        action="pyramid_buy",
        coin="SOL",
        price=145.30,
        amount=75.00,
        pnl_percent=-3.2,
        reason="金字塔加仓第2层"
    )
    print(f"  结果: {'✅ 成功' if result else '❌ 失败'}\n")
    await asyncio.sleep(1)

    # 测试 4: 错误通知
    print("测试 4: 错误通知")
    result = await notifier.notify_error(
        error_type="API连接失败",
        error_message="无法连接到OKX交易所API",
        context="尝试获取账户余额时发生错误"
    )
    print(f"  结果: {'✅ 成功' if result else '❌ 失败'}\n")

    print("🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_feishu_notification())
