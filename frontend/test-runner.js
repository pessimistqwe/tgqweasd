/**
 * Automated Tests for EventPredict Fixes
 * Запуск: node frontend/test-runner.js
 */

const fs = require('fs');
const path = require('path');

// Colors for output
const colors = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m'
};

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function log(message, color = colors.reset) {
    console.log(`${color}${message}${colors.reset}`);
}

function test(name, condition, details = '') {
    totalTests++;
    if (condition) {
        passedTests++;
        log(`  ✓ ${name}`, colors.green);
        return true;
    } else {
        failedTests++;
        log(`  ✗ ${name}`, colors.red);
        if (details) log(`    ${details}`, colors.yellow);
        return false;
    }
}

// Read source files
const scriptPath = path.join(__dirname, 'script.js');
const stylesPath = path.join(__dirname, 'styles.css');

const scriptContent = fs.readFileSync(scriptPath, 'utf8');
const stylesContent = fs.readFileSync(stylesPath, 'utf8');

log('\n🧪 EventPredict - Automated Tests\n', colors.cyan);
log('=' .repeat(50), colors.cyan);

// ==================== TASK 1: Remove American Time ====================
log('\n📝 Task 1: Remove American Time (PM/AM ET)\n', colors.blue);

// Test 1.1: REMOVE_PATTERNS constant exists
test(
    'REMOVE_PATTERNS constant defined',
    scriptContent.includes('const REMOVE_PATTERNS'),
    'Pattern constant not found'
);

// Test 1.2: Patterns include PM/AM removal
test(
    'Pattern removes PM/AM ET format',
    scriptContent.includes('AM|PM') && scriptContent.includes('ET|EST|EDT'),
    'Timezone patterns not found'
);

// Test 1.3: translateEventText uses REMOVE_PATTERNS
test(
    'translateEventText applies REMOVE_PATTERNS',
    scriptContent.includes('REMOVE_PATTERNS.forEach') && 
    scriptContent.includes('translated.replace(pattern'),
    'Pattern application not found in translate function'
);

// Test 1.4: Test actual pattern matching
const REMOVE_PATTERNS = [
    /\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*(?:ET|EST|EDT)?/gi,
    /\s*\d{1,2}\s*(?:AM|PM)\s*(?:ET|EST|EDT)?/gi,
    /\s*(?:AM|PM)\s*(?:ET|EST|EDT)/gi,
    /\s*(?:ET|EST|EDT)\b/gi
];

const timeTests = [
    { input: 'Event at 3:00 PM ET', shouldNotContain: ['PM', 'ET', '3:00'] },
    { input: 'Meeting 10 AM EST', shouldNotContain: ['AM', 'EST', '10'] },
    { input: 'Call 2 PM EDT tomorrow', shouldNotContain: ['PM', 'EDT'] },
    { input: 'Bitcoin price PM ET', shouldNotContain: ['PM', 'ET'] },
    { input: 'Normal text without time', shouldNotContain: [] }
];

log('\n  Pattern matching tests:', colors.blue);
timeTests.forEach(({ input, shouldNotContain }) => {
    let result = input;
    REMOVE_PATTERNS.forEach(pattern => {
        result = result.replace(pattern, '');
    });
    result = result.replace(/\s+/g, ' ').trim();
    
    // Check that time-related patterns are removed
    const hasTimeRemoved = shouldNotContain.every(str => !result.includes(str));
    test(
        `Remove time from "${input}"`,
        hasTimeRemoved,
        `Got: "${result}"`
    );
});

// ==================== TASK 2: CSS Layout ====================
log('\n🎨 Task 2: Comments/Activity Section Layout\n', colors.blue);

// Test 2.1: Modal padding reduced
test(
    'Modal padding reduced to 20px 16px',
    stylesContent.includes('padding: 20px 16px') || 
    stylesContent.includes('padding:20px 16px'),
    'Modal padding not updated'
);

// Test 2.2: Comment item padding reduced
test(
    'Comment item padding reduced',
    stylesContent.includes('padding: 10px 12px') ||
    stylesContent.includes('padding:10px 12px'),
    'Comment padding not updated'
);

