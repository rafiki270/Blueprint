# LLM API Wrapper - Architecture & Implementation Plan

## Executive Summary

This document specifies a production-ready LLM orchestration wrapper that unifies access to multiple backends (OpenAI, Claude, Gemini, Ollama, and self-reference to Opus for heavy reasoning). The wrapper provides a consistent interface, handles streaming with error recovery, manages credentials globally, tracks usage/costs, and supports advanced features like tool-calling and planning mode.

---

## 1. High-Level Architecture

### 1.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│          (CLI, Agents, Tasks, Orchestrators)                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Unified LLM Client                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Public API Surface                                   │  │
│  │  - chat() / generate() / stream()                     │  │
│  │  - listModels() / getUsage() / getHealth()           │  │
│  │  - planningMode() / toolCall()                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Orchestration Layer                             │  │
│  │  - Provider routing & selection                       │  │
│  │  - Request normalization                              │  │
│  │  - Response normalization                             │  │
│  │  - Fallback & retry logic                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Cross-Cutting Concerns                               │  │
│  │  - Credentials Manager                                │  │
│  │  - Usage Tracker & Cost Calculator                    │  │
│  │  - Cache Manager (prompt/response)                    │  │
│  │  - Stream Handler (subscribe/error/retry)             │  │
│  │  - Tool Execution Engine                              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┬──────────┐
        ▼            ▼            ▼            ▼          ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ OpenAI   │  │ Claude   │  │ Gemini   │  │ Ollama   │  │  Opus    │
│ Adapter  │  │ Adapter  │  │ Adapter  │  │ Adapter  │  │ Adapter  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 1.2 Module Breakdown

1. **Provider Adapters** - Backend-specific implementations
2. **Orchestration Core** - Request routing, normalization, fallback
3. **Credentials Manager** - Secure global credential storage/retrieval
4. **Stream Handler** - Streaming logic with error detection & retry
5. **Usage Tracker** - Token/cost tracking and quota management
6. **Tool Engine** - Tool-calling coordination & execution
7. **Cache Manager** - Optional caching for cost reduction
8. **Planning Mode Coordinator** - Heavy reasoning orchestration

---

## 2. Interface Definition (Public API)

### 2.1 Core Methods

```typescript
interface LLMClient {
  // ============ Generation Methods ============

  /**
   * Send a chat-style request (messages array)
   * @returns Promise with full response
   */
  chat(request: ChatRequest): Promise<ChatResponse>;

  /**
   * Generate completion from a prompt
   * @returns Promise with full response
   */
  generate(request: GenerateRequest): Promise<GenerateResponse>;

  /**
   * Stream chat response with incremental chunks
   * @returns AsyncGenerator yielding chunks
   */
  stream(request: ChatRequest): AsyncGenerator<StreamChunk, void, unknown>;

  // ============ Discovery & Introspection ============

  /**
   * List available models across all configured providers
   * @param provider Optional filter by provider
   */
  listModels(provider?: ProviderType): Promise<ModelInfo[]>;

  /**
   * Get health status of all providers
   */
  getHealth(): Promise<ProviderHealth[]>;

  // ============ Usage & Cost Tracking ============

  /**
   * Get aggregated usage stats
   * @param filter Optional filter by provider/model/timeframe
   */
  getUsage(filter?: UsageFilter): Promise<UsageStats>;

  /**
   * Reset usage counters
   */
  resetUsage(): void;

  // ============ Advanced Features ============

  /**
   * Planning mode: use heavy model for architecture/design tasks
   * @param context Large context, history, requirements
   * @returns Structured multi-step plan
   */
  planningMode(context: PlanningContext): Promise<Plan>;

  /**
   * Execute a tool call coordinated with LLM
   * @param toolCall Tool name & arguments from LLM
   * @returns Tool execution result
   */
  executeTool(toolCall: ToolCall): Promise<ToolResult>;

  /**
   * Configure fallback chain
   * @param chain Ordered list of providers to try
   */
  setFallbackChain(chain: ProviderType[]): void;
}
```

### 2.2 Type Definitions

```typescript
// ============ Request Types ============

interface ChatRequest {
  messages: Message[];
  model?: string;                 // Model name or "auto" for provider selection
  provider?: ProviderType;        // Explicit provider or use routing rules
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  stop?: string[];
  tools?: Tool[];                 // Function/tool definitions
  stream?: boolean;               // Enable streaming (use stream() method instead)
  metadata?: Record<string, any>; // Request-level metadata for tracking
}

interface GenerateRequest {
  prompt: string;
  model?: string;
  provider?: ProviderType;
  temperature?: number;
  maxTokens?: number;
  // ... similar params
}

interface Message {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  toolCallId?: string;  // For tool responses
  name?: string;        // Tool name
}

interface Tool {
  name: string;
  description: string;
  parameters: JSONSchema;  // JSON schema for arguments
}

// ============ Response Types ============

interface ChatResponse {
  content: string;
  finishReason: "stop" | "length" | "tool_call" | "error";
  usage: UsageInfo;
  toolCalls?: ToolCall[];
  provider: ProviderType;
  model: string;
  metadata: ResponseMetadata;
}

interface GenerateResponse {
  content: string;
  finishReason: "stop" | "length" | "error";
  usage: UsageInfo;
  provider: ProviderType;
  model: string;
}

interface StreamChunk {
  delta: string;              // Incremental text
  isDone: boolean;
  usage?: UsageInfo;          // Only in final chunk
  toolCall?: Partial<ToolCall>;  // Incremental tool call
  error?: Error;
}

interface UsageInfo {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  estimatedCost?: number;     // USD
}

interface ResponseMetadata {
  requestId: string;
  latencyMs: number;
  cached?: boolean;
  retriesAttempted: number;
}

// ============ Tool Calling ============

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

interface ToolResult {
  toolCallId: string;
  result: any;
  error?: string;
}

// ============ Provider & Model Info ============

enum ProviderType {
  OPENAI = "openai",
  CLAUDE = "claude",
  GEMINI = "gemini",
  OLLAMA = "ollama",
  OPUS_SELF = "opus_self"    // Self-reference for heavy reasoning
}

interface ModelInfo {
  id: string;
  provider: ProviderType;
  capabilities: Capability[];
  contextWindow: number;
  costPer1kTokens?: { input: number; output: number };
}

enum Capability {
  CHAT = "chat",
  STREAMING = "streaming",
  TOOL_CALLING = "tool_calling",
  JSON_MODE = "json_mode",
  MULTIMODAL = "multimodal"
}

interface ProviderHealth {
  provider: ProviderType;
  status: "healthy" | "degraded" | "down";
  latencyMs?: number;
  lastChecked: Date;
}

// ============ Usage Tracking ============

interface UsageStats {
  totalRequests: number;
  totalTokens: number;
  totalCost: number;
  byProvider: Map<ProviderType, ProviderUsage>;
  byModel: Map<string, ModelUsage>;
}

interface ProviderUsage {
  requests: number;
  tokens: number;
  cost: number;
  errors: number;
}

interface ModelUsage {
  requests: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
}

interface UsageFilter {
  provider?: ProviderType;
  model?: string;
  startTime?: Date;
  endTime?: Date;
}

// ============ Planning Mode ============

interface PlanningContext {
  goal: string;
  requirements: string[];
  codebaseContext?: string;
  constraints?: string[];
  previousPlans?: Plan[];
}

interface Plan {
  overview: string;
  steps: PlanStep[];
  estimatedComplexity: "low" | "medium" | "high";
  suggestedModels: string[];  // For implementing each step
  metadata: {
    generatedBy: string;
    tokensUsed: number;
    timestamp: Date;
  };
}

interface PlanStep {
  id: string;
  description: string;
  dependencies: string[];  // IDs of prerequisite steps
  suggestedApproach: string;
  risks?: string[];
}
```

