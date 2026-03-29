<template>
  <div class="strategy-config-page">
    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="top-left">
        <div class="direction-selector">
          <div class="direction-buttons">
            <button
              class="direction-btn long"
              :class="{ active: tradeDirection === 'long' }"
              @click="tradeDirection = 'long'"
            >
              <span class="icon">📈</span>
              <span class="text">做多策略</span>
            </button>
            <button
              class="direction-btn short"
              :class="{ active: tradeDirection === 'short' }"
              @click="tradeDirection = 'short'"
            >
              <span class="icon">📉</span>
              <span class="text">做空策略</span>
            </button>
          </div>
        </div>
      </div>
      <div class="top-center">
        <div class="system-status">
          <div class="status-indicator" :class="isPaused ? 'paused' : 'running'"></div>
          <span class="status-text">{{ isPaused ? '系统已暂停' : '系统运行中' }}</span>
        </div>
        <div class="balance-info">
          <span class="label">模拟资金:</span>
          <span class="value">{{ settings.simulationBalance }} USDT</span>
        </div>
      </div>
      <div class="top-right">
        <el-button @click="resetAll" :disabled="isPaused">恢复默认</el-button>
        <el-button type="primary" size="large" @click="saveAll" :disabled="isPaused">
          保存所有配置
        </el-button>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 左侧边栏 - 导航 -->
      <div class="sidebar">
        <div class="nav-section">
          <div class="nav-title">方向设置</div>
          <nav class="nav-list">
            <a
              class="nav-item"
              :class="{ active: activeNav === 'basic' }"
              @click="activeNav = 'basic'"
            >
              <span class="icon">⚙️</span>
              <span>基础配置</span>
            </a>
          </nav>
        </div>

        <div class="nav-section">
          <div class="nav-title">{{ tradeDirection === 'long' ? '做多策略' : '做空策略' }}</div>
          <nav class="nav-list">
            <a
              class="nav-item"
              :class="{ active: activeNav === 'coin-filter' }"
              @click="activeNav = 'coin-filter'"
            >
              <span class="icon">🔍</span>
              <span>选币门槛</span>
            </a>
            <a
              class="nav-item"
              :class="{ active: activeNav === 'resonance' }"
              @click="activeNav = 'resonance'"
            >
              <span class="icon">🔮</span>
              <span>共振策略</span>
            </a>
            <a
              class="nav-item"
              :class="{ active: activeNav === 'trade-config' }"
              @click="activeNav = 'trade-config'"
            >
              <span class="icon">💰</span>
              <span>交易配置</span>
            </a>
            <a
              class="nav-item"
              :class="{ active: activeNav === 'stop-loss' }"
              @click="activeNav = 'stop-loss'"
            >
              <span class="icon">🛡️</span>
              <span>止盈止损</span>
            </a>
            <a
              class="nav-item"
              :class="{ active: activeNav === 'pyramid' }"
              @click="activeNav = 'pyramid'"
            >
              <span class="icon">🏔️</span>
              <span>加仓策略</span>
            </a>
            <!-- 做多专属: 抄底策略 -->
            <a
              v-if="tradeDirection === 'long'"
              class="nav-item"
              :class="{ active: activeNav === 'dip-buy' }"
              @click="activeNav = 'dip-buy'"
            >
              <span class="icon">🔰</span>
              <span>抄底策略</span>
            </a>
            <!-- 做多专属: 阴线买入 -->
            <a
              v-if="tradeDirection === 'long'"
              class="nav-item"
              :class="{ active: activeNav === 'bearish-candle' }"
              @click="activeNav = 'bearish-candle'"
            >
              <span class="icon">🌙</span>
              <span>阴线买入</span>
            </a>
            <!-- 做多专属: 暴跌反弹 -->
            <a
              v-if="tradeDirection === 'long'"
              class="nav-item"
              :class="{ active: activeNav === 'crash-rebound' }"
              @click="activeNav = 'crash-rebound'"
            >
              <span class="icon">⚡</span>
              <span>暴跌反弹</span>
            </a>
            <!-- 做空专属: 顶部做空 -->
            <a
              v-if="tradeDirection === 'short'"
              class="nav-item"
              :class="{ active: activeNav === 'short-dip' }"
              @click="activeNav = 'short-dip'"
            >
              <span class="icon">🎯</span>
              <span>顶部做空</span>
            </a>
            <!-- 做空专属: 阳线卖出 -->
            <a
              v-if="tradeDirection === 'short'"
              class="nav-item"
              :class="{ active: activeNav === 'bullish-candle' }"
              @click="activeNav = 'bullish-candle'"
            >
              <span class="icon">☀️</span>
              <span>阳线卖出</span>
            </a>
            <!-- 做空专属: 暴涨回落 -->
            <a
              v-if="tradeDirection === 'short'"
              class="nav-item"
              :class="{ active: activeNav === 'short-crash' }"
              @click="activeNav = 'short-crash'"
            >
              <span class="icon">🚀</span>
              <span>暴涨回落</span>
            </a>
          </nav>
        </div>

        <div class="nav-section">
          <div class="nav-title">全局配置</div>
          <nav class="nav-list">
            <a
              class="nav-item"
              :class="{ active: activeNav === 'risk' }"
              @click="activeNav = 'risk'"
            >
              <span class="icon">⚠️</span>
              <span>风控配置</span>
            </a>
            <a
              class="nav-item"
              :class="{ active: activeNav === 'advanced' }"
              @click="activeNav = 'advanced'"
            >
              <span class="icon">🧠</span>
              <span>高级功能</span>
            </a>
            <a
              class="nav-item"
              :class="{ active: activeNav === 'sparrow' }"
              @click="activeNav = 'sparrow'"
            >
              <span class="icon">🌍</span>
              <span>时区感知</span>
            </a>
          </nav>
        </div>
      </div>

      <!-- 右侧内容区 -->
      <div class="content-area">
        <!-- 基础配置 -->
        <div v-show="activeNav === 'basic'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">基础配置</h2>
            <p class="panel-desc">设置交易模式和基本参数</p>
          </div>

          <div class="config-section">
            <div class="section-title">交易模式</div>
            <div class="mode-cards">
              <div
                class="mode-card"
                :class="{ active: settings.tradingMode === 'simulation' }"
                @click="settings.tradingMode = 'simulation'"
              >
                <div class="mode-icon">🎮</div>
                <div class="mode-info">
                  <div class="mode-name">模拟模式</div>
                  <div class="mode-desc">使用模拟资金进行测试</div>
                </div>
                <div class="check-icon" v-if="settings.tradingMode === 'simulation'">✓</div>
              </div>
              <div
                class="mode-card"
                :class="{ active: settings.tradingMode === 'live' }"
                @click="settings.tradingMode = 'live'"
              >
                <div class="mode-icon">💰</div>
                <div class="mode-info">
                  <div class="mode-name">实盘模式</div>
                  <div class="mode-desc">使用真实资金交易</div>
                </div>
                <div class="check-icon" v-if="settings.tradingMode === 'live'">✓</div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">合约设置</div>
            <div class="mode-cards">
              <div
                class="mode-card"
                :class="{ active: !settings.useSwap }"
                @click="settings.useSwap = false"
              >
                <div class="mode-icon">📦</div>
                <div class="mode-info">
                  <div class="mode-name">现货交易</div>
                  <div class="mode-desc">现货市场</div>
                </div>
                <div class="check-icon" v-if="!settings.useSwap">✓</div>
              </div>
              <div
                class="mode-card"
                :class="{ active: settings.useSwap }"
                @click="settings.useSwap = true"
              >
                <div class="mode-icon">📊</div>
                <div class="mode-info">
                  <div class="mode-name">合约交易</div>
                  <div class="mode-desc">永续合约</div>
                </div>
                <div class="check-icon" v-if="settings.useSwap">✓</div>
              </div>
            </div>

            <div v-if="settings.useSwap" class="leverage-cards">
              <div class="leverage-card">
                <div class="stat-icon">📈</div>
                <div class="stat-info">
                  <div class="stat-label">做多杠杆</div>
                  <div class="stat-control">
                    <el-input-number v-model="settings.longLeverage" :min="1" :max="125" :disabled="isPaused" />
                    <span class="stat-unit">x</span>
                  </div>
                </div>
              </div>
              <div class="leverage-card">
                <div class="stat-icon">📉</div>
                <div class="stat-info">
                  <div class="stat-label">做空杠杆</div>
                  <div class="stat-control">
                    <el-input-number v-model="settings.shortLeverage" :min="1" :max="125" :disabled="isPaused" />
                    <span class="stat-unit">x</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="balance-card" v-if="settings.tradingMode === 'simulation'">
              <div class="stat-icon">💵</div>
              <div class="stat-info">
                <div class="stat-label">模拟初始资金</div>
                <div class="stat-control">
                  <el-input-number v-model="settings.simulationBalance" :min="100" :max="100000" :step="100" :disabled="isPaused" />
                  <span class="stat-unit">USDT</span>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">🔬 技术面验证（共振策略专用）</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">✅</div>
                  <div class="stat-info">
                    <div class="stat-label">最少通过项数</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalMinPassCount" :min="1" :max="5" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">/{{ currentConfig.technicalMinPassCount }}项</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势评分阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalTrendScoreThreshold" :min="3" :max="8" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">〰️</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI 下限</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalRsiMin" :min="20" :max="40" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">{{ currentConfig.technicalRsiMin }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">〰️</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI 上限</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalRsiMax" :min="70" :max="90" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">{{ currentConfig.technicalRsiMax }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量比下限</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalVolumeRatioMin" :min="0.5" :max="2.0" :step="0.1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">{{ currentConfig.technicalVolumeRatioMin }}x</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">MA5 容忍度</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalMa5Tolerance" :min="0.95" :max="1.0" :step="0.01" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">{{ currentConfig.technicalMa5Tolerance }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">波动率下限</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.technicalVolatilityMin" :min="0.1" :max="1.0" :step="0.1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">{{ currentConfig.technicalVolatilityMin }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="config-tip" style="margin-top: 12px;">
              <span class="tip-icon">📋</span>
              <span>技术面验证 5 项：趋势评分、RSI、成交量比、价格位置、波动率。通过至少 {{ currentConfig.technicalMinPassCount }} 项即可</span>
            </div>
          </div>
        </div>

        <!-- 选币门槛 -->
        <div v-show="activeNav === 'coin-filter'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">{{ tradeDirection === 'long' ? '做多选币门槛' : '做空选币门槛' }}</h2>
            <p class="panel-desc">设置开仓前的技术指标筛选条件</p>
          </div>

          <div class="config-section">
            <div class="section-title">评分要求</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">{{ tradeDirection === 'long' ? '📈' : '📉' }}</div>
                  <div class="stat-info">
                    <div class="stat-label">{{ tradeDirection === 'long' ? '最小看涨评分' : '最小看跌评分' }}</div>
                    <div class="stat-control">
                      <el-slider v-model="bullishScoreValue" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge; {{ bullishScoreValue }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">{{ tradeDirection === 'long' ? '趋势评分下限' : '趋势评分上限' }}</div>
                    <div class="stat-control">
                      <el-slider v-model="trendScoreValue" :min="0" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit" v-if="tradeDirection === 'long'">&ge; {{ trendScoreValue }}</span>
                      <span class="stat-unit" v-else>&le; {{ trendScoreValue }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">舆情界限</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📰</div>
                  <div class="stat-info">
                    <div class="stat-label">{{ tradeDirection === 'long' ? '舆情买入阈值' : '舆情做空阈值' }}</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.sentimentThreshold" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge; {{ currentConfig.sentimentThreshold }}分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">资金流向评分</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.minCapitalFlowScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge; {{ currentConfig.minCapitalFlowScore }}分</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">技术指标</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI范围</div>
                    <div class="stat-control range">
                      <span class="range-value-left">{{ currentConfig.rsiRange[0] }}</span>
                      <el-slider
                        v-model="currentConfig.rsiRange"
                        range
                        :min="20"
                        :max="90"
                        :step="1"
                        :disabled="isPaused"
                      />
                      <span class="range-value-right">{{ currentConfig.rsiRange[1] }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">最小量比</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.minVolumeRatio" :min="0.1" :max="5" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">{{ currentConfig.minVolumeRatio }}x</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">市场环境</div>
            <div class="param-grid">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🕐</div>
                  <div class="stat-info">
                    <div class="stat-label">24h涨跌范围</div>
                    <div class="stat-control range">
                      <span class="range-value-left">{{ currentConfig.changeRange[0] }}%</span>
                      <el-slider
                        v-model="currentConfig.changeRange"
                        range
                        :min="-20"
                        :max="20"
                        :step="0.5"
                        :disabled="isPaused"
                      />
                      <span class="range-value-right">{{ currentConfig.changeRange[1] }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">波动率范围</div>
                    <div class="stat-control range">
                      <span class="range-value-left">{{ currentConfig.volatilityRange[0] }}%</span>
                      <el-slider
                        v-model="currentConfig.volatilityRange"
                        range
                        :min="0"
                        :max="20"
                        :step="0.1"
                        :disabled="isPaused"
                      />
                      <span class="range-value-right">{{ currentConfig.volatilityRange[1] }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🌐</div>
                  <div class="stat-info">
                    <div class="stat-label">{{ tradeDirection === 'long' ? '大盘趋势下限' : '大盘趋势上限' }}</div>
                    <div class="stat-control">
                      <el-slider v-model="marketTrendValue" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit" v-if="tradeDirection === 'long'">&ge; {{ marketTrendValue }}</span>
                      <span class="stat-unit" v-else>&le; {{ marketTrendValue }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 共振策略 -->
        <div v-show="activeNav === 'resonance'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">🔮 多维度共振策略</h2>
            <p class="panel-desc">对齐 ai_trading_bot.js 核心策略：舆情 + 技术 + 资金 + 大盘四维共振</p>
          </div>

          <div class="config-section">
            <div class="section-title">📊 共振权重配置</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">舆情评分权重</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.resonanceSentimentWeight" :min="0" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">{{ Math.round(currentConfig.resonanceSentimentWeight) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">技术面权重</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.resonanceTechnicalWeight" :min="0" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">{{ Math.round(currentConfig.resonanceTechnicalWeight) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">资金流向权重</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.resonanceCapitalFlowWeight" :min="0" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">{{ Math.round(currentConfig.resonanceCapitalFlowWeight) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🌍</div>
                  <div class="stat-info">
                    <div class="stat-label">大盘环境权重</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.resonanceMarketEnvWeight" :min="0" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">{{ Math.round(currentConfig.resonanceMarketEnvWeight) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="config-tip" style="margin-top: 12px;">
              <span class="tip-icon">💡</span>
              <span>建议配置：舆情 30% + 技术面 25% + 资金流 25% + 大盘 20% = 100%</span>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">🎯 共振门槛配置</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🔢</div>
                  <div class="stat-info">
                    <div class="stat-label">共振总分门槛</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.resonanceMinTotalScore" :min="4" :max="10" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">资金流最低分数</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.resonanceMinCapitalFlowScore" :min="3" :max="8" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">分</span>
                    </div>
                  </div>
                </div>
                <div class="config-tip" style="margin-top: 8px;">
                  <span class="tip-icon">📋</span>
                  <span>ai_trading_bot.js: capitalFlow.score >= 4</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 交易配置 -->
        <div v-show="activeNav === 'trade-config'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">{{ tradeDirection === 'long' ? '做多交易配置' : '做空交易配置' }}</h2>
            <p class="panel-desc">设置仓位管理和交易限制</p>
          </div>

          <div class="config-section">
            <div class="section-title">仓位管理</div>
            <div class="param-grid two-col" style="margin-bottom: 12px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💵</div>
                  <div class="stat-info">
                    <div class="stat-label">普通策略</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.tradeSize" :min="10" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">USDT</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⚡</div>
                  <div class="stat-info">
                    <div class="stat-label">短线策略</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.shortTermTradeSize" :min="10" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">USDT</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">仓位比例</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.positionRatio" :min="0.5" :max="2" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">{{ currentConfig.positionRatio }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">最大持仓数</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.maxPositions" :min="1" :max="10" :disabled="isPaused" />
                      <span class="stat-unit">个</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">单币最大占比</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.maxPositionPercent" :min="5" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">{{ currentConfig.maxPositionPercent }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">交易限制</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">每日最大交易</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.maxDailyTrades" :min="1" :max="50" :disabled="isPaused" />
                      <span class="stat-unit">笔</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">最小交易间隔</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.minTradeInterval" :min="30" :max="360" :disabled="isPaused" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">时间止损</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.timeStop" :min="12" :max="168" :disabled="isPaused" />
                      <span class="stat-unit">小时</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">🔗 情绪融合配置</div>
            <div class="param-grid two-col" style="gap: 12px;">
              <div class="param-item">
                <div class="toggle-card full-width" :class="{ active: currentConfig.sentimentFusionEnabled }">
                  <div class="toggle-info">
                    <div class="toggle-title">启用情绪融合</div>
                    <div class="toggle-desc">融合市场情绪与技术面评分，提高决策准确性</div>
                  </div>
                  <div class="toggle-control">
                    <el-switch v-model="currentConfig.sentimentFusionEnabled" :disabled="isPaused" active-text="开" inactive-text="关" />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="currentConfig.sentimentFusionEnabled" class="param-grid three-col" style="margin-top: 16px; gap: 12px;">
              <div class="param-item full-width">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">融合模式</div>
                    <div class="stat-control">
                      <el-radio-group v-model="currentConfig.sentimentFusionMode" :disabled="isPaused">
                        <el-radio-button value="free">
                          <span>🆓 免费模式</span>
                          <el-tooltip content="CoinGecko + Fear & Greed Index，完全免费无需API Key" placement="top">
                            <el-icon style="margin-left: 4px;"><QuestionFilled /></el-icon>
                          </el-tooltip>
                        </el-radio-button>
                        <el-radio-button value="news">
                          <span>📰 新闻模式</span>
                          <el-tooltip content="CoinGecko + 新闻情绪，需要网络稳定" placement="top">
                            <el-icon style="margin-left: 4px;"><QuestionFilled /></el-icon>
                          </el-tooltip>
                        </el-radio-button>
                      </el-radio-group>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🌐</div>
                  <div class="stat-info">
                    <div class="stat-label">CoinGecko 权重</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.sentimentCoingeckoWeight" :min="0" :max="100" :step="5" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="currentConfig.sentimentFusionMode === 'free'">
                <div class="stat-card">
                  <div class="stat-icon">😨</div>
                  <div class="stat-info">
                    <div class="stat-label">Fear & Greed 权重</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.sentimentFearGreedWeight" :min="0" :max="100" :step="5" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-else>
                <div class="stat-card">
                  <div class="stat-icon">📰</div>
                  <div class="stat-info">
                    <div class="stat-label">新闻情绪权重</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.sentimentNewsWeight" :min="0" :max="100" :step="5" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">技术面权重</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.sentimentTechnicalWeight" :min="0" :max="100" :step="5" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="currentConfig.sentimentFusionMode === 'news'">
                <div class="stat-card">
                  <div class="stat-icon">⚠️</div>
                  <div class="stat-info">
                    <div class="stat-label">极度看跌阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.sentimentBearishAlertThreshold" :min="1" :max="5" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">API 超时</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.sentimentFetchTimeout" :min="1" :max="10" :step="1" :disabled="isPaused" controls-position="right" />
                      <span class="stat-unit">秒</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="currentConfig.sentimentFusionEnabled" class="config-tip" style="margin-top: 12px;">
              <span class="tip-icon">💡</span>
              <span>权重分配建议: CoinGecko(40%) + 新闻(20%) + 技术面(40%) = 100%</span>
            </div>
            <div v-if="currentConfig.sentimentFusionEnabled" class="config-tip">
              <span class="tip-icon">⚠️</span>
              <span>当 CoinGecko 评分 ≤ {{ currentConfig.sentimentBearishAlertThreshold }} 分且技术面 ≥ 6 分时，系统会发出警告并降低综合评分</span>
            </div>
          </div>
        </div>

        <!-- 止盈止损 -->
        <div v-show="activeNav === 'stop-loss'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">{{ tradeDirection === 'long' ? '做多止盈止损' : '做空止盈止损' }}</h2>
            <p class="panel-desc">设置止损和止盈规则，支持多空分别配置</p>
          </div>

          <!-- 基础止盈止损 -->
          <div class="config-section">
            <div class="section-title">基础止损设置</div>
            <div class="param-grid">
              <div class="param-item full-width">
                <div class="stat-card">
                  <div class="stat-icon">🛡️</div>
                  <div class="stat-info">
                    <div class="stat-label">基础止损比例</div>
                    <div class="stat-control">
                      <el-slider
                        v-model="currentConfig.stopLossPercent"
                        :min="0.5"
                        :max="10"
                        :step="0.1"
                        :disabled="isPaused"
                      />
                      <span class="stat-unit highlight">-{{ currentConfig.stopLossPercent }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <p class="param-hint" v-if="tradeDirection === 'long'" style="margin-top: 8px;">价格下跌超过此比例时触发止损</p>
            <p class="param-hint" v-else style="margin-top: 8px;">价格上涨超过此比例时触发止损</p>
          </div>

          <!-- 智能止损（趋势档位） -->
          <div class="config-section">
            <div class="toggle-card" :class="{ active: currentConfig.smartStopLossEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">智能止损（趋势档位）</div>
                <div class="toggle-desc">根据趋势评分动态调整止损线，强趋势时放宽止损</div>
              </div>
              <el-switch v-model="currentConfig.smartStopLossEnabled" :disabled="isPaused" />
            </div>
            <div v-if="currentConfig.smartStopLossEnabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item" v-if="tradeDirection === 'long'">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势≥8分止损</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).stopLossTrend8Plus" :min="1" :max="5" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'long'">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势6-7分止损</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).stopLossTrend67" :min="1" :max="4" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'short'">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势0-2分止损</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).stopLossTrend02" :min="1" :max="5" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'short'">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势3-4分止损</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).stopLossTrend34" :min="1" :max="4" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">默认止损</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.stopLossTrendDefault" :min="0.5" :max="3" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 动态止盈（趋势档位） -->
          <div class="config-section">
            <div class="toggle-card" :class="{ active: currentConfig.dynamicTakeProfitEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">动态止盈（趋势档位）</div>
                <div class="toggle-desc">根据趋势评分动态调整止盈目标，强趋势时扩大止盈</div>
              </div>
              <el-switch v-model="currentConfig.dynamicTakeProfitEnabled" :disabled="isPaused" />
            </div>
            <div v-if="currentConfig.dynamicTakeProfitEnabled" class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item" v-if="tradeDirection === 'long'">
                <div class="stat-card">
                  <div class="stat-icon">🚀</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势9-10分止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).takeProfitTrend910" :min="5" :max="25" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'long'">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势7-8分止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).takeProfitTrend78" :min="5" :max="20" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'long'">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势5-6分止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).takeProfitTrend56" :min="3" :max="15" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'short'">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势0-1分止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).takeProfitTrend01" :min="5" :max="25" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'short'">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势2-3分止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).takeProfitTrend23" :min="5" :max="20" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item" v-if="tradeDirection === 'short'">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势4分止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="(currentConfig as any).takeProfitTrend4" :min="3" :max="15" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">默认止盈</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.takeProfitTrendDefault" :min="3" :max="15" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 分层减仓止盈（波段操作） -->
          <div class="config-section">
            <div class="toggle-card" :class="{ active: currentConfig.bandTradeEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">分层减仓止盈（波段操作）</div>
                <div class="toggle-desc">盈利时分批减仓锁定利润，参考示例项目逻辑</div>
              </div>
              <el-switch v-model="currentConfig.bandTradeEnabled" :disabled="isPaused" />
            </div>
            <div v-if="currentConfig.bandTradeEnabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">1️⃣</div>
                  <div class="stat-info">
                    <div class="stat-label">第一档减仓点</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.bandTradeReduceAt" :min="0.5" :max="5" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">第一档减仓比例</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.bandTradeReducePercent" :min="10" :max="50" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">2️⃣</div>
                  <div class="stat-info">
                    <div class="stat-label">第二档减仓点</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.bandTradeSecondReduceAt" :min="1" :max="8" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">第二档减仓比例</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.bandTradeSecondReducePercent" :min="20" :max="70" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🏆</div>
                  <div class="stat-info">
                    <div class="stat-label">最终止盈点</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.bandTradeFinalReduceAt" :min="3" :max="15" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="currentConfig.bandTradeEnabled" class="config-tip" style="margin-top: 12px;">
              <span class="tip-icon">💡</span>
              <span>示例：盈利1.5%减仓30% → 盈利3%减仓50% → 盈利6%清仓</span>
            </div>
          </div>

          <!-- 小盈减仓 -->
          <div class="config-section">
            <div class="toggle-card" :class="{ active: currentConfig.smallProfitReduceEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">小盈减仓</div>
                <div class="toggle-desc">盈利达到止盈线一定比例且仓位较大时提前减仓</div>
              </div>
              <el-switch v-model="currentConfig.smallProfitReduceEnabled" :disabled="isPaused" />
            </div>
            <div v-if="currentConfig.smallProfitReduceEnabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">触发阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.smallProfitReduceThresholdPercent" :min="20" :max="80" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">%止盈线</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">仓位阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.smallProfitReducePositionThreshold" :min="5" :max="30" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">减仓比例</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.smallProfitReduceRatio" :min="20" :max="80" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 止盈限价单 -->
          <div class="config-section">
            <div class="toggle-card" :class="{ active: currentConfig.takeProfitLimitOrderEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">止盈限价单</div>
                <div class="toggle-desc">开仓时自动挂止盈限价单，到达目标自动成交</div>
              </div>
              <el-switch v-model="currentConfig.takeProfitLimitOrderEnabled" :disabled="isPaused" />
            </div>
            <div v-if="currentConfig.takeProfitLimitOrderEnabled" class="param-grid" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📋</div>
                  <div class="stat-info">
                    <div class="stat-label">止盈仓位比例</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.takeProfitOrderPartial" :min="0.1" :max="1" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">{{ Math.round(currentConfig.takeProfitOrderPartial * 100) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">风控参数</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">最小现金保留</div>
                    <div class="stat-control">
                      <el-slider v-model="riskConfig.minCashReserve" :min="10" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">{{ riskConfig.minCashReserve }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">买入冷却期</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.buyCooldownMinutes" :min="15" :max="120" :disabled="isPaused" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- AI策略迭代 -->
          <div class="config-section">
            <div class="toggle-card" :class="{ active: aiEvolutionConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">AI策略迭代</div>
                <div class="toggle-desc">启用AI分析交易数据，自动优化止盈止损参数</div>
              </div>
              <el-switch v-model="aiEvolutionConfig.enabled" :disabled="isPaused" @change="updateAiEvolutionConfig" />
            </div>
            
            <div v-if="aiEvolutionConfig.enabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🤖</div>
                  <div class="stat-info">
                    <div class="stat-label">自动应用建议</div>
                    <div class="stat-control">
                      <el-switch v-model="aiEvolutionConfig.autoApply" :disabled="isPaused" @change="updateAiEvolutionConfig" />
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">最少交易数</div>
                    <div class="stat-control">
                      <el-input-number v-model="aiEvolutionConfig.minTrades" :min="5" :max="50" :disabled="isPaused" @change="updateAiEvolutionConfig" />
                      <span class="stat-unit">笔</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏰</div>
                  <div class="stat-info">
                    <div class="stat-label">分析间隔</div>
                    <div class="stat-control">
                      <el-input-number v-model="aiEvolutionConfig.intervalHours" :min="1" :max="72" :disabled="isPaused" @change="updateAiEvolutionConfig" />
                      <span class="stat-unit">小时</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">置信度阈值</div>
                    <div class="stat-control">
                      <el-slider v-model="aiEvolutionConfig.confidenceThreshold" :min="0.5" :max="1" :step="0.05" :disabled="isPaused" @change="updateAiEvolutionConfig" />
                      <span class="stat-unit">{{ (aiEvolutionConfig.confidenceThreshold * 100).toFixed(0) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div v-if="aiEvolutionConfig.enabled" style="margin-top: 16px;">
              <div class="config-tip">
                <span class="tip-icon">💡</span>
                <span>AI将分析交易表现，给出止盈止损参数优化建议。置信度越高，建议越可靠。</span>
              </div>
              <div style="display: flex; gap: 12px; margin-top: 12px;">
                <el-button type="primary" :loading="aiAnalyzing" @click="triggerAiAnalysis" :disabled="isPaused">
                  {{ aiAnalyzing ? 'AI分析中...' : '手动触发AI分析' }}
                </el-button>
                <el-button @click="showAiSuggestions" :disabled="isPaused">
                  查看待确认建议 ({{ pendingSuggestionsCount }})
                </el-button>
              </div>
              <div v-if="lastAiAnalysis" style="margin-top: 12px; font-size: 12px; color: #888;">
                上次分析: {{ lastAiAnalysis }}
              </div>
            </div>
          </div>
        </div>

        <!-- 金字塔加仓 -->
        <div v-show="activeNav === 'pyramid'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">{{ tradeDirection === 'long' ? '做多加仓策略' : '做空加仓策略' }}</h2>
            <p class="panel-desc">分层加仓策略，亏损时摊薄成本</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: currentConfig.pyramidEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">金字塔加仓</div>
                <div class="toggle-desc">亏损时分层加仓摊薄成本</div>
              </div>
              <el-switch v-model="currentConfig.pyramidEnabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="currentConfig.pyramidEnabled" class="config-section">
            <div class="section-title">📈 金字塔参数</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">最大层数</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.pyramidMaxLayers" :min="1" :max="5" :disabled="isPaused" />
                      <span class="stat-unit">层</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">亏损触发阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.pyramidDropThreshold" :min="-20" :max="20" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">{{ tradeDirection === 'long' ? '每层下跌幅度' : '每层上涨幅度' }}</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.pyramidDropPerLayer" :min="-20" :max="20" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">加仓基础金额</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.pyramidBaseAmount" :min="10" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">USDT</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">各层比例</div>
                    <div class="stat-control">
                      <el-input v-model="currentConfig.pyramidLayerRatios" placeholder="1.0,0.6,0.35,0.2" :disabled="isPaused" style="width: 200px;" />
                      <span class="stat-unit">100%, 60%, 35%, 20%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentConfig.pyramidEnabled" class="config-section">
            <div class="section-title">金字塔补仓条件</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">{{ tradeDirection === 'long' ? '趋势评分下限' : '趋势评分上限' }}</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.pyramidMaxTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">{{ tradeDirection === 'long' ? '≥' : '≤' }} {{ currentConfig.pyramidMaxTrendScore }}分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">%</div>
                  <div class="stat-info">
                    <div class="stat-label">仓位上限</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.maxPositionPercent" :min="5" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💵</div>
                  <div class="stat-info">
                    <div class="stat-label">最低资金</div>
                    <div class="stat-control">
                      <el-input-number v-model="currentConfig.minCashReserve" :min="10" :max="100" :step="5" :disabled="isPaused" />
                      <span class="stat-unit">U</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentConfig.pyramidEnabled" class="config-section">
            <div class="section-title">{{ tradeDirection === 'long' ? '止损拦截加仓' : '止盈拦截加仓' }}</div>
            <div class="toggle-card" :class="{ active: currentConfig.pyramidEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用{{ tradeDirection === 'long' ? '止损拦截' : '止盈拦截' }}</div>
                <div class="toggle-desc">{{ tradeDirection === 'long' ? '触发止损但趋势强劲时优先加仓' : '触发止盈但趋势看跌时优先加仓' }}</div>
              </div>
              <el-switch v-model="currentConfig.pyramidEnabled" :disabled="isPaused" />
            </div>
            <div v-if="currentConfig.pyramidEnabled" class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">最低趋势评分</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.pyramidMaxTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge; {{ currentConfig.pyramidMaxTrendScore }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">%</div>
                  <div class="stat-info">
                    <div class="stat-label">最大仓位占比</div>
                    <div class="stat-control">
                      <el-slider v-model="currentConfig.maxPositionPercent" :min="10" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">{{ currentConfig.maxPositionPercent }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentConfig.pyramidEnabled" class="config-section">
            <div class="section-title">📉 {{ tradeDirection === 'long' ? '回调加仓条件' : '上涨加仓条件' }}</div>
            <div class="param-grid two-col" style="gap: 12px;">
              <div class="param-item">
                <div class="toggle-card full-width" :class="{ active: riskConfig.pullbackBuyEnabled || (tradeDirection === 'short' && currentConfig.rallyEnabled) }">
                  <div class="toggle-info">
                    <div class="toggle-title">{{ tradeDirection === 'long' ? '回调加仓' : '上涨加仓' }}</div>
                    <div class="toggle-desc">{{ tradeDirection === 'long' ? '价格回调至一定比例时允许加仓' : '价格上涨至一定比例时允许加仓' }}</div>
                  </div>
                  <div class="toggle-control">
                    <el-input-number v-if="tradeDirection === 'long' && riskConfig.pullbackBuyEnabled" v-model="riskConfig.pullbackBuyThreshold" :min="0.90" :max="0.99" :step="0.01" :disabled="isPaused" controls-position="right" />
                    <el-input-number v-if="tradeDirection === 'short' && currentConfig.rallyEnabled" v-model="currentConfig.rallyThreshold" :min="1.01" :max="1.10" :step="0.01" :disabled="isPaused" controls-position="right" />
                    <el-switch v-if="tradeDirection === 'long'" v-model="riskConfig.pullbackBuyEnabled" :disabled="isPaused" active-text="开" inactive-text="关" />
                    <el-switch v-if="tradeDirection === 'short'" v-model="currentConfig.rallyEnabled" :disabled="isPaused" active-text="开" inactive-text="关" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="toggle-card full-width" :class="{ active: riskConfig.pnlCheckEnabled }">
                  <div class="toggle-info">
                    <div class="toggle-title">实时盈亏验证</div>
                    <div class="toggle-desc">{{ tradeDirection === 'long' ? '亏损超过阈值时禁止追高买入' : '盈利超过阈值时禁止追跌做空' }}</div>
                  </div>
                  <div class="toggle-control">
                    <el-input-number v-if="riskConfig.pnlCheckEnabled" v-model="riskConfig.pnlCheckThreshold" :min="-10" :max="-0.5" :step="0.1" :disabled="isPaused" controls-position="right" />
                    <el-switch v-model="riskConfig.pnlCheckEnabled" :disabled="isPaused" active-text="开" inactive-text="关" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 风控配置 -->
        <div v-show="activeNav === 'risk'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">风控配置</h2>
            <p class="panel-desc">全局风险管理和保护机制</p>
          </div>

          <div class="config-section">
            <div class="section-title">交易限制</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">每日最大交易</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.maxDailyTrades" :min="1" :max="9999" :disabled="isPaused" />
                      <span class="stat-unit">笔</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">每日最大损失</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.maxDailyLoss" :min="1" :max="50" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">💰</div>
                  <div class="stat-info">
                    <div class="stat-label">最小现金保留</div>
                    <div class="stat-control">
                      <el-slider v-model="riskConfig.minCashReserve" :min="10" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit highlight">{{ riskConfig.minCashReserve }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">每日最大交易量</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.maxDailyVolume" :min="100" :max="10000" :step="100" :disabled="isPaused" />
                      <span class="stat-unit">USDT</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">分层冷却期</div>
            <div class="toggle-card" :class="{ active: riskConfig.tieredCooldownEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用分层冷却</div>
                <div class="toggle-desc">根据趋势评分动态调整冷却时间</div>
              </div>
              <el-switch v-model="riskConfig.tieredCooldownEnabled" :disabled="isPaused" />
            </div>
            <div v-if="riskConfig.tieredCooldownEnabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势10分冷却</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.cooldownTrend10" :min="5" :max="60" :disabled="isPaused" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势8-9分冷却</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.cooldownTrend8_9" :min="10" :max="90" :disabled="isPaused" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势6-7分冷却</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.cooldownTrend6_7" :min="15" :max="120" :disabled="isPaused" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="riskConfig.tieredCooldownEnabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">第一档阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.cooldownScoreTier1" :min="6" :max="10" :disabled="isPaused" />
                      <span class="stat-unit">≥分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">第二档阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.cooldownScoreTier2" :min="4" :max="9" :disabled="isPaused" />
                      <span class="stat-unit">≥分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">第三档阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.cooldownScoreTier3" :min="1" :max="8" :disabled="isPaused" />
                      <span class="stat-unit">≥分</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">高级风控</div>
            <div class="param-grid two-col" style="gap: 12px;">
              <div class="param-item">
                <div class="toggle-card full-width" :class="{ active: riskConfig.blacklistTrendCheckEnabled }">
                  <div class="toggle-info">
                    <div class="toggle-title">黑名单趋势检查</div>
                    <div class="toggle-desc">趋势反转时自动解除黑名单</div>
                  </div>
                  <el-switch v-model="riskConfig.blacklistTrendCheckEnabled" :disabled="isPaused" active-text="开" inactive-text="关" />
                </div>
              </div>
              <div class="param-item">
                <div class="toggle-card full-width" :class="{ active: riskConfig.decreasingTradeSizeEnabled }">
                  <div class="toggle-info">
                    <div class="toggle-title">买入金额递减</div>
                    <div class="toggle-desc">同币种多次买入时递减金额</div>
                  </div>
                  <el-switch v-model="riskConfig.decreasingTradeSizeEnabled" :disabled="isPaused" active-text="开" inactive-text="关" />
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">黄金稳定币</div>
            <div class="toggle-card" :class="{ active: riskConfig.goldStablecoinSpecialHandling }">
              <div class="toggle-info">
                <div class="toggle-title">特殊处理</div>
                <div class="toggle-desc">XAUT, PAXG 等稳定币特殊止盈</div>
              </div>
              <el-switch v-model="riskConfig.goldStablecoinSpecialHandling" :disabled="isPaused" />
            </div>
            <div v-if="riskConfig.goldStablecoinSpecialHandling" class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🪙</div>
                  <div class="stat-info">
                    <div class="stat-label">币种列表</div>
                    <el-input v-model="riskConfig.goldStablecoinList" placeholder="XAUT,PAXG" :disabled="isPaused" style="width: 100%;" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">止盈目标</div>
                    <div class="stat-control">
                      <el-input-number v-model="riskConfig.goldStablecoinTakeProfit" :min="0.1" :max="2" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">多空互斥决策</div>
            <div class="toggle-card" :class="{ active: riskConfig.mutualExclusiveEnabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用多空互斥</div>
                <div class="toggle-desc">当同时满足做多和做空条件时，选择盈利概率更高的方向</div>
              </div>
              <el-switch v-model="riskConfig.mutualExclusiveEnabled" :disabled="isPaused" />
            </div>
            <div v-if="riskConfig.mutualExclusiveEnabled" class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">最低开仓评分</div>
                    <div class="stat-control">
                      <el-slider v-model="riskConfig.mutualExclusiveMinScore" :min="30" :max="90" :step="5" :disabled="isPaused" />
                      <span class="stat-unit highlight">{{ riskConfig.mutualExclusiveMinScore }}分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⚖️</div>
                  <div class="stat-info">
                    <div class="stat-label">多空分差阈值</div>
                    <div class="stat-control">
                      <el-slider v-model="riskConfig.mutualExclusiveScoreDiff" :min="5" :max="30" :step="1" :disabled="isPaused" />
                      <span class="stat-unit highlight">{{ riskConfig.mutualExclusiveScoreDiff }}分</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="riskConfig.mutualExclusiveEnabled" class="info-card" style="margin-top: 12px;">
              <div class="info-icon">💡</div>
              <div class="info-text">
                系统会综合趋势评分、看涨/看跌评分、RSI、成交量、大盘趋势、资金流向等因子，分别计算做多和做空的盈利概率评分。只有当某一方向的评分超过最低阈值，且与另一方向的分差超过阈值时，才会选择该方向开仓。否则保持观望。
              </div>
            </div>
          </div>
        </div>

        <!-- 高级功能 -->
        <div v-show="activeNav === 'advanced'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">高级功能</h2>
            <p class="panel-desc">V4.2 核心交易功能</p>
          </div>

          <div class="config-section">
            <div class="section-title">每日递减买入</div>
            <div class="toggle-card" :class="{ active: v42Features.decreasingBuy }">
              <div class="toggle-info">
                <div class="toggle-title">启用每日递减</div>
                <div class="toggle-desc">同一币种多次开仓金额递减</div>
              </div>
              <div class="toggle-control">
                <el-input v-if="v42Features.decreasingBuy" v-model="v42Features.decreasingBuyFactors" placeholder="1.0,0.6,0.35,0.2" :disabled="isPaused" />
                <el-switch v-model="v42Features.decreasingBuy" :disabled="isPaused" active-text="开" inactive-text="关" />
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">超仓减仓</div>
            <div class="toggle-card" :class="{ active: smartTradingConfig.over_position_reduce_enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用超仓减仓</div>
                <div class="toggle-desc">仓位>30%时强制减仓至20%</div>
              </div>
              <el-switch v-model="smartTradingConfig.over_position_reduce_enabled" :disabled="isPaused" active-text="开" inactive-text="关" />
            </div>
            <div v-if="smartTradingConfig.over_position_reduce_enabled" class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">超仓阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.over_position_reduce_threshold" :min="20" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🎯</div>
                  <div class="stat-info">
                    <div class="stat-label">减仓目标</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.over_position_reduce_target" :min="10" :max="30" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title" style="display: flex; justify-content: space-between; align-items: center;">
              <span>智能豁免期</span>
              <el-switch v-model="v42Features.overPositionExemption" :disabled="isPaused" active-text="开" inactive-text="关" />
            </div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">高亏损>1%</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.exemption_loss_high_minutes" :min="30" :max="120" :step="5" :disabled="isPaused || !v42Features.overPositionExemption" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">中亏损0-1%</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.exemption_loss_medium_minutes" :min="20" :max="90" :step="5" :disabled="isPaused || !v42Features.overPositionExemption" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">已盈利</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.exemption_profit_minutes" :min="15" :max="60" :step="5" :disabled="isPaused || !v42Features.overPositionExemption" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">时间衰减止损</div>
            <div class="toggle-card" :class="{ active: smartTradingConfig.time_decay_enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用时间衰减</div>
                <div class="toggle-desc">持仓越久止损越紧</div>
              </div>
              <div class="toggle-control">
                <el-input-number v-if="smartTradingConfig.time_decay_enabled" v-model="smartTradingConfig.time_decay_factor" :min="0.05" :max="0.5" :step="0.05" :precision="2" :disabled="isPaused" controls-position="right" />
                <el-switch v-model="smartTradingConfig.time_decay_enabled" :disabled="isPaused" active-text="开" inactive-text="关" />
              </div>
            </div>
          </div>

          <div class="config-section">
            <div class="section-title">技术面验证</div>
            <div class="toggle-card" :class="{ active: smartTradingConfig.technical_validation_enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用技术面验证</div>
                <div class="toggle-desc">共振分析时验证技术指标</div>
              </div>
              <el-switch v-model="smartTradingConfig.technical_validation_enabled" :disabled="isPaused" />
            </div>
            <div v-if="smartTradingConfig.technical_validation_enabled" class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">✅</div>
                  <div class="stat-info">
                    <div class="stat-label">最少通过项</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_min_pass_count" :min="1" :max="5" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">/5项</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势评分阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_trend_score_threshold" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">分</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI下限</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_rsi_min" :min="10" :max="50" :step="5" :disabled="isPaused" />
                      <span class="stat-unit"></span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI上限</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_rsi_max" :min="50" :max="90" :step="5" :disabled="isPaused" />
                      <span class="stat-unit"></span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">量比最小值</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_volume_ratio_min" :min="0.5" :max="2" :step="0.1" :precision="1" :disabled="isPaused" />
                      <span class="stat-unit">x</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">〰️</div>
                  <div class="stat-info">
                    <div class="stat-label">MA5容差</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_ma5_tolerance" :min="0.9" :max="1.0" :step="0.01" :precision="2" :disabled="isPaused" />
                      <span class="stat-unit"></span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🌊</div>
                  <div class="stat-info">
                    <div class="stat-label">波动率最小值</div>
                    <div class="stat-control">
                      <el-input-number v-model="smartTradingConfig.technical_volatility_min" :min="0.1" :max="1" :step="0.1" :precision="1" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- 抄底策略 -->
        <div v-show="activeNav === 'dip-buy'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">抄底策略</h2>
            <p class="panel-desc">暴跌后抄底买入策略配置</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: dipBuyConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用抄底策略</div>
                <div class="toggle-desc">暴跌后逆势买入</div>
              </div>
              <el-switch v-model="dipBuyConfig.enabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="dipBuyConfig.enabled" class="config-section">
            <div class="section-title">抄底条件</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势评分</div>
                    <div class="stat-control">
                      <el-input-number v-model="dipBuyConfig.minTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">₿</div>
                  <div class="stat-info">
                    <div class="stat-label">BTC趋势</div>
                    <div class="stat-control">
                      <el-input-number v-model="dipBuyConfig.minBtcTrend" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">Ξ</div>
                  <div class="stat-info">
                    <div class="stat-label">ETH趋势</div>
                    <div class="stat-control">
                      <el-input-number v-model="dipBuyConfig.minEthTrend" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI超卖</div>
                    <div class="stat-control">
                      <el-input-number v-model="dipBuyConfig.rsiThreshold" :min="10" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&lt;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量倍数</div>
                    <div class="stat-control">
                      <el-input-number v-model="dipBuyConfig.volumeMultiplier" :min="1" :max="5" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">x</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">连续阴线</div>
                    <div class="stat-control">
                      <el-input-number v-model="dipBuyConfig.minConsecutiveBearish" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">根</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">需要第4根收阳</div>
                    <el-switch v-model="dipBuyConfig.requireBullishReversal" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">价格&lt;MA5</div>
                    <el-switch v-model="dipBuyConfig.priceBelowMa5" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">价格&lt;MA10</div>
                    <el-switch v-model="dipBuyConfig.priceBelowMa10" :disabled="isPaused" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 阴线买入 -->
        <div v-show="activeNav === 'bearish-candle'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">阴线买入</h2>
            <p class="panel-desc">连续阴线后收阳买入策略</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: bearishCandleConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用阴线买入</div>
                <div class="toggle-desc">连续阴线后收阳买入</div>
              </div>
              <el-switch v-model="bearishCandleConfig.enabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="bearishCandleConfig.enabled" class="config-section">
            <div class="section-title">阴线条件</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">连续阴线数</div>
                    <div class="stat-control">
                      <el-input-number v-model="bearishCandleConfig.consecutiveCount" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">根</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势评分</div>
                    <div class="stat-control">
                      <el-input-number v-model="bearishCandleConfig.minTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI超卖</div>
                    <div class="stat-control">
                      <el-input-number v-model="bearishCandleConfig.rsiOversold" :min="10" :max="50" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&lt;</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">价格需低于MA</div>
                    <el-switch v-model="bearishCandleConfig.priceBelowMa" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI验证</div>
                    <el-switch v-model="bearishCandleConfig.rsiEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量验证</div>
                    <el-switch v-model="bearishCandleConfig.volumeEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量倍数</div>
                    <div class="stat-control">
                      <el-input-number v-model="bearishCandleConfig.volumeRatio" :min="0.5" :max="5" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">x</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">K线周期</div>
                    <div class="stat-control">
                      <el-select v-model="bearishCandleConfig.candleInterval" :disabled="isPaused" style="width: 120px;">
                        <el-option label="1分钟" value="1m" />
                        <el-option label="5分钟" value="5m" />
                        <el-option label="15分钟" value="15m" />
                        <el-option label="1小时" value="1h" />
                      </el-select>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 暴跌反弹 -->
        <div v-show="activeNav === 'crash-rebound'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">暴跌反弹</h2>
            <p class="panel-desc">暴跌后反弹买入策略</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: crashReboundConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用暴跌反弹</div>
                <div class="toggle-desc">暴跌后反弹买入</div>
              </div>
              <el-switch v-model="crashReboundConfig.enabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="crashReboundConfig.enabled" class="config-section">
            <div class="section-title">暴跌反弹条件</div>
            <div class="param-grid four-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">跌幅阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="crashReboundConfig.threshold" :min="-50" :max="-1" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势评分</div>
                    <div class="stat-control">
                      <el-input-number v-model="crashReboundConfig.minTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">反弹幅度</div>
                    <div class="stat-control">
                      <el-input-number v-model="crashReboundConfig.minReboundPercent" :min="0.5" :max="10" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量放大</div>
                    <div class="stat-control">
                      <el-input-number v-model="crashReboundConfig.volumeRatio" :min="0.5" :max="5" :step="0.1" :precision="1" :disabled="isPaused" />
                      <span class="stat-unit">x&gt;</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI检查</div>
                    <el-switch v-model="crashReboundConfig.rsiCheckEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量检查</div>
                    <el-switch v-model="crashReboundConfig.volumeCheckEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 暴涨回落 -->
        <div v-show="activeNav === 'short-crash'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">暴涨回落</h2>
            <p class="panel-desc">暴涨后回调做空策略</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: shortCrashConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用暴涨回落</div>
                <div class="toggle-desc">暴涨后回调做空</div>
              </div>
              <el-switch v-model="shortCrashConfig.enabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="shortCrashConfig.enabled" class="config-section">
            <div class="section-title">暴涨回落条件</div>
            <div class="param-grid four-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">24h涨幅</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortCrashConfig.minRise24h" :min="1" :max="50" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势上限</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortCrashConfig.maxTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&le;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">回调幅度</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortCrashConfig.minPullbackPercent" :min="0.5" :max="20" :step="0.5" :disabled="isPaused" />
                      <span class="stat-unit">%&ge;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量放大</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortCrashConfig.volumeRatio" :min="0.5" :max="5" :step="0.1" :precision="1" :disabled="isPaused" />
                      <span class="stat-unit">x&gt;</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI检查</div>
                    <el-switch v-model="shortCrashConfig.rsiCheckEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量检查</div>
                    <el-switch v-model="shortCrashConfig.volumeCheckEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 顶部做空 -->
        <div v-show="activeNav === 'short-dip'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">顶部做空</h2>
            <p class="panel-desc">追涨后回调做空策略</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: shortDipConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用顶部做空</div>
                <div class="toggle-desc">追涨后回调做空</div>
              </div>
              <el-switch v-model="shortDipConfig.enabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="shortDipConfig.enabled" class="config-section">
            <div class="section-title">顶部做空条件</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势上限</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortDipConfig.maxTrendScore" :min="0" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&le;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">₿</div>
                  <div class="stat-info">
                    <div class="stat-label">BTC趋势</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortDipConfig.maxBtcTrend" :min="0" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&le;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">Ξ</div>
                  <div class="stat-info">
                    <div class="stat-label">ETH趋势</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortDipConfig.maxEthTrend" :min="0" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&le;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI超买</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortDipConfig.rsiThreshold" :min="50" :max="90" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&gt;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量倍数</div>
                    <div class="stat-control">
                      <el-input-number v-model="shortDipConfig.volumeMultiplier" :min="1" :max="5" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">x</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">需要收阴确认</div>
                    <el-switch v-model="shortDipConfig.requireBearishReversal" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">价格&gt;MA5</div>
                    <el-switch v-model="shortDipConfig.priceAboveMa5" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">价格&gt;MA10</div>
                    <el-switch v-model="shortDipConfig.priceAboveMa10" :disabled="isPaused" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 阳线卖出 -->
        <div v-show="activeNav === 'bullish-candle'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">阳线卖出</h2>
            <p class="panel-desc">连续阳线后收阴做空策略</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: bullishCandleConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用阳线卖出</div>
                <div class="toggle-desc">连续阳线后收阴做空</div>
              </div>
              <el-switch v-model="bullishCandleConfig.enabled" :disabled="isPaused" />
            </div>
          </div>

          <div v-if="bullishCandleConfig.enabled" class="config-section">
            <div class="section-title">阳线条件</div>
            <div class="param-grid three-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">连续阳线数</div>
                    <div class="stat-control">
                      <el-input-number v-model="bullishCandleConfig.consecutiveCount" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">根</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">趋势上限</div>
                    <div class="stat-control">
                      <el-input-number v-model="bullishCandleConfig.maxTrendScore" :min="1" :max="10" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&le;</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📉</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI超买</div>
                    <div class="stat-control">
                      <el-input-number v-model="bullishCandleConfig.rsiOverbought" :min="50" :max="90" :step="1" :disabled="isPaused" />
                      <span class="stat-unit">&gt;</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid three-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">价格&gt;MA5</div>
                    <el-switch v-model="bullishCandleConfig.priceAboveMa" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">RSI验证</div>
                    <el-switch v-model="bullishCandleConfig.rsiEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量验证</div>
                    <el-switch v-model="bullishCandleConfig.volumeEnabled" :disabled="isPaused" />
                  </div>
                </div>
              </div>
            </div>
            <div class="param-grid two-col" style="margin-top: 16px;">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">成交量倍数</div>
                    <div class="stat-control">
                      <el-input-number v-model="bullishCandleConfig.volumeRatio" :min="0.5" :max="5" :step="0.1" :disabled="isPaused" />
                      <span class="stat-unit">x</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏱️</div>
                  <div class="stat-info">
                    <div class="stat-label">K线周期</div>
                    <div class="stat-control">
                      <el-select v-model="bullishCandleConfig.candleInterval" :disabled="isPaused" style="width: 120px;">
                        <el-option label="1分钟" value="1m" />
                        <el-option label="5分钟" value="5m" />
                        <el-option label="15分钟" value="15m" />
                        <el-option label="1小时" value="1h" />
                      </el-select>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 时区感知 -->
        <div v-show="activeNav === 'sparrow'" class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">🌍 时区感知</h2>
            <p class="panel-desc">麻雀战法核心：根据时段动态调整仓位</p>
          </div>

          <div class="config-section">
            <div class="toggle-card" :class="{ active: sparrowConfig.enabled }">
              <div class="toggle-info">
                <div class="toggle-title">启用时区感知</div>
                <div class="toggle-desc">根据时段动态调整仓位</div>
              </div>
              <el-switch v-model="sparrowConfig.enabled" />
            </div>
          </div>

          <div v-if="sparrowConfig.enabled" class="config-section">
            <div class="section-title">🌍 时区配置</div>
            <div class="timezone-config">
              <div v-for="(tz, key) in sparrowConfig.time_zones" :key="key" class="timezone-item">
                <div class="timezone-header">
                  <div class="timezone-info">
                    <span class="timezone-name">{{ getTimeZoneName(key) }}</span>
                    <span class="timezone-time">{{ key }}</span>
                  </div>
                  <div class="intensity-indicator">
                    <span v-for="i in 5" :key="i" class="star" :class="{ active: i <= tz.intensity }">⭐</span>
                  </div>
                </div>
                <div class="timezone-params">
                  <div class="param-row">
                    <span class="label">仓位比例</span>
                    <div class="control-group">
                      <el-input-number v-model="tz.position_ratio.min" :min="0.1" :max="1.0" :step="0.05" :precision="2" size="small" />
                      <span class="separator">-</span>
                      <el-input-number v-model="tz.position_ratio.max" :min="0.1" :max="1.5" :step="0.05" :precision="2" size="small" />
                      <span class="unit">%</span>
                    </div>
                    <span class="calculated-range">(普通{{ calculatePositionRange(tz.position_ratio).normalMin }}-{{ calculatePositionRange(tz.position_ratio).normalMax }}, 短线{{ calculatePositionRange(tz.position_ratio).shortMin }}-{{ calculatePositionRange(tz.position_ratio).shortMax }})</span>
                  </div>
                  <div class="param-row">
                    <span class="label">持仓时间</span>
                    <div class="control-group">
                      <el-input-number v-model="tz.hold_time.min" :min="5" :max="30" size="small" />
                      <span class="separator">-</span>
                      <el-input-number v-model="tz.hold_time.max" :min="10" :max="120" size="small" />
                      <span class="unit">分钟</span>
                    </div>
                  </div>
                  <div class="param-row quota-row">
                    <span class="label">日目标占比</span>
                    <div class="control-group slider-group">
                      <el-slider v-model="tz.daily_quota" :min="0.05" :max="0.50" :step="0.05" :format-tooltip="(v: number) => `${(v * 100).toFixed(0)}%`" />
                      <span class="unit">{{ (tz.daily_quota * 100).toFixed(0) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="sparrowConfig.enabled" class="config-section">
            <div class="section-title">
              ⏱️ 检查频率
              <el-tooltip content="启用时区感知后，系统会根据不同时段自动调整扫描频率">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="param-row" style="margin-bottom: 12px;">
              <el-checkbox v-model="sparrowConfig.timezone_aware_enabled">
                启用时区感知自动调整
              </el-checkbox>
            </div>
            <!-- 时区感知启用时显示 -->
            <div v-if="sparrowConfig.timezone_aware_enabled" class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⚡</div>
                  <div class="stat-info">
                    <div class="stat-label">活跃时段</div>
                    <div class="stat-control">
                      <el-input-number v-model="sparrowConfig.check_interval.active" :min="1" :max="10" :step="1" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🌙</div>
                  <div class="stat-info">
                    <div class="stat-label">清淡时段</div>
                    <div class="stat-control">
                      <el-input-number v-model="sparrowConfig.check_interval.quiet" :min="2" :max="30" :step="1" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <!-- 时区感知禁用时显示固定间隔 -->
            <div v-else class="param-grid">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">⏰</div>
                  <div class="stat-info">
                    <div class="stat-label">固定扫描间隔</div>
                    <div class="stat-control">
                      <el-input-number v-model="sparrowConfig.check_interval.fixed" :min="1" :max="60" :step="1" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="sparrowConfig.enabled" class="config-section">
            <div class="section-title">🚫 黑名单规则</div>
            <div class="param-grid two-col">
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">🛡️</div>
                  <div class="stat-info">
                    <div class="stat-label">止损锁定</div>
                    <div class="stat-control">
                      <el-input-number v-model="sparrowConfig.blacklist.stop_loss_duration" :min="30" :max="300" :step="10" />
                      <span class="stat-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="param-item">
                <div class="stat-card">
                  <div class="stat-icon">📊</div>
                  <div class="stat-info">
                    <div class="stat-label">强势解锁</div>
                    <el-switch v-model="sparrowConfig.blacklist.strong_trend_unlock" />
                  </div>
                </div>
              </div>
              <div class="param-item full-width">
                <div class="stat-card">
                  <div class="stat-icon">📈</div>
                  <div class="stat-info">
                    <div class="stat-label">解锁阈值</div>
                    <div class="stat-control">
                      <el-input-number v-model="sparrowConfig.blacklist.strong_trend_threshold" :min="5" :max="10" :step="1" />
                      <span class="stat-unit">分</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'

const isPaused = ref(false)
const activeNav = ref('basic')
const tradeDirection = ref('long')

function getTimeZoneName(key: string | number): string {
  const keyStr = String(key)
  const names: Record<string, string> = {
    '00:00-04:00': '亚洲尾盘',
    '04:00-08:00': '欧美交接',
    '08:00-12:00': '亚洲早盘',
    '12:00-16:00': '亚洲午盘',
    '16:00-20:00': '欧洲早盘',
    '20:00-24:00': '美国早盘'
  }
  return names[keyStr] || keyStr
}

function calculatePositionRange(positionRatio: { min: number; max: number }): { normalMin: number; normalMax: number; shortMin: number; shortMax: number } {
  const normalBase = longConfig.value.tradeSize || 32
  const shortBase = longConfig.value.shortTermTradeSize || 40
  return {
    normalMin: Math.round(normalBase * positionRatio.min),
    normalMax: Math.round(normalBase * positionRatio.max),
    shortMin: Math.round(shortBase * positionRatio.min),
    shortMax: Math.round(shortBase * positionRatio.max)
  }
}

const settings = ref({
  tradingMode: 'simulation',
  useSwap: false,
  longLeverage: 3,
  shortLeverage: 3,
  simulationBalance: 1000
})

const longConfig = ref({
  minBullishScore: 5,
  sentimentThreshold: 7,
  minCapitalFlowScore: 5,
  minTrendScore: 6,
  maxTrendScore: 10,
  rsiRange: [30, 70],
  rsiMin: 30,
  rsiMax: 70,
  minVolumeRatio: 0.8,
  changeRange: [-5, 8],
  volatilityRange: [0.3, 5.0],
  minMarketTrend: 4,
  tradeSize: 32,
  shortTermTradeSize: 40,
  positionRatio: 1.0,
  maxPositions: 3,
  maxPositionPercent: 15,
  stopLossPercent: 1.5,
  takeProfit1: 1.0,
  takeProfit2: 2.0,
  takeProfitPercent: 3.0,
  timeStop: 48,
  minTradeInterval: 120,
  maxDailyTrades: 5,
  decreasingBuyEnabled: true,
  cooldownTrend1: 15,
  cooldownTrend2_3: 20,
  cooldownTrend4: 30,
  pullbackBuyEnabled: true,
  pullbackBuyThreshold: 0.97,
  rallyEnabled: false,
  rallyThreshold: 1.03,
  trendWeakThreshold: 3,
  sidewaysMinScore: 3,
  sidewaysMaxScore: 5,
  pyramidEnabled: true,
  pyramidMaxLayers: 3,
  pyramidDropThreshold: -5.0,
  pyramidDropPerLayer: -10.0,
  pyramidMaxTrendScore: 6,
  pyramidLayerRatios: '1.0,0.6,0.35,0.2',
  pyramidBaseAmount: 25,
  minCashReserve: 15,
  sentimentFusionEnabled: false,
  sentimentFusionMode: 'free',
  sentimentCoingeckoWeight: 30,
  sentimentFearGreedWeight: 30,
  sentimentNewsWeight: 20,
  sentimentTechnicalWeight: 40,
  sentimentBearishAlertThreshold: 3,
  sentimentFetchTimeout: 5.0,
  resonanceMinTotalScore: 6,
  resonanceMinCapitalFlowScore: 4,
  resonanceSentimentWeight: 30,
  resonanceTechnicalWeight: 25,
  resonanceCapitalFlowWeight: 25,
  resonanceMarketEnvWeight: 20,
  technicalMinPassCount: 2,
  technicalTrendScoreThreshold: 5,
  technicalRsiMin: 30,
  technicalRsiMax: 80,
  technicalVolumeRatioMin: 0.8,
  technicalMa5Tolerance: 0.98,
  technicalVolatilityMin: 0.2,
  // 做多智能止损（趋势档位）
  smartStopLossEnabled: true,
  stopLossTrend8Plus: 3.0,
  stopLossTrend67: 2.0,
  stopLossTrendDefault: 1.5,
  // 做多动态止盈（趋势档位）
  dynamicTakeProfitEnabled: true,
  takeProfitTrend910: 15.0,
  takeProfitTrend78: 10.0,
  takeProfitTrend56: 8.0,
  takeProfitTrendDefault: 6.0,
  // 做多分层减仓止盈
  bandTradeEnabled: true,
  bandTradeReduceAt: 1.5,
  bandTradeReducePercent: 30.0,
  bandTradeSecondReduceAt: 3.0,
  bandTradeSecondReducePercent: 50.0,
  bandTradeFinalReduceAt: 6.0,
  // 做多小盈减仓
  smallProfitReduceEnabled: true,
  smallProfitReduceThresholdPercent: 50.0,
  smallProfitReducePositionThreshold: 15.0,
  smallProfitReduceRatio: 50.0,
  // 做多止盈限价单
  takeProfitLimitOrderEnabled: true,
  takeProfitOrderPartial: 0.5
})

const shortConfig = ref({
  minBearishScore: 7,
  sentimentThreshold: 7,
  minCapitalFlowScore: 5,
  minTrendScore: 0,
  maxTrendScore: 4,
  rsiRange: [30, 70],
  rsiMin: 30,
  rsiMax: 70,
  minVolumeRatio: 0.8,
  changeRange: [-8, 5],
  volatilityRange: [0.3, 5.0],
  maxMarketTrend: 4,
  tradeSize: 32,
  shortTermTradeSize: 40,
  positionRatio: 1.0,
  maxPositions: 3,
  maxPositionPercent: 15,
  stopLossPercent: 1.5,
  takeProfit1: 1.0,
  takeProfit2: 2.0,
  timeStop: 48,
  minTradeInterval: 120,
  maxDailyTrades: 5,
  decreasingBuyEnabled: true,
  cooldownTrend1: 15,
  cooldownTrend2_3: 20,
  cooldownTrend4: 30,
  rallyEnabled: true,
  rallyThreshold: 1.03,
  pullbackBuyEnabled: false,
  pullbackBuyThreshold: 0.97,
  takeProfitPercent: 3.0,
  pyramidEnabled: true,
  pyramidMaxLayers: 3,
  pyramidDropThreshold: -3.0,
  pyramidDropPerLayer: 10.0,
  pyramidMaxTrendScore: 4,
  pyramidLayerRatios: '1.0,0.6,0.35,0.2',
  pyramidBaseAmount: 25,
  exemptionEnabled: true,
  exemptionLossHigh: 60,
  exemptionLossMedium: 45,
  exemptionProfit: 30,
  minCashReserve: 30,
  sentimentFusionEnabled: false,
  sentimentFusionMode: 'free',
  sentimentCoingeckoWeight: 30,
  sentimentFearGreedWeight: 30,
  sentimentNewsWeight: 20,
  sentimentTechnicalWeight: 40,
  sentimentBearishAlertThreshold: 3,
  sentimentFetchTimeout: 5.0,
  resonanceMinTotalScore: 6,
  resonanceMinCapitalFlowScore: 4,
  resonanceSentimentWeight: 30,
  resonanceTechnicalWeight: 25,
  resonanceCapitalFlowWeight: 25,
  resonanceMarketEnvWeight: 20,
  technicalMinPassCount: 2,
  technicalTrendScoreThreshold: 5,
  technicalRsiMin: 30,
  technicalRsiMax: 80,
  technicalVolumeRatioMin: 0.8,
  technicalMa5Tolerance: 0.98,
  technicalVolatilityMin: 0.2,
  // 做空智能止损（趋势档位）
  smartStopLossEnabled: true,
  stopLossTrend02: 3.0,
  stopLossTrend34: 2.0,
  stopLossTrendDefault: 1.5,
  // 做空动态止盈（趋势档位）
  dynamicTakeProfitEnabled: true,
  takeProfitTrend01: 15.0,
  takeProfitTrend23: 10.0,
  takeProfitTrend4: 8.0,
  takeProfitTrendDefault: 6.0,
  // 做空分层减仓止盈
  bandTradeEnabled: true,
  bandTradeReduceAt: 1.5,
  bandTradeReducePercent: 30.0,
  bandTradeSecondReduceAt: 3.0,
  bandTradeSecondReducePercent: 50.0,
  bandTradeFinalReduceAt: 6.0,
  // 做空小盈减仓
  smallProfitReduceEnabled: true,
  smallProfitReduceThresholdPercent: 50.0,
  smallProfitReducePositionThreshold: 15.0,
  smallProfitReduceRatio: 50.0,
  // 做空止盈限价单
  takeProfitLimitOrderEnabled: true,
  takeProfitOrderPartial: 0.5
})

watch(() => longConfig.value.rsiRange, (newVal) => {
  if (newVal[0] > newVal[1]) {
    longConfig.value.rsiRange = [...newVal].reverse()
  }
  longConfig.value.rsiMin = longConfig.value.rsiRange[0]
  longConfig.value.rsiMax = longConfig.value.rsiRange[1]
}, { deep: true })

watch(() => shortConfig.value.rsiRange, (newVal) => {
  if (newVal[0] > newVal[1]) {
    shortConfig.value.rsiRange = [...newVal].reverse()
  }
  shortConfig.value.rsiMin = shortConfig.value.rsiRange[0]
  shortConfig.value.rsiMax = shortConfig.value.rsiRange[1]
}, { deep: true })

watch(() => longConfig.value.changeRange, (newVal) => {
  if (newVal[0] > newVal[1]) {
    longConfig.value.changeRange = [...newVal].reverse()
  }
}, { deep: true })

watch(() => longConfig.value.volatilityRange, (newVal) => {
  if (newVal[0] > newVal[1]) {
    longConfig.value.volatilityRange = [...newVal].reverse()
  }
}, { deep: true })

watch(() => shortConfig.value.changeRange, (newVal) => {
  if (newVal[0] > newVal[1]) {
    shortConfig.value.changeRange = [...newVal].reverse()
  }
}, { deep: true })

watch(() => shortConfig.value.volatilityRange, (newVal) => {
  if (newVal[0] > newVal[1]) {
    shortConfig.value.volatilityRange = [...newVal].reverse()
  }
}, { deep: true })

const riskConfig = ref({
  maxDailyTrades: 9999,
  maxDailyLoss: 5,
  minCashReserve: 30,
  maxDailyVolume: 1000,
  buyCooldownMinutes: 30,
  tieredCooldownEnabled: true,
  cooldownTrend10: 15,
  cooldownTrend8_9: 20,
  cooldownTrend6_7: 30,
  cooldownScoreTier1: 10,
  cooldownScoreTier2: 8,
  cooldownScoreTier3: 6,
  takeProfitScoreTier1: 9,
  takeProfitScoreTier2: 7,
  takeProfitScoreTier3: 5,
  stopLossScoreTier1: 8,
  stopLossScoreTier2: 6,
  positionPercentScoreTier1: 10,
  positionPercentScoreTier2: 8,
  positionPercentScoreTier3: 6,
  bullishFallbackThreshold: 7,
  shortBearishFallbackThreshold: 7,
  cooldownHighVolatility: 5.0,
  cooldownLowVolatility: 2.0,
  cooldownHighVolatilityMultiplier: 0.7,
  cooldownLowVolatilityMultiplier: 1.3,
  maxStopLoss: -5.0,
  minStopLoss: -1.0,
  maxTakeProfit: 15.0,
  minTakeProfit: 2.0,
  timeDecayMaxStop: -8.0,
  sentimentTrendWeight: 0.6,
  sentimentNewsWeight: 0.4,
  checkIntervalHighIntensity: 2,
  checkIntervalLowIntensity: 5,
  checkIntensityThreshold: 4,
  pullbackBuyEnabled: true,
  pullbackBuyThreshold: 0.97,
  pnlCheckEnabled: true,
  pnlCheckThreshold: -1.0,
  blacklistTrendCheckEnabled: true,
  decreasingTradeSizeEnabled: true,
  goldStablecoinSpecialHandling: true,
  goldStablecoinList: 'XAUT,PAXG',
  goldStablecoinTakeProfit: 0.2,
  mutualExclusiveEnabled: true,
  mutualExclusiveMinScore: 60.0,
  mutualExclusiveScoreDiff: 15.0
})

const aiEvolutionConfig = ref({
  enabled: false,
  autoApply: false,
  minTrades: 10,
  intervalHours: 24,
  confidenceThreshold: 0.7
})

const aiAnalyzing = ref(false)
const pendingSuggestionsCount = ref(0)
const lastAiAnalysis = ref('')

const v42Features = ref({
  timezoneAware: true,
  decreasingBuy: true,
  decreasingBuyFactors: '1.0,0.6,0.35,0.2',
  overPositionExemption: true
})

const smartTradingConfig = ref({
  pyramid_enabled: true,
  pyramid_max_layers: 3,
  pyramid_drop_threshold: -5.0,
  pyramid_drop_per_layer: -10.0,
  pyramid_base_amount: 25.0,
  pyramid_layer_ratios: '1.0,0.6,0.35',
  pyramid_max_position_percent: 15.0,
  pyramid_min_trend_score: 6,
  pyramid_min_cash: 15.0,
  pyramid_on_stop_loss_enabled: true,
  pyramid_on_stop_loss_trend_score: 8,
  pyramid_on_stop_loss_max_position_percent: 15.0,
  pyramid_on_stop_loss_min_cash: 25.0,
  smart_stop_loss_enabled: true,
  stop_loss_trend_8_plus: -3.0,
  stop_loss_trend_6_7: -2.0,
  stop_loss_trend_default: -1.5,
  stop_loss_time_protection_enabled: true,
  stop_loss_time_protection_minutes: 60,
  dynamic_take_profit_enabled: true,
  take_profit_trend_9_10: 15.0,
  take_profit_trend_7_8: 10.0,
  take_profit_trend_5_6: 8.0,
  take_profit_trend_default: 6.0,
  take_profit_score_tier1: 9,
  take_profit_score_tier2: 7,
  take_profit_score_tier3: 5,
  stop_loss_score_tier1: 8,
  stop_loss_score_tier2: 6,
  position_percent_score_tier1: 10,
  position_percent_score_tier2: 8,
  position_percent_score_tier3: 6,
  bullish_fallback_threshold: 7,
  short_bearish_fallback_threshold: 7,
  partial_take_profit_percent: 0.5,
  time_decay_enabled: true,
  time_decay_factor: 0.1,
  small_profit_reduce_enabled: true,
  small_profit_reduce_threshold_percent: 50.0,
  small_profit_reduce_position_threshold: 15.0,
  over_position_reduce_enabled: true,
  over_position_reduce_threshold: 30.0,
  over_position_reduce_target: 20.0,
  over_position_exemption_enabled: true,
  exemption_loss_high_minutes: 60,
  exemption_loss_medium_minutes: 45,
  exemption_profit_minutes: 30,
  band_trade_enabled: true,
  band_trade_reduce_at: 1.5,
  band_trade_second_reduce_at: 3.0,
  band_trade_final_reduce_at: 6.0,
  band_trade_reduce_percent: 30.0,
  band_trade_second_reduce_percent: 50.0,
  band_trade_buy_back_at: -2.0,
  technical_validation_enabled: true,
  technical_min_pass_count: 2,
  technical_trend_score_threshold: 5,
  technical_rsi_min: 30.0,
  technical_rsi_max: 80.0,
  technical_volume_ratio_min: 0.8,
  technical_ma5_tolerance: 0.98,
  technical_volatility_min: 0.2
})

const dipBuyConfig = ref({
  enabled: true,
  minTrendScore: 7,
  minBtcTrend: 6,
  minEthTrend: 5,
  rsiThreshold: 35,
  volumeMultiplier: 2.0,
  minConsecutiveBearish: 3,
  requireBullishReversal: true,
  priceBelowMa5: true,
  priceBelowMa10: true
})

const bearishCandleConfig = ref({
  enabled: true,
  consecutiveCount: 2,
  minTrendScore: 6,
  priceBelowMa: true,
  rsiEnabled: true,
  rsiOversold: 40,
  volumeEnabled: true,
  volumeRatio: 1.2,
  candleInterval: '5m'
})

const crashReboundConfig = ref({
  enabled: true,
  threshold: -10.0,
  minTrendScore: 6,
  minReboundPercent: 2.0,
  rsiCheckEnabled: false,
  rsiThreshold: 30.0,
  volumeCheckEnabled: false,
  volumeRatio: 1.5
})

const shortCrashConfig = ref({
  enabled: true,
  minRise24h: 10.0,
  maxTrendScore: 4,
  minPullbackPercent: 2.0,
  rsiCheckEnabled: false,
  rsiThreshold: 70.0,
  volumeCheckEnabled: false,
  volumeRatio: 1.2
})

const takeProfitOrderConfig = ref({
  enabled: true,
  partialPercent: 50,
  adjustOnBadSentiment: true,
  badSentimentThreshold: 3
})

const shortDipConfig = ref({
  enabled: true,
  minConsecutiveBullish: 3,
  maxTrendScore: 4,
  maxBtcTrend: 4,
  maxEthTrend: 4,
  rsiThreshold: 65,
  volumeMultiplier: 2.0,
  requireBearishReversal: true,
  priceAboveMa5: true,
  priceAboveMa10: true
})

const bullishCandleConfig = ref({
  enabled: true,
  consecutiveCount: 2,
  maxTrendScore: 4,
  rsiOverbought: 60,
  priceAboveMa: true,
  rsiEnabled: true,
  volumeEnabled: true,
  volumeRatio: 1.2,
  candleInterval: '5m'
})

const sparrowConfig = ref({
  enabled: true,
  timezone_aware_enabled: true,  // 时区感知总开关
  time_zones: {
    '00:00-04:00': { intensity: 1, position_ratio: { min: 0.33, max: 0.53 }, hold_time: { min: 30, max: 60 }, daily_quota: 0.10 },
    '04:00-08:00': { intensity: 2, position_ratio: { min: 0.53, max: 0.67 }, hold_time: { min: 20, max: 40 }, daily_quota: 0.15 },
    '08:00-12:00': { intensity: 5, position_ratio: { min: 0.80, max: 1.00 }, hold_time: { min: 15, max: 60 }, daily_quota: 0.30 },
    '12:00-16:00': { intensity: 3, position_ratio: { min: 0.67, max: 0.80 }, hold_time: { min: 20, max: 50 }, daily_quota: 0.20 },
    '16:00-20:00': { intensity: 5, position_ratio: { min: 0.80, max: 1.00 }, hold_time: { min: 15, max: 60 }, daily_quota: 0.30 },
    '20:00-24:00': { intensity: 5, position_ratio: { min: 0.80, max: 1.00 }, hold_time: { min: 10, max: 45 }, daily_quota: 0.40 }
  },
  check_interval: {
    active: 2,
    quiet: 5,
    fixed: 5
  },
  blacklist: {
    stop_loss_duration: 120,
    strong_trend_unlock: true,
    strong_trend_threshold: 8,
    medium_trend_duration: 30,
    medium_trend_threshold: 6
  }
})

const currentConfig = computed(() => {
  return tradeDirection.value === 'long' ? longConfig.value : shortConfig.value
})

const trendScoreValue = computed({
  get: () => {
    return tradeDirection.value === 'long' ? longConfig.value.minTrendScore : shortConfig.value.maxTrendScore
  },
  set: (val) => {
    if (tradeDirection.value === 'long') {
      longConfig.value.minTrendScore = val
    } else {
      shortConfig.value.maxTrendScore = val
    }
  }
})

const marketTrendValue = computed({
  get: () => {
    return tradeDirection.value === 'long' ? longConfig.value.minMarketTrend : shortConfig.value.maxMarketTrend
  },
  set: (val) => {
    if (tradeDirection.value === 'long') {
      longConfig.value.minMarketTrend = val
    } else {
      shortConfig.value.maxMarketTrend = val
    }
  }
})

const bullishScoreValue = computed({
  get: () => {
    return tradeDirection.value === 'long' ? longConfig.value.minBullishScore : shortConfig.value.minBearishScore
  },
  set: (val) => {
    if (tradeDirection.value === 'long') {
      longConfig.value.minBullishScore = val
    } else {
      shortConfig.value.minBearishScore = val
    }
  }
})

watch(tradeDirection, () => {
  activeNav.value = 'basic'
})

async function saveAll() {
  try {
    await Promise.all([
      fetch('/api/v1/services/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings.value)
      }),
      fetch('/api/v1/services/simulation/balance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_balance: settings.value.simulationBalance })
      }),
      fetch('/api/v1/trading/long-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(longConfig.value)
      }),
      fetch('/api/v1/trading/short-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(shortConfig.value)
      }),
      fetch('/api/v1/trading/risk-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(riskConfig.value)
      }),
      fetch('/api/v1/services/v42-features', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timezone_aware: v42Features.value.timezoneAware,
          decreasing_buy_enabled: v42Features.value.decreasingBuy,
          decreasing_buy_factors: v42Features.value.decreasingBuyFactors.split(',').map(Number),
          over_position_exemption_enabled: v42Features.value.overPositionExemption
        })
      }),
      fetch('/api/v1/services/config/smart-trading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(smartTradingConfig.value)
      }),
      fetch('/api/v1/services/config/dip-buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dip_buy_enabled: dipBuyConfig.value.enabled,
          dip_buy_min_trend_score: dipBuyConfig.value.minTrendScore,
          dip_buy_min_btc_trend: dipBuyConfig.value.minBtcTrend,
          dip_buy_min_eth_trend: dipBuyConfig.value.minEthTrend,
          dip_buy_rsi_threshold: dipBuyConfig.value.rsiThreshold,
          dip_buy_volume_multiplier: dipBuyConfig.value.volumeMultiplier,
          dip_buy_min_consecutive_bearish: dipBuyConfig.value.minConsecutiveBearish,
          dip_buy_require_bullish_reversal: dipBuyConfig.value.requireBullishReversal,
          dip_buy_price_below_ma5: dipBuyConfig.value.priceBelowMa5,
          dip_buy_price_below_ma10: dipBuyConfig.value.priceBelowMa10
        })
      }),
      fetch('/api/v1/services/config/bearish-candle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bearish_candle_enabled: bearishCandleConfig.value.enabled,
          bearish_candle_consecutive_count: bearishCandleConfig.value.consecutiveCount,
          bearish_candle_min_trend_score: bearishCandleConfig.value.minTrendScore,
          bearish_candle_price_below_ma: bearishCandleConfig.value.priceBelowMa,
          bearish_candle_rsi_enabled: bearishCandleConfig.value.rsiEnabled,
          bearish_candle_rsi_oversold: bearishCandleConfig.value.rsiOversold,
          bearish_candle_volume_enabled: bearishCandleConfig.value.volumeEnabled,
          bearish_candle_volume_ratio: bearishCandleConfig.value.volumeRatio,
          bearish_candle_interval: bearishCandleConfig.value.candleInterval
        })
      }),
      fetch('/api/v1/services/config/crash-rebound', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          crash_rebound_enabled: crashReboundConfig.value.enabled,
          crash_rebound_threshold: crashReboundConfig.value.threshold,
          crash_rebound_min_trend_score: crashReboundConfig.value.minTrendScore,
          crash_rebound_min_rebound_percent: crashReboundConfig.value.minReboundPercent,
          crash_rebound_rsi_check_enabled: crashReboundConfig.value.rsiCheckEnabled,
          crash_rebound_rsi_threshold: crashReboundConfig.value.rsiThreshold,
          crash_rebound_volume_check_enabled: crashReboundConfig.value.volumeCheckEnabled,
          crash_rebound_volume_ratio: crashReboundConfig.value.volumeRatio
        })
      }),
      fetch('/api/v1/services/config/short-crash', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          short_crash_enabled: shortCrashConfig.value.enabled,
          short_crash_min_rise_24h: shortCrashConfig.value.minRise24h,
          short_crash_max_trend_score: shortCrashConfig.value.maxTrendScore,
          short_crash_min_pullback_percent: shortCrashConfig.value.minPullbackPercent,
          short_crash_rsi_check_enabled: shortCrashConfig.value.rsiCheckEnabled,
          short_crash_rsi_threshold: shortCrashConfig.value.rsiThreshold,
          short_crash_volume_check_enabled: shortCrashConfig.value.volumeCheckEnabled,
          short_crash_volume_ratio: shortCrashConfig.value.volumeRatio
        })
      }),
      fetch('/api/v1/services/config/short-dip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          short_dip_enabled: shortDipConfig.value.enabled,
          short_dip_min_consecutive_bullish: shortDipConfig.value.minConsecutiveBullish,
          short_dip_max_trend_score: shortDipConfig.value.maxTrendScore,
          short_dip_max_btc_trend: shortDipConfig.value.maxBtcTrend,
          short_dip_max_eth_trend: shortDipConfig.value.maxEthTrend,
          short_dip_rsi_threshold: shortDipConfig.value.rsiThreshold,
          short_dip_volume_multiplier: shortDipConfig.value.volumeMultiplier,
          short_dip_require_bearish_reversal: shortDipConfig.value.requireBearishReversal,
          short_dip_price_above_ma5: shortDipConfig.value.priceAboveMa5,
          short_dip_price_above_ma10: shortDipConfig.value.priceAboveMa10
        })
      }),
      fetch('/api/v1/services/config/bullish-candle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          short_bearish_enabled: bullishCandleConfig.value.enabled,
          short_bearish_consecutive_count: bullishCandleConfig.value.consecutiveCount,
          short_bearish_max_trend_score: bullishCandleConfig.value.maxTrendScore,
          short_bearish_price_above_ma: bullishCandleConfig.value.priceAboveMa,
          short_bearish_rsi_enabled: bullishCandleConfig.value.rsiEnabled,
          short_bearish_rsi_overbought: bullishCandleConfig.value.rsiOverbought,
          short_bearish_volume_enabled: bullishCandleConfig.value.volumeEnabled,
          short_bearish_volume_ratio: bullishCandleConfig.value.volumeRatio,
          short_bearish_candle_interval: bullishCandleConfig.value.candleInterval
        })
      }),
      fetch('/api/v1/services/config/take-profit-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          take_profit_order_enabled: takeProfitOrderConfig.value.enabled,
          take_profit_order_partial: takeProfitOrderConfig.value.partialPercent / 100,
          take_profit_adjust_on_bad_sentiment: takeProfitOrderConfig.value.adjustOnBadSentiment,
          take_profit_bad_sentiment_threshold: takeProfitOrderConfig.value.badSentimentThreshold
        })
      }),
      fetch('/api/v1/services/sparrow-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sparrowConfig.value)
      })
    ])
    ElMessage.success('所有配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function updateAiEvolutionConfig() {
  try {
    const res = await fetch('/api/v1/services/evolution/ai-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ai_evolution_enabled: aiEvolutionConfig.value.enabled,
        ai_evolution_auto_apply: aiEvolutionConfig.value.autoApply,
        ai_evolution_min_trades: aiEvolutionConfig.value.minTrades,
        ai_evolution_interval_hours: aiEvolutionConfig.value.intervalHours,
        ai_evolution_confidence_threshold: aiEvolutionConfig.value.confidenceThreshold
      })
    })
    if (res.ok) {
      ElMessage.success('AI迭代配置已保存')
    }
  } catch (e) {
    ElMessage.error('保存AI迭代配置失败')
  }
}

