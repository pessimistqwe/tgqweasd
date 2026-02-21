let tg = window.Telegram.WebApp;

// Авто-определение языка (с проверкой готовности Telegram WebApp)
function getUserLanguage() {
    try {
        const user = tg.initDataUnsafe?.user;
        if (user && user.language_code) {
            return user.language_code;
        }
    } catch (e) {
        console.log('Telegram WebApp not ready, using browser language');
    }
    // Fallback на язык браузера
    return navigator.language?.startsWith('ru') ? 'ru' : 'en';
}

const userLang = getUserLanguage();
const isRussian = userLang === 'ru';

// Расширенный список сохраняемых терминов (имена, криптовалюты, команды, бренды)
const PRESERVE_TERMS = [
    // Криптовалюты и токены
    'Bitcoin', 'Ethereum', 'Solana', 'XRP', 'Cardano', 'Dogecoin', 'Polkadot',
    'Avalanche', 'Chainlink', 'Polygon', 'Litecoin', 'Uniswap', 'Cosmos',
    'Monero', 'Stellar', 'VeChain', 'Filecoin', 'Tron', 'Hedera', 'Algorand',
    'Elrond', 'Near', 'Fantom', 'Aptos', 'Arbitrum', 'Optimism', 'Injective',
    'BTC', 'ETH', 'SOL', 'DOGE', 'ADA', 'DOT', 'AVAX', 'LINK', 'MATIC', 'LTC',
    'UNI', 'ATOM', 'XLM', 'VET', 'FIL', 'TRX', 'HBAR', 'ALGO', 'EGLD', 'NEAR',
    'FTM', 'APT', 'ARB', 'OP', 'INJ', 'USDT', 'USDC', 'BNB', 'BUSD', 'DAI',
    // Известные люди
    'Trump', 'Biden', 'Putin', 'Zelensky', 'Musk', 'Bezos', 'Gates', 'Buffett',
    'Obama', 'Clinton', 'Bloomberg', 'Zuckerberg', 'Cook', 'Nadella', 'Altman',
    'Sam', 'Elon', 'Jeff', 'Bill', 'Warren', 'Barack', 'Hillary', 'Mike', 'Mark',
    'Tim', 'Satya', 'Jensen', 'Huang', 'Dimon', 'Larry', 'Sergey', 'Jack',
    // Компании и бренды
    'Tesla', 'Apple', 'Google', 'Amazon', 'Microsoft', 'Nvidia', 'Meta', 'Netflix',
    'OpenAI', 'SpaceX', 'Blue Origin', 'Boeing', 'Airbus', 'Fed', 'SEC', 'CFTC',
    'BlackRock', 'Vanguard', 'Fidelity', 'JPMorgan', 'Goldman Sachs', 'Morgan Stanley',
    'Coinbase', 'Binance', 'Kraken', 'FTX', 'Gemini', 'Bitfinex', 'Huobi', 'OKX',
    'Bybit', 'KuCoin', 'Gate.io', 'Bitstamp', 'Crypto.com', 'Ledger', 'Trezor',
    // Команды и лиги
    'NBA', 'NFL', 'MLB', 'NHL', 'UFC', 'FIFA', 'UEFA', 'Premier League', 'La Liga',
    'Serie A', 'Bundesliga', 'Ligue 1', 'Champions League', 'Europa League',
    'World Cup', 'Olympics', 'Super Bowl', 'Stanley Cup', 'Finals', 'Playoffs',
    'Lakers', 'Celtics', 'Warriors', 'Bulls', 'Heat', 'Nets', 'Knicks', 'Rockets',
    'Spurs', 'Mavericks', 'Suns', 'Clippers', '76ers', 'Bucks', 'Nuggets', 'Heat',
    'Chiefs', 'Eagles', '49ers', 'Cowboys', 'Patriots', 'Giants', 'Packers', 'Bills',
    'Ravens', 'Steelers', 'Bengals', 'Browns', 'Titans', 'Colts', 'Texans', 'Jaguars',
    'Dolphins', 'Jets', 'Chargers', 'Raiders', 'Seahawks', 'Rams', 'Cardinals', 'Falcons',
    'Panthers', 'Saints', 'Buccaneers', 'Lions', 'Vikings', 'Bears', 'Lions',
    'Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Cubs', 'Cardinals', 'Astros', 'Mets',
    'Real Madrid', 'Barcelona', 'Manchester United', 'Liverpool', 'Chelsea', 'Arsenal',
    'Manchester City', 'Tottenham', 'Bayern Munich', 'PSG', 'Juventus', 'AC Milan',
    'Inter Milan', 'Napoli', 'Roma', 'Lazio', 'Atletico Madrid', 'Sevilla', 'Valencia',
    // Технологии и продукты
    'ChatGPT', 'GPT', 'Claude', 'Gemini', 'LLaMA', 'Transformer', 'AI', 'ML', 'DL',
    'iOS', 'Android', 'Windows', 'macOS', 'Linux', 'Ubuntu', 'Red Hat', 'Docker',
    'Kubernetes', 'AWS', 'Azure', 'GCP', 'Cloudflare', 'Vercel', 'Netlify', 'Heroku',
    // Страны и города
    'USA', 'US', 'Russia', 'Ukraine', 'China', 'UK', 'Germany', 'France', 'Italy',
    'Spain', 'Japan', 'South Korea', 'India', 'Brazil', 'Canada', 'Australia',
    'Moscow', 'Kyiv', 'Beijing', 'Shanghai', 'London', 'Paris', 'Berlin', 'Rome',
    'Madrid', 'Tokyo', 'Seoul', 'Mumbai', 'Delhi', 'Sao Paulo', 'Toronto', 'Sydney',
    'Washington', 'New York', 'Los Angeles', 'San Francisco', 'Chicago', 'Houston',
    // Другое
    'Metamask', 'Trust Wallet', 'Phantom', 'Coinbase Wallet', 'Ledger Live',
    'OpenSea', 'Rarible', 'Foundation', 'SuperRare', 'NFT', 'DeFi', 'CeFi', 'DAO',
    'Staking', 'Yield Farming', 'Liquidity Pool', 'AMM', 'DEX', 'CEX', 'CEX',
    'Layer 1', 'Layer 2', 'Rollup', 'Sidechain', 'Bridge', 'Cross-chain',
    'Bull Market', 'Bear Market', 'HODL', 'FOMO', 'FUD', 'DYOR', 'WAGMI', 'NGMI'
];

// Регулярные выражения для сохранения паттернов (деньги, даты, числа)
const PRESERVE_PATTERNS = [
    // Денежные суммы: $100,000, $1M, $1.5B, 1000 USDT
    /\$[\d,]+(?:\.\d+)?(?:[MBK])?/gi,
    /\d+(?:\.\d+)?\s*(?:USDT|BTC|ETH|TON|USD|EUR)/gi,
    // Даты: December 2024, Jan 15, 2025, Q4 2024
    /(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}/gi,
    /(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}/gi,
    /Q[1-4]\s+\d{4}/gi,
    // Процентные значения: 50%, 75.5%
    /\d+(?:\.\d+)?%/g,
    // Числа с разделителями: 1,000,000
    /\b\d{1,3}(?:,\d{3})+\b/g
];

// Паттерны для удаления (американское время, лишние обозначения)
const REMOVE_PATTERNS = [
    /\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*(?:ET|EST|EDT)?/gi,  // 3:00 PM ET
    /\s*\d{1,2}\s*(?:AM|PM)\s*(?:ET|EST|EDT)?/gi,  // 3 PM ET
    /\s*(?:AM|PM)\s*(?:ET|EST|EDT)/gi,  // PM ET
    /\s*(?:ET|EST|EDT)\b/gi,  // ET, EST, EDT
];