---

## 3. Streaming Handling Logic

### 3.1 Stream Lifecycle

```
┌─────────────┐
│   Client    │
│  stream()   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  StreamHandler.initiate()                │
│  - Validate request                      │
│  - Select provider                       │
│  - Open stream connection                │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  StreamHandler.subscribe()               │
│  ┌────────────────────────────────────┐  │
│  │  While streaming:                  │  │
│  │  1. Receive chunk                  │  │
│  │  2. Validate chunk format          │  │
│  │  3. Detect errors/malformed data   │  │
│  │  4. Accumulate for validation      │  │
│  │  5. Yield to client                │  │
│  └────────────────────────────────────┘  │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  StreamHandler.finalize()                │
│  - Validate complete response            │
│  - Extract usage info                    │
│  - Update usage tracker                  │
└──────┬───────────────────────────────────┘
       │
       ▼ (if error detected)
┌──────────────────────────────────────────┐
│  StreamHandler.handleError()             │
│  - Classify error (retriable/fatal)      │
│  - Attempt retry or fallback             │
│  - Log error                             │
└──────────────────────────────────────────┘
```

### 3.2 Error Detection & Recovery

```typescript
class StreamHandler {
  private chunkBuffer: string[] = [];
  private retryCount: number = 0;
  private readonly MAX_RETRIES = 3;

  async *handleStream(
    request: ChatRequest,
    adapter: ProviderAdapter
  ): AsyncGenerator<StreamChunk> {
    try {
      const stream = adapter.stream(request);

      for await (const chunk of stream) {
        // Validate chunk structure
        if (!this.isValidChunk(chunk)) {
          yield { delta: "", isDone: false, error: new Error("Malformed chunk") };
          continue;
        }

        // Buffer chunks for validation
        if (chunk.delta) {
          this.chunkBuffer.push(chunk.delta);
        }

        // Yield to client
        yield chunk;

        // Stream completed
        if (chunk.isDone) {
          await this.validateCompleteResponse(this.chunkBuffer.join(""));
          break;
        }
      }

    } catch (error) {
      yield* this.handleStreamError(error, request, adapter);
    }
  }

  private async *handleStreamError(
    error: Error,
    request: ChatRequest,
    adapter: ProviderAdapter
  ): AsyncGenerator<StreamChunk> {
    const errorType = this.classifyError(error);

    // Retriable errors: network blip, timeout, rate limit
    if (errorType === "retriable" && this.retryCount < this.MAX_RETRIES) {
      this.retryCount++;
      const backoffMs = Math.pow(2, this.retryCount) * 1000;

      await this.sleep(backoffMs);
      yield* this.handleStream(request, adapter);  // Retry

    // Fallback to different provider
    } else if (errorType === "provider_failure") {
      const fallbackProvider = this.selectFallback(adapter.type);
      if (fallbackProvider) {
        const fallbackAdapter = this.getAdapter(fallbackProvider);
        yield* this.handleStream(request, fallbackAdapter);
      } else {
        yield { delta: "", isDone: true, error };
      }

    // Fatal error
    } else {
      yield { delta: "", isDone: true, error };
    }
  }

  private classifyError(error: Error): "retriable" | "provider_failure" | "fatal" {
    // Check HTTP status codes, error messages, etc.
    if (error.message.includes("429") || error.message.includes("timeout")) {
      return "retriable";
    }
    if (error.message.includes("401") || error.message.includes("403")) {
      return "provider_failure";
    }
    return "fatal";
  }

  private async validateCompleteResponse(fullResponse: string): Promise<void> {
    // Validate response format (e.g., complete JSON if tool-call expected)
    // Throw if invalid; will trigger retry/fallback
  }
}
```

### 3.3 Subscription API for Clients

```typescript
// Client usage example
async function exampleStreamUsage() {
  const client = new LLMClient();

  for await (const chunk of client.stream({
    messages: [{ role: "user", content: "Explain async generators" }],
    model: "auto"
  })) {
    if (chunk.error) {
      console.error("Stream error:", chunk.error);
      break;
    }

    process.stdout.write(chunk.delta);

    if (chunk.isDone) {
      console.log(`\n\nTokens used: ${chunk.usage?.totalTokens}`);
    }
  }
}
```

