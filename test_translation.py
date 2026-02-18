#!/usr/bin/env python3
"""
EventPredict Translation Tests
Tests for Russian translation function with context preservation
"""
import re
import sys

# Copy of PRESERVE_TERMS from script.js for testing
PRESERVE_TERMS = [
    # Cryptocurrencies
    'Bitcoin', 'Ethereum', 'Solana', 'XRP', 'Cardano', 'Dogecoin', 'Polkadot',
    'Avalanche', 'Chainlink', 'Polygon', 'Litecoin', 'Uniswap', 'Cosmos',
    'BTC', 'ETH', 'SOL', 'DOGE', 'ADA', 'DOT', 'AVAX', 'LINK', 'MATIC', 'LTC',
    'USDT', 'USDC', 'BNB', 'BUSD', 'DAI',
    # Famous people
    'Trump', 'Biden', 'Putin', 'Zelensky', 'Musk', 'Bezos', 'Gates', 'Buffett',
    'Obama', 'Clinton', 'Bloomberg', 'Zuckerberg', 'Cook', 'Nadella', 'Altman',
    # Companies and brands
    'Tesla', 'Apple', 'Google', 'Amazon', 'Microsoft', 'Nvidia', 'Meta', 'Netflix',
    'OpenAI', 'SpaceX', 'NASA', 'SEC', 'Fed',
    # Sports teams and leagues
    'NBA', 'NFL', 'MLB', 'NHL', 'UFC', 'FIFA', 'UEFA', 'Premier League',
    'Lakers', 'Celtics', 'Warriors', 'Real Madrid', 'Barcelona', 'Manchester United',
    'Liverpool', 'Chelsea', 'Arsenal', 'Manchester City',
    # Countries and cities
    'USA', 'US', 'Russia', 'Ukraine', 'China', 'UK', 'Germany', 'France',
    'Moscow', 'Kyiv', 'Beijing', 'London', 'Paris', 'Berlin', 'Tokyo',
    'New York', 'Los Angeles', 'San Francisco',
]

# Preserve patterns (regex)
PRESERVE_PATTERNS = [
    r'\$[\d,]+(?:\.\d+)?(?:[MBK])?',  # $100,000, $1M, $1.5B
    r'\d+(?:\.\d+)?\s*(?:USDT|BTC|ETH|TON|USD|EUR)',  # 1000 USDT
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',  # December 25, 2024
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',  # December 2024
    r'Q[1-4]\s+\d{4}',  # Q4 2024
    r'\d+(?:\.\d+)?%',  # 50%, 75.5%
    r'\b\d{1,3}(?:,\d{3})+\b',  # 1,000,000
]

# Translation dictionary (subset for testing)
TRANSLATION_DICT = {
    'Will': 'Будет', 'will': 'будет',
    'reach': 'достичь', 'Reach': 'Достичь',
    'by': 'к', 'By': 'К',
    'or': 'или', 'and': 'и',
    'market': 'рынок', 'Market': 'Рынок',
    'price': 'цена', 'Price': 'Цена',
    'election': 'выборы', 'Election': 'Выборы',
    'game': 'игра', 'Game': 'Игра',
    'team': 'команда', 'Team': 'Команда',
}


def escapeRegExp(string):
    """Escape special regex characters"""
    return re.escape(string)


def translate_question_patterns(text):
    """Handle special question patterns"""
    result = text
    
    # Will X reach Y? → Достигнет ли X Y?
    result = re.sub(r'\bWill\s+(.+?)\s+reach\s+(.+?)\?', r'Достигнет ли \1 \2?', result, flags=re.IGNORECASE)
    
    # Will X happen? → Произойдет ли X?
    result = re.sub(r'\bWill\s+(.+?)\s+happen\b', r'Произойдет ли \1', result, flags=re.IGNORECASE)
    
    # Will X win? → Победит ли X?
    result = re.sub(r'\bWill\s+(.+?)\s+win\b', r'Победит ли \1', result, flags=re.IGNORECASE)
    
    # Will X exceed Y? → Превысит ли X Y?
    result = re.sub(r'\bWill\s+(.+?)\s+exceed\s+(.+?)\?', r'Превысит ли \1 \2?', result, flags=re.IGNORECASE)
    
    # Will X fall below Y? → Упадет ли X ниже Y?
    result = re.sub(r'\bWill\s+(.+?)\s+fall\s+below\s+(.+?)\?', r'Упадет ли \1 ниже \2?', result, flags=re.IGNORECASE)
    
    # Will X rise above Y? → Поднимется ли X выше Y?
    result = re.sub(r'\bWill\s+(.+?)\s+rise\s+above\s+(.+?)\?', r'Поднимется ли \1 выше \2?', result, flags=re.IGNORECASE)
    
    # Fallback: Will X? → Будет ли X?
    def fallback_will(match):
        content = match.group(1)
        if 'ли' in content:  # Already processed
            return match.group(0)
        return f'Будет ли {content}?'
    
    result = re.sub(r'\bWill\s+(.+?)\?', fallback_will, result, flags=re.IGNORECASE)
    
    return result