// Расширенный словарь для перевода
const TRANSLATION_DICT = {
    // Месяцы
    'January': 'Январь', 'February': 'Февраль', 'March': 'Март',
    'April': 'Апрель', 'May': 'Май', 'June': 'Июнь',
    'July': 'Июль', 'August': 'Август', 'September': 'Сентябрь',
    'October': 'Октябрь', 'November': 'Ноябрь', 'December': 'Декабрь',
    // Направления и сравнения
    'Up': 'Вверх', 'Down': 'Вниз', 'Above': 'Выше', 'Below': 'Ниже',
    'Higher': 'Выше', 'Lower': 'Ниже', 'Rise': 'Рост', 'Fall': 'Падение',
    'Increase': 'Увеличение', 'Decrease': 'Уменьшение', 'Grow': 'Рост',
    'Will': 'Будет', 'will': 'будет', 'Won\'t': 'Не будет', 'won\'t': 'не будет',
    // Предлоги и союзы
    'or': 'или', 'and': 'и', 'the': '', 'The': '',
    'at': 'в', 'by': 'к', 'from': 'с', 'to': 'до', 'To': 'До',
    'of': '', 'in': 'в', 'In': 'В', 'on': 'на', 'On': 'На', 'for': 'для',
    'with': 'с', 'Without': 'Без', 'without': 'без',
    'between': 'между', 'Among': 'Среди', 'among': 'среди',
    'into': 'в', 'out': 'из', 'over': 'над', 'under': 'под',
    'before': 'до', 'after': 'после', 'during': 'во время',
    'Within': 'В пределах', 'within': 'в пределах',
    // Время
    'PM': 'МСК', 'AM': 'МСК', 'PM ET': 'МСК', 'AM ET': 'МСК',
    'end': 'конец', 'End': 'Конец', 'start': 'начало', 'Start': 'Начало',
    'time': 'время', 'Time': 'Время',
    'day': 'день', 'Day': 'День', 'week': 'неделя', 'Week': 'Неделя',
    'month': 'месяц', 'Month': 'Месяц', 'year': 'год', 'Year': 'Год',
    'today': 'сегодня', 'Tomorrow': 'Завтра', 'tomorrow': 'завтра',
    'yesterday': 'вчера', 'Yesterday': 'Вчера',
    'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
    'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье',
    // Финансы и рынки
    'price': 'цена', 'Price': 'Цена', 'value': 'значение', 'Value': 'Значение',
    'market': 'рынок', 'Market': 'Рынок', 'markets': 'рынки', 'Markets': 'Рынки',
    'trading': 'торговля', 'Trading': 'Торговля', 'trade': 'торговать',
    'close': 'закрытие', 'Close': 'Закрытие', 'closed': 'закрыто',
    'high': 'максимум', 'High': 'Максимум', 'low': 'минимум', 'Low': 'Минимум',
    'open': 'открытие', 'Open': 'Открытие', 'opened': 'открыто',
    'stock': 'акция', 'Stock': 'Акция', 'stocks': 'акции', 'Stocks': 'Акции',
    'share': 'акция', 'Share': 'Акция', 'shares': 'акции',
    'bond': 'облигация', 'Bond': 'Облигация',
    'fund': 'фонд', 'Fund': 'Фонд', 'ETF': 'ETF', 'Mutual Fund': 'Паевой фонд',
    'IPO': 'IPO', 'Merger': 'Слияние', 'merger': 'слияние',
    'Acquisition': 'Поглощение', 'acquisition': 'поглощение',
    'Revenue': 'Выручка', 'revenue': 'выручка', 'Earnings': 'Прибыль',
    'Profit': 'Прибыль', 'profit': 'прибыль', 'Loss': 'Убыток', 'loss': 'убыток',
    'CEO': 'Гендиректор', 'CFO': 'Финдиректор', 'COO': 'Опердиректор',
    'inflation': 'инфляция', 'Inflation': 'Инфляция',
    'recession': 'рецессия', 'Recession': 'Рецессия',
    'economy': 'экономика', 'Economy': 'Экономика',
    'GDP': 'ВВП', 'interest rate': 'процентная ставка',
    'Federal Reserve': 'Федеральная резервная система', 'Fed': 'ФРС',
    // События
    'event': 'событие', 'Event': 'Событие', 'events': 'события',
    'election': 'выборы', 'Election': 'Выборы',
    'vote': 'голосование', 'Vote': 'Голосование', 'voting': 'голосование',
    'ballot': 'бюллетень', 'Ballot': 'Бюллетень',
    'game': 'игра', 'Game': 'Игра', 'games': 'игры',
    'match': 'матч', 'Match': 'Матч', 'matches': 'матчи',
    'final': 'финал', 'Final': 'Финал', 'finals': 'финалы',
    'semifinal': 'полуфинал', 'Semifinal': 'Полуфинал',
    'championship': 'чемпионат', 'Championship': 'Чемпионат',
    'tournament': 'турнир', 'Tournament': 'Турнир',
    'season': 'сезон', 'Season': 'Сезон',
    'playoff': 'плей-офф', 'Playoff': 'Плей-офф', 'playoffs': 'плей-офф',
    // Крипто
    'crypto': 'крипто', 'Crypto': 'Крипто', 'cryptocurrency': 'криптовалюта',
    'blockchain': 'блокчейн', 'Blockchain': 'Блокчейн',
    'token': 'токен', 'Token': 'Токен', 'tokens': 'токены',
    'coin': 'монета', 'Coin': 'Монета', 'coins': 'монеты',
    'altcoin': 'альткоин', 'Altcoin': 'Альткоин',
    'mining': 'майнинг', 'Mining': 'Майнинг',
    'wallet': 'кошелёк', 'Wallet': 'Кошелёк',
    'exchange': 'биржа', 'Exchange': 'Биржа',
    'bull': 'бык', 'Bull': 'Бык', 'bear': 'медведь', 'Bear': 'Медведь',
    'staking': 'стейкинг', 'Staking': 'Стейкинг',
    'yield': 'доходность', 'Yield': 'Доходность',
    'farm': 'фарминг', 'Farm': 'Фарминг', 'farming': 'фарминг',
    // Спорт
    'team': 'команда', 'Team': 'Команда', 'teams': 'команды',
    'player': 'игрок', 'Player': 'Игрок', 'players': 'игроки',
    'coach': 'тренер', 'Coach': 'Тренер',
    'win': 'победа', 'Win': 'Победа', 'wins': 'победы',
    'loss': 'поражение', 'Loss': 'Поражение', 'losses': 'поражения',
    'score': 'счёт', 'Score': 'Счёт', 'scores': 'счёты',
    'points': 'очки', 'Points': 'Очки',
    'goals': 'голы', 'Goals': 'Голы', 'goal': 'гол', 'Goal': 'Гол',
    'assist': 'передача', 'Assist': 'Передача',
    'rebound': 'подбор', 'Rebound': 'Подбор',
    'touchdown': 'тачдаун', 'Touchdown': 'Тачдаун',
    'home run': 'хоум-ран', 'Home Run': 'Хоум-ран',
    'athlete': 'атлет', 'Athlete': 'Атлет',
    'sport': 'спорт', 'Sport': 'Спорт', 'sports': 'виды спорта',
    'league': 'лига', 'League': 'Лига',
    // Политика
    'president': 'президент', 'President': 'Президент',
    'congress': 'конгресс', 'Congress': 'Конгресс',
    'senate': 'сенат', 'Senate': 'Сенат',
    'democrat': 'демократ', 'Democrat': 'Демократ',
    'republican': 'республиканец', 'Republican': 'Республиканец',
    'government': 'правительство', 'Government': 'Правительство',
    'minister': 'министр', 'Minister': 'Министр',
    'parliament': 'парламент', 'Parliament': 'Парламент',
    'policy': 'политика', 'Policy': 'Политика',
    'legislation': 'законодательство', 'Legislation': 'Законодательство',
    'bill': 'законопроект', 'Bill': 'Законопроект',
    'veto': 'вето', 'Veto': 'Вето',
    'impeachment': 'импичмент', 'Impeachment': 'Импичмент',
    'sanction': 'санкция', 'Sanction': 'Санкция',
    'tariff': 'тариф', 'Tariff': 'Тариф',
    'embassy': 'посольство', 'Embassy': 'Посольство',
    'ambassador': 'посол', 'Ambassador': 'Посол',
    'summit': 'саммит', 'Summit': 'Саммит',
    'treaty': 'договор', 'Treaty': 'Договор',
    'campaign': 'кампания', 'Campaign': 'Кампания',
    'debate': 'дебаты', 'Debate': 'Дебаты',
    'poll': 'опрос', 'Poll': 'Опрос', 'polls': 'опросы',
    'referendum': 'референдум', 'Referendum': 'Референдум',
    // Наука и технологии
    'science': 'наука', 'Science': 'Наука',
    'research': 'исследование', 'Research': 'Исследование',
    'discovery': 'открытие', 'Discovery': 'Открытие',
    'scientist': 'учёный', 'Scientist': 'Учёный',
    'study': 'исследование', 'Study': 'Исследование',
    'experiment': 'эксперимент', 'Experiment': 'Эксперимент',
    'technology': 'технология', 'Technology': 'Технология',
    'physics': 'физика', 'Physics': 'Физика',
    'chemistry': 'химия', 'Chemistry': 'Химия',
    'biology': 'биология', 'Biology': 'Биология',
    'medicine': 'медицина', 'Medicine': 'Медицина',
    'health': 'здоровье', 'Health': 'Здоровье',
    'disease': 'болезнь', 'Disease': 'Болезнь',
    'treatment': 'лечение', 'Treatment': 'Лечение',
    'drug': 'препарат', 'Drug': 'Препарат',
    'vaccine': 'вакцина', 'Vaccine': 'Вакцина',
    'FDA': 'FDA', 'NASA': 'NASA', 'ESA': 'ESA',
    'rocket': 'ракета', 'Rocket': 'Ракета',
    'mars': 'марс', 'Mars': 'Марс', 'moon': 'луна', 'Moon': 'Луна',
    'climate': 'климат', 'Climate': 'Климат',
    'space': 'космос', 'Space': 'Космос',
    'satellite': 'спутник', 'Satellite': 'Спутник',
    'telescope': 'телескоп', 'Telescope': 'Телескоп',
    // Поп-культура
    'movie': 'фильм', 'Movie': 'Фильм', 'movies': 'фильмы',
    'film': 'фильм', 'Film': 'Фильм',
    'oscar': 'оскар', 'Oscar': 'Оскар', 'Oscars': 'Оскары',
    'grammy': 'грэмми', 'Grammy': 'Грэмми', 'Grammys': 'Грэмми',
    'emmy': 'эмми', 'Emmy': 'Эмми', 'Emmys': 'Эмми',
    'celebrity': 'знаменитость', 'Celebrity': 'Знаменитость',
    'music': 'музыка', 'Music': 'Музыка',
    'album': 'альбом', 'Album': 'Альбом',
    'artist': 'артист', 'Artist': 'Артист',
    'actor': 'актёр', 'Actor': 'Актёр',
    'actress': 'актриса', 'Actress': 'Актриса',
    'tv show': 'телешоу', 'TV Show': 'Телешоу',
    'series': 'сериал', 'Series': 'Сериал',
    'streaming': 'стриминг', 'Streaming': 'Стриминг',
    'netflix': 'netflix', 'Netflix': 'Netflix',
    'disney': 'disney', 'Disney': 'Disney',
    'marvel': 'marvel', 'Marvel': 'Marvel',
    'award': 'награда', 'Award': 'Награда', 'awards': 'награды',
    'premiere': 'премьера', 'Premiere': 'Премьера',
    // Общие слова
    'more': 'больше', 'More': 'Больше',
    'less': 'меньше', 'Less': 'Меньше',
    'than': 'чем', 'Than': 'Чем',
    'this': 'этот', 'This': 'Этот',
    'that': 'тот', 'That': 'Тот',
    'these': 'эти', 'These': 'Эти',
    'those': 'те', 'Those': 'Те',
    'what': 'что', 'What': 'Что',
    'which': 'который', 'Which': 'Который',
    'who': 'кто', 'Who': 'Кто',
    'when': 'когда', 'When': 'Когда',
    'where': 'где', 'Where': 'Где',
    'why': 'почему', 'Why': 'Почему',
    'how': 'как', 'How': 'Как',
    'new': 'новый', 'New': 'Новый',
    'old': 'старый', 'Old': 'Старый',
    'first': 'первый', 'First': 'Первый',
    'last': 'последний', 'Last': 'Последний',
    'next': 'следующий', 'Next': 'Следующий',
    'previous': 'предыдущий', 'Previous': 'Предыдущий',
    'current': 'текущий', 'Current': 'Текущий',
    'future': 'будущий', 'Future': 'Будущий',
    'past': 'прошлый', 'Past': 'Прошлый',
    'same': 'тот же', 'Same': 'Тот же',
    'different': 'другой', 'Different': 'Другой',
    'important': 'важный', 'Important': 'Важный',
    'possible': 'возможный', 'Possible': 'Возможный',
    'impossible': 'невозможный', 'Impossible': 'Невозможный',
    'likely': 'вероятный', 'Likely': 'Вероятный',
    'unlikely': 'маловероятный', 'Unlikely': 'Маловероятный',
    'certain': 'определённый', 'Certain': 'Определённый',
    'uncertain': 'неопределённый', 'Uncertain': 'Неопределённый',
    'sure': 'уверенный', 'Sure': 'Уверенный',
    'true': 'правда', 'True': 'Правда',
    'false': 'ложь', 'False': 'Ложь',
    'yes': 'да', 'Yes': 'Да',
    'no': 'нет', 'No': 'Нет',
    'not': 'не', 'Not': 'Не',
    'never': 'никогда', 'Never': 'Никогда',
    'always': 'всегда', 'Always': 'Всегда',
    'sometimes': 'иногда', 'Sometimes': 'Иногда',
    'often': 'часто', 'Often': 'Часто',
    'rarely': 'редко', 'Rarely': 'Редко',
    'already': 'уже', 'Already': 'Уже',
    'still': 'всё ещё', 'Still': 'Всё ещё',
    'yet': 'ещё', 'Yet': 'Ещё',
    'just': 'только что', 'Just': 'Только что',
    'only': 'только', 'Only': 'Только',
    'also': 'также', 'Also': 'Также',
    'too': 'тоже', 'Too': 'Тоже',
    'either': 'либо', 'Either': 'Либо',
    'neither': 'ни', 'Neither': 'Ни',
    'both': 'оба', 'Both': 'Оба',
    'all': 'все', 'All': 'Все',
    'some': 'некоторые', 'Some': 'Некоторые',
    'any': 'любой', 'Any': 'Любой',
    'each': 'каждый', 'Each': 'Каждый',
    'every': 'каждый', 'Every': 'Каждый',
    'many': 'много', 'Many': 'Много',
    'few': 'немного', 'Few': 'Немного',
    'several': 'несколько', 'Several': 'Несколько',
    'most': 'большинство', 'Most': 'Большинство',
    'such': 'такой', 'Such': 'Такой',
    'another': 'другой', 'Another': 'Другой',
    'other': 'другой', 'Other': 'Другой',
    'others': 'другие', 'Others': 'Другие',
    // Действия
    'make': 'делать', 'Make': 'Делать',
    'do': 'делать', 'Do': 'Делать',
    'have': 'иметь', 'Have': 'Иметь',
    'has': 'имеет', 'Has': 'Имеет',
    'had': 'имел', 'Had': 'Имел',
    'get': 'получать', 'Get': 'Получать',
    'got': 'получил', 'Got': 'Получил',
    'take': 'брать', 'Take': 'Брать',
    'took': 'взял', 'Took': 'Взял',
    'come': 'приходить', 'Come': 'Приходить',
    'came': 'пришёл', 'Came': 'Пришёл',
    'go': 'идти', 'Go': 'Идти',
    'went': 'пошёл', 'Went': 'Пошёл',
    'see': 'видеть', 'See': 'Видеть',
    'saw': 'увидел', 'Saw': 'Увидел',
    'know': 'знать', 'Know': 'Знать',
    'knew': 'знал', 'Knew': 'Знал',
    'think': 'думать', 'Think': 'Думать',
    'thought': 'думал', 'Thought': 'Думал',
    'want': 'хотеть', 'Want': 'Хотеть',
    'wanted': 'хотел', 'Wanted': 'Хотел',
    'need': 'нуждаться', 'Need': 'Нуждаться',
    'needed': 'нуждался', 'Needed': 'Нуждался',
    'use': 'использовать', 'Use': 'Использовать',
    'used': 'использовал', 'Used': 'Использовал',
    'find': 'находить', 'Find': 'Находить',
    'found': 'нашёл', 'Found': 'Нашёл',
    'give': 'давать', 'Give': 'Давать',
    'gave': 'дал', 'Gave': 'Дал',
    'tell': 'говорить', 'Tell': 'Говорить',
    'told': 'сказал', 'Told': 'Сказал',
    'say': 'сказать', 'Say': 'Сказать',
    'said': 'сказал', 'Said': 'Сказал',
    'ask': 'спрашивать', 'Ask': 'Спрашивать',
    'asked': 'спросил', 'Asked': 'Спросил',
    'answer': 'отвечать', 'Answer': 'Отвечать',
    'answered': 'ответил', 'Answered': 'Ответил',
    'work': 'работать', 'Work': 'Работать',
    'worked': 'работал', 'Worked': 'Работал',
    'play': 'играть', 'Play': 'Играть',
    'played': 'играл', 'Played': 'Играл',
    'run': 'бежать', 'Run': 'Бежать',
    'ran': 'бежал', 'Ran': 'Бежал',
    'move': 'двигать', 'Move': 'Двигать',
    'moved': 'двигал', 'Moved': 'Двигал',
    'live': 'жить', 'Live': 'Жить',
    'lived': 'жил', 'Lived': 'Жил',
    'believe': 'верить', 'Believe': 'Верить',
    'believed': 'верил', 'Believed': 'Верил',
    'happen': 'случаться', 'Happen': 'Случаться',
    'happened': 'случилось', 'Happened': 'Случилось',
    'become': 'становиться', 'Become': 'Становиться',
    'became': 'стал', 'Became': 'Стал',
    'show': 'показывать', 'Show': 'Показывать',
    'showed': 'показал', 'Showed': 'Показал',
    'mean': 'означать', 'Mean': 'Означать',
    'meant': 'означало', 'Meant': 'Означало',
    'keep': 'держать', 'Keep': 'Держать',
    'kept': 'держал', 'Kept': 'Держал',
    'let': 'позволять', 'Let': 'Позволять',
    'begin': 'начинать', 'Begin': 'Начинать',
    'began': 'начал', 'Began': 'Начал',
    'seem': 'казаться', 'Seem': 'Казаться',
    'seemed': 'казалось', 'Seemed': 'Казалось',
    'help': 'помогать', 'Help': 'Помогать',
    'helped': 'помог', 'Helped': 'Помог',
    'talk': 'говорить', 'Talk': 'Говорить',
    'talked': 'говорил', 'Talked': 'Говорил',
    'turn': 'поворачивать', 'Turn': 'Поворачивать',
    'turned': 'повернул', 'Turned': 'Повернул',
    'start': 'начинать', 'Start': 'Начинать',
    'started': 'начал', 'Started': 'Начал',
    'might': 'мог бы', 'Might': 'Мог бы',
    'could': 'мог', 'Could': 'Мог',
    'would': 'бы', 'Would': 'Бы',
    'should': 'должен', 'Should': 'Должен',
    'must': 'должен', 'Must': 'Должен',
    'may': 'может', 'May': 'Может',
    'can': 'может', 'Can': 'Может',
    // Существительные
    'thing': 'вещь', 'Thing': 'Вещь', 'things': 'вещи',
    'person': 'человек', 'Person': 'Человек', 'people': 'люди',
    'world': 'мир', 'World': 'Мир',
    'life': 'жизнь', 'Life': 'Жизнь',
    'hand': 'рука', 'Hand': 'Рука',
    'part': 'часть', 'Part': 'Часть',
    'child': 'ребёнок', 'Child': 'Ребёнок',
    'eye': 'глаз', 'Eye': 'Глаз',
    'woman': 'женщина', 'Woman': 'Женщина',
    'man': 'мужчина', 'Man': 'Мужчина',
    'face': 'лицо', 'Face': 'Лицо',
    'head': 'голова', 'Head': 'Голова',
    'body': 'тело', 'Body': 'Тело',
    'case': 'случай', 'Case': 'Случай',
    'week': 'неделя', 'Week': 'Неделя',
    'company': 'компания', 'Company': 'Компания',
    'system': 'система', 'System': 'Система',
    'program': 'программа', 'Program': 'Программа',
    'question': 'вопрос', 'Question': 'Вопрос',
    'number': 'число', 'Number': 'Число',
    'night': 'ночь', 'Night': 'Ночь',
    'point': 'точка', 'Point': 'Точка',
    'home': 'дом', 'Home': 'Дом',
    'water': 'вода', 'Water': 'Вода',
    'room': 'комната', 'Room': 'Комната',
    'mother': 'мать', 'Mother': 'Мать',
    'area': 'область', 'Area': 'Область',
    'money': 'деньги', 'Money': 'Деньги',
    'story': 'история', 'Story': 'История',
    'fact': 'факт', 'Fact': 'Факт',
    'month': 'месяц', 'Month': 'Месяц',
    'lot': 'много', 'Lot': 'Много',
    'right': 'право', 'Right': 'Право',
    'study': 'учеба', 'Study': 'Учеба',
    'book': 'книга', 'Book': 'Книга',
    'job': 'работа', 'Job': 'Работа',
    'word': 'слово', 'Word': 'Слово',
    'business': 'бизнес', 'Business': 'Бизнес',
    'issue': 'вопрос', 'Issue': 'Вопрос',
    'side': 'сторона', 'Side': 'Сторона',
    'kind': 'вид', 'Kind': 'Вид',
    'call': 'звонок', 'Call': 'Звонок',
    'power': 'сила', 'Power': 'Сила',
    'history': 'история', 'History': 'История',
    'family': 'семья', 'Family': 'Семья',
    'girl': 'девушка', 'Girl': 'Девушка',
    'boy': 'мальчик', 'Boy': 'Мальчик',
    'father': 'отец', 'Father': 'Отец',
    'son': 'сын', 'Son': 'Сын',
    'daughter': 'дочь', 'Daughter': 'Дочь',
    'friend': 'друг', 'Friend': 'Друг',
    'enemy': 'враг', 'Enemy': 'Враг',
    'name': 'имя', 'Name': 'Имя',
    'way': 'способ', 'Way': 'Способ',
    'place': 'место', 'Place': 'Место',
    'line': 'линия', 'Line': 'Линия',
    'group': 'группа', 'Group': 'Группа',
    'problem': 'проблема', 'Problem': 'Проблема',
    'result': 'результат', 'Result': 'Результат',
    'change': 'изменение', 'Change': 'Изменение',
    'reason': 'причина', 'Reason': 'Причина',
    'research': 'исследование', 'Research': 'Исследование',
    'girl': 'девушка', 'Girl': 'Девушка',
    'guy': 'парень', 'Guy': 'Парень',
    'moment': 'момент', 'Moment': 'Момент',
    'air': 'воздух', 'Air': 'Воздух',
    'teacher': 'учитель', 'Teacher': 'Учитель',
    'force': 'сила', 'Force': 'Сила',
    'education': 'образование', 'Education': 'Образование'
};