---

## 4. Credentials Management

### 4.1 Storage Strategy

**Location:** Global user configuration directory (not per-project)

- **Linux/macOS:** `~/.config/blueprint/credentials.json`
- **Windows:** `%APPDATA%\blueprint\credentials.json`
- **Permissions:** `chmod 600` (user-read-write only)

**Encryption:** Optional AES-256 encryption with user-provided master password or OS keychain integration.

### 4.2 Credential File Format

```json
{
  "version": "1.0",
  "providers": {
    "openai": {
      "api_key": "sk-...",
      "organization_id": "org-...",
      "base_url": "https://api.openai.com/v1"
    },
    "claude": {
      "api_key": "sk-ant-...",
      "base_url": "https://api.anthropic.com",
      "version": "2023-06-01"
    },
    "gemini": {
      "api_key": "AIza...",
      "project_id": "my-project",
      "base_url": "https://generativelanguage.googleapis.com/v1beta"
    },
    "ollama": {
      "base_url": "http://localhost:11434"
    },
    "opus_self": {
      "api_key": "sk-ant-...",
      "model": "claude-opus-4-5-20251101"
    }
  }
}
```

### 4.3 Credentials Manager Implementation

```typescript
class CredentialsManager {
  private credentialsPath: string;
  private credentials: Map<ProviderType, ProviderCredentials> = new Map();

  constructor() {
    this.credentialsPath = this.resolveCredentialsPath();
    this.load();
  }

  private resolveCredentialsPath(): string {
    const homeDir = process.env.HOME || process.env.USERPROFILE;
    const configDir = process.platform === "win32"
      ? path.join(homeDir, "AppData", "Roaming", "blueprint")
      : path.join(homeDir, ".config", "blueprint");

    return path.join(configDir, "credentials.json");
  }

  private load(): void {
    if (!fs.existsSync(this.credentialsPath)) {
      this.createDefault();
      return;
    }

    // Check file permissions
    const stats = fs.statSync(this.credentialsPath);
    if (stats.mode & 0o077) {  // World/group readable
      throw new Error(`Insecure permissions on ${this.credentialsPath}. Run: chmod 600`);
    }

    const raw = fs.readFileSync(this.credentialsPath, "utf-8");
    const data = JSON.parse(raw);

    for (const [provider, config] of Object.entries(data.providers)) {
      this.credentials.set(provider as ProviderType, config as ProviderCredentials);
    }
  }

  get(provider: ProviderType): ProviderCredentials {
    const creds = this.credentials.get(provider);
    if (!creds) {
      throw new Error(`No credentials found for provider: ${provider}`);
    }
    return creds;
  }

  set(provider: ProviderType, credentials: ProviderCredentials): void {
    this.credentials.set(provider, credentials);
    this.save();
  }

  private save(): void {
    const data = {
      version: "1.0",
      providers: Object.fromEntries(this.credentials)
    };

    fs.writeFileSync(
      this.credentialsPath,
      JSON.stringify(data, null, 2),
      { mode: 0o600 }  // User-only read/write
    );
  }

  private createDefault(): void {
    const defaultCreds = {
      version: "1.0",
      providers: {
        ollama: { base_url: "http://localhost:11434" }
      }
    };

    fs.mkdirSync(path.dirname(this.credentialsPath), { recursive: true });
    fs.writeFileSync(
      this.credentialsPath,
      JSON.stringify(defaultCreds, null, 2),
      { mode: 0o600 }
    );
  }
}

interface ProviderCredentials {
  api_key?: string;
  base_url?: string;
  organization_id?: string;
  project_id?: string;
  version?: string;
  model?: string;
  [key: string]: any;
}
```

### 4.4 Environment Variable Fallback

Allow credentials to be specified via environment variables for CI/CD:

- `BLUEPRINT_OPENAI_API_KEY`
- `BLUEPRINT_CLAUDE_API_KEY`
- `BLUEPRINT_GEMINI_API_KEY`
- `BLUEPRINT_OLLAMA_BASE_URL`

Priority: environment variable > credentials file > error

---

## 5. Usage & Cost Tracking

### 5.1 Tracking Architecture

```typescript
class UsageTracker {
  private stats: UsageStats = {
    totalRequests: 0,
    totalTokens: 0,
    totalCost: 0,
    byProvider: new Map(),
    byModel: new Map()
  };

  private costTable: Map<string, TokenCost> = new Map([
    ["gpt-4o", { input: 0.0025, output: 0.01 }],              // per 1k tokens
    ["gpt-4", { input: 0.03, output: 0.06 }],
    ["claude-opus-4-5", { input: 0.015, output: 0.075 }],
    ["claude-sonnet-4.5", { input: 0.003, output: 0.015 }],
    ["gemini-2-flash", { input: 0.0001, output: 0.0004 }],
    // Ollama: local, cost = 0
  ]);

  recordUsage(
    provider: ProviderType,
    model: string,
    usage: UsageInfo
  ): void {
    // Update totals
    this.stats.totalRequests++;
    this.stats.totalTokens += usage.totalTokens;

    // Calculate cost
    const cost = this.calculateCost(model, usage);
    this.stats.totalCost += cost;
    usage.estimatedCost = cost;

    // Update by-provider stats
    this.updateProviderStats(provider, usage, cost);

    // Update by-model stats
    this.updateModelStats(model, usage, cost);

    // Persist to disk (optional)
    this.persist();
  }

  private calculateCost(model: string, usage: UsageInfo): number {
    const rates = this.costTable.get(model);
    if (!rates) return 0;  // Unknown model or local

    const inputCost = (usage.promptTokens / 1000) * rates.input;
    const outputCost = (usage.completionTokens / 1000) * rates.output;

    return inputCost + outputCost;
  }

  getStats(filter?: UsageFilter): UsageStats {
    // Apply filters and return subset
    // ...
    return this.stats;
  }

  reset(): void {
    this.stats = {
      totalRequests: 0,
      totalTokens: 0,
      totalCost: 0,
      byProvider: new Map(),
      byModel: new Map()
    };
  }

  private persist(): void {
    // Write to ~/.config/blueprint/usage.json
  }
}

interface TokenCost {
  input: number;   // USD per 1k tokens
  output: number;
}
```

