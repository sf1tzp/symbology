import http from 'k6/http';
import { check } from 'k6';

// Type declarations for k6 environment
declare const __VU: number; // Virtual User ID - unique identifier for each simulated user

// Endpoints to test
const endpoints = ['http://10.0.0.21:5173']//  #, 'http://10.0.0.22:5173', 'http://10.0.0.24:5173'];

export const options = {
    stages: [
        { duration: '1m', target: 10 },
        { duration: '1m', target: 20 },
        { duration: '1m', target: 10 },
        { duration: '1m', target: 50 },
        { duration: '1m', target: 30 },
        { duration: '1m', target: 80 },
        { duration: '1m', target: 120 },
        { duration: '1m', target: 30 },
        { duration: '1m', target: 10 },
        { duration: '1m', target: 10 },
        // ramp up, starting at 100, multiplying by 1.6 each time until 2000
        // { duration: '1m', target: 100 },
        // { duration: '1m', target: 160 },
        // { duration: '15s', target: 100 },
        // { duration: '1m', target: 256 },
        // { duration: '15s', target: 100 },
        // { duration: '1m', target: 410 },
        // { duration: '15s', target: 300 },
        // { duration: '1m', target: 656 },
        // { duration: '15s', target: 400 },
        // { duration: '1m', target: 1050 },
        // { duration: '15s', target: 500 },
        // { duration: '1m', target: 1680 },
        // { duration: '15s', target: 800 },
        // { duration: '1m', target: 2000 },
        // { duration: '1m', target: 100 },
    ],
    thresholds: {
        'http_req_failed': ['rate<0.2'],
        'http_req_duration': ['p(95)<1000'],
    },
};

export default function () {
    // Alternate between endpoints based on VU ID
    const endpoint = endpoints[__VU % endpoints.length];

    // Step 1: Load the homepage (UI)
    const homepageResponse = http.get(`${endpoint}/`, {
        timeout: '10s',
    });

    // Step 2: Simulate the async API calls that the homepage makes
    const apiEndpoint = endpoint.replace(':5173', ':8000'); // Assuming API is on port 8000

    // Common API calls that your UI likely makes:
    // 1. Search companies (autocomplete/initial load)
    const searchResponse = http.get(`${apiEndpoint}/api/companies/?ticker=AAPL`, {
        timeout: '10s',
        headers: {
            'Accept': 'application/json',
        },
    });

    // 2. Get all companies (if your UI loads a list)
    const companiesResponse = http.get(`${apiEndpoint}/api/companies/list?offset=0&limit=50`, {
        timeout: '10s',
        headers: {
            'Accept': 'application/json',
        },
    });

    // For this test, we'll track both UI and API response times
    const responses = [homepageResponse, searchResponse, companiesResponse];

    // Use the slowest response as our main metric (realistic user experience)
    const response = responses.reduce((slowest, current) =>
        current.timings.duration > slowest.timings.duration ? current : slowest
    );

    // Check if the request was successful
    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    });
}