// Перевод названий и описаний событий с умным сохранением контекста
function translateEventText(text) {
    if (!isRussian || !text) return text;

    let translated = text;

    // Шаг 1: Сохраняем паттерны (деньги, даты, числа, проценты)
    const patternsMap = new Map();
    let patternIndex = 0;

    PRESERVE_PATTERNS.forEach(pattern => {
        translated = translated.replace(pattern, (match) => {
            const placeholder = `__PATTERN_${patternIndex}__`;
            patternsMap.set(placeholder, match);
            patternIndex++;
            return placeholder;
        });
    });

    // Шаг 2: Сохраняем термины из PRESERVE_TERMS (имена, бренды, команды)
    const preservedMap = new Map();
    let preserveIndex = 0;

    // Сортируем термины по длине (длинные primero) для корректной замены
    const sortedTerms = [...PRESERVE_TERMS].sort((a, b) => b.length - a.length);

    sortedTerms.forEach(term => {
        const regex = new RegExp(`\\b${escapeRegExp(term)}\\b`, 'gi');
        translated = translated.replace(regex, (match) => {
            const placeholder = `__PRESERVE_${preserveIndex}__`;
            preservedMap.set(placeholder, match);
            preserveIndex++;
            return placeholder;
        });
    });

    // Шаг 3: Обрабатываем вопросительные конструкции ПЕРЕД переводом по словарю
    // Will X reach Y? → Достигнет ли X Y?
    translated = translateQuestionPatterns(translated);

    // Шаг 4: Переводим по словарю (только оставшиеся слова)
    for (const [en, ru] of Object.entries(TRANSLATION_DICT)) {
        const regex = new RegExp(`\\b${escapeRegExp(en)}\\b`, 'gi');
        translated = translated.replace(regex, ru);
    }

    // Шаг 5: Восстанавливаем сохранённые термины
    preservedMap.forEach((original, placeholder) => {
        translated = translated.replace(placeholder, original);
    });

    // Шаг 6: Восстанавливаем сохранённые паттерны
    patternsMap.forEach((original, placeholder) => {
        translated = translated.replace(placeholder, original);
    });

    // Шаг 7: Удаляем американское время (PM/AM ET)
    REMOVE_PATTERNS.forEach(pattern => {
        translated = translated.replace(pattern, '');
    });

    // Шаг 8: Убираем лишние пробелы
    return translated.replace(/\s+/g, ' ').trim();
}

// Обработка специальных вопросительных паттернов
function translateQuestionPatterns(text) {
    let result = text;

    // Паттерн: "Will [Something] reach [Target]?" → "Достигнет ли [Something] [Target]?"
    result = result.replace(/\bWill\s+(.+?)\s+reach\s+(.+?)\?/gi, (match, subject, target) => {
        return `Достигнет ли ${subject} ${target}?`;
    });

    // Паттерн: "Will [Something] happen?" → "Произойдет ли [Something]?"
    result = result.replace(/\bWill\s+(.+?)\s+happen\b/gi, (match, subject) => {
        return `Произойдет ли ${subject}`;
    });

    // Паттерн: "Will [Someone] win?" → "Победит ли [Someone]?"
    result = result.replace(/\bWill\s+(.+?)\s+win\b/gi, (match, person) => {
        return `Победит ли ${person}`;
    });

    // Паттерн: "Will [Someone] announce?" → "Объявит ли [Someone]?"
    result = result.replace(/\bWill\s+(.+?)\s+announce\b/gi, (match, person) => {
        return `Объявит ли ${person}`;
    });

    // Паттерн: "Will [Something] be approved?" → "Будет ли одобрено [Something]?"
    result = result.replace(/\bWill\s+(.+?)\s+be\s+approved\b/gi, (match, thing) => {
        return `Будет ли одобрено ${thing}`;
    });

    // Паттерн: "Will [Something] launch?" → "Запустится ли [Something]?"
    result = result.replace(/\bWill\s+(.+?)\s+launch\b/gi, (match, thing) => {
        return `Запустится ли ${thing}`;
    });

    // Паттерн: "Will [Someone] join?" → "Присоединится ли [Someone]?"
    result = result.replace(/\bWill\s+(.+?)\s+join\b/gi, (match, person) => {
        return `Присоединится ли ${person}`;
    });

    // Паттерн: "Will [Something] exceed [Target]?" → "Превысит ли [Something] [Target]?"
    result = result.replace(/\bWill\s+(.+?)\s+exceed\s+(.+?)\?/gi, (match, subject, target) => {
        return `Превысит ли ${subject} ${target}?`;
    });

    // Паттерн: "Will [Something] fall below [Target]?" → "Упадет ли [Something] ниже [Target]?"
    result = result.replace(/\bWill\s+(.+?)\s+fall\s+below\s+(.+?)\?/gi, (match, subject, target) => {
        return `Упадет ли ${subject} ниже ${target}?`;
    });

    // Паттерн: "Will [Something] rise above [Target]?" → "Поднимется ли [Something] выше [Target]?"
    result = result.replace(/\bWill\s+(.+?)\s+rise\s+above\s+(.+?)\?/gi, (match, subject, target) => {
        return `Поднимется ли ${subject} выше ${target}?`;
    });

    // Паттерн: "Will [Someone] resign?" → "Уйдет ли [Someone] в отставку?"
    result = result.replace(/\bWill\s+(.+?)\s+resign\b/gi, (match, person) => {
        return `Уйдет ли ${person} в отставку?`;
    });

    // Паттерн: "Will [Someone] be impeached?" → "Будет ли импичмент [Someone]?"
    result = result.replace(/\bWill\s+(.+?)\s+be\s+impeached\b/gi, (match, person) => {
        return `Будет ли импичмент ${person}?`;
    });

    // Паттерн: "Will [Something] end?" → "Завершится ли [Something]?"
    result = result.replace(/\bWill\s+(.+?)\s+end\b/gi, (match, thing) => {
        return `Завершится ли ${thing}?`;
    });

    // Паттерн: "Will [Something] start?" → "Начнется ли [Something]?"
    result = result.replace(/\bWill\s+(.+?)\s+start\b/gi, (match, thing) => {
        return `Начнется ли ${thing}?`;
    });

    // Паттерн: "Will [Someone] fight?" → "Будет ли бой с участием [Someone]?"
    result = result.replace(/\bWill\s+(.+?)\s+fight\b/gi, (match, person) => {
        return `Будет ли бой с участием ${person}?`;
    });

    // Паттерн: "Will [Team] win the [Championship]?" → "Выиграет ли [Team] [Championship]?"
    result = result.replace(/\bWill\s+(.+?)\s+win\s+the\s+(.+?)\?/gi, (match, team, championship) => {
        return `Выиграет ли ${team} ${championship}?`;
    });

    // Паттерн: "Will [Someone] perform at [Event]?" → "Выступит ли [Someone] на [Event]?"
    result = result.replace(/\bWill\s+(.+?)\s+perform\s+at\s+(.+?)\?/gi, (match, artist, event) => {
        return `Выступит ли ${artist} на ${event}?`;
    });

    // Паттерн: "Will [Movie] win [Award]?" → "Выиграет ли [Movie] [Award]?"
    result = result.replace(/\bWill\s+(.+?)\s+win\s+(.+?)\?/gi, (match, subject, award) => {
        return `Выиграет ли ${subject} ${award}?`;
    });

    // Общий паттерн: "Will [Something]?" → "Будет ли [Something]?" (fallback)
    result = result.replace(/\bWill\s+(.+?)\?/gi, (match, content) => {
        // Избегаем двойной замены уже обработанных паттернов
        if (content.includes('ли')) {
            return match; // Уже обработано
        }
        return `Будет ли ${content}?`;
    });

    return result;
}

// Экранирование специальных символов для regex
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Словарь переводов
const translations = {
    en: {
        loading: 'Loading markets...',
        markets: 'Markets',
        wallet: 'Wallet',
        profile: 'Profile',
        admin: 'Admin Panel',
        all: 'All',
        politics: 'Politics',
        sports: 'Sports',
        crypto: 'Crypto',
        culture: 'Culture',
        business: 'Business',
        science: 'Science',
        other: 'Other',
        deposit: 'Deposit',
        withdraw: 'Withdraw',
        balance: 'Balance',
        available: 'Available',
        amount: 'Amount',
        description: 'Description',
        category: 'Category',
        image_url: 'Image URL',
        end_time: 'End Time',
        options: 'Options',
        create_event: 'Create Event',
        cancel: 'Cancel',
        confirm: 'Confirm',
        place_bet: 'Place Bet',
        yes: 'Yes',
        no: 'No',
        up: 'Up',
        down: 'Down',
        volume: 'Volume',
        time_left: 'Time left',
        my_predictions: 'My Predictions',
        transaction_history: 'Transaction History',
        no_transactions: 'No transactions yet',
        no_description: 'No description available',
        pending_withdrawals: 'Pending Withdrawals',
        sync_polymarket: 'Sync Polymarket',
        users: 'Users',
        events: 'Events',
        pending: 'Pending',
        event_details: 'Event Details',
        predict: 'Predict',
        min_10: 'Minimum $10 required',
        event_created: 'Event created! Waiting for moderation.',
        insufficient_balance: 'Insufficient balance',
        bet_placed: 'Bet placed successfully!',
        error: 'Error',
        success: 'Success'
    },
    ru: {
        loading: 'Загрузка рынков...',
        markets: 'Рынки',
        wallet: 'Кошелёк',
        profile: 'Профиль',
        admin: 'Админ-панель',
        all: 'Все',
        politics: 'Политика',
        sports: 'Спорт',
        crypto: 'Крипто',
        culture: 'Культура',
        business: 'Бизнес',
        science: 'Наука',
        other: 'Другое',
        deposit: 'Депозит',
        withdraw: 'Вывод',
        balance: 'Баланс',
        available: 'Доступно',
        amount: 'Сумма',
        description: 'Описание',
        category: 'Категория',
        image_url: 'Ссылка на изображение',
        end_time: 'Время окончания',
        options: 'Варианты',
        create_event: 'Создать событие',
        cancel: 'Отмена',
        confirm: 'Подтвердить',
        place_bet: 'Сделать ставку',
        yes: 'Да',
        no: 'Нет',
        up: 'Вверх',
        down: 'Вниз',
        volume: 'Объём',
        time_left: 'Осталось',
        my_predictions: 'Мои прогнозы',
        transaction_history: 'История транзакций',
        no_transactions: 'Пока нет транзакций',
        no_description: 'Описание отсутствует',
        pending_withdrawals: 'Ожидающие выводы',
        sync_polymarket: 'Синхронизация',
        users: 'Пользователи',
        events: 'События',
        pending: 'Ожидает',
        event_details: 'Детали события',
        predict: 'Предсказать',
        min_10: 'Минимум $10 требуется',
        event_created: 'Событие создано! Ожидает модерации.',
        insufficient_balance: 'Недостаточно средств',
        bet_placed: 'Ставка сделана!',
        error: 'Ошибка',
        success: 'Успешно'
    }
};

// Текущий язык
const t = translations[isRussian ? 'ru' : 'en'];

// Функция перевода
function tr(key) {
    return t[key] || key;
}

// ==================== BACKEND URL CONFIG ====================
// Backend НЕ использует префикс /api для основных endpoints
// Только betting routes используют /api/betting
const configuredBackendUrl = window.__BACKEND_URL__;
let backendUrl = configuredBackendUrl
    || (window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : window.location.origin); // Без /api префикса!

console.log('🔧 Backend URL:', backendUrl);

// Crypto symbols mapping for Binance
const CRYPTO_SYMBOLS = {
    'bitcoin': 'BTCUSDT',
    'btc': 'BTCUSDT',
    'ethereum': 'ETHUSDT',
    'eth': 'ETHUSDT',
    'solana': 'SOLUSDT',
    'sol': 'SOLUSDT',
    'ton': 'TONUSDT',
    'bnb': 'BNBUSDT',
    'xrp': 'XRPUSDT',
    'cardano': 'ADAUSDT',
    'dogecoin': 'DOGEUSDT',
    'doge': 'DOGEUSDT',
    'polkadot': 'DOTUSDT',
    'dot': 'DOTUSDT',
    'avalanche': 'AVAXUSDT',
    'avax': 'AVAXUSDT',
};

let currentEventId = null;
let currentOptionIndex = null;
let currentCategory = 'all';
let currentWithdrawalId = null;
let isAdmin = false;
let userBalance = 0;

// Auto-refresh interval (30 seconds)
let autoRefreshInterval = null;
const AUTO_REFRESH_DELAY = 30000;

// Обработка ошибки загрузки изображения
function handleImageError(imgElement) {
    console.log('Image failed to load:', imgElement.src);
    // Скрываем изображение и показываем placeholder
    imgElement.style.display = 'none';
    const placeholder = imgElement.nextElementSibling;
    if (placeholder && placeholder.classList.contains('event-image-placeholder')) {
        placeholder.style.display = 'flex';
    }
}

/**
 * Определяет является ли событие крипто-событием
 * @param {object} event - Объект события
 * @returns {boolean}
 */
function isCryptoEvent(event) {
    if (!event) return false;

    // Убрали 'price' — слишком общее слово (ложные срабатывания для политики/бизнеса)
    const cryptoKeywords = ['bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'crypto', 'ton', 'bnb', 'xrp', 'cardano', 'ada', 'dogecoin', 'doge', 'polkadot', 'dot', 'avalanche', 'avax'];
    const textToCheck = ((event.title || '') + ' ' + (event.description || '') + ' ' + (event.symbol || '')).toLowerCase();

    return cryptoKeywords.some(keyword => textToCheck.includes(keyword));
}

const categoryNames = {
    'all': 'All',
    'politics': 'Politics',
    'sports': 'Sports',
    'crypto': 'Crypto',
    'pop_culture': 'Culture',
    'business': 'Business',
    'science': 'Science',
    'other': 'Other'
};

document.addEventListener('DOMContentLoaded', function() {
    // Безопасная инициализация Telegram WebApp
    try {
        if (tg && typeof tg.expand === 'function') {
            tg.expand();
        }
        if (tg && typeof tg.ready === 'function') {
            tg.ready();
        }
    } catch (e) {
        console.warn('⚠️ Telegram WebApp not available, using web version');
    }

    // Telegram theme colors
    if (tg && tg.themeParams) {
        document.documentElement.style.setProperty('--bg-primary', tg.themeParams.bg_color || '#0a0a0a');
        document.documentElement.style.setProperty('--bg-secondary', tg.themeParams.secondary_bg_color || '#141414');
    }

    // Load profile immediately
    loadProfile();

    // CRITICAL: Скрываем лоадер СРАЗУ и дополнительно по таймерам
    const hideLoader = () => {
        const loader = document.getElementById('loading');
        if (loader && !loader.classList.contains('hidden')) {
            console.log('👋 Hiding loader');
            loader.classList.add('hidden');
        }
    };
    
    // Скрываем через 1 секунду (основной)
    setTimeout(hideLoader, 1000);
    // Дополнительные таймеры на случай если первый не сработал
    setTimeout(hideLoader, 3000);
    setTimeout(hideLoader, 5000);
    setTimeout(hideLoader, 10000);

    // Initial load - загружаем данные
    console.log('🚀 Starting initial load...');

    // Небольшая задержка чтобы DOM точно был готов
    setTimeout(() => {
        loadEvents();
        loadUserBalance();
        checkAdminStatus();
    }, 100);

    // Start auto-refresh
    startAutoRefresh();

    // Search clear button handler
    const searchClearBtn = document.getElementById('search-clear-btn');
    const searchInput = document.getElementById('search-input');

    if (searchClearBtn && searchInput) {
        searchClearBtn.addEventListener('click', () => {
            searchInput.value = '';
            searchClearBtn.style.display = 'none';
            if (window.clearSearch) {
                window.clearSearch();
            }
            searchInput.focus();
        });

        searchInput.addEventListener('input', () => {
            if (searchInput.value.length > 0) {
                searchClearBtn.style.display = 'flex';
            } else {
                searchClearBtn.style.display = 'none';
            }
        });
    }
});

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        const activeSection = document.querySelector('.section:not(.hidden)');
        if (activeSection && activeSection.id === 'events-section') {
            loadEvents(true); // Silent refresh
        }
    }, AUTO_REFRESH_DELAY);
}

