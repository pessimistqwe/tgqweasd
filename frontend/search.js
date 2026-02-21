/**
 * Search Module - Поиск событий Polymarket
 * 
 * Функционал:
 * - Поиск по названию и описанию
 * - Фильтрация по категории
 * - Debounce для оптимизации запросов
 * - Отображение результатов в реальном времени
 * - Интеграция с Telegram WebApp
 */

// ==================== Configuration ====================

const SEARCH_CONFIG = {
    API_BASE: '',  // Используем локальный backend
    DEBOUNCE_DELAY: 250,  // ms
    MIN_QUERY_LENGTH: 2,
    MAX_RESULTS: 50,
    CACHE_TTL: 2 * 60 * 1000,  // 2 минуты
};

// ==================== State ====================

let searchState = {
    query: '',
    isLoading: false,
    results: [],
    error: null,
    cache: new Map(),
    debounceTimer: null,
};

// ==================== Cache ====================

/**
 * Получить данные из кэша
 */
function getCachedSearch(query) {
    const cached = searchState.cache.get(query);
    if (!cached) return null;

    const now = Date.now();
    if (now - cached.timestamp > SEARCH_CONFIG.CACHE_TTL) {
        searchState.cache.delete(query);
        return null;
    }

    return cached.data;
}

/**
 * Сохранить данные в кэш
 */
function setCachedSearch(query, data) {
    searchState.cache.set(query, {
        data,
        timestamp: Date.now(),
    });

    // Очищаем старый кэш (максимум 50 записей)
    if (searchState.cache.size > 50) {
        const firstKey = searchState.cache.keys().next().value;
        searchState.cache.delete(firstKey);
    }
}

/**
 * Очистить весь кэш
 */
function clearSearchCache() {
    searchState.cache.clear();
    console.log('🧹 Search cache cleared');
}

// ==================== API Calls ====================

/**
 * Поиск рынков Polymarket
 *
 * @param {string} query - Поисковый запрос
 * @param {string} category - Категория (опционально)
 * @returns {Promise<Array>} Результаты поиска
 */
async function searchMarkets(query, category = null) {
    const cacheKey = `${query}:${category || 'all'}`;

    // Проверяем кэш
    const cached = getCachedSearch(cacheKey);
    if (cached) {
        console.log('💾 Search cache hit:', query);
        return cached;
    }

    // Ищем по локальной базе данных через backend API
    const params = new URLSearchParams({
        q: query,
        limit: SEARCH_CONFIG.MAX_RESULTS,
    });

    if (category) {
        params.append('category', category);
    }

    try {
        // Используем локальный endpoint /events с поиском
        const response = await fetch(`${SEARCH_CONFIG.API_BASE}/events/search?${params}`);

        if (!response.ok) {
            // Fallback: ищем в Polymarket API
            console.log('⚠️ Local search failed, trying Polymarket API...');
            return await searchPolymarketFallback(query, category);
        }

        const data = await response.json();
        const results = data.events || [];

        // Сохраняем в кэш
        setCachedSearch(cacheKey, results);

        return results;

    } catch (error) {
        console.error('❌ Search error:', error);
        // Fallback на Polymarket API
        return await searchPolymarketFallback(query, category);
    }
}

/**
 * Fallback поиск через Polymarket API
 */
async function searchPolymarketFallback(query, category = null) {
    const params = new URLSearchParams({
        q: query,
        limit: SEARCH_CONFIG.MAX_RESULTS,
    });

    if (category) {
        params.append('category', category);
    }

    const response = await fetch(`https://gamma-api.polymarket.com/markets?${params}`);
    
    if (!response.ok) {
        throw new Error(`Search API error: ${response.status}`);
    }

    const data = await response.json();
    const markets = data.markets || data.events || [];
    
    // Преобразуем в формат совместимый с локальным
    const results = markets.map(market => ({
        id: market.id || market.conditionId,
        polymarket_id: market.conditionId || market.id,
        title: market.question || market.title,
        description: market.description || '',
        category: market.category || detectCategory(market),
        image_url: market.image || '',
        volume: market.volume || 0,
        options: market.outcomes || market.tokens?.map(t => t.outcome) || [],
        end_time: market.endDate || market.end_date
    }));
    
    return results;
}

/**
 * Определяет категорию для рынка Polymarket
 */
