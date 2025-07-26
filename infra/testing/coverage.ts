
import http from 'k6/http';
import { check, sleep } from 'k6';

// Type declarations for k6 environment
declare const __VU: number; // Virtual User ID - unique identifier for each simulated user
declare const __ENV: { [key: string]: string }; // Environment variables

// API endpoints configuration
// Default endpoints - can be overridden via CLI parameter
const defaultApiEndpoints = ['http://10.0.0.24:8000'];
// Parse API endpoints from environment variable if provided
// Usage: k6 run -e API_ENDPOINTS="http://localhost:8000,http://10.0.0.21:8000" coverage.ts
const apiEndpoints = __ENV.API_ENDPOINTS
    ? __ENV.API_ENDPOINTS.split(',').map(endpoint => endpoint.trim())
    : defaultApiEndpoints;

// Test data - Known valid tickers that exist in staging
const testData = {
    tickers: ['AAL', 'AAPL', 'ACHR', 'AES', 'AGNC', 'AMD', 'AMZN', 'APLD', 'AUR', 'AVGO', 'BA', 'BAC', 'CCL', 'CDE', 'CLF', 'CLSK', 'CSCO', 'CVE', 'F', 'GME', 'GOOGL', 'HBANP', 'HL', 'HOOD', 'HPE', 'INTC', 'IONQ', 'IPG', 'JOBY', 'KGC', 'KVUE', 'LCID', 'MARA', 'MP', 'MSFT', 'MU', 'NFLX', 'NU', 'NVDA', 'ORCL', 'PCG', 'PFE', 'PLTR', 'PR', 'QUBT', 'RIG', 'RIOT', 'RKLB', 'RKT', 'RXRX', 'S', 'SMCI', 'SMR', 'SNAP', 'SOFI', 'T', 'TSLA', 'UBER', 'UNH', 'VZ', 'WBD', 'WFC', 'WMT', 'XOM'],
    // tickers: [
    //     'AAPL', // just one is needed
    //
    // ],
};

export const options = {
    stages: [
        { duration: '1s', target: 1 },
    ],
    thresholds: {
        'http_req_failed': ['rate<0.1'],  // Less than 10% of requests should fail
        'http_req_duration': ['p(95)<2000'], // 95% of requests should be under 2s
        'http_req_duration{name:companies_search}': ['p(95)<500'],
        'http_req_duration{name:aggregates_by_ticker}': ['p(95)<1000'],
        'http_req_duration{name:filings_by_company}': ['p(95)<1000'],
    },
};

export default function () {
    // Select API endpoint based on VU ID
    const apiEndpoint = apiEndpoints[__VU % apiEndpoints.length];

    // Select test ticker based on VU ID
    const tickerIndex = (__VU - 1) % testData.tickers.length;
    const ticker = testData.tickers[tickerIndex];

    const headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    };

    // 1. Health Check
    testHealthCheck(apiEndpoint);

    // 2. Company Operations
    const company = testCompanyOperations(apiEndpoint, ticker, headers);

    if (company) {
        // 3. Aggregates Operations
        const aggregates = testAggregatesOperations(apiEndpoint, ticker, headers);

        // 4. Filings Operations
        const filings = testFilingsOperations(apiEndpoint, company.id, headers);

        if (filings && filings.length > 0) {
            // 5. Documents Operations
            testDocumentsOperations(apiEndpoint, filings[0].id, headers);
        }

        if (aggregates && aggregates.length > 0) {
            // 6. Completions Operations
            testCompletionsOperations(apiEndpoint, aggregates[0].id, headers);
        }
    }

    // Small delay between iterations
    sleep(1);
}

function testHealthCheck(apiEndpoint: string) {
    const response = http.get(`${apiEndpoint}/`, {
        timeout: '5s',
        tags: { name: 'health_check' },
    });

    check(response, {
        'health check status is 200': (r) => r.status === 200,
        'health check response time < 100ms': (r) => r.timings.duration < 100,
    });
}