def translate_event_text(text, is_russian=True):
    """Translate event text with context preservation"""
    if not is_russian or not text:
        return text
    
    translated = text
    
    # Step 1: Preserve patterns (money, dates, numbers)
    patterns_map = {}
    pattern_index = 0
    
    for pattern in PRESERVE_PATTERNS:
        def replace_pattern(match):
            nonlocal pattern_index
            placeholder = f'__PATTERN_{pattern_index}__'
            patterns_map[placeholder] = match.group(0)
            pattern_index += 1
            return placeholder
        
        translated = re.sub(pattern, replace_pattern, translated, flags=re.IGNORECASE)
    
    # Step 2: Preserve terms (names, brands, teams)
    preserved_map = {}
    preserve_index = 0
    
    # Sort by length (longest first)
    sorted_terms = sorted(PRESERVE_TERMS, key=len, reverse=True)
    
    for term in sorted_terms:
        regex = r'\b' + escapeRegExp(term) + r'\b'
        
        def replace_term(match):
            nonlocal preserve_index
            placeholder = f'__PRESERVE_{preserve_index}__'
            preserved_map[placeholder] = match.group(0)
            preserve_index += 1
            return placeholder
        
        translated = re.sub(regex, replace_term, translated, flags=re.IGNORECASE)
    
    # Step 3: Handle question patterns BEFORE dictionary translation
    translated = translate_question_patterns(translated)
    
    # Step 4: Translate by dictionary
    for en, ru in TRANSLATION_DICT.items():
        regex = r'\b' + escapeRegExp(en) + r'\b'
        translated = re.sub(regex, ru, translated, flags=re.IGNORECASE)
    
    # Step 5: Restore preserved terms
    for placeholder, original in preserved_map.items():
        translated = translated.replace(placeholder, original)
    
    # Step 6: Restore preserved patterns
    for placeholder, original in patterns_map.items():
        translated = translated.replace(placeholder, original)
    
    # Step 7: Clean up extra spaces
    translated = re.sub(r'\s+', ' ', translated).strip()
    
    return translated


