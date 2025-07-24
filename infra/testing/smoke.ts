import http from 'k6/http';
import { sleep, check } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Type declarations for k6 environment
declare const __VU: number; // Virtual User ID - unique identifier for each simulated user
declare const __ITER: number; // Current iteration number for this VU
declare const __ENV: Record<string, string>;

// Custom metrics
const httpFailures = new Counter('http_failures');
const httpResponseTime = new Trend('http_response_time');
const httpSuccessRate = new Rate('http_success_rate');

// Stage-specific metrics for tracking degradation points
const stageMetrics = new Map();
let currentStage = 0;
const stageTargets = [500, 1000, 2000, 2500, 3000, 5000];

// Track test start time and stage transitions
let testStartTime = Date.now();
let lastStageTime = testStartTime;

// Endpoints to test
const endpoints = ['http://10.0.0.21:5173', 'http://10.0.0.22:5173'];
const endpointMetrics = new Map();

export const options = {
    stages: [
        // Round 4: 200 requests per second for 1 minute
        { duration: '1m', target: 500 },
        { duration: '10s', target: 0 }, // Cool down
        //
        // Round 5: 400 requests per second for 1 minute
        { duration: '1m', target: 1000 },
        { duration: '10s', target: 0 }, // Cool down

        // Round 6: 800 requests per second for 1 minute
        { duration: '1m', target: 2000 },
        { duration: '10s', target: 0 }, // Cool down

        // Round 7: 1,600 requests per second for 1 minute
        { duration: '1m', target: 2500 },
        { duration: '10s', target: 0 }, // Cool down

        // Round 8: 3,200 requests per second for 1 minute
        { duration: '1m', target: 3000 },
        { duration: '10s', target: 0 }, // Cool down

        // Round 9: 6,400 requests per second for 1 minute
        { duration: '1m', target: 5000 },
        { duration: '10s', target: 0 }, // Cool down
    ],
    thresholds: {
        // Fail the test if more than 5% of requests fail
        'http_req_failed': ['rate<0.05'],
        // Fail if 95th percentile response time exceeds 500ms
        'http_req_duration': ['p(95)<500'],
        // Custom threshold for our success rate metric
        'http_success_rate': ['rate>0.95'],
    },
};

export default function () {
    // Alternate between endpoints based on VU ID
    const endpoint = endpoints[__VU % endpoints.length];

    // Step 1: Load the homepage (UI)
    const homepageResponse = http.get(endpoint, {
        timeout: '10s',
    });

    // Step 2: Simulate the async API calls that the homepage makes
    const apiEndpoint = endpoint.replace(':5173', ':8000'); // Assuming API is on port 8000

    // Common API calls that your UI likely makes:
    // 1. Search companies (autocomplete/initial load)
    const searchResponse = http.get(`${apiEndpoint}/api/companies/search?query=apple&limit=10`, {
        timeout: '10s',
        headers: {
            'Accept': 'application/json',
        },
    });

    // 2. Get all companies (if your UI loads a list)
    const companiesResponse = http.get(`${apiEndpoint}/api/companies?limit=20`, {
        timeout: '10s',
        headers: {
            'Accept': 'application/json',
        },
    });

    // For this test, we'll track both UI and API response times
    const responses = [homepageResponse, searchResponse, companiesResponse];
    const totalDuration = responses.reduce((sum, r) => sum + r.timings.duration, 0);

    // Use the slowest response as our main metric (realistic user experience)
    const response = responses.reduce((slowest, current) =>
        current.timings.duration > slowest.timings.duration ? current : slowest
    );    // Determine current stage based on VU count (approximate)
    const estimatedStage = Math.floor(__VU / 10) < stageTargets.length ?
        Math.floor(__VU / 10) : stageTargets.length - 1;
    const stageTarget = stageTargets[estimatedStage] || 'unknown';

    // Initialize stage metrics if not exists
    if (!stageMetrics.has(stageTarget)) {
        stageMetrics.set(stageTarget, {
            requests: 0,
            failures: 0,
            responseTimes: [],
            slowRequests: 0
        });
    }

    // Initialize endpoint metrics if not exists
    if (!endpointMetrics.has(endpoint)) {
        endpointMetrics.set(endpoint, {
            requests: 0,
            failures: 0,
            responseTimes: [],
            slowRequests: 0
        });
    }

    const stage = stageMetrics.get(stageTarget);
    const endpointStats = endpointMetrics.get(endpoint);

    stage.requests++;
    stage.responseTimes.push(response.timings.duration);
    endpointStats.requests++;
    endpointStats.responseTimes.push(response.timings.duration);

    // Record custom metrics
    httpResponseTime.add(response.timings.duration);

    // Check if the request was successful
    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    });

    // Track stage-specific metrics
    if (!success) {
        stage.failures++;
        endpointStats.failures++;
    }
    if (response.timings.duration >= 500) {
        stage.slowRequests++;
        endpointStats.slowRequests++;
    }

    // Track success rate
    httpSuccessRate.add(success);

    // Count failures
    if (!success) {
        httpFailures.add(1);
    }

    // Log round information based on current VU and iteration
    // if (__ITER % 10000 === 0) { // Log every 10000th iteration to avoid spam
    //     console.log(`VU ${__VU}, Iteration ${__ITER} - Stage: ${stageTarget} - Status: ${response.status}, Duration: ${response.timings.duration.toFixed(2)}ms`);
    // }
}