function detectCategory(market) {
    const text = ((market.question || '') + ' ' + (market.description || '')).toLowerCase();
    if (text.includes('bitcoin') || text.includes('btc') || text.includes('ethereum') || text.includes('crypto')) return 'crypto';
    if (text.includes('sport') || text.includes('nba') || text.includes('football')) return 'sports';
    if (text.includes('politic') || text.includes('election') || text.includes('trump')) return 'politics';
    if (text.includes('movie') || text.includes('oscar') || text.includes('music')) return 'pop_culture';
    if (text.includes('business') || text.includes('stock') || text.includes('tesla')) return 'business';
    return 'other';
}

/**
 * Получить детали рынка
 * 
 * @param {string} marketId - ID рынка
 * @returns {Promise<Object>} Данные рынка
 */
async function getMarketDetails(marketId) {
    try {
        const response = await fetch(`${SEARCH_CONFIG.API_BASE}/market/${marketId}`);
        
        if (!response.ok) {
            throw new Error(`Market details API error: ${response.status}`);
        }

        return await response.json();

    } catch (error) {
        console.error('❌ Market details error:', error);
        throw error;
    }
}

/**
 * Получить трендовые рынки
 * 
 * @returns {Promise<Array>} Трендовые рынки
 */
async function getTrendingMarkets(limit = 10) {
    try {
        const response = await fetch(`${SEARCH_CONFIG.API_BASE}/trending?limit=${limit}`);
        
        if (!response.ok) {
            throw new Error(`Trending API error: ${response.status}`);
        }

        const data = await response.json();
        return data || [];

    } catch (error) {
        console.error('❌ Trending error:', error);
        return [];
    }
}

/**
 * Получить последние рынки
 * 
 * @returns {Promise<Array>} Последние рынки
 */
async function getRecentMarkets(limit = 10) {
    try {
        const response = await fetch(`${SEARCH_CONFIG.API_BASE}/recent?limit=${limit}`);
        
        if (!response.ok) {
            throw new Error(`Recent API error: ${response.status}`);
        }

        const data = await response.json();
        return data || [];

    } catch (error) {
        console.error('❌ Recent error:', error);
        return [];
    }
}

// ==================== Search UI ====================

/**
 * Инициализировать поиск
 * 
 * @param {string} inputSelector - Селектор input элемента
 * @param {string} resultsSelector - Селектор контейнера результатов
 * @param {Function} onResultClick - Callback при клике на результат
 */
function initSearch(inputSelector, resultsSelector, onResultClick = null) {
    const input = document.querySelector(inputSelector);
    const resultsContainer = document.querySelector(resultsSelector);

    if (!input || !resultsContainer) {
        console.error('❌ Search elements not found');
        return;
    }

    // Обработчик input
    input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        // Очищаем предыдущий таймер
        if (searchState.debounceTimer) {
            clearTimeout(searchState.debounceTimer);
        }

        // Если запрос пустой - очищаем результаты
        if (query.length < SEARCH_CONFIG.MIN_QUERY_LENGTH) {
            searchState.query = '';
            searchState.results = [];
            searchState.error = null;
            renderSearchResults([]);
            return;
        }

        // Debounce
        searchState.debounceTimer = setTimeout(async () => {
            await performSearch(query);
        }, SEARCH_CONFIG.DEBOUNCE_DELAY);
    });

    // Обработчик фокуса - показываем трендовые
    input.addEventListener('focus', async () => {
        if (searchState.results.length === 0 && searchState.query.length < SEARCH_CONFIG.MIN_QUERY_LENGTH) {
            const trending = await getTrendingMarkets(5);
            if (trending.length > 0) {
                renderTrendingPlaceholder(trending);
            }
        }
    });

    // Обработчик клика вне поиска - скрываем результаты
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
            resultsContainer.style.display = 'none';
        }
    });

    // Сохраняем ссылку на callback
    if (onResultClick) {
        window.searchResultClickHandler = onResultClick;
    }

    console.log('✅ Search initialized');
}

/**
 * Выполнить поиск
 * 
 * @param {string} query - Поисковый запрос
 */
