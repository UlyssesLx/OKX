# API路径快速参考

## 📋 路由结构总览

```
/api/v1/
├── trading/*          → trading.py  (基础交易端点)
├── services/*         → services.py (服务端点)
└── external/*         → external_data.py (外部数据端点)
```

---

## 🔄 Trading API (`/api/v1/trading/*`)

**文件位置:** `backend/app/api/trading.py`

### 基础交易端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/balance` | 获取账户余额 |
| GET | `/ticker/{inst_id}` | 获取单个币种行情 |
| GET | `/tickers` | 获取所有行情 |
| GET | `/trend/{inst_id}` | 趋势分析 |
| GET | `/positions` | 获取持仓 |
| POST | `/order` | 下单 |
| DELETE | `/order/{inst_id}/{order_id}` | 撤单 |

### 模拟交易端点
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/simulation/position` | 添加模拟持仓 |
| GET | `/simulation/positions` | 获取模拟持仓 |
| GET | `/simulation/trades` | 获取模拟交易记录 |
| DELETE | `/simulation/clear` | 清空模拟数据 |

### 策略配置端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/long-config` | 获取多单配置 |
| POST | `/long-config` | 更新多单配置 |
| GET | `/short-config` | 获取做空配置 |
| POST | `/short-config` | 更新做空配置 |
| GET | `/risk-config` | 获取风控配置 |
| POST | `/risk-config` | 更新风控配置 |

### 市场分析端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/market-environment` | 市场环境分析 |
| GET | `/resonance/{coin}` | 共振分析 |
| GET | `/time-zone` | 时区信息 |

---

## 🛠️ Services API (`/api/v1/services/*`)

**文件位置:** `backend/app/api/services.py`

### 通用配置
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/settings` | 获取设置 |
| POST | `/settings` | 更新设置 |
| GET | `/v42-features` | 获取v4.2功能配置 |
| POST | `/v42-features` | 更新v4.2功能 |
| GET | `/config/smart-trading` | 获取智能交易配置 |
| POST | `/config/smart-trading` | 更新智能交易配置 |

### 情绪分析
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sentiment/{coin}` | 获取币种情绪 |

### 策略演化
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/evolution/status` | 获取演化状态 |
| GET | `/evolution/params` | 获取演化参数 |
| POST | `/evolution/params` | 更新演化参数 |

### 黑名单管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/blacklist` | 获取黑名单 |
| POST | `/blacklist/{coin}` | 添加到黑名单 |
| DELETE | `/blacklist/{coin}` | 从黑名单移除 |

### 交易统计
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/stats` | 获取统计数据 |
| GET | `/stats/report` | 获取统计报告 |
| POST | `/stats/trade` | 记录交易 |
| GET | `/stats/recent` | 获取最近交易 |

### 通知信号
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notification/report` | 获取通知报告 |
| GET | `/notification/signals` | 获取信号 |
| DELETE | `/notification/signals` | 清除信号 |

### 带单交易
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/bandtrade/config` | 获取带单配置 |
| POST | `/bandtrade/config` | 更新带单配置 |
| GET | `/bandtrade/positions` | 获取带单持仓 |
| GET | `/bandtrade/position/{coin}` | 获取单个带单 |
| POST | `/bandtrade/position/{coin}` | 添加带单 |
| DELETE | `/bandtrade/position/{coin}` | 删除带单 |

### 协调器
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/coordinator/status` | 获取协调器状态 |
| POST | `/coordinator/start` | 启动协调器 |
| POST | `/coordinator/stop` | 停止协调器 |
| POST | `/coordinator/cycle` | 执行交易周期 |

### 紧急停止
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/emergency-stop` | 获取紧急停止状态 |
| POST | `/emergency-stop` | 触发紧急停止 |
| DELETE | `/emergency-stop` | 解除紧急停止 |

### 横盘检测
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sideways/status` | 获取横盘状态 |
| DELETE | `/sideways/{coin}` | 解除币种横盘 |
| DELETE | `/sideways` | 解除所有横盘 |

### 市场扫描
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/trading/scan-config` | 获取扫描配置 |
| POST | `/trading/scan-config` | 更新扫描配置 |
| GET | `/trading/scan` | 执行市场扫描 |
| POST | `/trading/execute` | 执行交易 |

### 持仓管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/position/config` | 获取持仓配置 |
| POST | `/position/config` | 更新持仓配置 |
| GET | `/position/all` | 获取所有持仓 |
| DELETE | `/position/{coin}` | 删除币种持仓 |
| DELETE | `/position` | 清空所有持仓 |

### 网格交易
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/grid/status` | 获取网格状态 |
| POST | `/grid/add` | 添加网格 |
| DELETE | `/grid/{name}` | 删除网格 |
| POST | `/grid/run` | 运行网格 |

### 趋势交易
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/trendstrategy/status` | 获取趋势策略状态 |
| POST | `/trendstrategy/run` | 运行趋势策略 |

### 智能网格
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/smartgrid/status` | 获取智能网格状态 |
| POST | `/smartgrid/add` | 添加智能网格 |
| DELETE | `/smartgrid/{name}` | 删除智能网格 |
| POST | `/smartgrid/run` | 运行智能网格 |

---

## 📡 External Data API (`/api/v1/external/*`)

**文件位置:** `backend/app/api/external_data.py`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/rss` | RSS新闻情绪 |
| GET | `/twitter` | Twitter情绪 |
| GET | `/lunarcrush` | LunarCrush情绪 |
| GET | `/sentiment` | 综合情绪 |
| GET | `/sentiment/batch` | 批量情绪 |
| GET | `/market-sentiment` | 市场情绪 |
| GET | `/sources/status` | 数据源状态 |

---

## ⚠️ 重要提示

### 路径选择规则

1. **配置端点 (long/short/risk-config)** → `/api/v1/trading/*`
   - 这些在 `trading.py` 中定义

2. **扫描配置 (scan-config)** → `/api/v1/services/trading/scan-config`
   - 虽然名字有 "trading"，但在 `services.py` 中定义

3. **其他所有服务端点** → `/api/v1/services/*`
   - 黑名单、统计、网格、协调器等

4. **基础交易端点** → `/api/v1/trading/*`
   - 余额、行情、持仓、下单等

---

## 🧪 快速测试

```bash
# 测试Trading API
curl http://localhost:8000/api/v1/trading/balance
curl http://localhost:8000/api/v1/trading/long-config

# 测试Services API
curl http://localhost:8000/api/v1/services/stats
curl http://localhost:8000/api/v1/services/blacklist
curl http://localhost:8000/api/v1/services/trading/scan-config

# 测试External Data API
curl http://localhost:8000/api/v1/external/health
curl http://localhost:8000/api/v1/external/sentiment?coin=BTC
```

---

## 📝 完整API文档

访问Swagger UI查看完整API文档：
```
http://localhost:8000/docs
```