### 5.2 Quota Management

```typescript
interface QuotaConfig {
  maxCostPerHour?: number;
  maxCostPerDay?: number;
  maxTokensPerRequest?: number;
  maxRequestsPerMinute?: number;
}

class QuotaGuard {
  constructor(private tracker: UsageTracker, private config: QuotaConfig) {}

  async checkQuota(estimatedTokens: number): Promise<void> {
    const stats = this.tracker.getStats({
      startTime: new Date(Date.now() - 3600 * 1000)  // Last hour
    });

    if (this.config.maxCostPerHour && stats.totalCost >= this.config.maxCostPerHour) {
      throw new Error(`Hourly cost quota exceeded: $${stats.totalCost.toFixed(2)}`);
    }

    // Check other quotas...
  }
}
```

---

## 6. Provider Adapter Abstraction

### 6.1 Adapter Interface

```typescript
abstract class ProviderAdapter {
  abstract type: ProviderType;

  constructor(protected credentials: ProviderCredentials) {}

  /**
   * Non-streaming chat
   */
  abstract chat(request: ChatRequest): Promise<ChatResponse>;

  /**
   * Streaming chat
   */
  abstract stream(request: ChatRequest): AsyncGenerator<StreamChunk>;

  /**
   * List available models
   */
  abstract listModels(): Promise<ModelInfo[]>;

  /**
   * Health check
   */
  abstract checkHealth(): Promise<ProviderHealth>;

  /**
   * Normalize request to provider-specific format
   */
  protected abstract normalizeRequest(request: ChatRequest): any;

  /**
   * Normalize provider response to unified format
   */
  protected abstract normalizeResponse(response: any): ChatResponse;
}
```

### 6.2 Example: OpenAI Adapter

```typescript
class OpenAIAdapter extends ProviderAdapter {
  type = ProviderType.OPENAI;

  private client: OpenAI;

  constructor(credentials: ProviderCredentials) {
    super(credentials);
    this.client = new OpenAI({
      apiKey: credentials.api_key,
      baseURL: credentials.base_url,
      organization: credentials.organization_id
    });
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const normalized = this.normalizeRequest(request);

    const response = await this.client.chat.completions.create({
      model: normalized.model,
      messages: normalized.messages,
      temperature: normalized.temperature,
      max_tokens: normalized.max_tokens,
      tools: normalized.tools,
      stream: false
    });

    return this.normalizeResponse(response);
  }

  async *stream(request: ChatRequest): AsyncGenerator<StreamChunk> {
    const normalized = this.normalizeRequest(request);

    const stream = await this.client.chat.completions.create({
      ...normalized,
      stream: true,
      stream_options: { include_usage: true }
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content || "";
      const isDone = chunk.choices[0]?.finish_reason !== null;

      yield {
        delta,
        isDone,
        usage: isDone ? this.extractUsage(chunk) : undefined
      };
    }
  }

  protected normalizeRequest(request: ChatRequest): any {
    return {
      model: request.model || "gpt-4o",
      messages: request.messages,
      temperature: request.temperature ?? 0.7,
      max_tokens: request.maxTokens,
      tools: request.tools?.map(t => ({
        type: "function",
        function: {
          name: t.name,
          description: t.description,
          parameters: t.parameters
        }
      }))
    };
  }

  protected normalizeResponse(response: any): ChatResponse {
    const choice = response.choices[0];

    return {
      content: choice.message.content || "",
      finishReason: this.mapFinishReason(choice.finish_reason),
      usage: {
        promptTokens: response.usage.prompt_tokens,
        completionTokens: response.usage.completion_tokens,
        totalTokens: response.usage.total_tokens
      },
      toolCalls: choice.message.tool_calls?.map(tc => ({
        id: tc.id,
        name: tc.function.name,
        arguments: JSON.parse(tc.function.arguments)
      })),
      provider: this.type,
      model: response.model,
      metadata: {
        requestId: response.id,
        latencyMs: 0,  // Computed by caller
        retriesAttempted: 0
      }
    };
  }

  async listModels(): Promise<ModelInfo[]> {
    const models = await this.client.models.list();
    return models.data
      .filter(m => m.id.includes("gpt"))
      .map(m => ({
        id: m.id,
        provider: this.type,
        capabilities: [Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING],
        contextWindow: this.getContextWindow(m.id),
        costPer1kTokens: this.getCost(m.id)
      }));
  }

  async checkHealth(): Promise<ProviderHealth> {
    const start = Date.now();
    try {
      await this.client.models.list();
      return {
        provider: this.type,
        status: "healthy",
        latencyMs: Date.now() - start,
        lastChecked: new Date()
      };
    } catch (error) {
      return {
        provider: this.type,
        status: "down",
        lastChecked: new Date()
      };
    }
  }

  private mapFinishReason(reason: string): ChatResponse["finishReason"] {
    switch (reason) {
      case "stop": return "stop";
      case "length": return "length";
      case "tool_calls": return "tool_call";
      default: return "error";
    }
  }

  private getContextWindow(modelId: string): number {
    if (modelId.includes("gpt-4o")) return 128000;
    if (modelId.includes("gpt-4")) return 8192;
    return 4096;
  }

  private getCost(modelId: string): { input: number; output: number } | undefined {
    // Return cost per 1k tokens
    if (modelId.includes("gpt-4o")) return { input: 0.0025, output: 0.01 };
    if (modelId.includes("gpt-4")) return { input: 0.03, output: 0.06 };
    return undefined;
  }

  private extractUsage(chunk: any): UsageInfo | undefined {
    if (!chunk.usage) return undefined;
    return {
      promptTokens: chunk.usage.prompt_tokens,
      completionTokens: chunk.usage.completion_tokens,
      totalTokens: chunk.usage.total_tokens
    };
  }
}
```

### 6.3 Adapter Factory