async function apiRequest(url, options = {}) {
    try {
        const fullUrl = `${backendUrl}${url}`;
        console.log('📡 API Request:', fullUrl);

        // Добавляем AbortController для timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 секунд timeout

        const response = await fetch(fullUrl, {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            signal: controller.signal,
            ...options
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            let error;
            try {
                error = await response.json();
            } catch {
                error = { detail: `HTTP ${response.status}: ${response.statusText}` };
            }
            console.error('❌ API Error:', error);
            throw new Error(error.detail || 'Request error');
        }

        const data = await response.json();
        console.log('✅ API Response:', url, data);
        return data;
    } catch (error) {
        console.error('❌ API Request Failed:', url, error);
        // Пробрасываем ошибку дальше для обработки в UI
        throw error;
    }
}

// ==================== USER & AUTH ====================

function getUserId() {
    return tg.initDataUnsafe?.user?.id || 123456789;
}

function getUsername() {
    return tg.initDataUnsafe?.user?.username || 
           tg.initDataUnsafe?.user?.first_name || 
           'User';
}

async function checkAdminStatus() {
    try {
        const userId = getUserId();
        const data = await apiRequest(`/admin/check/${userId}`);
        isAdmin = data.is_admin;
        
        if (isAdmin) {
            document.getElementById('admin-menu-item').style.display = 'flex';
        }
    } catch (error) {
        console.error('Admin check error:', error);
    }
}

// ==================== CATEGORIES & EVENTS ====================

function selectCategory(category) {
    currentCategory = category;

    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });

    loadEvents();
}

// Setup horizontal scroll for categories - simple touch/mouse scroll
function setupCategoryScroll() {
    const container = document.getElementById('categories-container');
    if (!container) return;

    // Mouse wheel horizontal scroll
    container.addEventListener('wheel', (e) => {
        if (e.deltaY !== 0) {
            container.scrollLeft += e.deltaY;
            e.preventDefault();
        }
    }, { passive: false });

    // Touch scroll - let native behavior handle it
    container.style.webkitOverflowScrolling = 'touch';
}

