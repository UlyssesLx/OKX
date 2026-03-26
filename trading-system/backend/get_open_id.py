#!/usr/bin/env python3
"""
获取与机器人对话的用户 open_id
"""
import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()


async def get_all_chats():
    """获取所有对话（包括单聊和群聊）"""
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")

    if not app_id or not app_secret:
        print("❌ 请在 .env 中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                print(f"❌ 获取 token 失败: {data}")
                return

            access_token = data.get("tenant_access_token")
            headers = {"Authorization": f"Bearer {access_token}"}

            # 尝试获取所有类型的对话
            print("获取所有对话列表...\n")

            # 尝试群聊列表
            for chat_type in ["group", "p2p"]:
                chat_url = f"https://open.feishu.cn/open-apis/im/v1/chats?chat_type={chat_type}"
                async with session.get(chat_url, headers=headers) as resp:
                    result = await resp.json()
                    print(f"{chat_type} 列表: code={result.get('code')}, msg={result.get('msg')}")
                    if result.get("code") == 0:
                        items = result.get("data", {}).get("items", [])
                        if items:
                            print(f"  找到 {len(items)} 个 {chat_type}:")
                            for item in items:
                                print(f"    - chat_id: {item.get('chat_id')}")
                                print(f"      name: {item.get('name')}")
                                print(f"      type: {item.get('chat_type')}")
                                print()
                        else:
                            print(f"  无 {chat_type} 记录")
                    else:
                        print(f"  错误: {result}")

            # 尝试获取消息列表（来自用户的单聊）
            print("\n尝试获取最近消息...")
            msg_url = "https://open.feishu.cn/open-apis/im/v1/messages?msg_type=text&page_size=10"
            async with session.get(msg_url, headers=headers) as resp:
                result = await resp.json()
                print(f"消息列表响应: {result}")


if __name__ == "__main__":
    asyncio.run(get_all_chats())