```typescript
class AdapterFactory {
  constructor(private credentialsManager: CredentialsManager) {}

  create(provider: ProviderType): ProviderAdapter {
    const credentials = this.credentialsManager.get(provider);

    switch (provider) {
      case ProviderType.OPENAI:
        return new OpenAIAdapter(credentials);
      case ProviderType.CLAUDE:
        return new ClaudeAdapter(credentials);
      case ProviderType.GEMINI:
        return new GeminiAdapter(credentials);
      case ProviderType.OLLAMA:
        return new OllamaAdapter(credentials);
      case ProviderType.OPUS_SELF:
        return new OpusSelfAdapter(credentials);
      default:
        throw new Error(`Unknown provider: ${provider}`);
    }
  }
}
```

---

## 7. Tool-Calling Support

### 7.1 Tool Execution Engine

```typescript
class ToolEngine {
  private tools: Map<string, ToolHandler> = new Map();

  registerTool(tool: Tool, handler: ToolHandler): void {
    this.tools.set(tool.name, handler);
  }

  async executeTool(toolCall: ToolCall): Promise<ToolResult> {
    const handler = this.tools.get(toolCall.name);

    if (!handler) {
      return {
        toolCallId: toolCall.id,
        result: null,
        error: `Unknown tool: ${toolCall.name}`
      };
    }

    try {
      // Validate arguments against schema
      this.validateArguments(toolCall);

      // Execute in sandboxed environment
      const result = await this.executeSandboxed(handler, toolCall.arguments);

      return {
        toolCallId: toolCall.id,
        result
      };
    } catch (error) {
      return {
        toolCallId: toolCall.id,
        result: null,
        error: error.message
      };
    }
  }

  private validateArguments(toolCall: ToolCall): void {
    // JSON schema validation
  }

  private async executeSandboxed(
    handler: ToolHandler,
    args: Record<string, any>
  ): Promise<any> {
    // Execute with timeout, resource limits, etc.
    return await handler(args);
  }
}

type ToolHandler = (args: Record<string, any>) => Promise<any>;
```

### 7.2 Tool-Calling Workflow

```typescript
async function toolCallingWorkflow(client: LLMClient) {
  // Register tools
  client.registerTool(
    {
      name: "apply_patch",
      description: "Apply a code patch to a file",
      parameters: {
        type: "object",
        properties: {
          file_path: { type: "string" },
          patch: { type: "string" }
        },
        required: ["file_path", "patch"]
      }
    },
    async (args) => {
      // Execute patch application
      return { success: true };
    }
  );

  // Initial request
  let messages: Message[] = [
    { role: "user", content: "Fix the bug in utils.ts" }
  ];

  while (true) {
    const response = await client.chat({
      messages,
      tools: client.getRegisteredTools()
    });

    // No tool call - done
    if (response.finishReason !== "tool_call") {
      console.log(response.content);
      break;
    }

    // Execute tool calls
    for (const toolCall of response.toolCalls) {
      const result = await client.executeTool(toolCall);

      // Add tool result to conversation
      messages.push({
        role: "tool",
        content: JSON.stringify(result.result),
        toolCallId: result.toolCallId,
        name: toolCall.name
      });
    }
  }
}
```

---

## 8. Error Handling & Fallback Logic

### 8.1 Fallback Chain

```typescript
class FallbackManager {
  private defaultChain: ProviderType[] = [
    ProviderType.CLAUDE,    // Primary
    ProviderType.OPENAI,    // Fallback 1
    ProviderType.GEMINI,    // Fallback 2
    ProviderType.OLLAMA     // Local fallback
  ];

  private customChain?: ProviderType[];

  setChain(chain: ProviderType[]): void {
    this.customChain = chain;
  }

  getChain(): ProviderType[] {
    return this.customChain || this.defaultChain;
  }

  getNextProvider(currentProvider: ProviderType): ProviderType | null {
    const chain = this.getChain();
    const currentIndex = chain.indexOf(currentProvider);

    if (currentIndex === -1 || currentIndex === chain.length - 1) {
      return null;
    }

    return chain[currentIndex + 1];
  }
}
```

### 8.2 Retry Logic

```typescript
class RetryManager {
  private readonly DEFAULT_MAX_RETRIES = 3;
  private readonly BACKOFF_MULTIPLIER = 2;
  private readonly INITIAL_BACKOFF_MS = 1000;

  async executeWithRetry<T>(
    operation: () => Promise<T>,
    options?: RetryOptions
  ): Promise<T> {
    const maxRetries = options?.maxRetries ?? this.DEFAULT_MAX_RETRIES;
    let lastError: Error;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;

        // Don't retry on non-retriable errors
        if (!this.isRetriable(error)) {
          throw error;
        }

        // Last attempt - throw
        if (attempt === maxRetries) {
          throw error;
        }

        // Backoff
        const backoffMs = this.INITIAL_BACKOFF_MS * Math.pow(this.BACKOFF_MULTIPLIER, attempt);
        await this.sleep(backoffMs);
      }
    }

    throw lastError!;
  }

  private isRetriable(error: Error): boolean {
    const retriablePatterns = [
      /timeout/i,
      /ECONNRESET/,
      /ETIMEDOUT/,
      /429/,  // Rate limit
      /503/,  // Service unavailable
      /504/   // Gateway timeout
    ];

    return retriablePatterns.some(pattern => pattern.test(error.message));
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

interface RetryOptions {
  maxRetries?: number;
}
```

### 8.3 Unified Error Handling

```typescript
class LLMClient {
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const providers = request.provider
      ? [request.provider]
      : this.fallbackManager.getChain();

    let lastError: Error;

    for (const provider of providers) {
      try {
        const adapter = this.adapterFactory.create(provider);

        // Execute with retries
        const response = await this.retryManager.executeWithRetry(
          () => adapter.chat(request)
        );

        // Track usage
        this.usageTracker.recordUsage(provider, response.model, response.usage);

        return response;

      } catch (error) {
        lastError = error;
        console.warn(`Provider ${provider} failed:`, error.message);
        // Continue to next provider in chain
      }
    }

    throw new Error(`All providers failed. Last error: ${lastError!.message}`);
  }
}
```

