"""
外部数据源测试脚本
用于验证RSS、Twitter、LunarCrush功能是否正常工作
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external_data_sources import rss_monitor, twitter_monitor, lunarcrush_monitor
from app.services.external_data_service import external_data_service


async def test_rss_monitor():
    """测试RSS监控"""
    print("\n" + "=" * 60)
    print("测试 RSS 新闻监控")
    print("=" * 60)

    try:
        # 获取最新新闻
        news = await rss_monitor.get_all_news()
        print(f"\n✅ 成功获取 {len(news)} 条新闻")

        # 显示前3条新闻
        for i, item in enumerate(news[:3], 1):
            print(f"\n{i}. [{item['source']}] {item['title'][:60]}...")
            print(f"   情绪评分: {item['sentiment']['score']}/10")
            if item['sentiment']['mentioned_coins']:
                print(f"   提到币种: {', '.join(item['sentiment']['mentioned_coins'])}")

        # 获取特定币种情绪
        btc_sentiment = await rss_monitor.get_coin_news_sentiment("BTC")
        if btc_sentiment:
            print(f"\n✅ BTC 新闻情绪: {btc_sentiment.score}/10")
            print(f"   相关新闻: {btc_sentiment.news_count}条")
            print(f"   看涨: {btc_sentiment.bullish_count}条 | 看跌: {btc_sentiment.bearish_count}条")
        else:
            print("\n⚠️  BTC 24小时内无相关新闻")

        # 获取整体市场情绪
        market_sentiment = await rss_monitor.get_overall_market_sentiment()
        print(f"\n✅ 整体市场情绪: {market_sentiment['score']}/10")
        print(f"   新闻数量: {market_sentiment['news_count']}条")

    except Exception as e:
        print(f"\n❌ RSS监控测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_twitter_monitor():
    """测试Twitter监控"""
    print("\n" + "=" * 60)
    print("测试 Twitter 监控")
    print("=" * 60)

    try:
        # 注意：需要配置Twitter API凭证才能测试
        print("\n⚠️  Twitter监控需要配置API凭证")
        print("   在.env文件中配置以下变量:")
        print("   - TWITTER_CONSUMER_KEY")
        print("   - TWITTER_CONSUMER_SECRET")
        print("   - TWITTER_ACCESS_TOKEN")
        print("   - TWITTER_ACCESS_TOKEN_SECRET")

        # 示例：如果有凭证，可以这样测试
        # sentiment = await twitter_monitor.get_user_sentiment("elonmusk")
        # if sentiment:
        #     print(f"\n✅ 用户情绪评分: {sentiment.sentiment_score}/10")
        #     print(f"   推文数: {len(sentiment.tweets)}")
        #     print(f"   粉丝数: {sentiment.user.followers_count}")

    except Exception as e:
        print(f"\n❌ Twitter监控测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_lunarcrush_monitor():
    """测试LunarCrush监控"""
    print("\n" + "=" * 60)
    print("测试 LunarCrush 监控")
    print("=" * 60)

    try:
        # 注意：需要配置LunarCrush API凭证才能测试
        print("\n⚠️  LunarCrush监控需要配置API凭证")
        print("   在.env文件中配置:")
        print("   - LUNARCRUSH_API_KEY")

        # 示例：如果有凭证，可以这样测试
        # sentiment = await lunarcrush_monitor.get_social_sentiment("BTC")
        # if sentiment:
        #     print(f"\n✅ BTC 社交媒体情绪: {sentiment.trend_score}/10")
        #     print(f"   社交量: {sentiment.social_volume}")
        #     print(f"   Galaxy Score: {sentiment.galaxy_score}")

    except Exception as e:
        print(f"\n❌ LunarCrush监控测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_unified_service():
    """测试统一服务"""
    print("\n" + "=" * 60)
    print("测试 统一外部数据服务")
    print("=" * 60)

    try:
        # 获取币种综合情绪
        report = await external_data_service.get_coin_sentiment("BTC")
        print(f"\n✅ BTC 综合情绪评分: {report.overall_score}/10")

        if report.rss_sentiment:
            print(f"   RSS评分: {report.rss_sentiment['score']}/10")
            print(f"   新闻数: {report.rss_sentiment['news_count']}条")

        if report.lunarcrush_sentiment:
            print(f"   LunarCrush趋势评分: {report.lunarcrush_sentiment['trend_score']}/10")
            print(f"   Galaxy Score: {report.lunarcrush_sentiment['galaxy_score']}")

        if report.twitter_sentiment:
            print(f"   Twitter评分: {report.twitter_sentiment['sentiment_score']}/10")
            print(f"   用户: @{report.twitter_sentiment['username']}")

        # 获取整体市场情绪
        market = await external_data_service.get_overall_market_sentiment()
        print(f"\n✅ 整体市场情绪: {market['score']}/10")
        print(f"   新闻数量: {market['news_count']}条")

        # 获取最新新闻
        news = await external_data_service.get_latest_news(limit=5)
        print(f"\n✅ 获取到 {len(news)} 条最新新闻")

    except Exception as e:
        print(f"\n❌ 统一服务测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("外部数据源功能测试")
    print("=" * 60)

    # 测试RSS监控
    await test_rss_monitor()

    # 测试Twitter监控（需要凭证）
    await test_twitter_monitor()

    # 测试LunarCrush监控（需要凭证）
    await test_lunarcrush_monitor()

    # 测试统一服务
    await test_unified_service()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