async function loadEvents(silent = false) {
    const container = document.getElementById('events-container');
    console.log('📥 loadEvents() called, silent:', silent, 'category:', currentCategory);

    try {
        if (!silent) {
            container.innerHTML = `
                <div class="loading-container">
                    <div class="spinner"></div>
                    <p>Loading markets...</p>
                </div>
            `;
        }

        const url = currentCategory && currentCategory !== 'all'
            ? `/events?category=${currentCategory}`
            : '/events';

        console.log('📡 Fetching events from:', url);
        const startTime = Date.now();
        
        const data = await apiRequest(url);
        const loadTime = Date.now() - startTime;
        console.log(`⏱️ Events loaded in ${loadTime}ms, count:`, data?.length || 0);

        // Обрабатываем оба формата ответа: массив и объект {events: []}
        const events = Array.isArray(data) ? data : (data?.events || []);

        if (!events || events.length === 0) {
            console.log('⚠️ No events found');
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                        </svg>
                    </div>
                    <div class="empty-state-title">No markets found</div>
                    <div class="empty-state-text">There are no active markets in this category</div>
                    <button class="empty-state-btn" onclick="syncPolymarket()">
                        Load from Polymarket
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = events.map(event => createEventCard(event)).join('');
        console.log('✅ Events rendered successfully');
    } catch (error) {
        console.error('❌ Load events error:', error);
        if (!silent) {
            const container = document.getElementById('events-container');
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M12 8v4M12 16h.01"/>
                        </svg>
                    </div>
                    <div class="empty-state-title">Connection Error</div>
                    <div class="empty-state-text">${error.message || 'Failed to load markets'}</div>
                    <button class="empty-state-btn" onclick="loadEvents()">
                        Try Again
                    </button>
                </div>
            `;
        }
    } finally {
        // Гарантированно скрываем главный лоадер если он есть
        const mainLoader = document.getElementById('loading');
        if (mainLoader && !mainLoader.classList.contains('hidden')) {
            console.log('👋 Hiding main loader');
            mainLoader.classList.add('hidden');
        }
    }
}

async function syncPolymarket() {
    try {
        showNotification('Syncing markets from Polymarket...', 'info');
        await apiRequest('/admin/force-sync', { method: 'GET' });
        showNotification('Markets synced successfully!', 'success');
        loadEvents();
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

function createEventCard(event) {
    const timeLeft = formatTimeLeft(event.time_left);
    const totalPool = formatNumber(event.total_pool || 0);
    const categoryName = categoryNames[event.category] || 'Other';
    const categoryInitial = categoryName.charAt(0).toUpperCase();
    
    // Форматируем время окончания в МСК
    const endTimeMSK = event.end_time ? formatTimeMSK(event.end_time) : '';

    // Определяем, запущено ли приложение в Telegram
    const isTelegramWebApp = tg && tg.initDataUnsafe && tg.initDataUnsafe.user;

    // CORS proxy для картинок + улучшенный fallback
    const imageUrl = event.image_url;
    let imageHtml;

    if (imageUrl) {
        // Используем backend proxy для обхода CORS
        // Для Telegram WebApp добавляем специальный параметр
        const telegramParam = isTelegramWebApp ? '&telegram_webapp=1' : '';
        const proxiedUrl = `${backendUrl}/proxy/image?url=${encodeURIComponent(imageUrl)}${telegramParam}`;

        imageHtml = `
            <div style="position: relative;">
                <img src="${proxiedUrl}"
                     alt=""
                     class="event-image"
                     loading="lazy"
                     referrerpolicy="no-referrer"
                     onerror="handleImageError(this)">
                <div class="event-image-placeholder" style="display:none">${categoryInitial}</div>
            </div>
        `;
    } else {
        imageHtml = `<div class="event-image-placeholder">${categoryInitial}</div>`;
    }

    return `
        <div class="event-card" onclick="openEventModal(${event.id})">
            <div class="event-header">
                ${imageHtml}
                <div class="event-info">
                    <div class="event-category">
                        <span class="category-badge">${categoryName}</span>
                    </div>
                    <h3 class="event-title">${escapeHtml(translateEventText(event.title))}</h3>
                </div>
            </div>

            <div class="event-meta">
                <div class="event-timer" title="${endTimeMSK}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 6v6l4 2"/>
                    </svg>
                    ${timeLeft}
                </div>
                <div class="event-volume">$${totalPool} Vol.</div>
            </div>

            <div class="options-container">
                ${event.options.map((opt, idx) => createOptionButton(event.id, opt, idx, event.options.length)).join('')}
            </div>
        </div>
    `;
}

function createOptionButton(eventId, option, idx, totalOptions) {
    const probability = option.probability || 50;
    const isYes = option.text.toLowerCase() === 'yes' || idx === 0;
    const optionClass = totalOptions === 2 ? (isYes ? 'yes-option' : 'no-option') : '';
    
    return `
        <button class="option-btn ${optionClass}" 
                style="--probability: ${probability}%"
                onclick="openBetModal(${eventId}, ${option.index}, '${escapeHtml(option.text)}')">
            <span class="option-text">${escapeHtml(option.text)}</span>
            <div class="option-right">
                <span class="option-probability">${probability}%</span>
            </div>
        </button>
    `;
}

// ==================== BALANCE & WALLET ====================

async function loadUserBalance() {
    try {
        const userId = getUserId();
        const data = await apiRequest(`/wallet/balance/${userId}`);

        userBalance = data.balance_usdt || 0;
        const formattedBalance = formatNumber(userBalance);

        document.getElementById('user-balance').textContent = formattedBalance;
        document.getElementById('wallet-balance-value').textContent = userBalance.toFixed(2);
        document.getElementById('wallet-balance-value').textContent = userBalance.toFixed(2);
        document.getElementById('profile-balance').textContent = userBalance.toFixed(2);
        document.getElementById('available-balance').textContent = userBalance.toFixed(2);

        // Load transactions
        if (data.transactions) {
            renderTransactions(data.transactions);
        }

        // Load user stats and positions
        const userData = await apiRequest(`/user/${userId}`);
        if (userData.stats) {
            document.getElementById('active-predictions').textContent = userData.stats.active_predictions || 0;
            document.getElementById('total-won').textContent = userData.stats.total_won || 0;
        }

        // Load and render positions
        if (userData.positions) {
            renderPositions(userData.positions);
        }
    } catch (error) {
        console.error('Balance load error:', error);
        document.getElementById('user-balance').textContent = '0';
    }
}

// Load profile with Telegram data
function loadProfile() {
    const user = tg.initDataUnsafe?.user;
    
    if (!user) {
        // Telegram not available, use defaults
        const displayName = getUsername();
        document.getElementById('profile-name').textContent = displayName;
        document.getElementById('profile-telegram-id').textContent = `ID: ${getUserId()}`;
        
        const avatarEl = document.getElementById('profile-avatar');
        avatarEl.textContent = displayName.charAt(0).toUpperCase();
        return;
    }

    // Формируем имя из first_name + last_name
    let displayName = '';
    if (user.first_name && user.last_name) {
        displayName = `${user.first_name} ${user.last_name}`;
    } else if (user.first_name) {
        displayName = user.first_name;
    } else if (user.last_name) {
        displayName = user.last_name;
    } else {
        displayName = user.username || 'User';
    }

    const avatarUrl = user.photo_url || null;

    document.getElementById('profile-name').textContent = displayName;
    document.getElementById('profile-telegram-id').textContent = `ID: ${getUserId()}`;

    // Обновляем аватар
    const avatarEl = document.getElementById('profile-avatar');
    if (avatarUrl) {
        avatarEl.innerHTML = `<img src="${avatarUrl}" alt="Avatar" style="width:100%;height:100%;border-radius:inherit;object-fit:cover;">`;
    } else {
        avatarEl.textContent = displayName.charAt(0).toUpperCase();
    }
}

// Render user's positions (shares)
function renderPositions(positions) {
    // Check if we have a positions container in profile, if not create one
    let container = document.getElementById('positions-container');
    
    if (!container) {
        // Create positions section in profile if it doesn't exist
        const profileCard = document.querySelector('.profile-card');
        if (profileCard) {
            const positionsSection = document.createElement('div');
            positionsSection.innerHTML = `
                <div class="profile-section-title" style="margin: 20px 0 12px; font-size: 16px; font-weight: 600; color: var(--text-primary);">
                    My Positions
                </div>
                <div id="positions-container"></div>
            `;
            profileCard.appendChild(positionsSection);
            container = document.getElementById('positions-container');
        }
    }
    
    if (!container) return;
    
    if (!positions || positions.length === 0) {
        container.innerHTML = `
            <div class="empty-state-small" style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 14px;">
                No active positions
            </div>
        `;
        return;
    }
    
    const html = positions.map(pos => {
        const profitClass = pos.profit_loss >= 0 ? 'amount-positive' : 'amount-negative';
        const profitSign = pos.profit_loss >= 0 ? '+' : '';
        const percentClass = pos.profit_loss_percent >= 0 ? 'status-approved' : 'status-rejected';
        
        return `
            <div class="position-item" style="display: flex; flex-direction: column; gap: 10px; padding: 14px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius-md); margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">${escapeHtml(pos.event_title)}</div>
                        <div style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(pos.option_text)}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">${pos.shares.toFixed(2)} shares</div>
                        <div style="font-size: 11px; color: var(--text-muted);">@ ${pos.average_price.toFixed(2)} USDT</div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid var(--border);">
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">Current Value</div>
                        <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">${pos.current_value.toFixed(2)} USDT</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 11px; color: var(--text-muted);">P/L</div>
                        <div style="font-size: 14px; font-weight: 600;" class="${profitClass}">${profitSign}${pos.profit_loss.toFixed(2)} USDT</div>
                        <div style="font-size: 11px;" class="${percentClass}">(${profitSign}${pos.profit_loss_percent.toFixed(1)}%)</div>
                    </div>
                </div>
                <button class="sell-position-btn" onclick="openSellModal(${pos.event_id}, ${pos.option_index}, '${escapeHtml(pos.option_text)}', ${pos.shares}, ${pos.current_price})" 
                    style="width: 100%; padding: 10px; background: linear-gradient(135deg, #ef4444, #b91c1c); border: none; border-radius: var(--radius-md); color: #fff; font-weight: 600; font-size: 13px; cursor: pointer; margin-top: 8px;">
                    Sell Position
                </button>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function renderTransactions(transactions) {
    const container = document.getElementById('transactions-container');
    
    if (!transactions || transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-transactions">
                <p>No transactions yet</p>
            </div>
        `;
        return;
    }
    
    const html = transactions.map(tx => {
        const isDeposit = tx.type === 'deposit';
        const isWithdraw = tx.type === 'withdrawal';
        const statusClass = tx.status === 'completed' ? 'status-completed' : 
                           tx.status === 'pending' ? 'status-pending' :
                           tx.status === 'approved' ? 'status-approved' :
                           tx.status === 'rejected' ? 'status-rejected' : '';
        
        const icon = isDeposit ? 
            `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7-7 7 7"/></svg>` :
            `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7 7 7-7"/></svg>`;
        
        const amountClass = isDeposit ? 'amount-positive' : 'amount-negative';
        const amountPrefix = isDeposit ? '+' : '-';
        
        return `
            <div class="transaction-item">
                <div class="transaction-icon ${isDeposit ? 'deposit' : 'withdraw'}">
                    ${icon}
                </div>
                <div class="transaction-info">
                    <span class="transaction-type">${isDeposit ? 'Deposit' : 'Withdrawal'}</span>
                    <span class="transaction-status ${statusClass}">${tx.status}</span>
                </div>
                <div class="transaction-amount ${amountClass}">
                    ${amountPrefix}${tx.amount.toFixed(2)} ${tx.asset}
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

// ==================== DEPOSIT ====================

function openDepositModal() {
    document.getElementById('deposit-modal').classList.remove('hidden');
    document.getElementById('deposit-amount').value = '';
    document.getElementById('deposit-amount').focus();
}

function closeDepositModal() {
    document.getElementById('deposit-modal').classList.add('hidden');
}

function setDepositAmount(amount) {
    document.getElementById('deposit-amount').value = amount;
}

async function processDeposit() {
    const amount = parseFloat(document.getElementById('deposit-amount').value);
    
    if (!amount || amount < 1) {
        showNotification('Minimum deposit is 1 USDT', 'error');
        return;
    }
    
    try {
        const btn = document.querySelector('#deposit-modal .modal-btn.confirm');
        btn.textContent = 'Processing...';
        btn.disabled = true;
        
        const result = await apiRequest('/wallet/deposit', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                amount: amount,
                asset: 'USDT'
            })
        });
        
        if (result.pay_url) {
            // Open CryptoBot payment link
            if (tg.openLink) {
                tg.openLink(result.pay_url);
            } else {
                window.open(result.pay_url, '_blank');
            }
            showNotification('Opening payment page...', 'info');
        }
        
        closeDepositModal();
        
        // Refresh balance after a delay
        setTimeout(loadUserBalance, 3000);
        
    } catch (error) {
        showNotification(error.message || 'Deposit error', 'error');
    } finally {
        const btn = document.querySelector('#deposit-modal .modal-btn.confirm');
        if (btn) {
            btn.textContent = 'Continue';
            btn.disabled = false;
        }
    }
}

// ==================== WITHDRAW ====================

function openWithdrawModal() {
    document.getElementById('withdraw-modal').classList.remove('hidden');
    document.getElementById('withdraw-amount').value = '';
    document.getElementById('available-balance').textContent = userBalance.toFixed(2);
}

function closeWithdrawModal() {
    document.getElementById('withdraw-modal').classList.add('hidden');
}

async function processWithdraw() {
    const amount = parseFloat(document.getElementById('withdraw-amount').value);
    
    if (!amount || amount < 5) {
        showNotification('Minimum withdrawal is 5 USDT', 'error');
        return;
    }
    
    if (amount > userBalance) {
        showNotification('Insufficient balance', 'error');
        return;
    }
    
    try {
        const btn = document.querySelector('#withdraw-modal .modal-btn.confirm');
        btn.textContent = 'Processing...';
        btn.disabled = true;
        
        const result = await apiRequest('/wallet/withdraw', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                amount: amount,
                asset: 'USDT'
            })
        });
        
        showNotification('Withdrawal request submitted! Waiting for approval.', 'success');
        closeWithdrawModal();
        loadUserBalance();
        
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
        
    } catch (error) {
        showNotification(error.message || 'Withdrawal error', 'error');
    } finally {
        const btn = document.querySelector('#withdraw-modal .modal-btn.confirm');
        if (btn) {
            btn.textContent = 'Request Withdrawal';
            btn.disabled = false;
        }
    }
}

// ==================== BET MODAL ====================

function openBetModal(eventId, optionIndex, optionText) {
    const eventCard = event.target.closest('.event-card');
    const title = eventCard.querySelector('.event-title').textContent;

    document.getElementById('modal-title').textContent = title;
    
    // Определяем цвет кнопки по тексту варианта
    const optionLower = optionText.toLowerCase();
    const isYes = optionLower.includes('yes') || optionLower.includes('да') || optionLower.includes('up') || optionLower.includes('вверх');
    const isNo = optionLower.includes('no') || optionLower.includes('нет') || optionLower.includes('down') || optionLower.includes('вниз');
    
    let buttonClass = 'confirm';
    if (isYes) buttonClass = 'yes-btn';
    if (isNo) buttonClass = 'no-btn';
    
    document.getElementById('modal-option').textContent = `${tr('predict')}: ${optionText}`;
    
    // Обновляем класс кнопки
    const confirmBtn = document.querySelector('#bet-modal .modal-btn.confirm');
    if (confirmBtn) {
        confirmBtn.className = `modal-btn ${buttonClass}`;
        confirmBtn.textContent = tr('place_bet');
    }
    
    document.getElementById('bet-modal').classList.remove('hidden');
    document.getElementById('points-input').value = '';
    document.getElementById('points-input').focus();

    currentEventId = eventId;
    currentOptionIndex = optionIndex;
}

function closeModal() {
    document.getElementById('bet-modal').classList.add('hidden');
    currentEventId = null;
    currentOptionIndex = null;
}

// Price Prediction Betting Functions
let currentPredictionType = null;
let currentPredictionEventId = null;
let currentOdds = { up: 1.95, down: 1.95 };

// Calculate dynamic odds based on 5-minute price volatility
// ⚠️ ВАЖНО: Для расчёта 5-минутной волатильности ВСЕГДА используем 1m интервал
// Это исправляет проблему "коэффициенты меняются при смене таймфрейма"
async function calculateDynamicOdds(prices, symbol = null) {
    if (!prices || prices.length < 2) {
        return { up: 1.95, down: 1.95 };
    }

    // ⚠️ ВСЕГДА используем последние 5 свечей 1m интервала для расчёта 5-минутной волатильности
    // Даже если график показывает 1h/4h, волатильность считаем по реальным 5 минутам
    
    let recentPrices = prices;
    
    // Если передан символ, загружаем свежие 1m данные для точного расчёта
    if (symbol && window.binanceService) {
        try {
            console.log('💰 [Prediction] Загрузка 1m данных для расчёта волатильности:', symbol);
            const { prices: m1Prices } = await window.binanceService.loadHistoricalCandles(symbol, '1m');
            if (m1Prices && m1Prices.length >= 5) {
                recentPrices = m1Prices.slice(-5); // Последние 5 минут
                console.log('💰 [Prediction] Использованы 1m данные:', recentPrices.length, 'цен');
            }
        } catch (e) {
            console.warn('⚠️ [Prediction] Не удалось загрузить 1m данные, используем fallback:', e.message);
        }
    }
    
    // Если не удалось загрузить 1m данные, используем последние 5 цен из переданных
    if (recentPrices.length > 5) {
        recentPrices = recentPrices.slice(-5);
    }

    if (recentPrices.length < 2) {
        return { up: 1.95, down: 1.95 };
    }

    // Расчёт изменения цены за последние 5 минут
    const firstPrice = recentPrices[0];
    const lastPrice = recentPrices[recentPrices.length - 1];
    const priceChange = (lastPrice - firstPrice) / firstPrice;

    // Расчёт волатильности (максимальное отклонение за период)
    const minPrice = Math.min(...recentPrices);
    const maxPrice = Math.max(...recentPrices);
    const volatility = (maxPrice - minPrice) / firstPrice;

    // Базовые коэффициенты
    let upOdds = 1.95;
    let downOdds = 1.95;

    // Корректировка по тренду
    if (priceChange > 0.001) {
        // Восходящий тренд - снижаем коэффициент на UP, повышаем на DOWN
        const trendStrength = Math.min(priceChange * 100, 0.5);
        upOdds = Math.max(1.2, 1.95 - trendStrength);
        downOdds = Math.min(3.0, 1.95 + trendStrength);
    } else if (priceChange < -0.001) {
        // Нисходящий тренд - повышаем коэффициент на UP, снижаем на DOWN
        const trendStrength = Math.min(Math.abs(priceChange) * 100, 0.5);
        upOdds = Math.min(3.0, 1.95 + trendStrength);
        downOdds = Math.max(1.2, 1.95 - trendStrength);
    }

    // Корректировка по волатильности (высокая волатильность = выше коэффициенты)
    const volMultiplier = 1 + (volatility * 5);
    upOdds *= volMultiplier;
    downOdds *= volMultiplier;

    // Ограничиваем коэффициенты
    upOdds = Math.max(1.1, Math.min(5.0, upOdds));
    downOdds = Math.max(1.1, Math.min(5.0, downOdds));

    console.log('💰 [Prediction] Коэффициенты:', { up: upOdds.toFixed(2), down: downOdds.toFixed(2) },
                '| волатильность:', (volatility * 100).toFixed(2) + '%',
                '| изменение:', (priceChange * 100).toFixed(2) + '%');

    return {
        up: parseFloat(upOdds.toFixed(2)),
        down: parseFloat(downOdds.toFixed(2))
    };
}

function updatePredictionOdds(prices, symbol = null) {
    // Если символ не передан, используем текущий Binance символ
    const binanceSymbol = symbol || currentBinanceSymbol;
    
    // Вызываем async функцию и обновляем когда данные готовы
    calculateDynamicOdds(prices, binanceSymbol).then(odds => {
        currentOdds = odds;

        const upEl = document.getElementById('up-odds');
        const downEl = document.getElementById('down-odds');

        if (upEl) upEl.textContent = `${odds.up}x`;
        if (downEl) downEl.textContent = `${odds.down}x`;
    }).catch(err => {
        console.warn('⚠️ [Prediction] Error calculating odds:', err.message);
        // Используем дефолтные коэффициенты
        currentOdds = { up: 1.95, down: 1.95 };
    });
}

function openPredictionBet(direction) {
    currentPredictionType = direction;
    
    const modal = document.getElementById('bet-modal');
    const odds = currentOdds[direction];
    const potentialWin = (odds * 100).toFixed(0);
    
    document.getElementById('modal-title').textContent = direction === 'up' ? 'Прогноз: ВВЕРХ' : 'Прогноз: ВНИЗ';
    document.getElementById('modal-option').innerHTML = `
        Цена ${direction === 'up' ? 'вырастет' : 'упадет'} в ближайшие 5 минут<br>
        <span style="color: #f2b03d; font-size: 13px; margin-top: 8px; display: block;">
            Коэффициент: ${odds}x (выигрыш +${potentialWin}%)
        </span>
    `;
    document.getElementById('points-input').value = '';
    
    modal.classList.remove('hidden');
}

async function confirmPrediction() {
    const points = parseFloat(document.getElementById('points-input').value);

    if (!points || points < 1) {
        showNotification('Enter a valid amount (minimum 1 USDT)', 'error');
        return;
    }

    if (points > userBalance) {
        showNotification('Insufficient balance', 'error');
        return;
    }

    try {
        const confirmBtn = document.querySelector('#bet-modal .modal-btn.confirm');
        confirmBtn.textContent = 'Processing...';
        confirmBtn.disabled = true;

        // Use regular predict endpoint for now
        const result = await apiRequest('/predict', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                event_id: currentEventId,
                option_index: currentPredictionType === 'up' ? 0 : 1,
                points: points
            })
        });

        showNotification(`Bet placed! New balance: ${formatNumber(result.new_balance)} USDT`, 'success');
        closeModal();
        loadEvents();
        loadUserBalance();

        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
    } catch (error) {
        showNotification(error.message || 'Prediction error', 'error');
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    } finally {
        const confirmBtn = document.querySelector('#bet-modal .modal-btn.confirm');
        if (confirmBtn) {
            confirmBtn.textContent = 'Place Bet';
            confirmBtn.disabled = false;
        }
    }
}

// ==================== SELL FUNCTIONS ====================

let currentSellEventId = null;
let currentSellOptionIndex = null;
let currentSellShares = 0;
let currentSellPrice = 0;

function openSellModal(eventId, optionIndex, optionText, shares, currentPrice) {
    currentSellEventId = eventId;
    currentSellOptionIndex = optionIndex;
    currentSellShares = shares;
    currentSellPrice = currentPrice;
    
    const modal = document.getElementById('sell-modal');
    if (!modal) return;
    
    document.getElementById('sell-option-text').textContent = optionText;
    document.getElementById('sell-shares-value').textContent = shares.toFixed(2);
    document.getElementById('sell-price-value').textContent = currentPrice.toFixed(2);
    document.getElementById('sell-current-value').textContent = (shares * currentPrice).toFixed(2);
    document.getElementById('sell-shares-input').value = shares.toFixed(2);
    document.getElementById('sell-shares-input').max = shares;
    
    updateSellProceeds(shares, currentPrice);
    
    modal.classList.remove('hidden');
}

function closeSellModal() {
    document.getElementById('sell-modal').classList.add('hidden');
    currentSellEventId = null;
    currentSellOptionIndex = null;
}

function updateSellProceeds(shares, price) {
    const sharesInput = parseFloat(document.getElementById('sell-shares-input').value) || 0;
    const validShares = Math.min(sharesInput, currentSellShares);
    const proceeds = validShares * (price || currentSellPrice);
    document.getElementById('sell-proceeds-value').textContent = proceeds.toFixed(2);
}

async function confirmSell() {
    const sharesToSell = parseFloat(document.getElementById('sell-shares-input').value) || 0;
    
    if (sharesToSell <= 0 || sharesToSell > currentSellShares) {
        showNotification('Invalid shares amount', 'error');
        return;
    }
    
    try {
        const confirmBtn = document.querySelector('#sell-modal .modal-btn.confirm');
        confirmBtn.textContent = 'Selling...';
        confirmBtn.disabled = true;
        
        const result = await apiRequest('/sell', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                event_id: currentSellEventId,
                option_index: currentSellOptionIndex,
                shares: sharesToSell
            })
        });
        
        showNotification(`Sold ${sharesToSell.toFixed(2)} shares for ${result.payout.toFixed(2)} USDT! P/L: ${result.profit_loss.toFixed(2)} USDT`, 
            result.profit_loss >= 0 ? 'success' : 'info');
        
        closeSellModal();
        loadUserBalance();
        
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
    } catch (error) {
        showNotification(error.message || 'Sell error', 'error');
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    } finally {
        const confirmBtn = document.querySelector('#sell-modal .modal-btn.confirm');
        if (confirmBtn) {
            confirmBtn.textContent = 'Sell';
            confirmBtn.disabled = false;
        }
    }
}

// ==================== ADMIN PANEL ====================

async function loadAdminData() {
    if (!isAdmin) return;
    
    try {
        const userId = getUserId();
        
        // Load stats
        const stats = await apiRequest(`/admin/stats?admin_telegram_id=${userId}`);
        document.getElementById('stat-users').textContent = stats.total_users || 0;
        document.getElementById('stat-events').textContent = stats.total_events || 0;
        document.getElementById('stat-pending').textContent = stats.pending_withdrawals || 0;
        
        // Load pending withdrawals
        const withdrawals = await apiRequest(`/admin/withdrawals?admin_telegram_id=${userId}`);
        renderPendingWithdrawals(withdrawals.withdrawals || []);
        
    } catch (error) {
        console.error('Admin data error:', error);
        showNotification('Error loading admin data', 'error');
    }
}

function renderPendingWithdrawals(withdrawals) {
    const container = document.getElementById('pending-withdrawals-container');
    
    if (!withdrawals || withdrawals.length === 0) {
        container.innerHTML = `<div class="empty-state-small">No pending withdrawals</div>`;
        return;
    }
    
    const html = withdrawals.map(w => `
        <div class="withdrawal-card" onclick="openAdminActionModal(${w.id}, ${w.user_telegram_id}, '${w.username || 'Unknown'}', ${w.amount}, '${w.asset}')">
            <div class="withdrawal-user">
                <div class="withdrawal-avatar">${(w.username || 'U').charAt(0).toUpperCase()}</div>
                <div class="withdrawal-user-info">
                    <span class="withdrawal-username">${w.username || 'User'}</span>
                    <span class="withdrawal-user-id">ID: ${w.user_telegram_id}</span>
                </div>
            </div>
            <div class="withdrawal-amount">
                <span class="amount-value">${w.amount.toFixed(2)}</span>
                <span class="amount-currency">${w.asset}</span>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function openAdminActionModal(id, telegramId, username, amount, asset) {
    currentWithdrawalId = id;
    
    document.getElementById('withdrawal-details').innerHTML = `
        <div class="detail-row">
            <span class="detail-label">User:</span>
            <span class="detail-value">${username} (ID: ${telegramId})</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Amount:</span>
            <span class="detail-value">${amount.toFixed(2)} ${asset}</span>
        </div>
    `;
    
    document.getElementById('admin-action-modal').classList.remove('hidden');
}

function closeAdminActionModal() {
    document.getElementById('admin-action-modal').classList.add('hidden');
    currentWithdrawalId = null;
}

async function approveWithdrawal() {
    await processWithdrawalAction('approve');
}

async function rejectWithdrawal() {
    await processWithdrawalAction('reject');
}

async function processWithdrawalAction(action) {
    if (!currentWithdrawalId) return;
    
    try {
        const comment = document.getElementById('admin-comment').value;
        
        await apiRequest('/admin/withdrawal/action', {
            method: 'POST',
            body: JSON.stringify({
                admin_telegram_id: getUserId(),
                transaction_id: currentWithdrawalId,
                action: action,
                comment: comment || null
            })
        });
        
        showNotification(`Withdrawal ${action}ed successfully`, 'success');
        closeAdminActionModal();
        loadAdminData();

    } catch (error) {
        showNotification(error.message || 'Error processing withdrawal', 'error');
    }
}

// ==================== USERS MANAGEMENT ====================

async function showUsersList() {
    try {
        const userId = getUserId();
        const data = await apiRequest(`/admin/users?admin_telegram_id=${userId}`);
        renderUsersList(data.users || []);
        document.getElementById('users-list-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Users list error:', error);
        showNotification('Error loading users: ' + error.message, 'error');
    }
}

function renderUsersList(users) {
    const container = document.getElementById('users-list-container');

    if (!users || users.length === 0) {
        container.innerHTML = `<div class="empty-state-small">No users found</div>`;
        return;
    }

    const html = users.map(user => {
        const avatarLetter = (user.username || 'U').charAt(0).toUpperCase();
        const balance = user.balance_usdt || 0;
        
        return `
            <div class="user-card">
                <div class="user-info">
                    <div class="user-avatar-small">${avatarLetter}</div>
                    <div class="user-details">
                        <div class="user-name">${escapeHtml(user.username || 'User')}</div>
                        <div class="user-id">ID: ${user.telegram_id}</div>
                    </div>
                </div>
                <div class="user-balance">
                    <div class="user-balance-value">$${balance.toFixed(2)}</div>
                    <div class="user-balance-label">USDT</div>
                </div>
                <div class="user-actions">
                    <button class="user-action-btn" onclick="openAddBalanceModal(${user.telegram_id}, '${escapeHtml(user.username || 'User')}', ${balance})">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 5v14M5 12h14"/>
                        </svg>
                        Add
                    </button>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function closeUsersListModal() {
    document.getElementById('users-list-modal').classList.add('hidden');
}

function openAddBalanceModal(telegramId, username, currentBalance) {
    document.getElementById('add-balance-userid').value = telegramId;
    document.getElementById('add-balance-username').value = `${username} (Balance: $${currentBalance.toFixed(2)})`;
    document.getElementById('add-balance-amount').value = '';
    document.getElementById('add-balance-comment').value = '';
    document.getElementById('add-balance-modal').classList.remove('hidden');
}

function closeAddBalanceModal() {
    document.getElementById('add-balance-modal').classList.add('hidden');
    document.getElementById('add-balance-userid').value = '';
    document.getElementById('add-balance-username').value = '';
}

async function processAddBalance() {
    const telegramId = document.getElementById('add-balance-userid').value;
    const amount = parseFloat(document.getElementById('add-balance-amount').value);
    const comment = document.getElementById('add-balance-comment').value;

    if (!telegramId || !amount || amount <= 0) {
        showNotification('Please enter a valid amount', 'error');
        return;
    }

    try {
        await apiRequest('/admin/add-balance', {
            method: 'POST',
            body: JSON.stringify({
                admin_telegram_id: getUserId(),
                user_telegram_id: parseInt(telegramId),
                amount: amount,
                asset: 'USDT',
                comment: comment || null
            })
        });

        showNotification(`Successfully added $${amount.toFixed(2)} to user balance`, 'success');
        closeAddBalanceModal();
        
        // Refresh users list if modal is still open
        showUsersList();
        
    } catch (error) {
        showNotification(error.message || 'Error adding balance', 'error');
    }
}

// ==================== NAVIGATION ====================

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(section => section.classList.add('hidden'));
    document.getElementById(`${sectionName}-section`).classList.remove('hidden');
    
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.section === sectionName);
    });
    
    // Load data for specific sections
    if (sectionName === 'events') {
        loadEvents();
    } else if (sectionName === 'wallet') {
        loadUserBalance();
    } else if (sectionName === 'profile') {
        loadProfile();
        loadUserBalance();
    } else if (sectionName === 'admin' && isAdmin) {
        loadAdminData();
    }
}

function showMyPredictions() {
    // TODO: Implement predictions history
    showNotification('Coming soon!', 'info');
}

// ==================== EVENT MODAL ====================

let selectedOptionIndex = null;
let currentEventIdForComments = null;
let eventComments = []; // Хранилище комментариев для текущего события

async function openEventModal(eventId) {
    try {
        console.log('📊 [Event] Opening modal for event ID:', eventId);

        const event = await apiRequest(`/events/${eventId}`);
        console.log('📊 [Event] Получен ответ:', event);

        if (!event) {
            console.error('❌ [Event] Событие не найдено (пустой ответ)');
            showNotification('Событие не найдено', 'error');
            return;
        }

        selectedOptionIndex = null;
        currentEventIdForComments = eventId;
        currentEventId = eventId;

        // Загружаем комментарии для события
        loadCommentsForEvent(eventId);

        document.getElementById('event-modal-title').textContent = translateEventText(event.title);

        // ⚠️ ЗАЩИТА: Проверяем что options существует и это массив
        const optionsContainer = document.getElementById('event-options');
        const options = Array.isArray(event.options) ? event.options : [];

        console.log('📊 [Event] Опции:', options.length, 'шт');

        if (options.length === 0) {
            console.warn('⚠️ [Event] Нет опций у события!');
            optionsContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Нет доступных вариантов</div>';
        } else {
            optionsContainer.innerHTML = options.map((opt, idx) => {
                const probability = opt.probability || 50;
                const text = opt.text || `Вариант ${idx + 1}`;
                return `
                    <div class="event-option-btn" onclick="selectEventOption(${idx}, ${probability})">
                        <span class="event-option-text">${translateEventText(text)}</span>
                        <span class="event-option-probability">${probability}%</span>
                    </div>
                `;
            }).join('');
        }

        // Определяем тип события (крипто или нет)
        const cryptoEvent = event.category === 'crypto';
        console.log('📊 [Event] Тип события:', cryptoEvent ? 'КРИПТО' : 'НЕ-КРИПТО', '| Category:', event.category);

        // Восстанавливаем HTML структуру графика перед любыми операциями
        const chartContainer = document.getElementById('event-chart');
        if (chartContainer) {
            // Восстанавливаем оригинальную HTML структуру
            chartContainer.innerHTML = `
                <div class="event-chart-live-badge" id="chart-live-badge" style="display: none;">
                    <span class="live-dot">🟢</span>
                    <span class="live-text">Live</span>
                </div>
                <div class="event-chart-info" id="event-chart-info" style="display: none;">
                    <div class="event-chart-price" id="chart-price">$0.00</div>
                    <div class="event-chart-change" id="chart-change">
                        <span>0.00%</span>
                    </div>
                    <div class="event-chart-updated" id="chart-updated">
                        <span>🔄 Обновлено только что</span>
                    </div>
                </div>
                <canvas id="event-chart-canvas"></canvas>
                <div class="event-chart-timeframe" id="event-chart-timeframe" style="display: none;">
                    <button class="timeframe-btn" data-interval="1m">1м</button>
                    <button class="timeframe-btn" data-interval="5m">5м</button>
                    <button class="timeframe-btn active" data-interval="15m">15м</button>
                    <button class="timeframe-btn" data-interval="1h">1ч</button>
                    <button class="timeframe-btn" data-interval="4h">4ч</button>
                    <button class="timeframe-btn" data-interval="1d">1д</button>
                </div>
            `;

            // ⚠️ ЗАЩИТА: has_chart может быть null/undefined
            const hasChart = event.has_chart === true;
            chartContainer.style.display = hasChart ? 'block' : 'none';
            console.log('📊 [Event] График:', hasChart ? 'показан' : 'скрыт', '| has_chart:', event.has_chart);
            console.log('📊 [Event] HTML структуры графика восстановлена');

            // Восстанавливаем видимость внутренних элементов если график показан
            const chartTimeframe = document.getElementById('event-chart-timeframe');
            const chartInfo = document.getElementById('event-chart-info');
            const liveBadge = document.getElementById('chart-live-badge');

            if (hasChart) {
                setTimeout(() => {
                    if (chartTimeframe) chartTimeframe.style.display = 'flex';
                    if (chartInfo) chartInfo.style.display = 'flex';
                    if (liveBadge) liveBadge.style.display = 'none';
                }, 100);
            } else {
                if (chartTimeframe) chartTimeframe.style.display = 'none';
                if (chartInfo) chartInfo.style.display = 'none';
                if (liveBadge) liveBadge.style.display = 'none';
            }
        }

        // Show/hide "Прогноз на 5 минут" block
        const predictionSection = document.querySelector('.price-prediction-section');
        if (predictionSection) {
            predictionSection.style.display = cryptoEvent ? 'block' : 'none';
            console.log('📊 [Event] Блок прогноза:', cryptoEvent ? 'показан' : 'скрыт');
        }

        // Show modal
        console.log('📊 [Event] Показываем модальное окно');
        document.getElementById('event-modal').classList.remove('hidden');

        // Reset to comments tab
        switchEventTab('comments');

        // Render chart only if has_chart is true
        if (event.has_chart === true) {
            console.log('📊 [Chart] Рендерим график для события', event.id);
            setTimeout(() => renderEventChart(event.id, options), 100);
        }
    } catch (e) {
        console.error('❌ [Event] Error loading event details:', e);
        console.error('❌ [Event] Stack:', e.stack);
        showNotification('Failed to load event details: ' + (e.message || 'Unknown error'), 'error');
    }
}

function selectEventOption(index, probability) {
    selectedOptionIndex = index;
    document.querySelectorAll('.event-option-btn').forEach((btn, idx) => {
        btn.classList.toggle('selected', idx === index);
    });

    // Open bet modal after selection
    setTimeout(() => {
        const eventTitle = document.getElementById('event-modal-title').textContent;
        const optionText = document.querySelectorAll('.event-option-text')[index]?.textContent;
        openBetModal(eventTitle, optionText, probability);
    }, 200);
}

function closeEventModal() {
    document.getElementById('event-modal').classList.add('hidden');
    selectedOptionIndex = null;
    currentEventIdForComments = null;

    // Clear chart update interval
    if (chartUpdateInterval) {
        clearInterval(chartUpdateInterval);
        chartUpdateInterval = null;
    }

    // Clear WebSocket debounce timer
    if (webSocketUpdateTimeout) {
        clearTimeout(webSocketUpdateTimeout);
        webSocketUpdateTimeout = null;
    }

    // Close Binance WebSocket
    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }

    // Destroy chart instance to free memory
    if (eventChart) {
        eventChart.destroy();
        eventChart = null;
    }

    // Clear price buffer
    webSocketPriceBuffer = [];

    // Clear chart data arrays
    currentChartLabels = [];
    currentChartPrices = [];

    // Reset chart price data
    chartPriceData = { firstPrice: 0, lastPrice: 0 };

    // Останавливаем таймер обновления
    if (window.chartUpdatedTimer) {
        clearInterval(window.chartUpdatedTimer);
        window.chartUpdatedTimer = null;
    }

    // Скрываем Live бейдж
    const liveBadgeEl = document.getElementById('chart-live-badge');
    if (liveBadgeEl) {
        liveBadgeEl.style.display = 'none';
    }

    // Скрываем индикатор обновления
    const updatedEl = document.getElementById('chart-updated');
    if (updatedEl) {
        updatedEl.style.display = 'none';
    }
}

// Event Tabs Switching
function switchEventTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.event-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-tab`);
    });

    // Load data for specific tab
    if (tabName === 'activity') {
        loadActivityData();
    } else if (tabName === 'positions') {
        loadPositionsData();
    } else if (tabName === 'holdings') {
        loadHoldingsData();
    }
}

// Load Activity Data
function loadActivityData() {
    const container = document.getElementById('activity-list');
    if (!container) return;

    // Generate mock activity data (replace with API call later)
    const activities = generateMockActivity();
    
    container.innerHTML = activities.map(act => `
        <div class="activity-item">
            <div class="activity-left">
                <div class="activity-avatar">${act.avatar}</div>
                <div class="activity-info">
                    <div class="activity-user">${act.user}</div>
                    <div class="activity-action">${act.action}</div>
                </div>
            </div>
            <div class="activity-right">
                <div class="activity-amount">${act.amount}</div>
                <div class="activity-time">${act.time}</div>
            </div>
        </div>
    `).join('');
}

function generateMockActivity() {
    const actions = ['купил YES', 'купил NO', 'продал YES', 'продал NO'];
    const result = [];
    for (let i = 0; i < 15; i++) {
        result.push({
            avatar: String.fromCharCode(65 + i),
            user: `User${1000 + i}`,
            action: actions[Math.floor(Math.random() * actions.length)],
            amount: `${(Math.random() * 100).toFixed(0)} USDT`,
            time: `${Math.floor(Math.random() * 60) + 1} мин назад`
        });
    }
    return result;
}

// Load Positions Data
function loadPositionsData() {
    const container = document.getElementById('positions-stats');
    if (!container) return;

    // Mock positions data
    const positions = {
        totalVolume: (Math.random() * 10000).toFixed(0),
        openInterest: (Math.random() * 5000).toFixed(0),
        totalTrades: Math.floor(Math.random() * 500)
    };

    container.innerHTML = `
        <div class="position-stat-card">
            <span class="position-stat-value">$${positions.totalVolume}</span>
            <span class="position-stat-label">Объём</span>
        </div>
        <div class="position-stat-card">
            <span class="position-stat-value">$${positions.openInterest}</span>
            <span class="position-stat-label">Открытый интерес</span>
        </div>
        <div class="position-stat-card">
            <span class="position-stat-value">${positions.totalTrades}</span>
            <span class="position-stat-label">Сделки</span>
        </div>
    `;
}

// Load Holdings Data
function loadHoldingsData() {
    const container = document.getElementById('holdings-list');
    if (!container) return;

    // Mock holdings data
    const holdings = [];
    let total = 0;
    for (let i = 0; i < 10; i++) {
        const value = Math.floor(Math.random() * 2000) + 100;
        total += value;
        holdings.push({
            rank: i + 1,
            user: `User${1000 + i}`,
            shares: Math.floor(Math.random() * 500) + 10,
            value: value
        });
    }

    container.innerHTML = holdings.map(h => `
        <div class="holding-item">
            <div class="holding-left">
                <div class="holding-rank">${h.rank}</div>
                <div class="holding-info">
                    <div class="holding-user">${h.user}</div>
                    <div class="holding-shares">${h.shares} акций</div>
                </div>
            </div>
            <div class="holding-right">
                <div class="holding-value">$${h.value}</div>
                <div class="holding-percent">${((h.value / total) * 100).toFixed(1)}%</div>
            </div>
        </div>
    `);
}

// Toggle description visibility
function toggleDescription() {
    const descContent = document.getElementById('event-description');
    const toggleBtn = document.querySelector('.description-toggle');
    
    if (!descContent || !toggleBtn) return;
    
    const isHidden = descContent.style.display === 'none';
    descContent.style.display = isHidden ? 'block' : 'none';
    toggleBtn.classList.toggle('active', isHidden);
}

// ==================== COMMENTS FUNCTIONS ====================

function loadCommentsForEvent(eventId) {
    // Загружаем комментарии из localStorage
    const stored = localStorage.getItem(`event_${eventId}_comments`);
    if (stored) {
        eventComments = JSON.parse(stored);
    } else {
        // Демо комментарии для примера
        const user = tg.initDataUnsafe?.user;
        const displayName = user?.first_name || 'User';
        
        eventComments = [
            {
                id: 1,
                user_id: 12345,
                username: 'CryptoTrader',
                avatar: null,
                text: 'This looks like a great opportunity! I\'m bullish on this outcome.',
                timestamp: Date.now() - 7200000,
                likes: 5
            },
            {
                id: 2,
                user_id: 67890,
                username: 'MarketMaker',
                avatar: null,
                text: 'Not sure about this one. The odds seem off.',
                timestamp: Date.now() - 3600000,
                likes: 2
            }
        ];
    }
    
    renderComments();
}

function renderComments() {
    const commentsList = document.getElementById('comments-list');
    const commentsCount = document.getElementById('comments-count');
    
    if (!commentsList || !commentsCount) return;
    
    commentsCount.textContent = eventComments.length;
    
    if (eventComments.length === 0) {
        commentsList.innerHTML = '<div class="empty-comments">No comments yet. Be the first!</div>';
        return;
    }
    
    // Сортируем по времени (новые сверху)
    const sortedComments = [...eventComments].sort((a, b) => b.timestamp - a.timestamp);
    
    const html = sortedComments.map(comment => {
        const timeAgo = formatTimeAgo(comment.timestamp);
        const avatarInitial = (comment.username || 'U').charAt(0).toUpperCase();
        const avatarHtml = comment.avatar 
            ? `<img src="${comment.avatar}" alt="Avatar">`
            : avatarInitial;
        
        return `
            <div class="comment-item">
                <div class="comment-avatar">
                    ${avatarHtml}
                </div>
                <div class="comment-content">
                    <div class="comment-header">
                        <span class="comment-username">${escapeHtml(comment.username)}</span>
                        <span class="comment-time">${timeAgo}</span>
                    </div>
                    <div class="comment-text">${escapeHtml(comment.text)}</div>
                </div>
            </div>
        `;
    }).join('');
    
    commentsList.innerHTML = html;
}

function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function addComment() {
    const commentInput = document.getElementById('comment-input');
    const text = commentInput.value.trim();
    
    if (!text) {
        showNotification('Please enter a comment', 'error');
        return;
    }
    
    const user = tg.initDataUnsafe?.user;
    const displayName = user?.first_name || 'User';
    const avatarUrl = user?.photo_url || null;
    
    const newComment = {
        id: Date.now(),
        user_id: user?.id || 12345,
        username: displayName,
        avatar: avatarUrl,
        text: text,
        timestamp: Date.now(),
        likes: 0
    };
    
    eventComments.push(newComment);
    
    // Сохраняем в localStorage
    if (currentEventIdForComments) {
        localStorage.setItem(`event_${currentEventIdForComments}_comments`, JSON.stringify(eventComments));
    }
    
    commentInput.value = '';
    renderComments();
    
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
    
    showNotification('Comment added!', 'success');
}

function openBetModal(title, option, probability) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-option').textContent = `Predicting: ${option}`;
    document.getElementById('bet-modal').classList.remove('hidden');
}

// Chart rendering using Chart.js (Polymarket style) with gradient
let eventChart = null;
let chartUpdateInterval = null; // Auto-update interval

async function renderEventChart(eventId, options) {
    console.log('📊 [Chart] === ЗАПУСК renderEventChart ===');
    console.log('📊 [Chart] Event ID:', eventId);
    console.log('📊 [Chart] Options count:', options?.length);
    
    const canvas = document.getElementById('event-chart-canvas');
    if (!canvas) {
        console.error('❌ [Chart] Canvas элемент не найден!');
        return;
    }
    console.log('📊 [Chart] Canvas найден:', canvas);

    // Clear any existing update interval
    if (chartUpdateInterval) {
        clearInterval(chartUpdateInterval);
        chartUpdateInterval = null;
    }

    // Destroy existing chart
    if (eventChart) {
        eventChart.destroy();
        eventChart = null;
    }

    // Get event details to determine type
    let eventType = 'crypto'; // default
    try {
        const event = await apiRequest(`/events/${eventId}`);
        console.log('📊 [Chart] Данные события:', event);
        if (event && event.category) {
            eventType = event.category;
        }
    } catch (e) {
        console.error('❌ [Chart] Error loading event:', e);
        console.log('⚠️ [Chart] Could not determine event type, using default');
    }

    console.log('📊 [Chart] Тип события:', eventType);

    // For sports and politics, show bet history instead of chart
    if (['sports', 'politics', 'pop_culture'].includes(eventType)) {
        console.log('📊 [Chart] Показываем bet history для не-крипто события');
        renderBetHistory(eventId);
        return;
    }

    // For crypto, business, science - show price chart
    console.log('📊 [Chart] Показываем price chart для крипто события');
    renderPriceChart(eventId, options);
}

// Render bet history for sports/politics events
async function renderBetHistory(eventId) {
    const chartContainer = document.getElementById('event-chart');
    if (!chartContainer) return;

    // Сохраняем структуру контейнера для последующего восстановления графика
    const originalInnerHTML = chartContainer.innerHTML;

    try {
        const response = await fetch(`${backendUrl}/events/${eventId}/bet-history`);
        let betHistory = [];
        if (response.ok) {
            betHistory = await response.json();
        }

        if (betHistory.length === 0) {
            // No bets yet - show message
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

        // Render bet history list - оборачиваем в контейнер с классом для идентификации
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
        // Восстанавливаем оригинальную структуру при ошибке
        chartContainer.innerHTML = originalInnerHTML;
    }
}

// Render chart with REAL Binance WebSocket data - Polymarket/Binance Style
// Используем модуль useBinanceWebSocket для загрузки истории и WebSocket
let binanceWebSocket = null;
let currentChartInterval = '15m';
let chartPriceData = { firstPrice: 0, lastPrice: 0, symbol: null };
let webSocketPriceBuffer = [];
let webSocketUpdateTimeout = null;
let currentChartLabels = [];
let currentChartPrices = [];
let chartYMin = null;
let chartYMax = null;
let currentBinanceSymbol = null; // Текущий символ Binance

// Константы BINANCE_INTERVALS и CANDLE_LIMITS определены в binanceService.js
// Используем глобальные переменные оттуда

async function renderPriceChart(eventId, options) {
    console.log('📊 [Chart] === renderPriceChart: ЗАПУСК ===');
    console.log('📊 [Chart] Event ID:', eventId);
    
    const canvas = document.getElementById('event-chart-canvas');
    if (!canvas) {
        console.error('❌ [Chart] Canvas не найден в renderPriceChart');
        return;
    }

    console.log('📊 [Chart] Инициализация графика для события:', eventId);

    // Закрываем предыдущее WebSocket соединение
    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }

    // Сбрасываем буферы и данные
    webSocketPriceBuffer = [];
    currentChartLabels = [];
    currentChartPrices = [];
    chartYMin = null;
    chartYMax = null;
    chartPriceData = { firstPrice: 0, lastPrice: 0, symbol: null };

    let event = null;
    try {
        event = await apiRequest(`/events/${eventId}`);
        console.log('📊 [Chart] Данные события:', event.title);
    } catch (e) {
        console.error('❌ [Chart] Error loading event:', e);
        return;
    }

    // Определяем символ Binance из названия события
    let binanceSymbol = null;
    const eventText = (event.title + ' ' + (event.description || '')).toLowerCase();

    console.log('📊 [Chart] Анализ текста события:', eventText.substring(0, 100) + '...');

    for (const [key, symbol] of Object.entries(CRYPTO_SYMBOLS)) {
        if (eventText.includes(key)) {
            binanceSymbol = symbol;
            console.log('📊 [Chart] Найден символ:', key, '→', symbol);
            break;
        }
    }

    if (!binanceSymbol) {
        console.log('⚠️ [Chart] Binance symbol not found, trying Polymarket chart...');
        // Пробуем использовать Polymarket chart для не-крипто событий
        renderPolymarketChart(eventId, event, options);
        return;
    }

    currentBinanceSymbol = binanceSymbol;
    console.log('📊 [Chart] Запуск графика для:', binanceSymbol);

    renderRealtimeChart(canvas, binanceSymbol, options);
}

/**
 * Рендерит график используя Polymarket Candles API
 * Для событий которые не являются крипто-событиями
 */
async function renderPolymarketChart(eventId, event, options) {
    console.log('📊 [PolymarketChart] === renderPolymarketChart: ЗАПУСК ===');
    console.log('📊 [PolymarketChart] Event ID:', eventId);
    console.log('📊 [PolymarketChart] Event:', event.title);

    const canvas = document.getElementById('event-chart-canvas');
    const chartContainer = document.getElementById('event-chart');
    const chartTimeframe = document.getElementById('event-chart-timeframe');
    const chartInfo = document.getElementById('event-chart-info');
    const chartLiveBadge = document.getElementById('chart-live-badge');

    if (!canvas) {
        console.error('❌ [PolymarketChart] Canvas не найден');
        return;
    }

    // Показываем UI графика
    if (chartTimeframe) chartTimeframe.style.display = 'flex';
    if (chartInfo) chartInfo.style.display = 'block';
    if (chartLiveBadge) chartLiveBadge.style.display = 'none'; // Polymarket не real-time

    // Устанавливаем размеры canvas
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    const ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Destroy existing chart
    if (eventChart) {
        eventChart.destroy();
        eventChart = null;
    }

    // Получаем Polymarket ID из события
    const polymarketId = event.polymarket_id;
    
    if (!polymarketId) {
        console.warn('⚠️ [PolymarketChart] No Polymarket ID for this event');
        // Показываем fallback
        if (chartContainer) {
            chartContainer.innerHTML = `
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

    // Используем первый option по умолчанию
    const selectedOption = options && options.length > 0 ? options[0] : null;
    const outcomeName = selectedOption?.text || selectedOption?.outcome || 'Yes';

    console.log('📊 [PolymarketChart] Market ID:', polymarketId);
    console.log('📊 [PolymarketChart] Outcome:', outcomeName);

    // Показываем loading
    updateChartPriceDisplay(0.5, 0);

    try {
        // Загружаем данные из Polymarket Chart API
        console.log('📊 [PolymarketChart] Loading candles from Polymarket API...');
        
        const chartData = await window.polymarketChartService.loadCandles(
            polymarketId,
            outcomeName,
            currentChartInterval || '1h',
            168
        );

        console.log('📊 [PolymarketChart] Data loaded:', chartData);
        console.log('📊 [PolymarketChart] Source:', chartData.source);
        console.log('📊 [PolymarketChart] Candles count:', chartData.candles?.length || 0);
        console.log('📊 [PolymarketChart] Price range:', chartData.firstPrice?.toFixed(3), '-', chartData.lastPrice?.toFixed(3));

        // Обновляем UI с данными
        const priceChange = chartData.priceChange || 0;
        updateChartPriceDisplay(chartData.lastPrice || 0.5, priceChange);

        // Рендерим график Chart.js
        const chartColor = priceChange >= 0 ? '#10b981' : '#ef4444'; // Зеленый/Красный

        eventChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels.map(ts => {
                    const date = new Date(ts);
                    return date.toLocaleDateString('ru-RU', { 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    });
                }),
                datasets: [{
                    label: outcomeName,
                    data: chartData.prices,
                    borderColor: chartColor,
                    borderWidth: 2,
                    fill: true,
                    backgroundColor: chartColor + '20', // 20% opacity
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: chartColor,
                    pointHoverBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                    axis: 'x'
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(13, 17, 23, 0.98)',
                        titleColor: chartColor,
                        bodyColor: '#f0f6fc',
                        borderColor: chartColor + '80',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            title: (items) => {
                                const idx = items[0].dataIndex;
                                const label = chartData.labels[idx];
                                return new Date(label).toLocaleString('ru-RU');
                            },
                            label: (item) => {
                                const value = item.parsed.y;
                                const percent = (value * 100).toFixed(1) + '%';
                                return `Цена: ${percent}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#888',
                            maxTicksLimit: 6,
                            maxRotation: 0,
                            callback: (val, index) => {
                                const label = chartData.labels[index];
                                if (!label) return '';
                                const date = new Date(label);
                                return date.toLocaleDateString('ru-RU', { 
                                    day: 'numeric', 
                                    hour: '2-digit' 
                                });
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#888',
                            callback: (value) => (value * 100).toFixed(0) + '%'
                        },
                        min: Math.max(0, (chartData.firstPrice || 0.5) - 0.3),
                        max: Math.min(1, (chartData.firstPrice || 0.5) + 0.3)
                    }
                }
            }
        });

        console.log('✅ [PolymarketChart] Chart rendered successfully');

        // Setup timeframe buttons
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.onclick = async () => {
                document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentChartInterval = btn.dataset.interval;

                console.log('📊 [PolymarketChart] Changing interval to:', currentChartInterval);
                
                // Перезагружаем данные для нового интервала
                await renderPolymarketChart(eventId, event, options);
            };
        });

    } catch (error) {
        console.error('❌ [PolymarketChart] Error loading chart:', error);
        
        // Показываем ошибку
        if (chartContainer) {
            chartContainer.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center; padding: 20px;">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 8v4M12 16h.01"/>
                    </svg>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">Ошибка загрузки графика</div>
                    <div style="font-size: 12px; color: var(--text-muted);">${error.message || 'Неизвестная ошибка'}</div>
                </div>
            `;
        }
    }
}

function renderRealtimeChart(canvas, binanceSymbol, options) {
    const ctx = canvas.getContext('2d');
    const chartColor = '#f2b03d';

    console.log('📊 [Chart] Рендер графика для:', binanceSymbol);

    // Устанавливаем размеры canvas
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    document.getElementById('event-chart-timeframe').style.display = 'flex';
    document.getElementById('event-chart-info').style.display = 'block';

    if (eventChart) {
        eventChart.destroy();
    }

    // Setup timeframe buttons
    document.querySelectorAll('.timeframe-btn').forEach(btn => {
        btn.onclick = () => {
            // Обновляем активную кнопку
            document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentChartInterval = btn.dataset.interval;

            console.log('📊 [Chart] Смена таймфрейма на:', currentChartInterval);

            // Сбрасываем состояние при смене таймфрейма
            webSocketPriceBuffer = [];
            currentChartLabels = [];
            currentChartPrices = [];
            chartYMin = null;
            chartYMax = null;

            if (webSocketUpdateTimeout) {
                clearTimeout(webSocketUpdateTimeout);
            }

            // Отключаем WebSocket через сервис
            if (window.binanceService) {
                window.binanceService.disconnectWebSocket();
            } else if (binanceWebSocket) {
                binanceWebSocket.close();
                binanceWebSocket = null;
            }

            // Загружаем новые данные для выбранного интервала
            loadChartData(binanceSymbol, currentChartInterval);
        };
    });

    eventChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: currentChartLabels,
            datasets: [{
                label: binanceSymbol,
                data: currentChartPrices,
                borderColor: chartColor,
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: chartColor,
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                intersect: false,
                mode: 'index',
                axis: 'x'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(13, 17, 23, 0.98)',
                    titleColor: '#f2b03d',
                    bodyColor: '#f0f6fc',
                    borderColor: 'rgba(242, 176, 61, 0.5)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    titleFont: { size: 13, weight: '700' },
                    bodyFont: { size: 12 },
                    cornerRadius: 8,
                    callbacks: {
                        title: (ctx) => {
                            const date = new Date(ctx[0].label);
                            return date.toLocaleString(isRussian ? 'ru-RU' : 'en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        },
                        label: (ctx) => `$${ctx.parsed.y.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    display: false,
                    grid: { display: false },
                    ticks: { display: false }
                },
                y: {
                    display: true,
                    position: 'right',
                    grid: {
                        color: 'rgba(255,255,255,0.03)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#71717a',
                        font: { size: 10 },
                        padding: 4,
                        maxTicksLimit: 5,
                        callback: (value) => {
                            if (value >= 1000) {
                                return '$' + (value / 1000).toFixed(1) + 'K';
                            }
                            return '$' + value.toFixed(2);
                        }
                    },
                    min: chartYMin,
                    max: chartYMax
                }
            }
        }
    });

    const gradient = ctx.createLinearGradient(0, 0, 0, rect.height);
    gradient.addColorStop(0, 'rgba(242, 176, 61, 0.3)');
    gradient.addColorStop(0.5, 'rgba(242, 176, 61, 0.08)');
    gradient.addColorStop(1, 'rgba(242, 176, 61, 0.02)');
    eventChart.data.datasets[0].backgroundColor = gradient;

    // Загружаем данные через binanceService если доступен
    if (window.binanceService) {
        console.log('📊 [Chart] Используем binanceService для:', binanceSymbol);
        loadChartData(binanceSymbol, currentChartInterval);
    } else {
        console.log('📊 [Chart] binanceService не найден, используем fallback');
        loadChartData(binanceSymbol, currentChartInterval);
    }
}