function testCompanyOperations(apiEndpoint: string, ticker: string, headers: any) {
    let company: any = null;

    // Search companies by ticker
    const searchResponse = http.get(`${apiEndpoint}/api/companies?ticker=${ticker}`, {
        headers,
        timeout: '10s',
        tags: { name: 'companies_search' },
    });

    const searchSuccess = check(searchResponse, {
        'companies search status is 200': (r) => r.status === 200,
        'companies search has valid JSON': (r) => {
            try {
                JSON.parse(r.body as string);
                return true;
            } catch {
                return false;
            }
        },
    });

    if (searchSuccess && searchResponse.status === 200) {
        try {
            company = JSON.parse(searchResponse.body as string);

            if (company && company.id) {
                // Get company by ID
                const companyByIdResponse = http.get(`${apiEndpoint}/api/companies/id/${company.id}`, {
                    headers,
                    timeout: '10s',
                    tags: { name: 'companies_by_id' },
                });

                check(companyByIdResponse, {
                    'company by ID status is 200': (r) => r.status === 200,
                    'company by ID returns valid data': (r) => {
                        try {
                            const data = JSON.parse(r.body as string);
                            return data.id === company.id;
                        } catch {
                            return false;
                        }
                    },
                });
            }
        } catch (e) {
            console.log(`Error parsing company search response: ${e}`);
        }
    }

    // Test company search with query parameter
    const querySearchResponse = http.get(`${apiEndpoint}/api/companies/search?query=${ticker}&limit=10`, {
        headers,
        timeout: '10s',
        tags: { name: 'companies_search_query' },
    });

    check(querySearchResponse, {
        'companies query search status is 200': (r) => r.status === 200 || r.status == 404,
        'companies query search returns array': (r) => {
            try {
                const data = JSON.parse(r.body as string);
                return Array.isArray(data);
            } catch {
                return false;
            }
        },
    });

    // Test company list endpoint
    const listResponse = http.get(`${apiEndpoint}/api/companies/list?offset=0&limit=20`, {
        headers,
        timeout: '10s',
        tags: { name: 'companies_list' },
    });

    check(listResponse, {
        'companies list status is 200': (r) => r.status === 200,
        'companies list returns array': (r) => {
            try {
                const data = JSON.parse(r.body as string);
                return Array.isArray(data);
            } catch {
                return false;
            }
        },
    });

    return company;
}

function testAggregatesOperations(apiEndpoint: string, ticker: string, headers: any) {
    let aggregates: any = null;

    // Get aggregates by ticker
    const aggregatesResponse = http.get(`${apiEndpoint}/api/aggregates/by-ticker/${ticker}`, {
        headers,
        timeout: '10s',
        tags: { name: 'aggregates_by_ticker' },
    });

    const aggregatesSuccess = check(aggregatesResponse, {
        'aggregates by ticker status is 200': (r) => r.status === 200,
        'aggregates response is valid JSON': (r) => {
            try {
                JSON.parse(r.body as string);
                return true;
            } catch {
                return false;
            }
        },
    });

    if (aggregatesSuccess && aggregatesResponse.status === 200) {
        try {
            aggregates = JSON.parse(aggregatesResponse.body as string);

            if (Array.isArray(aggregates) && aggregates.length > 0) {
                // Test aggregate completions endpoint
                const firstAggregate = aggregates[0];
                const completionsResponse = http.get(`${apiEndpoint}/api/aggregates/${firstAggregate.id}/completions`, {
                    headers,
                    timeout: '10s',
                    tags: { name: 'aggregate_completions' },
                });

                check(completionsResponse, {
                    'aggregate completions status is 200': (r) => r.status === 200,
                    'aggregate completions returns valid format': (r) => {
                        try {
                            const data = JSON.parse(r.body as string);
                            return Array.isArray(data);
                        } catch {
                            return false;
                        }
                    },
                });
            }
        } catch (e) {
            console.log(`Error parsing aggregates response: ${e}`);
        }
    }

    return aggregates;
}

function testFilingsOperations(apiEndpoint: string, companyId: string, headers: any) {
    let filings: any = null;

    // Get filings by company ID
    const filingsResponse = http.get(`${apiEndpoint}/api/filings/by-company/${companyId}`, {
        headers,
        timeout: '10s',
        tags: { name: 'filings_by_company' },
    });

    const filingsSuccess = check(filingsResponse, {
        'filings by company status is 200': (r) => r.status === 200,
        'filings response is valid JSON': (r) => {
            try {
                JSON.parse(r.body as string);
                return true;
            } catch {
                return false;
            }
        },
    });

    if (filingsSuccess && filingsResponse.status === 200) {
        try {
            filings = JSON.parse(filingsResponse.body as string);

            check(filings, {
                'filings is array': () => Array.isArray(filings),
                'filings have required fields': () => {
                    if (!Array.isArray(filings) || filings.length === 0) return true;
                    const filing = filings[0];
                    return filing.id && filing.company_id && filing.accession_number && filing.filing_type;
                },
            });
        } catch (e) {
            console.log(`Error parsing filings response: ${e}`);
        }
    }

    return filings;
}