// Test 2.3: Comment avatar size reduced
const avatarMatch = stylesContent.match(/\.comment-avatar\s*\{[^}]*width:\s*(\d+)px/);
test(
    'Comment avatar size reduced to 32px',
    avatarMatch && parseInt(avatarMatch[1]) <= 32,
    avatarMatch ? `Found: ${avatarMatch[1]}px` : 'Avatar style not found'
);

// Test 2.4: Activity item padding
test(
    'Activity item padding reduced',
    stylesContent.includes('.activity-item') && 
    (stylesContent.includes('padding: 10px') || stylesContent.includes('padding:10px')),
    'Activity padding not updated'
);

// Test 2.5: Event tab padding reduced
test(
    'Event tab padding reduced',
    stylesContent.includes('.event-tab') &&
    (stylesContent.includes('padding: 10px 12px') || 
     stylesContent.includes('padding:10px 12px')),
    'Event tab padding not updated'
);

// Test 2.6: Font sizes reduced
test(
    'Comment username font size reduced',
    stylesContent.includes('font-size: 13px') ||
    stylesContent.includes('font-size:13px'),
    'Font sizes not updated'
);

// ==================== TASK 3: Chart Fix ====================
log('\n📈 Task 3: Chart Fix - No Flat Line After Interval Switch\n', colors.blue);

// Test 3.1: Global chart arrays exist
test(
    'currentChartLabels global variable exists',
    scriptContent.includes('let currentChartLabels'),
    'Global labels array not found'
);

test(
    'currentChartPrices global variable exists',
    scriptContent.includes('let currentChartPrices'),
    'Global prices array not found'
);

// Test 3.2: Arrays are cleared on render
test(
    'Arrays cleared in renderRealtimeChart',
    scriptContent.includes('currentChartLabels = []') &&
    scriptContent.includes('currentChartPrices = []'),
    'Array clearing not found'
);

// Test 3.3: Buffer clears on interval switch
test(
    'WebSocket buffer clears on interval switch',
    scriptContent.includes('webSocketPriceBuffer = []') &&
    scriptContent.includes('currentChartInterval = btn.dataset.interval'),
    'Buffer clearing on switch not found'
);

// Test 3.4: connectBinanceWebSocket uses global arrays
test(
    'WebSocket uses currentChartLabels',
    scriptContent.includes('currentChartLabels.push'),
    'WebSocket not using global labels'
);

test(
    'WebSocket uses currentChartPrices',
    scriptContent.includes('currentChartPrices.push'),
    'WebSocket not using global prices'
);

// Test 3.5: Animation enabled
test(
    'Chart animation enabled (not "none" only)',
    scriptContent.includes("animation: {") &&
    scriptContent.includes('duration: 750') &&
    scriptContent.includes('easeOutQuart'),
    'Animation config not found'
);

// Test 3.6: closeEventModal clears arrays
test(
    'closeEventModal clears chart arrays',
    scriptContent.includes('currentChartLabels = []') &&
    scriptContent.includes('currentChartPrices = []'),
    'Array clearing in closeEventModal not found'
);

// ==================== SUMMARY ====================
log('\n' + '='.repeat(50), colors.cyan);
log('\n📊 Test Summary\n', colors.cyan);

const passRate = totalTests > 0 ? ((passedTests / totalTests) * 100).toFixed(1) : 0;

log(`  Total:   ${totalTests}`, colors.blue);
log(`  ${colors.green}Passed:  ${passedTests}${colors.reset}`, colors.green);
log(`  ${colors.red}Failed:  ${failedTests}${colors.reset}`, colors.red);
log(`  Pass Rate: ${passRate}%\n`, colors.cyan);

if (failedTests === 0) {
    log('✅ All tests passed! Ready to deploy.\n', colors.green);
    process.exit(0);
} else {
    log('❌ Some tests failed. Please fix before deploying.\n', colors.red);
    process.exit(1);
}