async function triggerAiAnalysis() {
  aiAnalyzing.value = true
  try {
    const res = await fetch(`/api/v1/services/evolution/ai-analyze?side=${tradeDirection.value}`, {
      method: 'POST'
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('AI分析完成')
      lastAiAnalysis.value = new Date().toLocaleString()
      if (data.suggestion) {
        pendingSuggestionsCount.value++
      }
    } else {
      ElMessage.warning(data.message || 'AI分析失败')
    }
  } catch (e) {
    ElMessage.error('AI分析请求失败')
  } finally {
    aiAnalyzing.value = false
  }
}

async function showAiSuggestions() {
  try {
    const res = await fetch('/api/v1/services/evolution/pending-suggestions')
    const data = await res.json()
    if (data.success && data.suggestions.length > 0) {
      const suggestion = data.suggestions[0]
      ElMessageBox.confirm(
        `${suggestion.analysis}\n\n建议内容:\n${JSON.stringify(suggestion.suggestion, null, 2)}\n\n置信度: ${(suggestion.confidence * 100).toFixed(0)}%`,
        'AI策略建议',
        {
          confirmButtonText: '应用建议',
          cancelButtonText: '忽略',
          type: 'info'
        }
      ).then(async () => {
        const applyRes = await fetch(`/api/v1/services/evolution/apply-pending?suggestion_id=${suggestion.timestamp}`)
        if (applyRes.ok) {
          ElMessage.success('AI建议已应用')
          pendingSuggestionsCount.value = Math.max(0, pendingSuggestionsCount.value - 1)
          await loadAll()
        }
      }).catch(() => {
        ElMessage.info('已忽略建议')
      })
    } else {
      ElMessage.info('暂无待确认的AI建议')
    }
  } catch (e) {
    ElMessage.error('获取AI建议失败')
  }
}

async function resetAll() {
  ElMessage.info('已恢复默认配置')
}

async function loadAll() {
  try {
    const [longRes, shortRes, riskRes, smartRes, v42Res, settingsRes, bearishRes, bullishRes, shortDipRes, shortCrashRes, simBalanceRes, dipBuyRes, crashReboundRes, takeProfitRes, sparrowRes, aiRes] = await Promise.all([
      fetch('/api/v1/trading/long-config'),
      fetch('/api/v1/trading/short-config'),
      fetch('/api/v1/trading/risk-config'),
      fetch('/api/v1/services/config/smart-trading'),
      fetch('/api/v1/services/v42-features'),
      fetch('/api/v1/services/settings'),
      fetch('/api/v1/services/config/bearish-candle'),
      fetch('/api/v1/services/config/bullish-candle'),
      fetch('/api/v1/services/config/short-dip'),
      fetch('/api/v1/services/config/short-crash'),
      fetch('/api/v1/services/simulation/balance'),
      fetch('/api/v1/services/config/dip-buy'),
      fetch('/api/v1/services/config/crash-rebound'),
      fetch('/api/v1/services/config/take-profit-order'),
      fetch('/api/v1/services/sparrow-config'),
      fetch('/api/v1/services/evolution/ai-config')
    ])

    if (longRes.ok) {
      const data = await longRes.json()
      Object.assign(longConfig.value, {
        ...data,
        pyramidDropThreshold: data.pyramidDropThreshold ?? -5.0,
        pyramidDropPerLayer: data.pyramidDropPerLayer ?? -10.0,
        pyramidMaxTrendScore: data.pyramidMaxTrendScore ?? 6,
        pyramidLayerRatios: data.pyramidLayerRatios ?? '1.0,0.6,0.35,0.2',
        pyramidBaseAmount: data.pyramidBaseAmount ?? 25,
        pyramidMaxLayers: data.pyramidMaxLayers ?? 3
      })
    }
    if (shortRes.ok) {
      const data = await shortRes.json()
      Object.assign(shortConfig.value, {
        ...data,
        pyramidDropThreshold: data.pyramidDropThreshold ?? -3.0,
        pyramidDropPerLayer: data.pyramidDropPerLayer ?? 10.0,
        pyramidMaxTrendScore: data.pyramidMaxTrendScore ?? 4,
        pyramidLayerRatios: data.pyramidLayerRatios ?? '1.0,0.6,0.35,0.2',
        pyramidBaseAmount: data.pyramidBaseAmount ?? 25,
        pyramidMaxLayers: data.pyramidMaxLayers ?? 3
      })
      if (data.rsiRange) shortConfig.value.rsiRange = data.rsiRange
      if (data.changeRange) shortConfig.value.changeRange = data.changeRange
      if (data.volatilityRange) shortConfig.value.volatilityRange = data.volatilityRange
    }
    if (riskRes.ok) {
      const data = await riskRes.json()
      Object.assign(riskConfig.value, {
        ...data,
        // 多空互斥决策配置（向后兼容）
        mutualExclusiveEnabled: data.mutualExclusiveEnabled ?? true,
        mutualExclusiveMinScore: data.mutualExclusiveMinScore ?? 60.0,
        mutualExclusiveScoreDiff: data.mutualExclusiveScoreDiff ?? 15.0
      })
    }
    if (smartRes.ok) {
      const data = await smartRes.json()
      Object.assign(smartTradingConfig.value, data)
    }
    if (v42Res.ok) {
      const data = await v42Res.json()
      v42Features.value.timezoneAware = data.timezone_aware || false
      v42Features.value.decreasingBuy = data.decreasing_buy_enabled || false
      v42Features.value.decreasingBuyFactors = Array.isArray(data.decreasing_buy_factors) 
        ? data.decreasing_buy_factors.join(',') 
        : '1.0,0.6,0.35,0.2'
      v42Features.value.overPositionExemption = data.over_position_exemption_enabled || false
    }
    if (settingsRes.ok) {
      const data = await settingsRes.json()
      Object.assign(settings.value, data)
    }
    if (bearishRes.ok) {
      const data = await bearishRes.json()
      Object.assign(bearishCandleConfig.value, {
        enabled: data.bearish_candle_enabled,
        consecutiveCount: data.bearish_candle_consecutive_count,
        minTrendScore: data.bearish_candle_min_trend_score,
        priceBelowMa: data.bearish_candle_price_below_ma,
        rsiEnabled: data.bearish_candle_rsi_enabled,
        rsiOversold: data.bearish_candle_rsi_oversold,
        volumeEnabled: data.bearish_candle_volume_enabled ?? true,
        volumeRatio: data.bearish_candle_volume_ratio ?? 1.2,
        candleInterval: data.bearish_candle_interval ?? '5m'
      })
    }
    if (bullishRes.ok) {
      const data = await bullishRes.json()
      Object.assign(bullishCandleConfig.value, {
        enabled: data.short_bearish_enabled ?? true,
        consecutiveCount: data.short_bearish_consecutive_count ?? 2,
        maxTrendScore: data.short_bearish_max_trend_score ?? 4,
        priceAboveMa: data.short_bearish_price_above_ma ?? true,
        rsiEnabled: data.short_bearish_rsi_enabled ?? true,
        rsiOverbought: data.short_bearish_rsi_overbought ?? 70,
        volumeEnabled: data.short_bearish_volume_enabled ?? true,
        volumeRatio: data.short_bearish_volume_ratio ?? 1.2,
        candleInterval: data.short_bearish_candle_interval ?? '5m'
      })
    }
    if (shortDipRes.ok) {
      const data = await shortDipRes.json()
      Object.assign(shortDipConfig.value, {
        enabled: data.short_dip_enabled ?? true,
        minConsecutiveBullish: data.short_dip_min_consecutive_bullish ?? 3,
        maxTrendScore: data.short_dip_max_trend_score ?? 4,
        maxBtcTrend: data.short_dip_max_btc_trend ?? 4,
        maxEthTrend: data.short_dip_max_eth_trend ?? 4,
        rsiThreshold: data.short_dip_rsi_threshold ?? 65,
        volumeMultiplier: data.short_dip_volume_multiplier ?? 2.0,
        requireBearishReversal: data.short_dip_require_bearish_reversal ?? true,
        priceAboveMa5: data.short_dip_price_above_ma5 ?? true,
        priceAboveMa10: data.short_dip_price_above_ma10 ?? true
      })
    }
    if (shortCrashRes.ok) {
      const data = await shortCrashRes.json()
      Object.assign(shortCrashConfig.value, {
        enabled: data.short_crash_enabled ?? true,
        minRise24h: data.short_crash_min_rise_24h ?? 10.0,
        maxTrendScore: data.short_crash_max_trend_score ?? 4,
        minPullbackPercent: data.short_crash_min_pullback_percent ?? 2.0,
        rsiCheckEnabled: data.short_crash_rsi_check_enabled ?? false,
        rsiThreshold: data.short_crash_rsi_threshold ?? 70.0,
        volumeCheckEnabled: data.short_crash_volume_check_enabled ?? false,
        volumeRatio: data.short_crash_volume_ratio ?? 1.2
      })
    }
    if (dipBuyRes.ok) {
      const data = await dipBuyRes.json()
      Object.assign(dipBuyConfig.value, {
        enabled: data.dip_buy_enabled ?? true,
        minTrendScore: data.dip_buy_min_trend_score ?? 7,
        minBtcTrend: data.dip_buy_min_btc_trend ?? 6,
        minEthTrend: data.dip_buy_min_eth_trend ?? 5,
        rsiThreshold: data.dip_buy_rsi_threshold ?? 35,
        volumeMultiplier: data.dip_buy_volume_multiplier ?? 2.0,
        minConsecutiveBearish: data.dip_buy_min_consecutive_bearish ?? 3,
        requireBullishReversal: data.dip_buy_require_bullish_reversal ?? true,
        priceBelowMa5: data.dip_buy_price_below_ma5 ?? true,
        priceBelowMa10: data.dip_buy_price_below_ma10 ?? true
      })
    }
    if (crashReboundRes.ok) {
      const data = await crashReboundRes.json()
      Object.assign(crashReboundConfig.value, {
        enabled: data.crash_rebound_enabled,
        threshold: data.crash_rebound_threshold,
        minTrendScore: data.crash_rebound_min_trend_score,
        minReboundPercent: data.crash_rebound_min_rebound_percent,
        rsiCheckEnabled: data.crash_rebound_rsi_check_enabled ?? false,
        rsiThreshold: data.crash_rebound_rsi_threshold ?? 30.0,
        volumeCheckEnabled: data.crash_rebound_volume_check_enabled ?? false,
        volumeRatio: data.crash_rebound_volume_ratio ?? 1.5
      })
    }
    if (takeProfitRes.ok) {
      const data = await takeProfitRes.json()
      Object.assign(takeProfitOrderConfig.value, {
        enabled: data.take_profit_order_enabled,
        partialPercent: data.take_profit_order_partial * 100,
        adjustOnBadSentiment: data.take_profit_adjust_on_bad_sentiment,
        badSentimentThreshold: data.take_profit_bad_sentiment_threshold
      })
    }
    if (sparrowRes.ok) {
      const data = await sparrowRes.json()
      // 转换后端数据结构以匹配前端期望
      if (data.time_zones) {
        for (const key in data.time_zones) {
          const tz = data.time_zones[key]
          if (tz.position_size) {
            // 后端使用 position_size: {min, max}，前端使用 position_ratio: {min, max}
            // 如果后端值在 0-1 范围，直接使用；否则假设是百分比需要除以 100
            const min = tz.position_size.min <= 1 ? tz.position_size.min : tz.position_size.min / 100
            const max = tz.position_size.max <= 1 ? tz.position_size.max : tz.position_size.max / 100
            tz.position_ratio = { min, max }
            delete tz.position_size
          }
          // 确保 hold_time 存在
          if (!tz.hold_time) {
            tz.hold_time = { min: 15, max: 60 }
          }
        }
      }
      // 确保 timezone_aware_enabled 有默认值
      if (data.timezone_aware_enabled === undefined) {
        data.timezone_aware_enabled = true
      }
      // 确保 check_interval.fixed 有默认值
      if (data.check_interval && data.check_interval.fixed === undefined) {
        data.check_interval.fixed = 5
      }
      Object.assign(sparrowConfig.value, data)
    }
    if (aiRes.ok) {
      const data = await aiRes.json()
      aiEvolutionConfig.value.enabled = data.ai_evolution_enabled || false
      aiEvolutionConfig.value.autoApply = data.ai_evolution_auto_apply || false
      aiEvolutionConfig.value.minTrades = data.ai_evolution_min_trades || 10
      aiEvolutionConfig.value.intervalHours = data.ai_evolution_interval_hours || 24
      aiEvolutionConfig.value.confidenceThreshold = data.ai_evolution_confidence_threshold || 0.7
      lastAiAnalysis.value = data.last_ai_analysis || ''
      pendingSuggestionsCount.value = data.pending_suggestions_count || 0
    }
    if (simBalanceRes.ok) {
      const data = await simBalanceRes.json()
      settings.value.simulationBalance = data.initial_balance
    }
  } catch (e) {
    console.error('加载配置失败:', e)
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style lang="scss" scoped>
* {
  box-sizing: border-box;
}

:deep(.el-switch) {
  --el-switch-off-color: rgba(255, 255, 255, 0.15);
  --el-switch-on-color: rgba(102, 126, 234, 0.8);

  .el-switch__core {
    background: var(--el-switch-off-color);
    border-radius: 16px;

    &::after {
      background: rgba(255, 255, 255, 0.6);
    }
  }

  &.is-checked .el-switch__core {
    background: var(--el-switch-on-color);
    border-color: var(--el-switch-on-color);

    &::after {
      background: #fff;
    }
  }

  .el-switch__label {
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
    font-weight: 500;

    &.is-active {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

.strategy-config-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  margin: 24px 32px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;

  .top-left {
    display: flex;
    align-items: center;
  }

  .top-center {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .top-right {
    display: flex;
    align-items: center;
    gap: 8px;

    :deep(.el-button) {
      min-width: 100px;
      height: 36px;
      padding: 8px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      border: none;
      background: linear-gradient(135deg, #f44336, #d32f2f);
      color: #fff;
      transition: all 0.3s ease;

      &:hover {
        background: linear-gradient(135deg, #ff6659, #f44336);
        box-shadow: 0 2px 8px rgba(244, 67, 54, 0.4);
      }
    }

    :deep(.el-button--primary) {
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: #fff;
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);

      &:hover {
        background: linear-gradient(135deg, #7b8ff0, #8a5cb3);
      }
    }
  }

  .system-status {
    display: flex;
    align-items: center;
    gap: 10px;

    .status-indicator {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #4caf50;
      animation: pulse 2s infinite;

      &.paused {
        background: #f44336;
        animation: none;
      }
    }

    .status-text {
      font-size: 14px;
      font-weight: 500;
    }
  }

  .balance-info {
    font-size: 14px;

    .label {
      color: rgba(255, 255, 255, 0.6);
      margin-right: 8px;
    }

    .value {
      font-weight: 600;
      color: #4caf50;
    }
  }
}

.direction-selector {
  display: flex;
  align-items: center;

  .direction-buttons {
    display: flex;
    gap: 0;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 10px;
    padding: 4px;
  }

  .direction-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    background: transparent;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    min-width: 100px;

    .icon {
      font-size: 16px;
    }

    .text {
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.5);
    }

    &.long:hover {
      .text {
        color: rgba(255, 255, 255, 0.8);
      }
    }

    &.long.active {
      background: linear-gradient(135deg, #667eea, #764ba2);
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);

      .text {
        color: #fff;
      }
    }

    &.short:hover {
      .text {
        color: rgba(255, 255, 255, 0.8);
      }
    }

    &.short.active {
      background: linear-gradient(135deg, #667eea, #764ba2);
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);

      .text {
        color: #fff;
      }
    }
  }
}

.main-content {
  flex: 1;
  display: flex;
  padding: 16px 32px 32px;
  gap: 24px;

  .sidebar {
    width: 240px;
    flex-shrink: 0;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 16px;
    padding: 24px 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    height: fit-content;
    position: sticky;
    top: 24px;

    .nav-section {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .nav-title {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: rgba(255, 255, 255, 0.4);
      margin-bottom: 12px;
      padding-left: 12px;
    }

    .nav-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      color: rgba(255, 255, 255, 0.6);
      font-size: 14px;

      .icon {
        font-size: 16px;
      }

      &:hover {
        background: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.9);
      }

      &.active {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.3));
        color: #fff;
        border-left: 3px solid #667eea;
      }
    }
  }

  .content-area {
    flex: 1;
    min-width: 0;
  }
}

.config-panel {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 20px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.08);

  .panel-header {
    margin-bottom: 32px;

    .panel-title {
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .panel-desc {
      color: rgba(255, 255, 255, 0.5);
      margin: 0;
      font-size: 14px;
    }
  }
}

.config-section {
  margin-bottom: 32px;

  &:last-child {
    margin-bottom: 0;
  }

  .section-title {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
}

.config-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }

  .tip-icon {
    font-size: 14px;
  }
}

.mode-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;

  .mode-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      border-color: rgba(102, 126, 234, 0.5);
      background: rgba(102, 126, 234, 0.1);
    }

    &.active {
      border-color: #667eea;
      background: rgba(102, 126, 234, 0.15);
    }

    .mode-icon {
      font-size: 28px;
    }

    .mode-info {
      flex: 1;

      .mode-name {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 4px;
      }

      .mode-desc {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
      }
    }

    .check-icon {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #667eea;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }
  }
}