/**
 * Загружает данные графика через binanceService
 */
async function loadChartData(symbol, interval) {
    console.log('📊 [Chart] ========== ЗАГРУЗКА ГРАФИКА ==========');
    console.log('📊 [Chart] Символ:', symbol, '| Таймфрейм:', interval);
    console.log('📊 [Chart] Вызов binanceService.loadHistoricalCandles...');

    try {
        // Используем binanceService если доступен
        if (window.binanceService) {
            const { labels, prices, firstPrice, lastPrice, candles } =
                await window.binanceService.loadHistoricalCandles(symbol, interval);

            console.log('📊 [Chart] ✅ Получено данных:', labels.length, 'свечей');
            console.log('📊 [Chart] 📊 Первая свеча:', {
                time: labels[0],
                price: firstPrice.toFixed(2)
            });
            console.log('📊 [Chart] 📊 Последняя свеча:', {
                time: labels[labels.length - 1],
                price: lastPrice.toFixed(2)
            });

            // Проверка на "ровную линию" - все цены одинаковые
            const uniquePrices = new Set(prices);
            console.log('📊 [Chart] 🔍 Уникальных цен:', uniquePrices.size, 'из', prices.length);

            if (uniquePrices.size < 5) {
                console.error('❌ [Chart] ⚠️ ПОДОЗРИТЕЛЬНО: мало уникальных цен! Возможно данные шаблонные');
            }

            if (labels.length === 0) {
                console.warn('⚠️ [Chart] Нет данных от Binance API');
                return;
            }

            // Проверка диапазона цен для разных монет
            const priceRange = lastPrice - firstPrice;
            const priceChangePercent = (priceRange / firstPrice) * 100;
            console.log('📊 [Chart] 💹 Изменение цены:', priceChangePercent.toFixed(2), '%');

            // Обновляем глобальные переменные
            currentChartLabels = labels;
            currentChartPrices = prices;
            chartPriceData = { firstPrice, lastPrice, symbol, candles };

            console.log('📊 [Chart] Диапазон цен:', firstPrice.toFixed(2), '-', lastPrice.toFixed(2));

            // Обновляем время последнего обновления
            window.chartLastUpdateTime = Date.now();

            // Обновляем отображение цены
            updateChartPriceDisplay(lastPrice);
            updatePredictionOdds(currentChartPrices, chartPriceData.symbol);

            // Рассчитываем масштаб Y
            const minPrice = Math.min(...currentChartPrices);
            const maxPrice = Math.max(...currentChartPrices);
            const range = maxPrice - minPrice;
            const padding = range > 0 ? range * 0.15 : minPrice * 0.15;

            chartYMin = minPrice - padding;
            chartYMax = maxPrice + padding;

            if (eventChart) {
                eventChart.options.scales.y.min = chartYMin;
                eventChart.options.scales.y.max = chartYMax;

                // Обновляем данные графика
                eventChart.data.labels = currentChartLabels;
                eventChart.data.datasets[0].data = currentChartPrices;
                eventChart.data.datasets[0].label = symbol;
                eventChart.update('none');

                console.log('📊 [Chart] ✅ График обновлён успешно');
                console.log('📊 [Chart] ========== ЗАГРУЗКА ЗАВЕРШЕНА ==========');
            }

            // Подключаем WebSocket для реального времени
            connectBinanceWebSocket(symbol, interval);

        } else {
            // Fallback на прямую загрузку
            console.log('📊 [Chart] binanceService не найден, загрузка напрямую...');
            await loadChartDataDirect(symbol, interval);
        }

    } catch (err) {
        console.error('❌ [Chart] Error loading chart data:', err);
        console.error('❌ [Chart] Stack:', err.stack);

        // Показываем сообщение об ошибке пользователю
        const chartContainer = document.getElementById('event-chart');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center; padding: 20px;">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 8v4M12 16h.01"/>
                    </svg>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">График временно недоступен</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Попробуйте обновить страницу или выберите другое событие</div>
                    <div style="font-size: 10px; color: #666; margin-top: 12px; max-width: 80%;">${err.message || 'Ошибка загрузки данных'}</div>
                </div>
            `;
        }
    }
}

/**
 * Fallback загрузка данных напрямую (если binanceService недоступен)
 */
async function loadChartDataDirect(symbol, interval) {
    // Используем глобальные константы из binanceService.js
    const binanceIntervals = window.BINANCE_INTERVALS || {
        '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d'
    };
    const candleLimits = window.CANDLE_LIMITS || {
        '1m': 100, '5m': 100, '15m': 96, '1h': 168, '4h': 168, '1d': 90
    };
    
    const binanceInterval = binanceIntervals[interval] || '15m';
    const limit = candleLimits[interval] || 96;

    // Нормализация символа: ВЕРХНИЙ регистр для REST API
    const normalizedSymbol = symbol.toUpperCase();

    const url = `https://api.binance.com/api/v3/klines?symbol=${normalizedSymbol}&interval=${binanceInterval}&limit=${limit}`;
    console.log('📊 [Chart] REST запрос URL:', url);

    const response = await fetch(url);
    console.log('📊 [Chart] Статус ответа:', response.status, response.ok ? '✅' : '❌');

    if (!response.ok) {
        throw new Error(`Binance API error: ${response.status}`);
    }

    const data = await response.json();
    console.log('📊 [Chart] Получено свечей:', data.length);

    currentChartLabels = [];
    currentChartPrices = [];

    data.forEach(candle => {
        const timestamp = candle[0];
        const close = parseFloat(candle[4]);
        currentChartLabels.push(new Date(timestamp).toISOString());
        currentChartPrices.push(close);
    });

    if (currentChartPrices.length > 0) {
        chartPriceData.firstPrice = currentChartPrices[0];
        chartPriceData.lastPrice = currentChartPrices[currentChartPrices.length - 1];

        updateChartPriceDisplay(currentChartPrices[currentChartPrices.length - 1]);
        updatePredictionOdds(currentChartPrices, chartPriceData.symbol);

        const minPrice = Math.min(...currentChartPrices);
        const maxPrice = Math.max(...currentChartPrices);
        const range = maxPrice - minPrice;
        const padding = range > 0 ? range * 0.15 : minPrice * 0.15;

        chartYMin = minPrice - padding;
        chartYMax = maxPrice + padding;

        if (eventChart) {
            eventChart.options.scales.y.min = chartYMin;
            eventChart.options.scales.y.max = chartYMax;
            eventChart.data.labels = currentChartLabels;
            eventChart.data.datasets[0].data = currentChartPrices;
            eventChart.update('none');
        }
    }

    connectBinanceWebSocket(symbol);
}

function updateChartPriceDisplay(currentPrice) {
    const priceEl = document.getElementById('chart-price');
    const changeEl = document.getElementById('chart-change');
    const updatedEl = document.getElementById('chart-updated');
    const liveBadgeEl = document.getElementById('chart-live-badge');

    if (!priceEl || !changeEl) return;

    priceEl.textContent = `$${currentPrice.toFixed(2)}`;

    const firstPrice = chartPriceData.firstPrice || currentPrice;
    const change = ((currentPrice - firstPrice) / firstPrice) * 100;
    const changeStr = change >= 0 ? `+${change.toFixed(2)}%` : `${change.toFixed(2)}%`;

    changeEl.textContent = changeStr;
    changeEl.className = 'event-chart-change' + (change >= 0 ? '' : ' negative');

    // Показываем Live бейдж для крипто событий
    if (liveBadgeEl) {
        liveBadgeEl.style.display = 'flex';
    }

    // Обновляем индикатор "Обновлено X сек назад"
    if (updatedEl) {
        updatedEl.style.display = 'block';
        updateChartUpdatedTime(updatedEl);
        
        // Запускаем таймер обновления
        if (window.chartUpdatedTimer) {
            clearInterval(window.chartUpdatedTimer);
        }
        window.chartUpdatedTimer = setInterval(() => {
            updateChartUpdatedTime(updatedEl);
        }, 1000);
    }
}

/**
 * Обновляет текст "Обновлено X сек назад"
 */
function updateChartUpdatedTime(element) {
    if (!element) return;
    
    const now = Date.now();
    const lastUpdate = window.chartLastUpdateTime || now;
    const seconds = Math.floor((now - lastUpdate) / 1000);
    
    if (seconds < 1) {
        element.textContent = '🔄 Обновлено только что';
    } else if (seconds < 60) {
        element.textContent = `🔄 Обновлено ${seconds} сек назад`;
    } else {
        const minutes = Math.floor(seconds / 60);
        element.textContent = `🔄 Обновлено ${minutes} мин назад`;
    }
}

/**
 * Connect to Binance WebSocket for real-time price updates
 */
function connectBinanceWebSocket(symbol) {
    console.log('🔌 [Chart] Подключение WebSocket для:', symbol);

    // Закрываем предыдущее соединение если есть
    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }

    // Нормализация символа: НИЖНИЙ регистр для WebSocket
    const wsSymbol = symbol.toLowerCase();

    const streamName = `${wsSymbol}@trade`;
    const wsUrl = `wss://stream.binance.com:9443/ws/${streamName}`;

    console.log('🔌 [Chart] WebSocket URL:', wsUrl, '(символ:', symbol, '→', wsSymbol + ')');

    binanceWebSocket = new WebSocket(wsUrl);
    webSocketPriceBuffer = [];
    if (webSocketUpdateTimeout) {
        clearTimeout(webSocketUpdateTimeout);
    }

    // Обработчик открытия соединения
    binanceWebSocket.onopen = function() {
        console.log('✅ [Chart] WebSocket соединени�� открыто для:', symbol);
    };

    // Функция обновления графика
    function updateChartFromBuffer() {
        if (webSocketPriceBuffer.length === 0 || !eventChart) {
            console.log('🔌 [Chart] Пропуск обновления: буфер пуст или нет eventChart');
            return;
        }

        // Получаем последнюю цену
        const lastTrade = webSocketPriceBuffer[webSocketPriceBuffer.length - 1];
        const lastPrice = lastTrade.price;

        console.log('🔌 [Chart] Обновление графика: цена =', lastPrice.toFixed(4));

        // Добавляем новую точку
        currentChartLabels.push(lastTrade.timestamp.toISOString());
        currentChartPrices.push(lastPrice);

        // Keep last N points - оптимизация для производительности
        const maxPoints = currentChartInterval === '1m' ? 100 :
                         currentChartInterval === '5m' ? 100 :
                         currentChartInterval === '15m' ? 96 :
                         currentChartInterval === '1h' ? 168 : 168;

        while (currentChartLabels.length > maxPoints) {
            currentChartLabels.shift();
            currentChartPrices.shift();
        }

        // Проверяем масштаб Y - обновляем только если цена вышла за границы
        if (chartYMin !== null && chartYMax !== null) {
            const threshold = 0.1; // 10%
            if (lastPrice > chartYMax * (1 - threshold) || lastPrice < chartYMin * (1 + threshold)) {
                const newMin = Math.min(...currentChartPrices);
                const newMax = Math.max(...currentChartPrices);
                const range = newMax - newMin;
                const padding = range > 0 ? range * 0.15 : newMax * 0.15;

                chartYMin = newMin - padding;
                chartYMax = newMax + padding;

                eventChart.options.scales.y.min = chartYMin;
                eventChart.options.scales.y.max = chartYMax;
            }
        }

        // Обновляем график БЕЗ полной перерисовки (используем 'none' для производительности)
        eventChart.data.labels = currentChartLabels;
        eventChart.data.datasets[0].data = currentChartPrices;
        eventChart.update('none');

        // Обновляем отображение цены и коэффициенты
        updateChartPriceDisplay(lastPrice);
        updatePredictionOdds(currentChartPrices, chartPriceData.symbol);

        // Очищаем буфер
        webSocketPriceBuffer = [];
    }

    // Обработчик входящих сообщений
    binanceWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const price = parseFloat(data.p);
        const timestamp = new Date(data.T);

        // Добавляем в буфер
        webSocketPriceBuffer.push({ price, timestamp });

        // Обновляем цену в UI сразу (для мгновенной реакции)
        updateChartPriceDisplay(price);

        // ⚠️ Debounce обновления графика ЗАВИСИТ от таймфрейма!
        // Это исправляет проблему "одинаковой скорости" графиков
        // 1m: обновляем часто (каждые 500мс) — видно движение
        // 5m: обновляем реже (каждые 2 сек) — сглаженное движение
        // 15m+: обновляем ещё реже (каждые 5 сек) — для долгосрочных графиков
        const debounceTime = currentChartInterval === '1m' ? 500 :
                            currentChartInterval === '5m' ? 2000 :
                            currentChartInterval === '15m' ? 5000 :
                            currentChartInterval === '1h' ? 10000 :
                            currentChartInterval === '4h' ? 15000 : 20000;

        if (webSocketUpdateTimeout) {
            clearTimeout(webSocketUpdateTimeout);
        }

        webSocketUpdateTimeout = setTimeout(() => {
            updateChartFromBuffer();
        }, debounceTime);
        
        console.log('🔌 [WebSocket] Новая цена:', price.toFixed(2), '| таймфрейм:', currentChartInterval, '| debounce:', debounceTime + 'мс');
    };

    // Обработчик ошибок
    binanceWebSocket.onerror = function(err) {
        console.error('❌ [Chart] Binance WebSocket error:', err);
    };

    // Обработчик закрытия - авто-реконнект через 5 секунд
    binanceWebSocket.onclose = function() {
        console.log('🔌 [Chart] Binance WebSocket закрыт для:', symbol);
        if (webSocketUpdateTimeout) {
            clearTimeout(webSocketUpdateTimeout);
        }
        setTimeout(() => {
            if (binanceWebSocket && binanceWebSocket.readyState === WebSocket.CLOSED) {
                console.log('🔌 [Chart] Переподключение WebSocket для:', symbol);
                connectBinanceWebSocket(symbol);
            }
        }, 5000);
    };

    console.log('✅ [Chart] Binance WebSocket подключён:', streamName);
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Конвертирует время в МСК с 24-часовым форматом
 * @param {string|Date} isoString - ISO строка времени или Date объект
 * @returns {string} Отформатированная строка времени в МСК (24-часовой формат)
 */