async function performSearch(query) {
    searchState.query = query;
    searchState.isLoading = true;
    searchState.error = null;

    updateSearchUI('loading');

    try {
        const results = await searchMarkets(query);
        searchState.results = results;
        searchState.isLoading = false;

        if (results.length === 0) {
            updateSearchUI('empty');
        } else {
            renderSearchResults(results);
            updateSearchUI('results');
        }

    } catch (error) {
        searchState.isLoading = false;
        searchState.error = error.message;
        updateSearchUI('error');
    }
}

/**
 * Обновить UI поиска
 * 
 * @param {string} state - 'loading', 'results', 'empty', 'error'
 */
function updateSearchUI(state) {
    const resultsContainer = document.querySelector('.search-results');
    if (!resultsContainer) return;

    resultsContainer.style.display = 'block';

    switch (state) {
        case 'loading':
            resultsContainer.innerHTML = `
                <div class="search-loading">
                    <div class="spinner"></div>
                    <span>${isRussian ? 'Поиск...' : 'Searching...'}</span>
                </div>
            `;
            break;

        case 'empty':
            resultsContainer.innerHTML = `
                <div class="search-empty">
                    <span class="emoji">🔍</span>
                    <span>${isRussian ? 'Ничего не найдено' : 'Nothing found'}</span>
                </div>
            `;
            break;

        case 'error':
            resultsContainer.innerHTML = `
                <div class="search-error">
                    <span class="emoji">❌</span>
                    <span>${isRussian ? 'Ошибка поиска' : 'Search error'}</span>
                </div>
            `;
            break;

        case 'results':
            // Результаты уже отрендерены
            break;
    }
}

/**
 * Отрендерить результаты поиска
 * 
 * @param {Array} results - Результаты поиска
 */
