import asyncio
from app.core.okx_client import OKXClient
from app.strategies.resonance import check_capital_flow

async def test():
    async with OKXClient() as client:
        coins = ['TRUMP', 'BNB', 'ETH', 'BTC', 'SOL']
        print('Python版本 - 成交量比计算结果:')
        print('=' * 50)
        for coin in coins:
            result = await check_capital_flow(client, coin)
            print(f'{coin}: 成交量比={result.volume_ratio:.2f}x, 评分={result.score}, 原因={result.reason}')

asyncio.run(test())
