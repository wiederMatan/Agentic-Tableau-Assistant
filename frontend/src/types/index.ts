/**
 * TypeScript type definitions for the Tableau Analytics Agent frontend.
 */

// === Agent Types ===

export type AgentName = 'router' | 'researcher' | 'analyst' | 'critic';

export type AgentStatus = 'idle' | 'running' | 'completed' | 'error';

export type QueryType = 'tableau' | 'general' | 'hybrid';

export type ValidationStatus = 'pending' | 'approved' | 'revision_needed';

export interface AgentState {
  name: AgentName;
  status: AgentStatus;
  startTime?: Date;
  endTime?: Date;
  error?: string;
}

// === SSE Event Types ===

export type SSEEventType =
  | 'agent_start'
  | 'tool_call'
  | 'tool_result'
  | 'validation'
  | 'token'
  | 'complete'
  | 'error'
  | 'heartbeat'
  | 'done';

export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
  timestamp?: string;
}

export interface AgentStartEvent {
  agent: AgentName;
  status: 'running';
}

export interface ToolResultEvent {
  agent: AgentName;
  [key: string]: unknown;
}

export interface ValidationEvent {
  status: ValidationStatus;
  iteration: number;
  revision_needed: boolean;
}

export interface TokenEvent {
  content: string;
}

export interface CompleteEvent {
  content: string;
  query_type: QueryType;
  iterations: number;
}

export interface ErrorEvent {
  error: string;
  type: string;
}

// === Chat Types ===

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    queryType?: QueryType;
    iterations?: number;
    validationStatus?: ValidationStatus;
  };
}

export interface ChatRequest {
  message: string;
  conversationId?: string;
}

export interface ChatResponse {
  success: boolean;
  response: string;
  query_type: QueryType;
  iterations: number;
  validation_status: ValidationStatus;
}

// === Tableau Asset Types ===

export interface TableauAsset {
  luid: string;
  name: string;
  projectName?: string;
  ownerName?: string;
  contentUrl?: string;
}

export interface TableauWorkbook extends TableauAsset {
  views: string[];
}

export interface TableauView extends TableauAsset {
  workbookId: string;
  workbookName?: string;
}

export interface TableauDatasource extends TableauAsset {
  datasourceType?: string;
  hasExtracts: boolean;
}

// === UI State Types ===

export interface WorkflowStep {
  agent: AgentName;
  status: AgentStatus;
  startTime?: Date;
  endTime?: Date;
  details?: string;
}

export interface ConversationState {
  id: string;
  messages: ChatMessage[];
  isLoading: boolean;
  error?: string;
  workflowSteps: WorkflowStep[];
  currentAgent?: AgentName;
}

// === API Types ===

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  environment: string;
  model: string;
}

export interface ConfigResponse {
  max_revision_iterations: number;
  max_csv_rows: number;
  sse_heartbeat_interval: number;
  environment: string;
}
