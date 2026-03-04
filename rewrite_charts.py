import os

filepath = 'frontend/script.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we don't accidentally do this multiple times if the script runs twice
if 'LightweightCharts' in content and 'Chart.js' not in content:
    print('Already done')
    exit(0)

print('Reading script...')

content = content.replace('let currentChartLabels = [];', 'let currentChartData = [];')
content = content.replace('let currentChartPrices = [];', 'let currentCandleSeries = null;')

start_str = "// Chart rendering using Chart.js (Polymarket style) with gradient"
end_str = "function updateChartPriceDisplay("

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx == -1 or end_idx == -1:
    print('Could not find start or end block')
    exit(1)

new_code = '''// Chart rendering using Lightweight Charts
let eventChart = null;
let currentCandleSeries = null;
let chartUpdateInterval = null; // Auto-update interval

async function renderEventChart(eventId, options) {
    console.log('📊 [Chart] === ЗАПУСК renderEventChart ===');
    const chartContainer = document.getElementById('event-chart-canvas');
    if (!chartContainer) {
        console.error('❌ [Chart] Canvas элемент не найден!');
        return;
    }

    if (chartUpdateInterval) {
        clearInterval(chartUpdateInterval);
        chartUpdateInterval = null;
    }

    if (eventChart) {
        eventChart.remove();
        eventChart = null;
        currentCandleSeries = null;
    }

    let eventType = 'crypto';
    try {
        const event = await apiRequest(`/events/${eventId}`);
        if (event && event.category) {
            eventType = event.category;
        }
    } catch (e) {
        console.error('❌ [Chart] Error loading event:', e);
    }

    if (['sports', 'politics', 'pop_culture'].includes(eventType)) {
        renderBetHistory(eventId);
        return;
    }

    renderPriceChart(eventId, options);
}

async function renderBetHistory(eventId) {
    const chartContainer = document.getElementById('event-chart');
    if (!chartContainer) return;

    const originalInnerHTML = chartContainer.innerHTML;

    try {
        const response = await fetch(`${backendUrl}/events/${eventId}/bet-history`);
        let betHistory = [];
        if (response.ok) {
            betHistory = await response.json();
        }

        if (betHistory.length === 0) {
            chartContainer.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center;">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                    </svg>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">Нет ставок</div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">Будьте первым кто сделает ставку!</div>
                </div>
            `;
            return;
        }

        chartContainer.innerHTML = `
            <div class="bet-history-container" style="height: 100%; overflow-y: auto; padding: 8px;">
                <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 12px; margin-bottom: 8px;">
                    История ставок
                </div>
                ${betHistory.map(bet => `
                    <div class="bet-history-item" style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 32px; height: 32px; border-radius: var(--radius-md); background: var(--accent-muted); display: flex; align-items: center; justify-content: center; font-weight: 600; color: var(--accent); font-size: 14px;">
                                ${bet.username.charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <div style="font-size: 13px; font-weight: 500; color: var(--text-primary);">${escapeHtml(bet.username)}</div>
                                <div style="font-size: 11px; color: var(--text-muted);">${formatTimeAgo(new Date(bet.timestamp).getTime())}</div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">${bet.amount.toFixed(2)} USDT</div>
                            <div style="font-size: 11px; color: var(--text-muted);">${bet.shares.toFixed(2)} shares @ ${(bet.price * 100).toFixed(1)}%</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        console.error('Error loading bet history:', e);
        chartContainer.innerHTML = originalInnerHTML;
    }
}

let binanceWebSocket = null;
let currentChartInterval = '15m';
let chartPriceData = { firstPrice: 0, lastPrice: 0, symbol: null };
let webSocketPriceBuffer = [];
let webSocketUpdateTimeout = null;
let currentChartData = [];
let currentBinanceSymbol = null;

async function renderPriceChart(eventId, options) {
    const chartContainer = document.getElementById('event-chart-canvas');
    if (!chartContainer) return;

    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }

    webSocketPriceBuffer = [];
    currentChartData = [];
    chartPriceData = { firstPrice: 0, lastPrice: 0, symbol: null };

    let event = null;
    try {
        event = await apiRequest(`/events/${eventId}`);
    } catch (e) {
        return;
    }

    let binanceSymbol = null;
    const eventText = (event.title + ' ' + (event.description || '')).toLowerCase();

    for (const [key, symbol] of Object.entries(CRYPTO_SYMBOLS)) {
        if (eventText.includes(key)) {
            binanceSymbol = symbol;
            break;
        }
    }

    if (!binanceSymbol) {
        renderPolymarketChart(eventId, event, options);
        return;
    }

    currentBinanceSymbol = binanceSymbol;
    renderRealtimeChart(chartContainer, binanceSymbol, options);
}

async function renderPolymarketChart(eventId, event, options) {
    const chartContainer = document.getElementById('event-chart-canvas');
    const chartTimeframe = document.getElementById('event-chart-timeframe');
    const chartInfo = document.getElementById('event-chart-info');
    const chartLiveBadge = document.getElementById('chart-live-badge');
    const parent = document.getElementById('event-chart');

    if (!chartContainer) return;

    if (chartTimeframe) chartTimeframe.style.display = 'flex';
    if (chartInfo) chartInfo.style.display = 'block';
    if (chartLiveBadge) chartLiveBadge.style.display = 'none';

    if (eventChart) {
        eventChart.remove();
        eventChart = null;
    }

    const polymarketId = event.polymarket_id;
    if (!polymarketId) {
        if (parent) {
            parent.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center; padding: 20px;">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 8v4M12 16h.01"/>
                    </svg>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">График недоступен</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Для этого события нет данных графика</div>
                </div>
            `;
        }
        return;
    }

    const selectedOption = options && options.length > 0 ? options[0] : null;
    const outcomeName = selectedOption?.text || selectedOption?.outcome || 'Yes';

    updateChartPriceDisplay(0.5, 0);

    try {
        const chartData = await window.polymarketChartService.loadCandles(
            polymarketId,
            outcomeName,
            currentChartInterval || '1h',
            168
        );

        const priceChange = chartData.priceChange || 0;
        updateChartPriceDisplay(chartData.lastPrice || 0.5, priceChange);

        const chartColor = priceChange >= 0 ? '#10b981' : '#ef4444';

        eventChart = LightweightCharts.createChart(chartContainer, {
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#888',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            timeScale: { timeVisible: true, secondsVisible: false },
            rightPriceScale: { borderVisible: false }
        });

        currentCandleSeries = eventChart.addLineSeries({
            color: chartColor,
            lineWidth: 2,
            crosshairMarkerRadius: 4,
        });

        let seriesData = chartData.labels.map((ts, i) => {
            return {
                time: Math.floor(new Date(ts).getTime() / 1000),
                value: chartData.prices[i]
            };
        }).filter(item => !isNaN(item.time) && !isNaN(item.value));
        
        seriesData.sort((a, b) => a.time - b.time);
        
        // Remove duplicates
        const uniqueSeriesData = [];
        let lastTime = 0;
        for (const item of seriesData) {
            if (item.time > lastTime) {
                uniqueSeriesData.push(item);
                lastTime = item.time;
            }
        }

        currentCandleSeries.setData(uniqueSeriesData);
        eventChart.timeScale().fitContent();

        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.onclick = async () => {
                document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentChartInterval = btn.dataset.interval;
                await renderPolymarketChart(eventId, event, options);
            };
        });

    } catch (error) {
        if (parent) {
            parent.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center; padding: 20px;">
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">Ошибка загрузки графика</div>
                    <div style="font-size: 12px; color: var(--text-muted);">${error.message || 'Неизвестная ошибка'}</div>
                </div>
            `;
        }
    }
}

function renderRealtimeChart(chartContainer, binanceSymbol, options) {
    const chartColor = '#f2b03d';
    document.getElementById('event-chart-timeframe').style.display = 'flex';
    document.getElementById('event-chart-info').style.display = 'block';

    if (eventChart) {
        eventChart.remove();
        eventChart = null;
    }

    document.querySelectorAll('.timeframe-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentChartInterval = btn.dataset.interval;

            webSocketPriceBuffer = [];
            currentChartData = [];
            
            if (webSocketUpdateTimeout) {
                clearTimeout(webSocketUpdateTimeout);
            }

            if (window.binanceService) {
                window.binanceService.disconnectWebSocket();
            } else if (binanceWebSocket) {
                binanceWebSocket.close();
                binanceWebSocket = null;
            }

            loadChartData(binanceSymbol, currentChartInterval);
        };
    });

    eventChart = LightweightCharts.createChart(chartContainer, {
        layout: {
            background: { type: 'solid', color: 'transparent' },
            textColor: '#888',
        },
        grid: {
            vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
            horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        timeScale: { timeVisible: true, secondsVisible: false },
        rightPriceScale: { borderVisible: false }
    });

    currentCandleSeries = eventChart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
    });

    if (window.binanceService) {
        loadChartData(binanceSymbol, currentChartInterval);
    } else {
        loadChartDataDirect(binanceSymbol, currentChartInterval);
    }
}

async function loadChartData(symbol, interval) {
    try {
        if (window.binanceService) {
            const { labels, prices, firstPrice, lastPrice, candles } =
                await window.binanceService.loadHistoricalCandles(symbol, interval);

            if (labels.length === 0) return;

            currentChartData = candles.map(c => ({
                time: Math.floor(c.timestamp / 1000),
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close
            }));
            
            currentChartData.sort((a, b) => a.time - b.time);
            
            // Remove duplicates
            const uniqueSeriesData = [];
            let lastTime = 0;
            for (const item of currentChartData) {
                if (item.time > lastTime) {
                    uniqueSeriesData.push(item);
                    lastTime = item.time;
                }
            }
            currentChartData = uniqueSeriesData;

            chartPriceData = { firstPrice, lastPrice, symbol, candles };
            window.chartLastUpdateTime = Date.now();
            updateChartPriceDisplay(lastPrice);
            updatePredictionOdds(prices, symbol);

            if (currentCandleSeries) {
                currentCandleSeries.setData(currentChartData);
                eventChart.timeScale().fitContent();
            }

            connectBinanceWebSocket(symbol, interval);
        } else {
            await loadChartDataDirect(symbol, interval);
        }
    } catch (err) {
        console.error('Error loading chart:', err);
    }
}

async function loadChartDataDirect(symbol, interval) {
    const binanceIntervals = window.BINANCE_INTERVALS || {
        '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d'
    };
    const candleLimits = window.CANDLE_LIMITS || {
        '1m': 100, '5m': 100, '15m': 96, '1h': 168, '4h': 168, '1d': 90
    };
    
    const binanceInterval = binanceIntervals[interval] || '15m';
    const limit = candleLimits[interval] || 96;
    const normalizedSymbol = symbol.toUpperCase();

    const url = "https://api.binance.com/api/v3/klines?symbol=" + normalizedSymbol + "&interval=" + binanceInterval + "&limit=" + limit;
    const response = await fetch(url);
    if (!response.ok) throw new Error("Binance API error: " + response.status);

    const data = await response.json();
    currentChartData = data.map(candle => ({
        time: Math.floor(candle[0] / 1000),
        open: parseFloat(candle[1]),
        high: parseFloat(candle[2]),
        low: parseFloat(candle[3]),
        close: parseFloat(candle[4])
    }));
    
    currentChartData.sort((a, b) => a.time - b.time);

    // Remove duplicates
    const uniqueSeriesData = [];
    let lastTime = 0;
    for (const item of currentChartData) {
        if (item.time > lastTime) {
            uniqueSeriesData.push(item);
            lastTime = item.time;
        }
    }
    currentChartData = uniqueSeriesData;

    if (currentChartData.length > 0) {
        const firstPrice = currentChartData[0].close;
        const lastPrice = currentChartData[currentChartData.length - 1].close;
        chartPriceData.firstPrice = firstPrice;
        chartPriceData.lastPrice = lastPrice;

        updateChartPriceDisplay(lastPrice);
        updatePredictionOdds(currentChartData.map(c => c.close), symbol);

        if (currentCandleSeries) {
            currentCandleSeries.setData(currentChartData);
            eventChart.timeScale().fitContent();
        }
    }

    connectBinanceWebSocket(symbol);
}

// Ensure function signatures match the remaining file
'''