---

## 9. Caching & Optimization

### 9.1 Prompt Caching

```typescript
class CacheManager {
  private cache: Map<string, CachedResponse> = new Map();
  private readonly MAX_CACHE_SIZE = 1000;
  private readonly TTL_MS = 3600 * 1000;  // 1 hour

  getCacheKey(request: ChatRequest): string {
    // Hash messages + model + key params
    return crypto
      .createHash("sha256")
      .update(JSON.stringify({
        messages: request.messages,
        model: request.model,
        temperature: request.temperature
      }))
      .digest("hex");
  }

  get(key: string): ChatResponse | null {
    const cached = this.cache.get(key);

    if (!cached) return null;

    // Check TTL
    if (Date.now() - cached.timestamp > this.TTL_MS) {
      this.cache.delete(key);
      return null;
    }

    return {
      ...cached.response,
      metadata: { ...cached.response.metadata, cached: true }
    };
  }

  set(key: string, response: ChatResponse): void {
    // Evict oldest if at capacity
    if (this.cache.size >= this.MAX_CACHE_SIZE) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(key, {
      response,
      timestamp: Date.now()
    });
  }
}

interface CachedResponse {
  response: ChatResponse;
  timestamp: number;
}
```

### 9.2 Provider-Level Prompt Caching

Some providers (Claude, OpenAI) support server-side prompt caching. Leverage this:

```typescript
class ClaudeAdapter extends ProviderAdapter {
  async chat(request: ChatRequest): Promise<ChatResponse> {
    // Mark system prompts as cacheable
    const messages = request.messages.map((msg, idx) => {
      if (msg.role === "system" && idx === 0) {
        return {
          ...msg,
          cache_control: { type: "ephemeral" }  // Claude-specific
        };
      }
      return msg;
    });

    // ... rest of implementation
  }
}
```

---

## 10. Planning Mode Coordinator

### 10.1 Planning Mode Implementation

```typescript
class PlanningModeCoordinator {
  constructor(
    private client: LLMClient,
    private planningModel: string = "claude-opus-4-5-20251101"
  ) {}

  async createPlan(context: PlanningContext): Promise<Plan> {
    const planningPrompt = this.buildPlanningPrompt(context);

    const response = await this.client.chat({
      messages: [
        {
          role: "system",
          content: `You are a software architect. Generate detailed implementation plans in JSON format with this schema:
{
  "overview": "string",
  "steps": [
    {
      "id": "string",
      "description": "string",
      "dependencies": ["step_id"],
      "suggestedApproach": "string",
      "risks": ["string"]
    }
  ],
  "estimatedComplexity": "low" | "medium" | "high",
  "suggestedModels": ["model_name"]
}`
        },
        { role: "user", content: planningPrompt }
      ],
      model: this.planningModel,
      provider: ProviderType.OPUS_SELF,
      temperature: 0.2,
      maxTokens: 4000
    });

    // Parse JSON plan
    const planData = JSON.parse(response.content);

    return {
      ...planData,
      metadata: {
        generatedBy: this.planningModel,
        tokensUsed: response.usage.totalTokens,
        timestamp: new Date()
      }
    };
  }

  private buildPlanningPrompt(context: PlanningContext): string {
    return `
## Goal
${context.goal}

## Requirements
${context.requirements.map((r, i) => `${i + 1}. ${r}`).join("\n")}

${context.codebaseContext ? `## Codebase Context\n${context.codebaseContext}` : ""}

${context.constraints ? `## Constraints\n${context.constraints.join("\n")}` : ""}

${context.previousPlans ? `## Previous Plans (for reference)\n${JSON.stringify(context.previousPlans, null, 2)}` : ""}

Generate a detailed implementation plan.
`.trim();
  }
}
```

### 10.2 Plan Execution

```typescript
async function executePlan(plan: Plan, client: LLMClient) {
  const completed = new Set<string>();

  while (completed.size < plan.steps.length) {
    // Find next executable step (dependencies met)
    const nextStep = plan.steps.find(step =>
      !completed.has(step.id) &&
      step.dependencies.every(dep => completed.has(dep))
    );

    if (!nextStep) {
      throw new Error("Circular dependencies or blocked steps");
    }

    console.log(`\n=== Executing: ${nextStep.description} ===\n`);

    // Choose model based on plan suggestion
    const model = plan.suggestedModels[0] || "gpt-4o";

    const response = await client.chat({
      messages: [
        { role: "user", content: `Implement: ${nextStep.description}\n\nApproach: ${nextStep.suggestedApproach}` }
      ],
      model
    });

    console.log(response.content);

    completed.add(nextStep.id);
  }
}
```

---

## 11. Implementation Pseudocode

### 11.1 Main Client Class

