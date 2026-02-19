/**
 * Polymarket SDK Wrapper for Frontend
 * 
 * Обёртка над официальным Polymarket CLOB SDK для TypeScript
 * Статус: Prepared for Integration (требуется подключение кошелька)
 * 
 * Установка зависимостей:
 *   npm install @polymarket/clob-client ethers@5
 * 
 * Использование:
 *   import { PolymarketSDK } from './services/polymarketSDK';
 *   
 *   const sdk = new PolymarketSDK();
 *   await sdk.connectWallet();
 *   const markets = await sdk.getMarkets();
 */

// Типы для Polymarket API
export interface Market {
    id: string;
    question: string;
    outcomes: string[];
    outcomePrices: string[];
    volume: number;
    endDate: string;
    active: boolean;
    image?: string;
}

export interface OrderBook {
    bids: { price: number; size: number }[];
    asks: { price: number; size: number }[];
}

export interface Order {
    id: string;
    token_id: string;
    price: number;
    size: number;
    side: 'BUY' | 'SELL';
    status: 'OPEN' | 'FILLED' | 'CANCELLED';
    createdAt: string;
}

export interface Position {
    market: string;
    outcome: string;
    size: number;
    avgPrice: number;
    pnl: number;
}

export interface Candle {
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export type OrderType = 'GTC' | 'GTD' | 'FOK';
export type Resolution = 'minute' | 'hour' | 'day' | 'week';

/**
 * Polymarket SDK Error
 */
export class PolymarketSDKError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'PolymarketSDKError';
    }
}

/**
 * Polymarket Not Configured Error
 */
export class PolymarketNotConfiguredError extends PolymarketSDKError {
    constructor(message: string) {
        super(message);
        this.name = 'PolymarketNotConfiguredError';
    }
}

/**
 * Polymarket SDK Class
 * 
 * Wrapper над официальным Polymarket CLOB SDK
 * Предоставляет методы для работы с рынками, ордерами и позициями
 */
export class PolymarketSDK {
    private client: any = null;
    private configured: boolean = false;
    private host: string;
    private chainId: number;
    private signer: any = null;
    private apiCreds: any = null;

    constructor(host: string = 'https://clob.polymarket.com', chainId: number = 137) {
        this.host = host;
        this.chainId = chainId;
    }

    /**
     * Проверка настроено ли SDK
     */
    isConfigured(): boolean {
        return this.configured;
    }

    /**
     * Подключение кошелька
     * 
     * @param privateKey - Приватный ключ кошелька
     * @param apiCreds - API credentials (опционально)
     */
    async connectWallet(privateKey: string, apiCreds?: { apiKey: string; apiSecret: string; apiPassphrase: string }): Promise<void> {
        try {
            // Проверяем наличие ethers.js
            if (typeof window === 'undefined' || !(window as any).ethers) {
                throw new PolymarketSDKError('ethers.js not available');
            }

            const ethers = (window as any).ethers;
            
            // Создаём signer из приватного ключа
            this.signer = new ethers.Wallet(privateKey);

            // Импортируем CLOB клиент
            const { ClobClient } = await import('@polymarket/clob-client');
            
            // Создаём клиента
            this.client = new ClobClient(
                this.host,
                this.chainId,
                this.signer,
                apiCreds || undefined
            );

            this.apiCreds = apiCreds || null;
            this.configured = true;

            console.log('✅ PolymarketSDK connected for chain:', this.chainId);
        } catch (error) {
            console.error('❌ Failed to connect wallet:', error);
            throw new PolymarketSDKError(`Failed to connect wallet: ${error}`);
        }
    }

    /**
     * Подключение через браузерный кошелёк (MetaMask, etc.)
     */
    async connectBrowserWallet(): Promise<void> {
        try {
            if (typeof window === 'undefined' || !(window as any).ethereum) {
                throw new PolymarketNotConfiguredError('No crypto wallet found');
            }

            const ethers = (window as any).ethers;
            
            // Запрашиваем доступ к кошельку
            await (window as any).ethereum.request({ method: 'eth_requestAccounts' });
            
            // Создаём signer из provider
            const provider = new ethers.BrowserProvider((window as any).ethereum);
            this.signer = await provider.getSigner();

            // Переключаемся на Polygon
            const chainId = await (window as any).ethereum.request({ method: 'eth_chainId' });
            const polygonChainId = '0x89'; // 137 in hex
            
            if (chainId !== polygonChainId) {
                try {
                    await (window as any).ethereum.request({
                        method: 'wallet_switchEthereumChain',
                        params: [{ chainId: polygonChainId }],
                    });
                } catch (switchError) {
                    // Network needs to be added
                    await (window as any).ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [{
                            chainId: polygonChainId,
                            chainName: 'Polygon Mainnet',
                            nativeCurrency: { name: 'MATIC', symbol: 'MATIC', decimals: 18 },
                            rpcUrls: ['https://polygon-rpc.com'],
                            blockExplorerUrls: ['https://polygonscan.com'],
                        }],
                    });
                }
            }

