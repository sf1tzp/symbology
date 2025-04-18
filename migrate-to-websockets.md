# Migrating to WebSockets for Real-time Ingestion Status

## Current Implementation

Currently, the Symbology application uses a synchronous API pattern for company data ingestion:

1. User searches for a company by ticker
2. If the company is not found, the API endpoint triggers ingestion
3. The API request remains open while ingestion completes
4. Frontend uses timeouts to guess when ingestion is happening based on request duration

This approach has several limitations:
- Long-running HTTP requests can time out
- Users receive no real-time feedback on ingestion progress
- The UI has to guess what's happening using arbitrary timeouts
- No visibility into how many filings have been processed

## Benefits of WebSockets

Implementing WebSockets would provide:

1. **Real-time feedback** - Push notifications as each step completes
2. **Progress indicators** - Show actual percentage completion
3. **Improved UX** - Keep users informed about what's happening
4. **Resilience** - Better handling of timeouts and disconnections
5. **Scalability** - Offload long-running processes from API servers

## Implementation Plan

### 1. Backend Changes

#### 1.1 WebSocket Server Integration

```python
# FastAPI WebSocket integration
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from uuid import uuid4
import asyncio

app = FastAPI()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_update(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

#### 1.2 Ingestion Status Tracking

```python
# Status tracking system
class IngestionStatus:
    def __init__(self):
        self.tasks = {}

    def create_task(self, ticker: str):
        task_id = str(uuid4())
        self.tasks[task_id] = {
            "ticker": ticker,
            "status": "pending",
            "progress": 0,
            "message": f"Preparing to ingest {ticker}",
            "steps_completed": 0,
            "total_steps": 0,
            "filings": [],
            "error": None
        }
        return task_id

    def update_task(self, task_id: str, **kwargs):
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)

    def get_task(self, task_id: str):
        return self.tasks.get(task_id)

ingestion_status = IngestionStatus()
```

#### 1.3 Modified Ingestion Process

```python
# Modify ingestion_helpers.py to report progress
async def ingest_company_async(ticker: str, task_id: str, client_id: str):
    try:
        # Update status
        ingestion_status.update_task(
            task_id,
            status="processing",
            message=f"Retrieving company data for {ticker}",
            progress=10
        )
        await manager.send_update(client_id, ingestion_status.get_task(task_id))

        # Get company data from EDGAR
        edgar_company = get_company(ticker)

        # ...existing ingestion code...

        # Update status
        ingestion_status.update_task(
            task_id,
            progress=20,
            message=f"Company {edgar_company.name} found, processing filings",
        )
        await manager.send_update(client_id, ingestion_status.get_task(task_id))

        # Process filings
        current_year = datetime.datetime.now().year
        filing_years = range(current_year - 1, current_year - 6, -1)
        ingestion_status.update_task(
            task_id,
            total_steps=len(filing_years)
        )

        for i, year in enumerate(filing_years):
            try:
                # Update status for this filing
                ingestion_status.update_task(
                    task_id,
                    message=f"Processing {year} filing ({i+1}/{len(filing_years)})",
                    progress=20 + (i * 15)
                )
                await manager.send_update(client_id, ingestion_status.get_task(task_id))

                # ...filing ingestion code...

                # Update progress after filing completes
                ingestion_status.update_task(
                    task_id,
                    steps_completed=i+1,
                    filings=ingestion_status.get_task(task_id)["filings"] + [{
                        "year": year,
                        "status": "completed"
                    }],
                    progress=20 + ((i+1) * 15)
                )
                await manager.send_update(client_id, ingestion_status.get_task(task_id))

            except Exception as e:
                # Update filing status on error
                ingestion_status.update_task(
                    task_id,
                    filings=ingestion_status.get_task(task_id)["filings"] + [{
                        "year": year,
                        "status": "failed",
                        "error": str(e)
                    }]
                )
                await manager.send_update(client_id, ingestion_status.get_task(task_id))
                logger.error("filing_ingestion_failed", year=year, error=str(e))

        # Mark complete
        ingestion_status.update_task(
            task_id,
            status="completed",
            progress=100,
            message=f"Ingestion of {ticker} completed"
        )
        await manager.send_update(client_id, ingestion_status.get_task(task_id))

        return company_id

    except Exception as e:
        # Update status on error
        ingestion_status.update_task(
            task_id,
            status="failed",
            error=str(e),
            message=f"Failed to ingest {ticker}: {str(e)}"
        )
        await manager.send_update(client_id, ingestion_status.get_task(task_id))
        logger.error("company_ingestion_failed", ticker=ticker, error=str(e))
        raise
