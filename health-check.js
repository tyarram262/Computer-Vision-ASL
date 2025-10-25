#!/usr/bin/env node

/**
 * Health Check Script for ASL Form Correction App
 * Verifies that all components are working correctly
 */

const fs = require('fs');
const path = require('path');
const http = require('http');

// Colors for console output
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

function checkFile(filePath, description) {
    const exists = fs.existsSync(filePath);
    const status = exists ? '✅' : '❌';
    const color = exists ? 'green' : 'red';
    log(`${status} ${description}: ${filePath}`, color);
    return exists;
}

function checkDirectory(dirPath, description) {
    const exists = fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory();
    const status = exists ? '✅' : '❌';
    const color = exists ? 'green' : 'red';
    log(`${status} ${description}: ${dirPath}`, color);
    return exists;
}

function checkUrl(url, description) {
    return new Promise((resolve) => {
        const request = http.get(url, (res) => {
            const status = res.statusCode === 200 ? '✅' : '❌';
            const color = res.statusCode === 200 ? 'green' : 'red';
            log(`${status} ${description}: ${url} (${res.statusCode})`, color);
            resolve(res.statusCode === 200);
        });

        request.on('error', () => {
            log(`❌ ${description}: ${url} (Connection failed)`, 'red');
            resolve(false);
        });

        request.setTimeout(5000, () => {
            request.destroy();
            log(`❌ ${description}: ${url} (Timeout)`, 'red');
            resolve(false);
        });
    });
}

async function runHealthCheck() {
    log('\n🏥 ASL Form Correction App - Health Check', 'cyan');
    log('==========================================', 'cyan');

    let allGood = true;

    // Check core files
    log('\n📁 Core Files:', 'blue');
    allGood &= checkFile('package.json', 'Package configuration');
    allGood &= checkFile('src/App.js', 'Main React component');
    allGood &= checkFile('src/utils/matcher.js', 'Analysis engine');
    allGood &= checkFile('backend/app.py', 'Flask backend');
    allGood &= checkFile('backend/requirements.txt', 'Python dependencies');

    // Check ML model
    log('\n🤖 Machine Learning:', 'blue');
    allGood &= checkFile('backend/asl_cnn_augmented.keras', 'Trained CNN model');
    allGood &= checkFile('tidalhack_\'25.py', 'Training script');

    // Check components
    log('\n🧩 React Components:', 'blue');
    allGood &= checkFile('src/components/SignPrompt.jsx', 'Sign display component');
    allGood &= checkFile('src/components/WebcamField.jsx', 'Camera component');
    allGood &= checkFile('src/components/MatchGauge.jsx', 'Score display');
    allGood &= checkFile('src/components/FeedbackPanel.js', 'AI feedback panel');
    allGood &= checkFile('src/components/SignGallery.js', 'Sign gallery');
    allGood &= checkFile('src/components/ConfigStatus.js', 'Status indicator');

    // Check services
    log('\n🔧 Services:', 'blue');
    allGood &= checkFile('src/services/mlModelService.js', 'ML model service');
    allGood &= checkFile('src/services/bedrockService.js', 'AWS Bedrock service');

    // Check assets
    log('\n🎨 Visual Assets:', 'blue');
    allGood &= checkDirectory('public/assets/sign-examples', 'Sign example images');
    allGood &= checkFile('public/assets/sign-examples/hello.svg', 'Hello sign example');
    allGood &= checkFile('public/assets/sign-examples/thankyou.svg', 'Thank you sign example');
    allGood &= checkFile('public/assets/sign-examples/yes.svg', 'Yes sign example');
    allGood &= checkFile('public/assets/sign-examples/no.svg', 'No sign example');

    // Check dependencies
    log('\n📦 Dependencies:', 'blue');
    allGood &= checkDirectory('node_modules', 'Node.js dependencies');

    // Check if servers are running
    log('\n🌐 Server Status:', 'blue');
    const backendRunning = await checkUrl('http://localhost:5000/health', 'ML Backend API');
    const frontendRunning = await checkUrl('http://localhost:3000', 'React Frontend');

    // Summary
    log('\n📊 Health Check Summary:', 'magenta');
    log('========================', 'magenta');

    if (allGood) {
        log('✅ All core files are present', 'green');
    } else {
        log('❌ Some core files are missing', 'red');
    }

    if (backendRunning) {
        log('✅ ML Backend is running', 'green');
    } else {
        log('❌ ML Backend is not running (start with: npm run ml-server)', 'yellow');
    }

    if (frontendRunning) {
        log('✅ React Frontend is running', 'green');
    } else {
        log('❌ React Frontend is not running (start with: npm run start:ml)', 'yellow');
    }

    // Recommendations
    log('\n💡 Recommendations:', 'cyan');
    if (!allGood) {
        log('• Run: npm install (to install dependencies)', 'yellow');
        log('• Check file paths and ensure all files are present', 'yellow');
    }

    if (!backendRunning && !frontendRunning) {
        log('• Run: ./start.sh (to start both servers)', 'yellow');
    } else if (!backendRunning) {
        log('• Run: npm run ml-server (to start ML backend)', 'yellow');
    } else if (!frontendRunning) {
        log('• Run: npm run start:ml (to start React frontend)', 'yellow');
    }

    if (allGood && backendRunning && frontendRunning) {
        log('🎉 Everything looks great! Your app is ready to use.', 'green');
        log('🌐 Open http://localhost:3000 in your browser', 'green');
    }

    log('');
}

// Run the health check
runHealthCheck().catch(console.error);