final_content = content[:start_idx] + new_code + "\n" + content[end_idx:]

ws_start_str = "function connectBinanceWebSocket("
ws_end_str = "// ==================== UTILITY FUNCTIONS ===================="

start_ws = final_content.find(ws_start_str)
end_ws = final_content.find(ws_end_str)

ws_code = '''function connectBinanceWebSocket(symbol) {
    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }

    const wsSymbol = symbol.toLowerCase();
    const streamName = wsSymbol + '@kline_' + (window.BINANCE_INTERVALS ? window.BINANCE_INTERVALS[currentChartInterval] : '15m');
    const wsUrl = "wss://stream.binance.com:9443/ws/" + streamName;

    binanceWebSocket = new WebSocket(wsUrl);

    binanceWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.k) {
            const kline = data.k;
            const price = parseFloat(kline.c);
            
            const currentCandle = {
                time: Math.floor(kline.t / 1000),
                open: parseFloat(kline.o),
                high: parseFloat(kline.h),
                low: parseFloat(kline.l),
                close: price
            };

            if (currentCandleSeries) {
                currentCandleSeries.update(currentCandle);
            }
            updateChartPriceDisplay(price);
        } else if (data.p) {
            const price = parseFloat(data.p);
            updateChartPriceDisplay(price);
        }
    };

    binanceWebSocket.onclose = function() {
        setTimeout(() => {
            if (binanceWebSocket && binanceWebSocket.readyState === WebSocket.CLOSED) {
                connectBinanceWebSocket(symbol);
            }
        }, 5000);
    };
}
'''

final_content = final_content[:start_ws] + ws_code + "\n" + final_content[end_ws:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(final_content)

print('Done')