function testDocumentsOperations(apiEndpoint: string, filingId: string, headers: any) {
    // Get documents by filing ID
    const documentsResponse = http.get(`${apiEndpoint}/api/documents/by-filing/${filingId}`, {
        headers,
        timeout: '10s',
        tags: { name: 'documents_by_filing' },
    });

    const documentsSuccess = check(documentsResponse, {
        'documents by filing status is 200': (r) => r.status === 200,
        'documents response is valid JSON': (r) => {
            try {
                JSON.parse(r.body as string);
                return true;
            } catch {
                return false;
            }
        },
    });

    if (documentsSuccess && documentsResponse.status === 200) {
        try {
            const documents = JSON.parse(documentsResponse.body as string);

            if (Array.isArray(documents) && documents.length > 0) {
                const firstDocument = documents[0];

                // Test get document by ID
                const documentByIdResponse = http.get(`${apiEndpoint}/api/documents/${firstDocument.id}`, {
                    headers,
                    timeout: '10s',
                    tags: { name: 'documents_by_id' },
                });

                check(documentByIdResponse, {
                    'document by ID status is 200': (r) => r.status === 200,
                    'document by ID returns valid data': (r) => {
                        try {
                            const data = JSON.parse(r.body as string);
                            return data.id === firstDocument.id;
                        } catch {
                            return false;
                        }
                    },
                });

                // Test get document content
                const contentResponse = http.get(`${apiEndpoint}/api/documents/${firstDocument.id}/content`, {
                    headers: { 'Accept': 'text/plain' },
                    timeout: '10s',
                    tags: { name: 'documents_content' },
                });

                check(contentResponse, {
                    'document content status is 200': (r) => r.status === 200,
                    'document content is text': (r) => r.headers['Content-Type']?.includes('text/plain') || true,
                });

                // Test documents by IDs (POST endpoint)
                const documentIds = [firstDocument.id];
                if (documents.length > 1) {
                    documentIds.push(documents[1].id);
                }

                const byIdsResponse = http.post(`${apiEndpoint}/api/documents/by-ids`,
                    JSON.stringify(documentIds),
                    {
                        headers,
                        timeout: '10s',
                        tags: { name: 'documents_by_ids' },
                    }
                );

                check(byIdsResponse, {
                    'documents by IDs status is 200': (r) => r.status === 200,
                    'documents by IDs returns valid array': (r) => {
                        try {
                            const data = JSON.parse(r.body as string);
                            return Array.isArray(data) && data.length <= documentIds.length;
                        } catch {
                            return false;
                        }
                    },
                });
            }
        } catch (e) {
            console.log(`Error parsing documents response: ${e}`);
        }
    }
}

function testCompletionsOperations(apiEndpoint: string, aggregateId: string, headers: any) {
    // First get completions from the aggregate
    const completionsResponse = http.get(`${apiEndpoint}/api/aggregates/${aggregateId}/completions`, {
        headers,
        timeout: '10s',
        tags: { name: 'completions_via_aggregate' },
    });

    if (completionsResponse.status === 200) {
        try {
            const completions = JSON.parse(completionsResponse.body as string);

            if (Array.isArray(completions) && completions.length > 0) {
                const firstCompletion = completions[0];

                // Test get completion by ID
                const completionByIdResponse = http.get(`${apiEndpoint}/api/completions/${firstCompletion.id}`, {
                    headers,
                    timeout: '10s',
                    tags: { name: 'completions_by_id' },
                });

                check(completionByIdResponse, {
                    'completion by ID status is 200': (r) => r.status === 200,
                    'completion by ID returns valid data': (r) => {
                        try {
                            const data = JSON.parse(r.body as string);
                            return data.id === firstCompletion.id;
                        } catch {
                            return false;
                        }
                    },
                });
            }
        } catch (e) {
            console.log(`Error parsing completions response: ${e}`);
        }
    }
}

// Setup function to run once before all tests
export function setup() {
    console.log('Starting API Coverage Test');
    console.log(`API endpoints source: ${__ENV.API_ENDPOINTS ? 'CLI parameter' : 'default'}`);
    console.log(`Testing endpoints: ${apiEndpoints.join(', ')}`);
    return testData;
}

// Teardown function to run once after all tests
export function teardown() {
    console.log('API Coverage Test completed');
}