function formatTimeMSK(isoString) {
    if (!isoString) return '';
    
    try {
        const date = new Date(isoString);
        
        // Конвертируем в МСК (UTC+3)
        const mskOffset = 3 * 60; // минут
        const utc = date.getTime() + (date.getTimezoneOffset() * 60000);
        const mskDate = new Date(utc + (mskOffset * 60000));
        
        // Формати��уем в 24-часовом формате
        const day = mskDate.getDate().toString().padStart(2, '0');
        const month = (mskDate.getMonth() + 1).toString().padStart(2, '0');
        const year = mskDate.getFullYear();
        const hours = mskDate.getHours().toString().padStart(2, '0');
        const minutes = mskDate.getMinutes().toString().padStart(2, '0');
        
        if (isRussian) {
            return `${day}.${month}.${year} ${hours}:${minutes} МСК`;
        }
        return `${day}/${month}/${year} ${hours}:${minutes} MSK`;
    } catch (e) {
        console.error('Error formatting time MSK:', e);
        return isoString;
    }
}

/**
 * Форматирует оставшееся время до события
 */
function formatTimeLeft(seconds) {
    if (seconds < 0) return isRussian ? "Завершено" : "Ended";

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 30) {
        const months = Math.floor(days / 30);
        return `${months}${isRussian ? ' мес' : 'mo'}`;
    }
    if (days > 0) return `${days}${isRussian ? 'д' : 'd'} ${hours}${isRussian ? 'ч' : 'h'}`;
    if (hours > 0) return `${hours}${isRussian ? 'ч' : 'h'} ${minutes}${isRussian ? 'м' : 'm'}`;
    return `${minutes}${isRussian ? 'м' : 'm'}`;
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return Math.floor(num).toString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('notification-hide');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Close modals on backdrop click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.add('hidden');
    }
});