.leverage-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 20px;

  .leverage-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    height: 100%;
    min-height: 64px;

    .stat-icon {
      font-size: 20px;
    }

    .stat-info {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;

      .stat-label {
        font-size: 13px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.8);
        white-space: nowrap;
        min-width: 80px;
      }

      .stat-control {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;

        .el-input-number {
          flex: 1;
          min-width: 60px;
        }

        .stat-unit {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          white-space: nowrap;
        }
      }
    }
  }
}

.balance-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  margin-top: 16px;
  height: 100%;
  min-height: 64px;

  .stat-icon {
    font-size: 20px;
  }

  .stat-info {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;

    .stat-label {
      font-size: 13px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.8);
      white-space: nowrap;
      min-width: 80px;
    }

    .stat-control {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;

      .el-input-number {
        flex: 1;
        min-width: 60px;
      }

      .stat-unit {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        white-space: nowrap;

        &.highlight {
          color: #f56c6c;
        }
      }
    }
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  height: 100%;
  min-height: 64px;

  .stat-icon {
    font-size: 20px;
  }

  .stat-info {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;

    .stat-label {
      font-size: 13px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.8);
      white-space: nowrap;
      min-width: 80px;
    }

    .stat-control {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;

      &.range {
        justify-content: space-between;
      }

      .el-slider {
        flex: 1;
        min-width: 100px;
      }

      .el-input-number {
        flex: 1;
        min-width: 60px;
      }

      .range-value-left,
      .range-value-right {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        white-space: nowrap;
        min-width: 40px;
      }

      .range-value-left {
        text-align: right;
      }

      .range-value-right {
        text-align: left;
      }

      .stat-unit {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        white-space: nowrap;
      }
    }
  }
}

