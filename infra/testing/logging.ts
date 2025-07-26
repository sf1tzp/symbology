import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('logging_errors');

// Test configuration
export const options = {
    stages: [
        { duration: '5m', target: 2 },   // Ramp up to 5 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
        logging_errors: ['rate<0.01'],    // Error rate should be below 1%
        http_req_failed: ['rate<0.01'],   // HTTP failure rate should be below 1%
    },
};

// Base URL for the API
const BASE_URL = 'http://10.0.0.21:8000';

// Sample log data that mimics the frontend logger
const sampleLogData = [
    {
        level: 'info',
        component: "test",
        event: "test_info",
        user_agent: 'grafana_k6',
    },
    {
        level: 'warn',
        component: "test",
        event: "test_warn",
        user_agent: 'grafana_k6',
    },
    {
        level: 'error',
        component: "test",
        event: "test_error",
        user_agent: 'grafana_k6',
    },
];

export default function () {
    // Pick a random log entry to simulate real usage patterns
    const logData = sampleLogData[Math.floor(Math.random() * sampleLogData.length)];

    // Add current timestamp
    const payload = {
        ...logData,
        timestamp: new Date().toISOString(),
    };

    // Send the log request
    const response = http.post(
        `${BASE_URL}/api/logs/log`,
        JSON.stringify(payload),
        {
            headers: {
                'Content-Type': 'application/json',
            },
        }
    );

    // Validate the response
    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'response has logged status': (r) => {
            try {
                const body = JSON.parse(r.body as string);
                return body.status === 'logged';
            } catch {
                return false;
            }
        },
        'response time < 200ms': (r) => r.timings.duration < 200,
        'content type is JSON': (r) => r.headers['Content-Type']?.includes('application/json'),
    });

    // Track error rate
    errorRate.add(!success);

    const searchResponse = http.get(`${BASE_URL}/api/companies/?ticker=AAPL`, {
        timeout: '10s',
        headers: {
            'Accept': 'application/json',
        },
    });

    // Simulate realistic timing between log events
    sleep(Math.random() * 2 + 0.5); // Sleep between 0.5-2.5 seconds
}

// Setup function to verify the endpoint is available
export function setup() {
    console.log('Testing logging endpoint availability...');

    const testPayload = {
        timestamp: new Date().toISOString(),
        level: 'info',
        user_agent: 'grafana_k6',
        event: "test_setup",
        component: "test",
    };

    const response = http.post(
        `${BASE_URL}/api/logs/log`,
        JSON.stringify(testPayload),
        {
            headers: {
                'Content-Type': 'application/json',
            },
        }
    );

    if (response.status !== 200) {
        throw new Error(`Logging endpoint not available. Status: ${response.status}`);
    }

    console.log('✅ Logging endpoint is available and responding correctly');
    return { baseUrl: BASE_URL };

}

// Teardown function for cleanup
export function teardown(data: any) {
    console.log('✅ Logging endpoint test completed');
    console.log(`Base URL tested: ${data.baseUrl}`);
}