function renderSearchResults(results) {
    const resultsContainer = document.querySelector('.search-results');
    if (!resultsContainer) return;

    if (!results || results.length === 0) {
        resultsContainer.style.display = 'none';
        return;
    }

    const html = results.map((market, index) => {
        const changeClass = market.change24h >= 0 ? 'positive' : 'negative';
        const changeSign = market.change24h >= 0 ? '+' : '';
        
        return `
            <div class="search-result-item" data-market-id="${market.id}" data-index="${index}">
                <div class="search-result-header">
                    <span class="search-result-title">${escapeHtml(market.question)}</span>
                    ${market.category ? `<span class="search-result-category">${market.category}</span>` : ''}
                </div>
                <div class="search-result-meta">
                    <span class="search-result-volume">
                        💰 ${formatVolume(market.volume)}
                    </span>
                    ${market.change24h !== null ? `
                        <span class="search-result-change ${changeClass}">
                            ${changeSign}${market.change24h}%
                        </span>
                    ` : ''}
                </div>
                ${market.outcomes && market.outcomes.length > 0 ? `
                    <div class="search-result-outcomes">
                        ${market.outcomes.slice(0, 3).map((outcome, i) => {
                            const price = market.outcomePrices?.[i] ? `${market.outcomePrices[i].toFixed(1)}%` : '?';
                            return `
                                <div class="search-result-outcome">
                                    <span class="outcome-name">${escapeHtml(outcome)}</span>
                                    <span class="outcome-price">${price}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    resultsContainer.innerHTML = html;

    // Добавляем обработчики кликов
    resultsContainer.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const marketId = item.dataset.marketId;
            const index = parseInt(item.dataset.index);
            const market = results[index];

            if (window.searchResultClickHandler) {
                window.searchResultClickHandler(market);
            } else {
                // Default behavior: открыть детали рынка
                openMarketDetails(marketId);
            }

            // Скрываем результаты
            resultsContainer.style.display = 'none';
            
            // Haptic feedback
            if (tg.HapticFeedback) {
                tg.HapticFeedback.impactOccurred('light');
            }
        });
    });
}

/**
 * Отрендерить трендовые placeholder
 * 
 * @param {Array} trending - Трендовые рынки
 */
function renderTrendingPlaceholder(trending) {
    const resultsContainer = document.querySelector('.search-results');
    if (!resultsContainer) return;

    const title = isRussian ? '🔥 Трендовые рынки' : '🔥 Trending Markets';

    const html = `
        <div class="search-trending-title">${title}</div>
        ${trending.map(market => `
            <div class="search-result-item" data-market-id="${market.id}">
                <div class="search-result-header">
                    <span class="search-result-title">${escapeHtml(market.question)}</span>
                </div>
                <div class="search-result-meta">
                    <span class="search-result-volume">💰 ${formatVolume(market.volume)}</span>
                    ${market.change24h !== null ? `
                        <span class="search-result-change ${market.change24h >= 0 ? 'positive' : 'negative'}">
                            ${market.change24h >= 0 ? '+' : ''}${market.change24h}%
                        </span>
                    ` : ''}
                </div>
            </div>
        `).join('')}
    `;

    resultsContainer.innerHTML = html;

    // Добавляем обработчики кликов
    resultsContainer.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const marketId = item.dataset.marketId;
            openMarketDetails(marketId);
            resultsContainer.style.display = 'none';
            
            if (tg.HapticFeedback) {
                tg.HapticFeedback.impactOccurred('light');
            }
        });
    });
}

// ==================== Helpers ====================

/**
 * Открыть детали рынка
 * 
 * @param {string} marketId - ID рынка
 */
async function openMarketDetails(marketId) {
    try {
        // Показываем loading
        if (tg.showPopup) {
            tg.showPopup({
                title: isRussian ? 'Загрузка...' : 'Loading...',
                message: isRussian ? 'Получение данных рынка' : 'Fetching market data',
            });
        }

        const market = await getMarketDetails(marketId);
        
        // Здесь можно открыть модальное окно или перейти на страницу рынка
        console.log('Market details:', market);

        // Для примера - покажем popup
        if (tg.showPopup) {
            tg.showPopup({
                title: market.question,
                message: `${isRussian ? 'Объем:' : 'Volume:'} ${formatVolume(market.volume)}\n${isRussian ? 'Исходы:' : 'Outcomes:'} ${market.outcomes?.join(', ')}`,
                buttons: [{ type: 'ok' }]
            });
        }

    } catch (error) {
        console.error('❌ Error opening market details:', error);
        
        if (tg.showPopup) {
            tg.showPopup({
                title: isRussian ? 'Ошибка' : 'Error',
                message: isRussian ? 'Не удалось загрузить данные рынка' : 'Failed to load market data',
                buttons: [{ type: 'ok' }]
            });
        }
    }
}

/**
 * Форматировать объем
 * 
 * @param {number} volume - Объем
 * @returns {string} Форматированный объем
 */
function formatVolume(volume) {
    if (!volume) return '$0';
    
    if (volume >= 1000000) {
        return `$${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
        return `$${(volume / 1000).toFixed(1)}K`;
    } else {
        return `$${volume.toFixed(0)}`;
    }
}

/**
 * Экранировать HTML
 * 
 * @param {string} text - Текст
 * @returns {string} Экранированный текст
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Очистить поиск
 */
function clearSearch() {
    const input = document.querySelector('input[type="search"], input.search-input');
    const resultsContainer = document.querySelector('.search-results');
    
    if (input) {
        input.value = '';
    }
    
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
        resultsContainer.style.display = 'none';
    }

    searchState.query = '';
    searchState.results = [];
    searchState.error = null;
    
    if (searchState.debounceTimer) {
        clearTimeout(searchState.debounceTimer);
        searchState.debounceTimer = null;
    }
}

/**
 * Получить текущее состояние поиска
 * 
 * @returns {Object} Состояние поиска
 */
function getSearchState() {
    return {
        query: searchState.query,
        isLoading: searchState.isLoading,
        results: searchState.results,
        error: searchState.error,
        cacheSize: searchState.cache.size,
    };
}

// ==================== Export ====================

// Делаем функции доступными глобально
window.searchMarkets = searchMarkets;
window.getMarketDetails = getMarketDetails;
window.getTrendingMarkets = getTrendingMarkets;
window.getRecentMarkets = getRecentMarkets;
window.initSearch = initSearch;
window.performSearch = performSearch;
window.clearSearch = clearSearch;
window.getSearchState = getSearchState;
window.clearSearchCache = clearSearchCache;

// ==================== Init ====================

// Авто-инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    // Ищем search input в header
    const searchInput = document.querySelector('header input[type="search"], header .search-input, #search-input');
    const resultsContainer = document.querySelector('.search-results');

    if (searchInput && !resultsContainer) {
        // Создаем контейнер для результатов если его нет
        const container = document.createElement('div');
        container.className = 'search-results';
        searchInput.parentNode.appendChild(container);
    }

    if (searchInput) {
        initSearch('input[type="search"], .search-input', '.search-results');
    }
});