// ==================== CREATE EVENT ====================

function openCreateEventModal() {
    document.getElementById('create-event-modal').classList.remove('hidden');
    
    // Set default end time (7 days from now)
    const now = new Date();
    now.setDate(now.getDate() + 7);
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('create-end-time').value = now.toISOString().slice(0, 16);
}

function closeCreateEventModal() {
    document.getElementById('create-event-modal').classList.add('hidden');
}

async function submitCreateEvent() {
    const title = document.getElementById('create-title').value.trim();
    const description = document.getElementById('create-description').value.trim();
    const category = document.getElementById('create-category').value;
    const image_url = document.getElementById('create-image').value.trim();
    const end_time = document.getElementById('create-end-time').value;
    const options_str = document.getElementById('create-options').value.trim();

    if (!title || !options_str) {
        showNotification('Title and options are required', 'error');
        return;
    }

    const options = options_str.split(',').map(s => s.trim()).filter(s => s);
    if (options.length < 2) {
        showNotification('At least 2 options required', 'error');
        return;
    }

    try {
        const user = await apiRequest(`/user/${tg.initDataUnsafe.user.id}`);
        
        const response = await fetch(`${backendUrl}/events/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: tg.initDataUnsafe.user.id,
                title,
                description,
                category,
                image_url,
                end_time: new Date(end_time).toISOString(),
                options
            })
        });

        const result = await response.json();
        
        if (result.success) {
            showNotification('Event created! Waiting for moderation.', 'success');
            closeCreateEventModal();
            loadEvents();
        } else {
            showNotification(result.detail || 'Failed to create event', 'error');
        }
    } catch (e) {
        console.error('Create event error:', e);
        showNotification('Failed to create event', 'error');
    }
}

// Initialize category scroll on page load
setupCategoryScroll();

// Apply translations on page load
function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            el.textContent = t[key];
        }
    });
    
    // ��еревод категорий
    document.querySelectorAll('.category-btn').forEach(btn => {
        const cat = btn.dataset.category;
        const nameSpan = btn.querySelector('.category-name');
        if (nameSpan && t[cat]) {
            nameSpan.textContent = t[cat];
        }
    });
}

// Apply translations after DOM loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyTranslations);
} else {
    applyTranslations();
}