            // Импортируем CLOB клиент
            const { ClobClient } = await import('@polymarket/clob-client');
            
            this.client = new ClobClient(
                this.host,
                this.chainId,
                this.signer
            );

            this.configured = true;
            console.log('✅ PolymarketSDK connected via browser wallet');
        } catch (error) {
            console.error('❌ Failed to connect browser wallet:', error);
            throw new PolymarketSDKError(`Failed to connect browser wallet: ${error}`);
        }
    }

    // ==================== MARKET DATA ====================

    /**
     * Получить список рынков
     */
    async getMarkets(limit: number = 100, active: boolean = true): Promise<Market[]> {
        this.ensureConfigured();
        
        try {
            const markets = await this.client.getMarkets();
            
            // Фильтрация
            let filtered = active ? markets.filter((m: any) => m.active) : markets;
            return filtered.slice(0, limit);
        } catch (error) {
            console.error('❌ Error fetching markets:', error);
            throw new PolymarketSDKError(`Failed to fetch markets: ${error}`);
        }
    }

    /**
     * Получить данные конкретного рынка
     */
    async getMarket(marketId: string): Promise<Market | null> {
        this.ensureConfigured();
        
        try {
            return await this.client.getMarket(marketId);
        } catch (error) {
            console.error(`❌ Error fetching market ${marketId}:`, error);
            return null;
        }
    }

    /**
     * Получить стакан заявок
     */
    async getOrderbook(tokenId: string): Promise<OrderBook> {
        this.ensureConfigured();
        
        try {
            return await this.client.getOrderbook(tokenId);
        } catch (error) {
            console.error(`❌ Error fetching orderbook for ${tokenId}:`, error);
            return { bids: [], asks: [] };
        }
    }

    /**
     * Получить текущую цену токена
     */
    async getPrice(tokenId: string): Promise<number | null> {
        this.ensureConfigured();
        
        try {
            return await this.client.getPrice(tokenId);
        } catch (error) {
            console.error(`❌ Error fetching price for ${tokenId}:`, error);
            return null;
        }
    }

    /**
     * Получить историю цен
     */
    async getPricesHistory(
        tokenId: string,
        resolution: Resolution = 'hour',
        limit: number = 168
    ): Promise<Candle[]> {
        this.ensureConfigured();
        
        try {
            return await this.client.getPricesHistory(tokenId, resolution, limit);
        } catch (error) {
            console.error(`❌ Error fetching price history for ${tokenId}:`, error);
            return [];
        }
    }

    // ==================== ORDERS ====================

    /**
     * Разместить ордер
     */
    async placeOrder(
        tokenId: string,
        price: number,
        size: number,
        side: 'BUY' | 'SELL' = 'BUY',
        orderType: OrderType = 'GTC'
    ): Promise<Order | null> {
        this.ensureConfigured();
        
        try {
            const { OrderArgs, OrderType: ClobOrderType, BUY, SELL } = await import('@polymarket/clob-client');
            
            const orderArgs = new OrderArgs({
                price,
                size,
                side: side === 'BUY' ? BUY : SELL,
                token_id: tokenId
            });
            
            const signedOrder = await this.client.createOrder(orderArgs);
            
            const clobOrderType = orderType === 'GTC' ? ClobOrderType.GTC 
                : orderType === 'GTD' ? ClobOrderType.GTD 
                : ClobOrderType.FOK;
            
            const resp = await this.client.postOrder(signedOrder, clobOrderType);
            
            console.log('✅ Order placed:', resp.orderID);
            return resp;
        } catch (error) {
            console.error('❌ Error placing order:', error);
            throw new PolymarketSDKError(`Failed to place order: ${error}`);
        }
    }

    /**
     * Отменить ордер
     */
    async cancelOrder(orderId: string): Promise<boolean> {
        this.ensureConfigured();
        
        try {
            const resp = await this.client.cancelOrder(orderId);
            console.log('✅ Order cancelled:', orderId);
            return resp.success;
        } catch (error) {
            console.error(`❌ Error cancelling order ${orderId}:`, error);
            return false;
        }
    }

    /**
     * Отменить все ордера
     */
    async cancelAllOrders(): Promise<number> {
        this.ensureConfigured();
        
        try {
            const resp = await this.client.cancelAll();
            const cancelled = resp.orderIDs?.length || 0;
            console.log(`✅ Cancelled ${cancelled} orders`);
            return cancelled;
        } catch (error) {
            console.error('❌ Error cancelling all orders:', error);
            return 0;
        }
    }

    /**
     * Получить ордера пользователя
     */
    async getOrders(marketId?: string): Promise<Order[]> {
        this.ensureConfigured();
        
        try {
            let orders = await this.client.getOrders();
            
            if (marketId) {
                orders = orders.filter((o: any) => o.market === marketId);
            }
            
            return orders;
        } catch (error) {
            console.error('❌ Error fetching orders:', error);
            return [];
        }
    }

    // ==================== POSITIONS ====================

    /**
     * Получить текущие позиции
     */
    async getPositions(): Promise<Position[]> {
        this.ensureConfigured();
        
        try {
            return await this.client.getPositions();
        } catch (error) {
            console.error('❌ Error fetching positions:', error);
            return [];
        }
    }

    /**
     * Получить баланс
     */
    async getBalance(tokenId?: string): Promise<Record<string, number>> {
        this.ensureConfigured();
        
        try {
            const balances = await this.client.getBalances();
            
            if (tokenId) {
                return { [tokenId]: balances[tokenId] || 0 };
            }
            
            return balances;
        } catch (error) {
            console.error('❌ Error fetching balances:', error);
            return {};
        }
    }

    // ==================== UTILITY ====================

    /**
     * Получить время сервера
     */
    async getServerTime(): Promise<Date | null> {
        try {
            return this.client ? await this.client.getTime() : null;
        } catch (error) {
            console.error('❌ Error fetching server time:', error);
            return null;
        }
    }

    /**
     * Получить ставку комиссии
     */
    async getFeeRate(): Promise<number> {
        try {
            return this.client ? await this.client.getFeeRate() : 0;
        } catch (error) {
            console.error('❌ Error fetching fee rate:', error);
            return 0;
        }
    }

    /**
     * Получить tick size для токена
     */
    async getTickSize(tokenId: string): Promise<number> {
        try {
            return this.client ? await this.client.getTickSize(tokenId) : 0.01;
        } catch (error) {
            console.error(`❌ Error fetching tick size for ${tokenId}:`, error);
            return 0.01;
        }
    }

    // ==================== BUILDER SDK (Placeholders) ====================

    /**
     * Подписать транзакцию
     * Требует @polymarket/builder-signing-sdk
     */
    async signTransaction(transaction: any): Promise<string | null> {
        console.warn('⚠️ signTransaction() requires @polymarket/builder-signing-sdk (not installed)');
        return null;
    }

    /**
     * Отправить безгазовую транзакцию
     * Требует @polymarket/builder-relayer-client
     */
    async submitGaslessTransaction(transaction: any, signature: string): Promise<string | null> {
        console.warn('⚠️ submitGaslessTransaction() requires @polymarket/builder-relayer-client (not installed)');
        return null;
    }

    /**
     * Получить объём билдера
     */
    async getBuilderVolume(): Promise<number> {
        console.warn('⚠️ getBuilderVolume() requires Builder SDK (not installed)');
        return 0;
    }

    // ==================== HELPERS ====================

    private ensureConfigured(): void {
        if (!this.configured) {
            throw new PolymarketNotConfiguredError(
                'Polymarket SDK not configured. Call connectWallet() first.'
            );
        }
    }
}

// ==================== GLOBAL INSTANCE ====================

let globalSDK: PolymarketSDK | null = null;

/**
 * Получить глобальный экземпляр SDK
 */
export function getPolymarketSDK(): PolymarketSDK {
    if (globalSDK === null) {
        globalSDK = new PolymarketSDK();
    }
    return globalSDK;
}

/**
 * Проверить настроен ли SDK
 */
export function isPolymarketConfigured(): boolean {
    return globalSDK?.isConfigured() || false;
}
