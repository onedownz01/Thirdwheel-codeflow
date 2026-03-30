export const SCHEMA_VERSION = '2.0.0';

export type FunctionType =
  | 'component'
  | 'hook'
  | 'route'
  | 'handler'
  | 'service'
  | 'db'
  | 'auth'
  | 'util'
  | 'other';

export type IntentStatus = 'candidate' | 'observed' | 'verified';

export interface Param {
  name: string;
  type: string;
  direction: 'in' | 'out';
}

export interface IntentEvidence {
  kind:
    | 'ui_event'
    | 'form_action'
    | 'router_transition'
    | 'network_mutation'
    | 'backend_route'
    | 'symbol_heuristic'
    | 'cli_command'
    | 'server_action';
  weight: number;
}

export interface ParsedFunction {
  id: string;
  name: string;
  file: string;
  type: FunctionType;
  params: Param[];
  line: number;
  return_type?: string;
  docstring?: string;
  calls: string[];
}

export interface Intent {
  id: string;
  canonical_id: string;
  label: string;
  icon: string;
  trigger: string;
  handler_fn_id: string;
  source_file: string;
  group: string;
  flow_ids: string[];
  hop_count: number;
  status: IntentStatus;
  confidence: number;
  evidence: IntentEvidence[];
  frequency: number;
  failure_rate: number;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  type: 'calls' | 'imports' | 'triggers';
}

export interface ParsedRepo {
  schema_version: string;
  repo: string;
  branch: string;
  functions: ParsedFunction[];
  intents: Intent[];
  edges?: Edge[];
  file_count: number;
  parsed_at: string;
  fn_type_index: Record<string, string[]>;
  file_index: Record<string, string[]>;
}

export type TraceEventType =
  | 'call'
  | 'return'
  | 'error'
  | 'intent_start'
  | 'intent_end'
  | 'warning';

export interface RuntimeValue {
  name: string;
  value: string;
  type_name: string;
  is_sensitive: boolean;
}

export interface TraceEvent {
  event_type: TraceEventType;
  fn_id: string;
  fn_name: string;
  file: string;
  line: number;
  timestamp_ms: number;
  inputs: RuntimeValue[];
  outputs: RuntimeValue[];
  error?: string;
  error_type?: string;
  error_line?: number;
  duration_ms?: number;
  sequence: number;
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  attributes: Record<string, unknown>;
  service_name: string;
}

export interface TraceSession {
  schema_version: string;
  session_id: string;
  intent_id: string;
  intent_label: string;
  trace_mode: 'simulation' | 'otel';
  trace_id: string;
  root_span_id?: string;
  parent_span_id?: string;
  events: TraceEvent[];
  status: 'queued' | 'running' | 'success' | 'error';
  total_duration_ms: number;
  error_at_fn_id?: string;
}

export interface FixSuggestion {
  explanation: string;
  fix: string;
  code_diff?: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface ApiEnvelope<T = unknown> {
  schema_version: string;
  success: boolean;
  error?: string;
  data: T;
}

export type BlockStatus = 'idle' | 'calling' | 'returned' | 'error' | 'dimmed';

export interface BlockState {
  status: BlockStatus;
  stepNumber?: number;
  inputs?: RuntimeValue[];
  outputs?: RuntimeValue[];
  error?: string;
  durationMs?: number;
}
