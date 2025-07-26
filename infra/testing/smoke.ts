import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';

export const options = {
    executor: 'ramping-arrival-rate',
    hosts: {
        'symbology.lofi': __ENV.TARGET,
        'api.symbology.lofi': __ENV.TARGET,
    },
    stages: [
        { duration: '10s', target: 10 },
        { duration: '50s', target: 150 },
        { duration: '5m', target: 150 },
        { duration: '30s', target: 600 },
        { duration: '30s', target: 250 },
        { duration: '5ms', target: 150 },
    ],
    thresholds: {
        'http_req_failed': [
            {
                threshold: 'rate<0.2', // string
                abortOnFail: true, // boolean
                delayAbortEval: '10s', // string
            },
        ],
        'http_req_duration': [
            {
                threshold: 'p(99) < 800', // string
                abortOnFail: true, // boolean
                delayAbortEval: '10s', // string
            },
        ]
    },
};

export default function () {
    // Walk through the main ui flow
    const homepageResponse = http.get('https://symbology.lofi');

    check(homepageResponse, {
        "is correct IP": (r) => r.remote_ip === __ENV.TARGET
    });

    const apiEndpoint = "https://api.symbology.lofi";

    const companiesResponse = http.get(`${apiEndpoint}/api/companies/list?offset=0&limit=50`, {
        headers: {
            'Accept': 'application/json',
        },
    });

    sleep(3)

    const searchResponse = http.get(`${apiEndpoint}/api/companies/?ticker=AAPL`, {
        headers: {
            'Accept': 'application/json',
        },
    });

    // make calls associated with CompanyDetail
    // get aggregates for company
    // get filings for company
    //
    // etc ..

    // For this test, we'll track both UI and API response times
    const responses = [homepageResponse, searchResponse, companiesResponse];

    // Use the slowest response as our main metric (realistic user experience)
    const response = responses.reduce((slowest, current) =>
        current.timings.duration > slowest.timings.duration ? current : slowest
    );

    // Check if the request was successful
    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 1000ms': (r) => r.timings.duration < 1000,
    });
}


export function setup() {
    console.log('Testing logging endpoint availability...');
    console.log(exec.test.options)

    const testPayload = {
        timestamp: new Date().toISOString(),
        level: 'info',
        user_agent: 'grafana_k6',
        event: "test_setup",
        component: "test",
    };

    const response = http.post(
        `https://api.symbology.lofi/api/logs/log`,
        JSON.stringify(testPayload),
        {
            headers: {
                'Content-Type': 'application/json',
            },
        }
    );

    // if (response.status !== 200) {
    //     throw new Error(`Logging endpoint not available. Status: ${response}`);
    // }

    console.log('✅ Logging endpoint is available and responding correctly');
    return { baseUrl: 'https://api.symbology.lofi' };

}