.param-row {
  margin-bottom: 20px;

  &:last-child {
    margin-bottom: 0;
  }
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;

  &.two-col {
    grid-template-columns: repeat(2, 1fr);
  }

  &.three-col {
    grid-template-columns: repeat(3, 1fr);
  }

  .param-item {
    &.full-width {
      grid-column: 1 / -1;
    }

    .param-label {
      display: block;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
      margin-bottom: 10px;
    }

    .param-control {
      display: flex;
      align-items: center;
      gap: 12px;

      &.slider-control {
        flex: 1;

        .value {
          min-width: 50px;
          text-align: right;
          font-weight: 600;
          color: #667eea;

          &.highlight {
            color: #f44336;
          }
        }
      }

      &.range-control {
        flex-direction: column;
        align-items: stretch;

        .range-values {
          display: flex;
          justify-content: space-between;
          margin-top: 8px;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.5);
        }
      }

      .unit {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.4);
        white-space: nowrap;
      }
    }

    .param-hint {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.4);
      margin-top: 6px;
    }
  }
}

.toggle-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  transition: all 0.3s ease;

  &.active {
    border-color: rgba(102, 126, 234, 0.5);
    background: rgba(102, 126, 234, 0.1);
  }

  .toggle-info {
    flex: 1;
    min-width: 0;

    .toggle-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .toggle-desc {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }
  }

  .toggle-control {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;

    .el-input-number {
      flex: 1;
      min-width: 80px;
    }
  }
}

