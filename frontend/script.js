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

    // Шаг 7: Убираем лишние пробелы
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
// Автоматическое определение backend URL
const configuredBackendUrl = window.__BACKEND_URL__;
let backendUrl = configuredBackendUrl
    || (window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : `${window.location.origin}/api`);

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
    tg.expand();
    tg.ready();

    // Telegram theme colors
    if (tg.themeParams) {
        document.documentElement.style.setProperty('--bg-primary', tg.themeParams.bg_color || '#0a0a0a');
        document.documentElement.style.setProperty('--bg-secondary', tg.themeParams.secondary_bg_color || '#141414');
    }

    // Load profile immediately
    loadProfile();

    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 500);

    // Initial load
    loadEvents();
    loadUserBalance();
    checkAdminStatus();

    // Start auto-refresh
    startAutoRefresh();
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
        
        const response = await fetch(fullUrl, {
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            ...options
        });
        
        if (!response.ok) {
            let error;
            try {
                error = await response.json();
            } catch {
                error = { detail: `HTTP ${response.status}: ${response.statusText}` };
            }
            throw new Error(error.detail || 'Request error');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
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
    try {
        const container = document.getElementById('events-container');
        
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
        
        const data = await apiRequest(url);
        
        if (!data.events || data.events.length === 0) {
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
        
        container.innerHTML = data.events.map(event => createEventCard(event)).join('');
    } catch (error) {
        console.error('Load events error:', error);
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
                    <div class="empty-state-text">${error.message}</div>
                    <button class="empty-state-btn" onclick="loadEvents()">
                        Try Again
                    </button>
                </div>
            `;
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
        
        const result = await apiRequest('/predict', {
            method: 'POST',
            body: JSON.stringify({
                telegram_id: getUserId(),
                event_id: currentEventId,
                option_index: currentOptionIndex,
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
        const event = await apiRequest(`/events/${eventId}`);
        if (!event) return;

        selectedOptionIndex = null;
        currentEventIdForComments = eventId;

        // Загружаем комментарии для события (из localStorage для демо)
        loadCommentsForEvent(eventId);

        document.getElementById('event-modal-title').textContent = translateEventText(event.title);
        document.getElementById('event-description').innerHTML = `
            <strong>${tr('description')}:</strong><br>
            ${translateEventText(event.description) || tr('no_description')}
        `;

        // Render options
        const optionsContainer = document.getElementById('event-options');
        optionsContainer.innerHTML = event.options.map((opt, idx) => `
            <div class="event-option-btn" onclick="selectEventOption(${idx}, ${opt.probability})">
                <span class="event-option-text">${translateEventText(opt.text)}</span>
                <span class="event-option-probability">${opt.probability}%</span>
            </div>
        `).join('');

        // Show/hide chart based on has_chart flag
        const chartContainer = document.getElementById('event-chart');
        if (chartContainer) {
            chartContainer.style.display = event.has_chart ? 'block' : 'none';
        }

        // Show modal
        document.getElementById('event-modal').classList.remove('hidden');

        // Render chart only if has_chart is true
        if (event.has_chart) {
            setTimeout(() => renderEventChart(event.id, event.options), 100);
        }
    } catch (e) {
        console.error('Error loading event:', e);
        showNotification('Failed to load event details', 'error');
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
    
    // Close Binance WebSocket
    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }
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
    const canvas = document.getElementById('event-chart-canvas');
    if (!canvas) return;

    // Clear any existing update interval
    if (chartUpdateInterval) {
        clearInterval(chartUpdateInterval);
        chartUpdateInterval = null;
    }

    // Destroy existing chart
    if (eventChart) {
        eventChart.destroy();
    }

    // Get event details to determine type
    let eventType = 'crypto'; // default
    try {
        const event = await apiRequest(`/events/${eventId}`);
        if (event && event.category) {
            eventType = event.category;
        }
    } catch (e) {
        console.log('Could not determine event type, using default');
    }

    // For sports and politics, show bet history instead of chart
    if (['sports', 'politics', 'pop_culture'].includes(eventType)) {
        renderBetHistory(eventId);
        return;
    }

    // For crypto, business, science - show price chart
    renderPriceChart(eventId, options);
}

// Render bet history for sports/politics events
async function renderBetHistory(eventId) {
    const chartContainer = document.getElementById('event-chart');
    if (!chartContainer) return;

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

        // Render bet history list
        chartContainer.innerHTML = `
            <div style="height: 100%; overflow-y: auto; padding: 8px;">
                <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 12px; margin-bottom: 8px;">
                    История ставок
                </div>
                ${betHistory.map(bet => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); margin-bottom: 8px;">
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
        chartContainer.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                Error loading bet history
            </div>
        `;
    }
}

// Render price chart for crypto/business/science events with REAL Binance data
let binanceWebSocket = null; // WebSocket для реальных данных

async function renderPriceChart(eventId, options) {
    const canvas = document.getElementById('event-chart-canvas');
    if (!canvas) return;

    // Close existing WebSocket
    if (binanceWebSocket) {
        binanceWebSocket.close();
        binanceWebSocket = null;
    }

    // Get event to determine crypto symbol
    let event = null;
    try {
        event = await apiRequest(`/events/${eventId}`);
    } catch (e) {
        console.error('Error loading event:', e);
        return;
    }

    // Try to find crypto symbol in event title/description
    let binanceSymbol = null;
    const eventText = (event.title + ' ' + (event.description || '')).toLowerCase();
    
    for (const [key, symbol] of Object.entries(CRYPTO_SYMBOLS)) {
        if (eventText.includes(key)) {
            binanceSymbol = symbol;
            break;
        }
    }

    if (!binanceSymbol) {
        // No crypto found - use simulated data
        renderSimulatedChart(canvas, options);
        return;
    }

    // Load real-time data from Binance via WebSocket
    renderRealtimeChart(canvas, binanceSymbol, options, eventId);
}

// Render chart with REAL Binance WebSocket data
function renderRealtimeChart(canvas, binanceSymbol, options, eventId) {
    const ctx = canvas.getContext('2d');
    const primaryColor = '#22c55e';

    // Initialize chart with empty data
    const labels = [];
    const prices = [];
    const maxPoints = 60;

    // Create initial chart with Polymarket-style settings
    eventChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: binanceSymbol,
                data: prices,
                borderColor: primaryColor,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: primaryColor,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: 0
            },
            animation: {
                duration: 0,
                x: { duration: 0 },
                y: { duration: 0 }
            },
            interaction: {
                intersect: false,
                mode: 'nearest'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 15, 18, 0.98)',
                    titleColor: '#fff',
                    bodyColor: '#a1a1aa',
                    borderColor: 'rgba(34, 197, 94, 0.5)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    titleFont: { size: 12, weight: '600' },
                    bodyFont: { size: 11 },
                    cornerRadius: 6,
                    callbacks: {
                        title: (ctx) => {
                            const date = new Date(ctx[0].label);
                            return date.toLocaleTimeString(isRussian ? 'ru-RU' : 'en-US', {
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
                    display: true,
                    grid: { display: false },
                    ticks: {
                        color: '#71717a',
                        font: { size: 9 },
                        maxTicksLimit: 6,
                        maxRotation: 0,
                        autoSkip: true,
                        padding: 0
                    },
                    offset: false,
                    min: 0,
                    max: maxPoints - 1
                },
                y: {
                    display: true,
                    position: 'right',
                    grid: {
                        color: 'rgba(255,255,255,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#71717a',
                        font: { size: 9 },
                        padding: 0,
                        maxTicksLimit: 5,
                        callback: (value) => {
                            if (value >= 1000) {
                                return '$' + (value / 1000).toFixed(1) + 'K';
                            }
                            return '$' + value.toFixed(2);
                        }
                    },
                    min: undefined,
                    max: undefined
                }
            }
        }
    });

    // Apply gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.5)');
    gradient.addColorStop(0.5, 'rgba(34, 197, 94, 0.15)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0.2)');
    eventChart.data.datasets[0].backgroundColor = gradient;

    // Fetch historical data first (REST API)
    fetch(`https://api.binance.com/api/v3/klines?symbol=${binanceSymbol}&interval=1m&limit=${maxPoints}`)
        .then(res => res.json())
        .then(data => {
            data.forEach(candle => {
                const timestamp = candle[0];
                const close = parseFloat(candle[4]);
                const time = new Date(timestamp);
                labels.push(time.toISOString());
                prices.push(close);
            });

            // Connect WebSocket - it will set fixed scale and start real-time updates
            connectBinanceWebSocket(binanceSymbol, labels, prices);
        })
        .catch(err => {
            console.error('Error fetching historical data:', err);
            // Fallback to WebSocket only
            connectBinanceWebSocket(binanceSymbol, labels, prices);
        });
}

// Connect to Binance WebSocket for real-time price updates
function connectBinanceWebSocket(symbol, labels, prices) {
    const streamName = `${symbol.toLowerCase()}@trade`;
    binanceWebSocket = new WebSocket(`wss://stream.binance.com:9443/ws/${streamName}`);

    // FIXED scaling - center the price in the middle of the chart
    const currentPrice = prices.length > 0 ? prices[prices.length - 1] : 0;

    // Set fixed percentage range around current price (±10% for stability)
    const priceRange = 0.10; // 10% range on each side
    let fixedMinPrice = currentPrice * (1 - priceRange);
    let fixedMaxPrice = currentPrice * (1 + priceRange);

    // Ensure min price is positive
    if (fixedMinPrice <= 0) {
        fixedMinPrice = currentPrice * 0.5;
        fixedMaxPrice = currentPrice * 1.5;
    }

    // Apply fixed scale immediately
    if (eventChart) {
        eventChart.options.scales.y.min = fixedMinPrice;
        eventChart.options.scales.y.max = fixedMaxPrice;
        eventChart.update('none');
    }

    binanceWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const price = parseFloat(data.p);
        const timestamp = new Date(data.T);

        // Add new data point
        labels.push(timestamp.toISOString());
        prices.push(price);

        // Keep only last 60 points for wider horizontal view
        if (labels.length > 60) {
            labels.shift();
            prices.shift();
        }

        // Update chart WITHOUT changing Y-axis scale (fixed scale)
        if (eventChart) {
            eventChart.data.labels = labels;
            eventChart.data.datasets[0].data = prices;
            // Smooth update without animation
            eventChart.update('none');
        }
    };

    binanceWebSocket.onerror = function(err) {
        console.error('WebSocket error:', err);
    };

    binanceWebSocket.onclose = function() {
        console.log('WebSocket closed');
        // Reconnect after 5 seconds
        setTimeout(() => {
            if (binanceWebSocket && binanceWebSocket.readyState === WebSocket.CLOSED) {
                connectBinanceWebSocket(symbol, labels, prices);
            }
        }, 5000);
    };
}

// Fallback: simulated chart for non-crypto events
function renderSimulatedChart(canvas, options) {
    const ctx = canvas.getContext('2d');
    const primaryColor = '#22c55e';
    const labels = [];
    const prices = [];
    const historyPoints = 50;
    const now = Date.now();

    // Generate time labels
    for (let i = historyPoints; i >= 0; i--) {
        const time = new Date(now - i * 60000); // 1 minute intervals
        labels.push(time.toISOString());
    }

    // Generate simulated prices based on option probability
    if (options.length > 0) {
        const opt = options[0];
        let basePrice = opt.probability / 100;
        
        for (let i = 0; i <= historyPoints; i++) {
            const randomChange = (Math.random() - 0.5) * 0.02;
            let price = basePrice + randomChange;
            price = Math.max(0.01, Math.min(0.99, price));
            prices.push(price);
        }
    }

    // Create chart
    eventChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: options.length > 0 ? translateEventText(options[0].text) : 'Price',
                data: prices,
                borderColor: primaryColor,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 15, 18, 0.98)',
                    titleColor: '#fff',
                    bodyColor: '#a1a1aa',
                    callbacks: {
                        label: (ctx) => (ctx.parsed.y * 100).toFixed(1) + '%'
                    }
                }
            },
            scales: {
                x: { display: false },
                y: {
                    min: 0,
                    max: 1,
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: {
                        color: '#71717a',
                        callback: (value) => (value * 100) + '%'
                    }
                }
            }
        }
    });

    // Apply gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.5)');
    gradient.addColorStop(0.5, 'rgba(34, 197, 94, 0.2)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0.3)');
    eventChart.data.datasets[0].backgroundColor = gradient;
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
        
        // Форматируем в 24-часовом формате
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
    
    // Перевод категорий
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