```typescript
class LLMClient {
  private adapterFactory: AdapterFactory;
  private credentialsManager: CredentialsManager;
  private usageTracker: UsageTracker;
  private cacheManager: CacheManager;
  private streamHandler: StreamHandler;
  private toolEngine: ToolEngine;
  private fallbackManager: FallbackManager;
  private retryManager: RetryManager;
  private planningCoordinator: PlanningModeCoordinator;

  constructor(config?: ClientConfig) {
    this.credentialsManager = new CredentialsManager();
    this.adapterFactory = new AdapterFactory(this.credentialsManager);
    this.usageTracker = new UsageTracker();
    this.cacheManager = new CacheManager();
    this.streamHandler = new StreamHandler();
    this.toolEngine = new ToolEngine();
    this.fallbackManager = new FallbackManager();
    this.retryManager = new RetryManager();
    this.planningCoordinator = new PlanningModeCoordinator(this);
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    // Check cache
    const cacheKey = this.cacheManager.getCacheKey(request);
    const cached = this.cacheManager.get(cacheKey);
    if (cached) return cached;

    // Get provider chain
    const providers = request.provider
      ? [request.provider]
      : this.fallbackManager.getChain();

    let lastError: Error;

    for (const provider of providers) {
      try {
        const adapter = this.adapterFactory.create(provider);
        const startTime = Date.now();

        // Execute with retries
        const response = await this.retryManager.executeWithRetry(
          () => adapter.chat(request)
        );

        // Add metadata
        response.metadata.latencyMs = Date.now() - startTime;

        // Track usage
        this.usageTracker.recordUsage(provider, response.model, response.usage);

        // Cache response
        this.cacheManager.set(cacheKey, response);

        return response;

      } catch (error) {
        lastError = error;
        console.warn(`Provider ${provider} failed:`, error.message);
      }
    }

    throw new Error(`All providers failed. Last error: ${lastError!.message}`);
  }

  async *stream(request: ChatRequest): AsyncGenerator<StreamChunk> {
    const provider = request.provider || this.fallbackManager.getChain()[0];
    const adapter = this.adapterFactory.create(provider);

    yield* this.streamHandler.handleStream(request, adapter);
  }

  async listModels(provider?: ProviderType): Promise<ModelInfo[]> {
    const providers = provider
      ? [provider]
      : [ProviderType.OPENAI, ProviderType.CLAUDE, ProviderType.GEMINI, ProviderType.OLLAMA];

    const results = await Promise.allSettled(
      providers.map(p => this.adapterFactory.create(p).listModels())
    );

    return results
      .filter(r => r.status === "fulfilled")
      .flatMap(r => (r as PromiseFulfilledResult<ModelInfo[]>).value);
  }

  async getHealth(): Promise<ProviderHealth[]> {
    const providers = [
      ProviderType.OPENAI,
      ProviderType.CLAUDE,
      ProviderType.GEMINI,
      ProviderType.OLLAMA
    ];

    const results = await Promise.allSettled(
      providers.map(p => this.adapterFactory.create(p).checkHealth())
    );

    return results
      .filter(r => r.status === "fulfilled")
      .map(r => (r as PromiseFulfilledResult<ProviderHealth>).value);
  }

  getUsage(filter?: UsageFilter): Promise<UsageStats> {
    return Promise.resolve(this.usageTracker.getStats(filter));
  }

  resetUsage(): void {
    this.usageTracker.reset();
  }

  async planningMode(context: PlanningContext): Promise<Plan> {
    return this.planningCoordinator.createPlan(context);
  }

  async executeTool(toolCall: ToolCall): Promise<ToolResult> {
    return this.toolEngine.executeTool(toolCall);
  }

  registerTool(tool: Tool, handler: ToolHandler): void {
    this.toolEngine.registerTool(tool, handler);
  }

  setFallbackChain(chain: ProviderType[]): void {
    this.fallbackManager.setChain(chain);
  }
}
```

### 11.2 Usage Example

```typescript
// Initialize client
const client = new LLMClient();

// Example 1: Simple chat
const response = await client.chat({
  messages: [
    { role: "user", content: "Explain async/await in JavaScript" }
  ],
  model: "auto"  // Auto-select based on fallback chain
});
console.log(response.content);

// Example 2: Streaming
for await (const chunk of client.stream({
  messages: [{ role: "user", content: "Write a sorting algorithm" }]
})) {
  process.stdout.write(chunk.delta);
}

// Example 3: Planning mode
const plan = await client.planningMode({
  goal: "Add authentication to the app",
  requirements: [
    "JWT-based auth",
    "Password hashing with bcrypt",
    "Role-based access control"
  ],
  codebaseContext: "Express.js backend with MongoDB"
});
console.log(JSON.stringify(plan, null, 2));

// Example 4: Tool calling
client.registerTool(
  {
    name: "read_file",
    description: "Read contents of a file",
    parameters: {
      type: "object",
      properties: {
        path: { type: "string" }
      },
      required: ["path"]
    }
  },
  async (args) => {
    return fs.readFileSync(args.path, "utf-8");
  }
);

const toolResponse = await client.chat({
  messages: [{ role: "user", content: "Read the package.json file" }],
  tools: client.getRegisteredTools()
});

// Example 5: Get usage stats
const usage = await client.getUsage({
  startTime: new Date(Date.now() - 86400 * 1000)  // Last 24 hours
});
console.log(`Total cost: $${usage.totalCost.toFixed(2)}`);
console.log(`Total tokens: ${usage.totalTokens}`);

// Example 6: Configure fallback chain
client.setFallbackChain([
  ProviderType.OLLAMA,    // Try local first
  ProviderType.CLAUDE,    // Then cloud
  ProviderType.OPENAI     // Last resort
]);

// Example 7: Health check
const health = await client.getHealth();
health.forEach(h => {
  console.log(`${h.provider}: ${h.status} (${h.latencyMs}ms)`);
});
```

---

## 12. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. Set up project structure
2. Implement credentials manager with file storage
3. Create base `ProviderAdapter` abstract class
4. Implement usage tracker
5. Build retry manager

### Phase 2: Provider Adapters (Week 2-3)
1. Implement `OpenAIAdapter`
2. Implement `ClaudeAdapter`
3. Implement `GeminiAdapter`
4. Implement `OllamaAdapter`
5. Implement `OpusSelfAdapter` (Claude Opus reference)
6. Add adapter factory

### Phase 3: Core Client (Week 3-4)
1. Build main `LLMClient` class
2. Implement `chat()` and `generate()` methods
3. Add fallback chain logic
4. Integrate usage tracking
5. Add model listing and health checks

### Phase 4: Streaming (Week 4-5)
1. Implement `StreamHandler` with error detection
2. Add streaming support to all adapters
3. Build retry logic for stream failures
4. Add partial response validation

### Phase 5: Advanced Features (Week 5-6)
1. Implement tool calling engine
2. Add planning mode coordinator
3. Build cache manager
4. Add quota guards

### Phase 6: Testing & Polish (Week 6-7)
1. Write unit tests for all adapters
2. Integration tests for fallback chains
3. Stress tests for streaming
4. Documentation and examples
5. CLI tool for testing