export function handleSummary(data: any) {
    // Helper function to safely access nested properties
    const safeGet = (obj: any, path: string, defaultValue: any = 0) => {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : defaultValue;
        }, obj);
    };

    const summary = {
        'Summary Report': {
            'Total Requests': safeGet(data, 'metrics.http_reqs.values.count', 0),
            'Failed Requests': safeGet(data, 'metrics.http_req_failed.values.count', 0),
            'Success Rate': `${((1 - safeGet(data, 'metrics.http_req_failed.values.rate', 0)) * 100).toFixed(2)}%`,
            'Avg Response Time': `${safeGet(data, 'metrics.http_req_duration.values.avg', 0).toFixed(2)}ms`,
            'P95 Response Time': `${safeGet(data, 'metrics.http_req_duration.values.p(95)', 0).toFixed(2)}ms`,
            'Max Response Time': `${safeGet(data, 'metrics.http_req_duration.values.max', 0).toFixed(2)}ms`,
        }
    };

    // Debug: Log the data structure to understand what we're working with
    console.log('\n=== DEBUG: Available metrics ===');
    console.log('Keys in data.metrics:', Object.keys(data.metrics || {}));
    if (data.metrics?.http_req_duration) {
        console.log('http_req_duration keys:', Object.keys(data.metrics.http_req_duration));
    }

    // Analyze stage-specific performance degradation
    let firstFailureStage = null;
    let firstSlowStage = null;
    const stageAnalysis: any = {};

    console.log('\n=== DEBUG: Stage metrics ===');
    console.log('Stage metrics size:', stageMetrics.size);
    console.log('Stage metrics keys:', Array.from(stageMetrics.keys()));

    for (const [target, metrics] of stageMetrics.entries()) {
        if (metrics.requests > 0) {
            const failureRate = metrics.failures / metrics.requests;
            const avgResponseTime = metrics.responseTimes.reduce((a: number, b: number) => a + b, 0) / metrics.responseTimes.length;
            const slowRequestRate = metrics.slowRequests / metrics.requests;

            stageAnalysis[`${target} r/s`] = {
                'Total Requests': metrics.requests,
                'Failure Rate': `${(failureRate * 100).toFixed(2)}%`,
                'Avg Response Time': `${avgResponseTime.toFixed(2)}ms`,
                'Slow Request Rate (>500ms)': `${(slowRequestRate * 100).toFixed(2)}%`
            };

            // Track first degradation points
            if (!firstFailureStage && failureRate > 0.05) {
                firstFailureStage = target;
            }
            if (!firstSlowStage && slowRequestRate > 0.05) {
                firstSlowStage = target;
            }
        }
    }

    // Analyze endpoint-specific performance
    const endpointAnalysis: any = {};
    console.log('\n=== DEBUG: Endpoint metrics ===');
    console.log('Endpoint metrics size:', endpointMetrics.size);
    console.log('Endpoint metrics keys:', Array.from(endpointMetrics.keys()));

    for (const [endpoint, metrics] of endpointMetrics.entries()) {
        if (metrics.requests > 0) {
            const failureRate = metrics.failures / metrics.requests;
            const avgResponseTime = metrics.responseTimes.reduce((a: number, b: number) => a + b, 0) / metrics.responseTimes.length;
            const slowRequestRate = metrics.slowRequests / metrics.requests;

            endpointAnalysis[endpoint] = {
                'Total Requests': metrics.requests,
                'Failure Rate': `${(failureRate * 100).toFixed(2)}%`,
                'Avg Response Time': `${avgResponseTime.toFixed(2)}ms`,
                'Slow Request Rate (>500ms)': `${(slowRequestRate * 100).toFixed(2)}%`
            };
        }
    }

    const degradationAnalysis = {
        'First Failure Threshold Breach': firstFailureStage ? `${firstFailureStage} r/s` : 'None detected',
        'First Performance Degradation': firstSlowStage ? `${firstSlowStage} r/s` : 'None detected'
    };

    console.log('\n=== PROGRESSIVE LOAD TEST SUMMARY ===');
    console.log(JSON.stringify(summary, null, 2));
    console.log('\n=== DEGRADATION ANALYSIS ===');
    console.log(JSON.stringify(degradationAnalysis, null, 2));
    console.log('\n=== ENDPOINT COMPARISON ===');
    console.log(JSON.stringify(endpointAnalysis, null, 2));
    console.log('\n=== STAGE-BY-STAGE BREAKDOWN ===');
    console.log(JSON.stringify(stageAnalysis, null, 2));

    return {
        'stdout': JSON.stringify({
            summary,
            degradationAnalysis,
            endpointAnalysis,
            stageAnalysis
        }, null, 2),
    };
}