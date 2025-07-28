import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';

export const options = {
    executor: 'ramping-arrival-rate',
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
                abortOnFail: false, // boolean
                delayAbortEval: '10s', // string
            },
        ],
        'http_req_duration': [
            {
                threshold: 'p(99) < 1000', // string
                abortOnFail: false, // boolean
                delayAbortEval: '10s', // string
            },
        ]
    },
};

export default function () {
    // Walk through the main ui flow
    const homepageResponse = http.get('https://symbology.online');


    const apiEndpoint = "https://api.symbology.online";

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

    const apiEndpoint = "https://api.symbology.online";

    const response = http.post(
        `${apiEndpoint}/api/logs/log`,
        JSON.stringify(testPayload),
        {
            headers: {
                'Content-Type': 'application/json',
            },
        }
    );


    console.log('✅ Logging endpoint is available and responding correctly');
    return { baseUrl: 'https://${apiEndpoint}' };

}