### Phase 7: Production Hardening (Week 7-8)
1. Add comprehensive logging
2. Implement metrics/observability hooks
3. Security audit (credential handling)
4. Performance optimization
5. Beta testing with real workloads

---

## 13. Configuration File Schema

### 13.1 Global Config (~/.config/blueprint/config.json)

```json
{
  "version": "1.0",
  "defaultProvider": "claude",
  "fallbackChain": ["claude", "openai", "gemini", "ollama"],
  "quotas": {
    "maxCostPerHour": 10.0,
    "maxCostPerDay": 100.0,
    "maxTokensPerRequest": 100000
  },
  "caching": {
    "enabled": true,
    "ttlSeconds": 3600,
    "maxEntries": 1000
  },
  "planning": {
    "defaultModel": "claude-opus-4-5-20251101",
    "provider": "opus_self"
  },
  "retries": {
    "maxAttempts": 3,
    "initialBackoffMs": 1000,
    "backoffMultiplier": 2
  },
  "logging": {
    "level": "info",
    "file": "~/.config/blueprint/llm-wrapper.log"
  }
}
```

---

## 14. Security Considerations

1. **Credential Storage**
   - File permissions: 600 (user-only)
   - Optional encryption at rest
   - Never log API keys
   - Sanitize error messages to avoid leaking keys

2. **Tool Execution**
   - Sandbox external commands
   - Validate tool arguments against schemas
   - Implement timeouts and resource limits
   - Whitelist allowed tools

3. **Input Validation**
   - Validate all user inputs
   - Sanitize prompts to prevent injection
   - Limit request sizes

4. **Network Security**
   - Use HTTPS for all API calls
   - Validate SSL certificates
   - Implement request signing where supported

---

## 15. Monitoring & Observability

### 15.1 Metrics to Track

- **Request Metrics**
  - Requests per second (by provider, model)
  - Latency percentiles (p50, p95, p99)
  - Error rates
  - Retry counts

- **Cost Metrics**
  - Spend per provider
  - Spend per model
  - Spend per hour/day/month
  - Token usage trends

- **Cache Metrics**
  - Hit rate
  - Miss rate
  - Cache size
  - Eviction rate

### 15.2 Logging Strategy

```typescript
interface LogEntry {
  timestamp: Date;
  level: "debug" | "info" | "warn" | "error";
  provider: ProviderType;
  model: string;
  operation: string;
  latencyMs: number;
  tokens?: number;
  cost?: number;
  error?: string;
  metadata?: Record<string, any>;
}
```

---

## 16. Future Enhancements

1. **Multi-turn optimization** - Summarize conversation history intelligently
2. **Model routing by task** - Auto-select model based on task complexity
3. **Distributed caching** - Redis for multi-instance deployments
4. **Observability integrations** - Datadog, Prometheus, OpenTelemetry
5. **Fine-tuned models** - Support for custom fine-tuned models
6. **Multimodal support** - Images, audio, video inputs
7. **Batch processing** - Efficient batch API support
8. **Rate limit coordination** - Global rate limiting across instances
9. **Cost prediction** - Estimate costs before making requests
10. **A/B testing** - Compare outputs from different providers/models

---

## Appendix A: Provider Comparison Matrix

| Feature | OpenAI | Claude | Gemini | Ollama |
|---------|--------|--------|--------|--------|
| Streaming | ✅ | ✅ | ✅ | ✅ |
| Tool Calling | ✅ (native) | ✅ (native) | ✅ (native) | ⚠️ (prompt-based) |
| JSON Mode | ✅ | ✅ | ✅ | ⚠️ (prompt-based) |
| Usage Reporting | ✅ (per-call) | ✅ (per-call) | ✅ (per-call) | ❌ (local) |
| Prompt Caching | ✅ (server-side) | ✅ (server-side) | ⚠️ (limited) | ❌ |
| Max Context | 128K (4o) | 200K+ (Opus) | 1M+ (Flash) | Model-dependent |
| Cost | Medium | Medium-High | Low | Free (local) |
| Latency | Medium | Medium | Low | Very Low |
| Multimodal | ✅ | ✅ | ✅ | ⚠️ (model-dependent) |

---

## Appendix B: Sample Directory Structure

```
blueprint-llm-wrapper/
├── src/
│   ├── core/
│   │   ├── LLMClient.ts
│   │   ├── AdapterFactory.ts
│   │   └── types.ts
│   ├── adapters/
│   │   ├── ProviderAdapter.ts
│   │   ├── OpenAIAdapter.ts
│   │   ├── ClaudeAdapter.ts
│   │   ├── GeminiAdapter.ts
│   │   ├── OllamaAdapter.ts
│   │   └── OpusSelfAdapter.ts
│   ├── managers/
│   │   ├── CredentialsManager.ts
│   │   ├── UsageTracker.ts
│   │   ├── CacheManager.ts
│   │   ├── FallbackManager.ts
│   │   └── RetryManager.ts
│   ├── streaming/
│   │   └── StreamHandler.ts
│   ├── tools/
│   │   └── ToolEngine.ts
│   ├── planning/
│   │   └── PlanningModeCoordinator.ts
│   └── utils/
│       ├── logger.ts
│       └── validation.ts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── examples/
│   ├── basic-chat.ts
│   ├── streaming.ts
│   ├── tool-calling.ts
│   └── planning-mode.ts
├── docs/
│   ├── API.md
│   ├── Configuration.md
│   └── Migration.md
├── package.json
├── tsconfig.json
└── README.md
```

---

## Conclusion

This architecture provides a robust, production-ready foundation for unifying multiple LLM backends. Key design principles:

1. **Abstraction** - Consistent interface regardless of provider
2. **Resilience** - Retry logic, fallback chains, error recovery
3. **Observability** - Usage tracking, cost monitoring, health checks
4. **Security** - Global credential management with proper permissions
5. **Flexibility** - Easy to add new providers, configure behavior
6. **Performance** - Streaming support, caching, parallel requests

The modular design allows incremental implementation and easy testing of individual components. Start with Phase 1 (foundation) and gradually add providers and advanced features.
