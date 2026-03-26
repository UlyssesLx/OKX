# 加密货币自动交易系统

基于 **币市麻雀战法** 的现代化全栈自动交易系统，采用 Python FastAPI 后端 + Vue3 前端架构。

## 🏗️ 系统架构

```
trading-system/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── trading.py     # 交易接口
│   │   │   └── websocket.py   # WebSocket 实时推送
│   │   ├── core/              # 核心模块
│   │   │   ├── config.py      # 配置管理
│   │   │   └── okx_client.py  # OKX API 客户端
│   │   ├── models/            # 数据模型
│   │   ├── strategies/        # 策略模块
│   │   │   ├── sparrow_config.py   # 币市麻雀战法配置
│   │   │   ├── indicators.py       # 技术指标计算
│   │   │   ├── short_term.py       # 短线策略
│   │   │   ├── pyramid.py          # 金字塔建仓
│   │   │   └── resonance.py        # 多维度共振
│   │   └── main.py            # 应用入口
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── api/               # API 调用
│   │   ├── components/        # 组件
│   │   │   ├── StatsCard.vue
│   │   │   ├── TimeZoneCard.vue
│   │   │   ├── MarketEnvironmentCard.vue
│   │   │   └── PositionsCard.vue
│   │   ├── composables/       # 组合式函数
│   │   ├── layouts/           # 布局
│   │   ├── router/            # 路由
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── styles/            # 样式
│   │   ├── types/             # TypeScript 类型
│   │   ├── utils/             # 工具函数
│   │   └── views/             # 页面
│   │       ├── Dashboard.vue
│   │       ├── Positions.vue
│   │       ├── Trades.vue
│   │       └── Settings.vue
│   ├── package.json
│   └── vite.config.ts
│
└── start.bat                  # 启动脚本
```

## ✨ 功能特性

### 策略模块
- **币市麻雀战法 v4.1** - 时区感知 + 小步快跑 + 严格风控
- **短线高胜率策略 v3.0** - 高胜率 + 严格止损 + 快速进出
- **金字塔建仓策略** - 分层建仓，降低成本
- **多维度共振策略** - 舆情 + 技术面 + 资金流向 + 大盘环境

### 技术指标
- MA/EMA 移动平均线
- MACD 指标
- RSI 相对强弱指数
- 布林带
- 波动率计算

### 前端界面
- 📊 实时仪表盘 - 资产概览、大盘环境、时区感知
- 💼 持仓管理 - 实时持仓、一键卖出
- 📈 交易记录 - 历史交易、统计分析
- ⚙️ 系统设置 - 策略配置、风控参数

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Node.js 18+
- npm 或 yarn

### 后端安装

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OKX API 密钥

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 一键启动 (Windows)

```bash
# 双击运行
start.bat
```

## 📡 API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/balance` | GET | 获取账户余额 |
| `/api/v1/ticker/{inst_id}` | GET | 获取行情数据 |
| `/api/v1/tickers` | GET | 获取所有行情 |
| `/api/v1/trend/{inst_id}` | GET | 获取趋势分析 |
| `/api/v1/market-environment` | GET | 获取大盘环境 |
| `/api/v1/resonance/{coin}` | GET | 获取共振分析 |
| `/api/v1/time-zone` | GET | 获取时区信息 |
| `/api/v1/order` | POST | 下单 |
| `/api/v1/order/{inst_id}/{order_id}` | DELETE | 撤单 |
| `/ws/trading` | WebSocket | 实时数据推送 |

## 🎨 界面预览

### 仪表盘
- 总资产、可用USDT、持仓数量、大盘评分卡片
- 时区感知面板（活跃强度、建议仓位、持仓时间）
- 大盘环境面板（BTC/ETH评分、资金费率）
- 持仓管理面板
- 资产趋势图表
- 交易统计图表

### 设计风格
- 现代化扁平化设计
- 深色主题（金融科技感）
- 渐变色强调
- 卡片式布局
- 响应式适配

## ⚠️ 风险提示

1. 本系统仅供学习和研究使用
2. 加密货币交易存在高风险，请谨慎投资
3. 使用前请充分理解策略逻辑和风险
4. 建议先在模拟环境测试

## 📄 许可证

MIT License
