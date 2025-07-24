import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Type declarations for k6 environment
declare const __VU: number;
declare const __ITER: number;
declare const __ENV: Record<string, string>;

// Custom metrics
const uiMetrics = new Trend('ui_response_time');
const apiMetrics = new Trend('api_response_time');
const overallSuccess = new Rate('overall_success_rate');

// Endpoints
const uiEndpoints = ['http://10.0.0.21:5173', 'http://10.0.0.22:5173'];
const apiEndpoints = ['http://10.0.0.21:8000', 'http://10.0.0.22:8000'];

export const options = {
    stages: [
        { duration: '2m', target: 25 },   // Warm up
        { duration: '5m', target: 100 },  // Normal load
        { duration: '2m', target: 500 },  // Peak load
        { duration: '30s', target: 25 },    // Cool down
    ],
    thresholds: {
        'ui_response_time': ['p(95)<500'],
        'api_response_time': ['p(95)<1000'],
        'overall_success_rate': ['rate>0.95'],
    },
};

export default function () {
    const uiEndpoint = uiEndpoints[__VU % uiEndpoints.length];
    const apiEndpoint = apiEndpoints[__VU % apiEndpoints.length];

    // Simulate realistic user behavior:
    // 1. User loads the page
    const homepageResponse = http.get(uiEndpoint, { timeout: '10s' });
    uiMetrics.add(homepageResponse.timings.duration);

    // 2. Small delay while user sees the page
    sleep(0.5);

    // 3. User performs search (most common action)
    const searchQueries = ['apple', 'microsoft', 'tesla', 'google', 'amazon'];
    const query = searchQueries[__ITER % searchQueries.length];

    const searchResponse = http.get(
        `${apiEndpoint}/api/companies/search?query=${query}&limit=10`,
        {
            timeout: '10s',
            headers: { 'Accept': 'application/json' },
        }
    );
    apiMetrics.add(searchResponse.timings.duration);

    // 4. 30% chance user does additional action
    if (Math.random() < 0.3) {
        sleep(1); // User thinks

        const additionalResponse = http.get(
            `${apiEndpoint}/api/companies?limit=20`,
            {
                timeout: '10s',
                headers: { 'Accept': 'application/json' },
            }
        );
        apiMetrics.add(additionalResponse.timings.duration);
    }

    // Check overall success
    const allSuccessful = check({
        ui: homepageResponse,
        search: searchResponse,
    }, {
        'UI loads successfully': (responses) => responses.ui.status === 200,
        'Search works': (responses) => responses.search.status === 200,
        'UI responds quickly': (responses) => responses.ui.timings.duration < 500,
        'API responds reasonably': (responses) => responses.search.timings.duration < 1000,
    });

    overallSuccess.add(allSuccessful);

    // Realistic pause between user actions
    sleep(Math.random() * 2 + 1); // 1-3 second pause
}

export function handleSummary(data: any) {
    console.log('\n=== MIXED WORKLOAD TEST SUMMARY ===');
    console.log('UI Performance:', {
        'Avg Response Time': `${data.metrics.ui_response_time.avg.toFixed(2)}ms`,
        'P95 Response Time': `${data.metrics.ui_response_time.p95.toFixed(2)}ms`,
    });
    console.log('API Performance:', {
        'Avg Response Time': `${data.metrics.api_response_time.avg.toFixed(2)}ms`,
        'P95 Response Time': `${data.metrics.api_response_time.p95.toFixed(2)}ms`,
    });
    console.log('Overall Success Rate:', `${(data.metrics.overall_success_rate.rate * 100).toFixed(2)}%`);
}