def test_translation_preserve_names():
    """Test that names are preserved"""
    tests = [
        ("Will Trump win the election?", "Достигнет ли Trump the election?"),
        ("Will Biden announce his decision?", "Объявит ли Biden his decision?"),
        ("Will Putin attend the summit?", "Будет ли Putin attend the summit?"),
    ]
    
    passed = 0
    for en, expected_pattern in tests:
        result = translate_event_text(en)
        # Check that name is preserved
        name = en.split()[1]  # Trump, Biden, Putin
        if name in result:
            passed += 1
            print(f"  [PASS] Name '{name}' preserved")
        else:
            print(f"  [FAIL] Name '{name}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def test_translation_preserve_crypto():
    """Test that cryptocurrency names are preserved"""
    tests = [
        "Will Bitcoin reach $100,000 by December 2024?",
        "Will Ethereum exceed $5,000?",
        "Will Solana fall below $50?",
    ]
    
    passed = 0
    for en in tests:
        result = translate_event_text(en)
        # Extract crypto name
        crypto = en.split()[1]
        if crypto in result:
            passed += 1
            print(f"  [PASS] Crypto '{crypto}' preserved")
        else:
            print(f"  [FAIL] Crypto '{crypto}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def test_translation_preserve_money():
    """Test that money amounts are preserved"""
    tests = [
        ("Will Bitcoin reach $100,000?", "$100,000"),
        ("Will Ethereum reach $10,000 by 2025?", "$10,000"),
        ("Will BTC exceed $50,000?", "$50,000"),
    ]
    
    passed = 0
    for en, money_pattern in tests:
        result = translate_event_text(en)
        if money_pattern in result:
            passed += 1
            print(f"  [PASS] Money '{money_pattern}' preserved")
        else:
            print(f"  [FAIL] Money '{money_pattern}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def test_translation_preserve_dates():
    """Test that dates are preserved"""
    tests = [
        ("Will Trump win by December 2024?", "December 2024"),
        ("Will Bitcoin reach $100K by January 15, 2025?", "January 15, 2025"),
        ("Will Tesla stock rise in Q4 2024?", "Q4 2024"),
    ]
    
    passed = 0
    for en, date_pattern in tests:
        result = translate_event_text(en)
        if date_pattern in result:
            passed += 1
            print(f"  [PASS] Date '{date_pattern}' preserved")
        else:
            print(f"  [FAIL] Date '{date_pattern}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def test_translation_question_patterns():
    """Test that question patterns are translated correctly"""
    tests = [
        ("Will Bitcoin reach $100,000?", "Достигнет ли"),
        ("Will Trump win?", "Победит ли"),
        ("Will Ethereum exceed $5,000?", "Превысит ли"),
        ("Will Solana fall below $50?", "Упадет ли"),
        ("Will Tesla rise above $300?", "Поднимется ли"),
    ]
    
    passed = 0
    for en, expected_ru_pattern in tests:
        result = translate_event_text(en)
        if expected_ru_pattern in result:
            passed += 1
            print(f"  [PASS] Pattern translated correctly")
        else:
            print(f"  [FAIL] Expected '{expected_ru_pattern}' in result. Got: {result}")
    
    return passed == len(tests)


def test_translation_teams():
    """Test that sports teams are preserved"""
    tests = [
        "Will Lakers win the NBA Finals?",
        "Will Manchester United beat Arsenal?",
        "Will Real Madrid win La Liga?",
    ]
    
    passed = 0
    for en in tests:
        result = translate_event_text(en)
        # Extract team name
        words = en.split()
        team = words[1] if len(words) > 1 else ""
        if team in result:
            passed += 1
            print(f"  [PASS] Team '{team}' preserved")
        else:
            print(f"  [FAIL] Team '{team}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def test_translation_companies():
    """Test that company names are preserved"""
    tests = [
        "Will Tesla stock reach $1,000?",
        "Will Apple announce new iPhone?",
        "Will Google launch new AI?",
    ]
    
    passed = 0
    for en in tests:
        result = translate_event_text(en)
        # Extract company name
        company = en.split()[1]
        if company in result:
            passed += 1
            print(f"  [PASS] Company '{company}' preserved")
        else:
            print(f"  [FAIL] Company '{company}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def test_translation_percentages():
    """Test that percentages are preserved"""
    tests = [
        ("Will Bitcoin reach 50% market dominance?", "50%"),
        ("Will Ethereum fall below 20%?", "20%"),
    ]
    
    passed = 0
    for en, pct_pattern in tests:
        result = translate_event_text(en)
        if pct_pattern in result:
            passed += 1
            print(f"  [PASS] Percentage '{pct_pattern}' preserved")
        else:
            print(f"  [FAIL] Percentage '{pct_pattern}' NOT preserved. Result: {result}")
    
    return passed == len(tests)


def main():
    """Run all translation tests"""
    print("=" * 70)
    print("EventPredict Translation Tests")
    print("Testing: Name preservation, money, dates, question patterns")
    print("=" * 70)
    print()
    
    tests = [
        ("Names Preservation", test_translation_preserve_names),
        ("Crypto Names Preservation", test_translation_preserve_crypto),
        ("Money Amounts Preservation", test_translation_preserve_money),
        ("Dates Preservation", test_translation_preserve_dates),
        ("Question Patterns", test_translation_question_patterns),
        ("Sports Teams Preservation", test_translation_teams),
        ("Companies Preservation", test_translation_companies),
        ("Percentages Preservation", test_translation_percentages),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        results.append(test_func())
    
    print()
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} test groups passed")
    
    if passed == total:
        print("[OK] All translation tests passed!")
    else:
        print(f"[WARN] {total - passed} test groups had failures. Check details above.")
    
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