```

#### 1.4 Background Task Execution

```python
from fastapi import BackgroundTasks

@app.post("/companies/ingest")
async def trigger_ingestion(
    ticker: str,
    background_tasks: BackgroundTasks,
    client_id: str = Query(None)
):
    # Create a new ingestion task
    task_id = ingestion_status.create_task(ticker)

    # Start ingestion in background
    background_tasks.add_task(ingest_company_async, ticker, task_id, client_id)

    # Return task ID immediately
    return {
        "message": f"Started ingestion for {ticker}",
        "task_id": task_id
    }

@app.get("/companies/ingest/{task_id}/status")
async def get_ingestion_status(task_id: str):
    # Get current status for polling fallback
    status = ingestion_status.get_task(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Ingestion task not found")
    return status
```

### 2. Frontend Changes

#### 2.1 WebSocket Client

```typescript
// websocket-service.ts
export class WebSocketService {
  private socket: WebSocket | null = null;
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor() {
    // Generate a client ID for this session
    this.clientId = crypto.randomUUID();
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${config.api.wsBaseUrl}/ws/${this.clientId}`;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
          this.reconnectAttempts = 0;
          resolve();
        };

        this.socket.onclose = () => {
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
          }
        };

        this.socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          const listeners = this.listeners.get(data.type) || new Set();
          listeners.forEach(callback => callback(data));
        };

        this.socket.onerror = (error) => {
          reject(error);
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  addListener<T>(type: string, callback: (data: T) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(callback);

    // Return a function to remove this listener
    return () => {
      const listenersOfType = this.listeners.get(type);
      if (listenersOfType) {
        listenersOfType.delete(callback);
      }
    };
  }

  getClientId(): string {
    return this.clientId;
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

// Create a singleton instance
export const webSocketService = new WebSocketService();
```

#### 2.2 Updated CompanySelector Component

```svelte
<script lang="ts">
  // ...existing imports...
  import { webSocketService } from '$utils/websocket-service';
  import { onMount, onDestroy } from 'svelte';

  // ...existing variables...
  let ingestionTaskId = $state<string | null>(null);
  let ingestionProgress = $state(0);
  let ingestionStatus = $state<'idle' | 'pending' | 'processing' | 'completed' | 'failed'>('idle');
  let ingestionMessage = $state<string>('');
  let ingestionFilings = $state<Array<{year: number, status: string}>>([]);

  onMount(async () => {
    try {
      await webSocketService.connect();

      // Listen for ingestion updates
      const unsubscribe = webSocketService.addListener('ingestion_update', (data) => {
        ingestionProgress = data.progress;
        ingestionStatus = data.status;
        ingestionMessage = data.message;
        ingestionFilings = data.filings || [];

        // If completed, fetch the company data
        if (data.status === 'completed') {
          fetchCompanyById(data.company_id);
        }
      });

      return () => {
        unsubscribe();
      };
    } catch (err) {
      logger.error('Failed to connect to WebSocket', err);
      error = 'Could not establish real-time connection. Using fallback.';
    }
  });

  onDestroy(() => {
    webSocketService.disconnect();
  });

  // Function to search for a company by ticker
  async function searchCompany() {
    if (!ticker) {
      error = 'Please enter a ticker symbol';
      return;
    }

    try {
      loading = true;
      error = null;
      selectedCompany = null;
      ingestionTaskId = null;
      ingestionProgress = 0;
      ingestionStatus = 'idle';
      ingestionMessage = '';
      ingestionFilings = [];

      const apiUrl = `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}`;
      logger.info(`Searching for company with ticker: ${ticker.toUpperCase()}`, { apiUrl });

      try {
        // First try to get existing company
        const company = await fetchApi<CompanyResponse>(apiUrl, { timeout: 5000 });
        selectedCompany = company;
        logger.info(`Company found: ${company.name}`, { company });
        dispatch('companySelected', company);
      } catch (err) {
        // If not found, trigger ingestion with WebSocket updates
        const ingestResponse = await fetchApi<{task_id: string}>(
          `${config.api.baseUrl}/companies/ingest?ticker=${ticker.toUpperCase()}&client_id=${webSocketService.getClientId()}`
        );

        ingestionTaskId = ingestResponse.task_id;
        ingestionStatus = 'pending';
        ingestionMessage = `Started ingestion for ${ticker.toUpperCase()}`;

        // Fallback polling for status updates if WebSocket fails
        if (!webSocketService.isConnected()) {
          pollIngestionStatus(ingestResponse.task_id);
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('Error searching company by ticker:', {
        ticker: ticker.toUpperCase(),
        error: errorMessage,
      });
      error = errorMessage;
    } finally {
      if (!ingestionTaskId) {
        loading = false;
      }
    }
  }

  // Fallback polling function for status updates
  async function pollIngestionStatus(taskId: string) {
    try {
      const statusResponse = await fetchApi(
        `${config.api.baseUrl}/companies/ingest/${taskId}/status`
      );

      ingestionProgress = statusResponse.progress;
      ingestionStatus = statusResponse.status;
      ingestionMessage = statusResponse.message;
      ingestionFilings = statusResponse.filings || [];

      if (statusResponse.status === 'completed') {
        // Ingestion complete, fetch the company data
        loading = false;
        const company = await fetchApi<CompanyResponse>(
          `${config.api.baseUrl}/companies/${statusResponse.company_id}`
        );
        selectedCompany = company;
        dispatch('companySelected', company);
      } else if (statusResponse.status === 'failed') {
        // Ingestion failed
        loading = false;
        error = statusResponse.error || 'Ingestion failed';
      } else {
        // Still processing, poll again after a delay
        setTimeout(() => pollIngestionStatus(taskId), 2000);
      }
    } catch (err) {
      loading = false;
      error = `Error checking ingestion status: ${err instanceof Error ? err.message : String(err)}`;
    }
  }

  async function fetchCompanyById(companyId: string) {
    try {
      const company = await fetchApi<CompanyResponse>(
        `${config.api.baseUrl}/companies/${companyId}`
      );
      selectedCompany = company;
      dispatch('companySelected', company);
    } catch (err) {
      error = `Error fetching company: ${err instanceof Error ? err.message : String(err)}`;
    } finally {
      loading = false;
    }
  }
</script>

<div class="company-selector card">
  <!-- ...existing HTML... -->

  {#if ingestionStatus !== 'idle'}
    <div class="ingestion-container">
      <div class="progress-bar">
        <div class="progress-fill" style="width: {ingestionProgress}%"></div>
      </div>
      <p class="ingestion-message">{ingestionMessage}</p>

      {#if ingestionFilings.length > 0}
        <div class="filings-status">
          {#each ingestionFilings as filing}
            <div class="filing-item" class:success={filing.status === 'completed'} class:error={filing.status === 'failed'}>
              <span>{filing.year}</span>
              <span class="status-icon">{filing.status === 'completed' ? '✓' : filing.status === 'failed' ? '✗' : '…'}</span>
            </div>
          {/each}
        </div>
      {/if}

      {#if ingestionStatus === 'failed'}
        <p class="error">Ingestion failed: {error}</p>
      {/if}
    </div>
  {/if}

  <!-- ...existing HTML... -->
</div>

<style>
  /* ...existing styles... */

  .ingestion-container {
    margin-top: var(--space-md);
    padding: var(--space-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    background-color: var(--color-surface);
  }

  .progress-bar {
    height: 8px;
    width: 100%;
    background-color: var(--color-surface-hover);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: var(--space-sm);
  }

  .progress-fill {
    height: 100%;
    background-color: var(--color-primary);
    transition: width 0.3s ease;
  }

  .ingestion-message {
    margin-bottom: var(--space-sm);
    font-weight: 500;
  }

  .filings-status {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-sm);
    margin-top: var(--space-sm);
  }

  .filing-item {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 4px;
    background-color: var(--color-surface-hover);
    font-size: 0.9em;
  }

  .filing-item.success {
    background-color: var(--color-success-bg, #e6f4ea);
    color: var(--color-success, #137333);
  }

  .filing-item.error {
    background-color: var(--color-error-bg, #fce8e6);
    color: var(--color-error, #c5221f);
  }

  .status-icon {
    font-weight: bold;
  }
</style>
```

### 3. Configuration Updates

#### 3.1 Backend Configuration

```python
# Add WebSocket settings to config.py
class SymbologyApiSettings(BaseSettings):
    host: str = Field(default="localhost")
    port: int = Field(default=8000)
    ws_path: str = Field(default="/ws")
    ws_protocol: str = Field(default="ws")

    model_config = SettingsConfigDict(
        env_prefix="SYMBOLOGY_API_",
        extra="ignore",
    )

    @property
    def ws_url(self) -> str:
        """Construct WebSocket URL."""
        return f"{self.ws_protocol}://{self.host}:{self.port}{self.ws_path}"
```

#### 3.2 Frontend Configuration

```typescript
// Add WebSocket configuration to config.ts
export default {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    wsBaseUrl: import.meta.env.VITE_API_WS_BASE_URL || 'ws://localhost:8000'
  },
  // ...other config
};
```

### 4. Testing Strategy

1. **Unit Tests**:
   - Test WebSocket connection manager
   - Test ingestion status tracking
   - Test background task execution

2. **Integration Tests**:
   - Test WebSocket connections and message passing
   - Test ingestion status updates
   - Test reconnection behavior

3. **End-to-end Tests**:
   - Test full ingestion workflow with WebSockets
   - Test fallback polling mechanism
   - Test error handling and recovery

### 5. Deployment Considerations

1. **Load Balancing**: Ensure WebSocket connections are properly handled if behind a load balancer
2. **Connection Limits**: Configure proper connection limits based on expected user load
3. **Timeouts**: Configure appropriate timeouts for WebSocket connections
4. **Monitoring**: Add monitoring for WebSocket connections and message throughput
5. **Fallbacks**: Ensure polling fallback works reliably when WebSockets fail

### 6. Migration Strategy

1. **Phase 1**: Implement backend WebSocket infrastructure
   - Add WebSocket endpoints
   - Implement status tracking system
   - Update ingestion helpers to report progress
   - Keep existing API endpoints working for backward compatibility

2. **Phase 2**: Implement frontend WebSocket client
   - Add WebSocket service
   - Update components to use WebSockets
   - Implement fallback polling
   - Add comprehensive error handling

3. **Phase 3**: Testing and rollout
   - Test all functionality thoroughly
   - Implement monitoring
   - Deploy to production
   - Monitor for any issues and adjust as needed

## Project Timeline Estimate

- Backend WebSocket implementation: 1-2 weeks
- Frontend WebSocket client: 1 week
- Testing and integration: 1 week
- Deployment and refinement: 1 week

**Total estimated time**: 4-5 weeks