from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "2.0.0"


class FunctionType(str, Enum):
    COMPONENT = "component"
    HOOK = "hook"
    ROUTE = "route"
    HANDLER = "handler"
    SERVICE = "service"
    DB = "db"
    AUTH = "auth"
    UTIL = "util"
    OTHER = "other"


class IntentStatus(str, Enum):
    CANDIDATE = "candidate"
    OBSERVED = "observed"
    VERIFIED = "verified"


class TraceMode(str, Enum):
    SIMULATION = "simulation"
    OTel = "otel"
    LIVE = "live"


class EvidenceKind(str, Enum):
    UI_EVENT = "ui_event"
    FORM_ACTION = "form_action"
    ROUTER_TRANSITION = "router_transition"
    NETWORK_MUTATION = "network_mutation"
    BACKEND_ROUTE = "backend_route"
    SYMBOL_HEURISTIC = "symbol_heuristic"
    CLI_COMMAND = "cli_command"
    SERVER_ACTION = "server_action"


class Param(BaseModel):
    name: str
    type: str = "any"
    direction: Literal["in", "out"] = "in"


class IntentEvidence(BaseModel):
    kind: EvidenceKind
    source_file: str
    line: int = 0
    symbol: str = ""
    excerpt: str = ""
    weight: float = 0.0


class ParsedFunction(BaseModel):
    id: str
    name: str
    file: str
    type: FunctionType
    params: list[Param] = Field(default_factory=list)
    line: int = 0
    description: str = ""
    calls: list[str] = Field(default_factory=list)
    called_by: list[str] = Field(default_factory=list)


class Intent(BaseModel):
    id: str
    canonical_id: str
    label: str
    icon: str
    trigger: str
    handler_fn_id: str
    source_file: str
    group: str
    flow_ids: list[str] = Field(default_factory=list)
    hop_count: int = 0
    status: IntentStatus = IntentStatus.CANDIDATE
    confidence: float = 0.0
    evidence: list[IntentEvidence] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    frequency: int = 0
    failure_rate: float = 0.0


class Edge(BaseModel):
    id: str
    source: str
    target: str
    type: Literal["calls", "imports", "triggers"] = "calls"


class ParsedRepo(BaseModel):
    schema_version: str = SCHEMA_VERSION
    repo: str
    branch: str
    functions: list[ParsedFunction]
    intents: list[Intent]
    edges: list[Edge]
    file_count: int
    parsed_at: str


class TraceEventType(str, Enum):
    CALL = "call"
    RETURN = "return"
    ERROR = "error"
    INTENT_START = "intent_start"
    INTENT_END = "intent_end"
    WARNING = "warning"


class RuntimeValue(BaseModel):
    name: str
    value: Any
    type_name: str
    is_sensitive: bool = False


class TraceEvent(BaseModel):
    event_type: TraceEventType
    fn_id: str
    fn_name: str
    file: str
    line: int
    timestamp_ms: float
    inputs: list[RuntimeValue] = Field(default_factory=list)
    outputs: list[RuntimeValue] = Field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_line: Optional[int] = None
    duration_ms: Optional[float] = None
    sequence: int = 0
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    service_name: str = "codeflow"


class TraceSession(BaseModel):
    schema_version: str = SCHEMA_VERSION
    session_id: str
    intent_id: str
    intent_label: str
    trace_mode: TraceMode = TraceMode.SIMULATION
    trace_id: str = ""
    root_span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    events: list[TraceEvent] = Field(default_factory=list)
    status: Literal["queued", "running", "success", "error"] = "queued"
    total_duration_ms: float = 0.0
    error_at_fn_id: Optional[str] = None


class IntentOccurrence(BaseModel):
    schema_version: str = SCHEMA_VERSION
    occurrence_id: str
    repo: str
    intent_id: str
    trace_id: str
    session_id: str
    outcome: Literal["success", "error"]
    latency_ms: float
    started_at: str


class FixRequest(BaseModel):
    session_id: str
    error_fn_id: str
    trace_session: TraceSession
    parsed_repo: ParsedRepo


class FixSuggestion(BaseModel):
    explanation: str
    fix: str
    code_diff: Optional[str] = None
    confidence: Literal["high", "medium", "low"] = "medium"


class ParseRequest(BaseModel):
    repo: str
    token: Optional[str] = None


class TraceStartRequest(BaseModel):
    repo: str
    intent_id: str
    mode: TraceMode = TraceMode.SIMULATION
    simulate_error_at_step: Optional[int] = None
    # Live mode only
    project_root: str = ""
    command: list[str] = []


class IngestedSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    service_name: str = "unknown-service"
    start_time_ms: float
    end_time_ms: float
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: Literal["ok", "error"] = "ok"
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class TraceIngestRequest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    session_id: Optional[str] = None
    trace_id: str
    spans: list[IngestedSpan] = Field(default_factory=list)


class ParseProgress(BaseModel):
    schema_version: str = SCHEMA_VERSION
    repo: str
    progress: int
    step: str


class ApiEnvelope(BaseModel):
    schema_version: str = SCHEMA_VERSION
    success: bool = True
    error: Optional[str] = None
    data: Any = None