.feature-cards {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 12px;

  .feature-card {
    flex: 1;
    min-width: 280px;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    transition: all 0.3s ease;

    &.active {
      border-color: rgba(102, 126, 234, 0.5);
      background: rgba(102, 126, 234, 0.1);
    }

    .feature-icon {
      font-size: 24px;
    }

    .feature-info {
      flex: 1;

      .feature-name {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 2px;
      }

      .feature-desc {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
      }
    }
  }
}

.bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  background: rgba(0, 0, 0, 0.3);
  border-top: 1px solid rgba(255, 255, 255, 0.1);

  :deep(.el-button) {
    min-width: 140px;
  }

  :deep(.el-button--primary) {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border: none;

    &:hover {
      background: linear-gradient(135deg, #7b8ff0, #8a5cb3);
    }
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

:deep(.el-slider) {
  .el-slider__runway {
    background: rgba(255, 255, 255, 0.1);
  }

  .el-slider__bar {
    background: linear-gradient(90deg, #667eea, #764ba2);
  }

  .el-slider__button {
    border-color: #667eea;
  }
}

:deep(.el-input-number) {
  .el-input__inner {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
    color: #fff;

    &:hover {
      border-color: rgba(102, 126, 234, 0.5);
    }
  }
}

:deep(.el-radio-button__inner) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);

  &:hover {
    color: #fff;
  }
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-color: #667eea;
  color: #fff;
}

:deep(.el-switch) {
  &.is-checked .el-switch__core {
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-color: #667eea;
  }
}

.base-trade-size-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 12px;

  .label {
    font-size: 14px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
  }

  .control-group {
    display: flex;
    align-items: center;
    gap: 8px;

    .unit {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
    }
  }
}

.timezone-config {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.timezone-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px;
  overflow: hidden;

  .timezone-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;

    .timezone-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .timezone-name {
      font-weight: 600;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.9);
    }

    .timezone-time {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
    }

    .intensity-indicator {
      display: flex;
      gap: 1px;

      .star {
        font-size: 10px;
        opacity: 0.3;

        &.active {
          opacity: 1;
        }
      }
    }
  }

  .timezone-params {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .param-row {
      display: flex;
      align-items: center;
      gap: 8px;

      .label {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        min-width: 70px;
      }

      .control-group {
        display: flex;
        align-items: center;
        gap: 6px;
        flex: 1;
        min-width: 0;

        .el-input-number {
          flex: 1;
          min-width: 45px !important;

          :deep(.el-input__inner) {
            min-width: 40px !important;
          }
        }

        .separator {
          color: rgba(255, 255, 255, 0.4);
          font-size: 12px;
          flex-shrink: 0;
        }

        .unit {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.5);
          min-width: 35px;
          text-align: right;
          flex-shrink: 0;
        }
      }

      .calculated-range {
        font-size: 11px;
        color: rgba(102, 126, 234, 0.9);
        white-space: nowrap;
      }

      &.quota-row {
        .control-group {
          gap: 10px;
        }

        .el-slider {
          flex: 1;
        }

        .unit {
          min-width: 35px;
          text-align: right;
        }
      }
    }
  }
}
</style>
