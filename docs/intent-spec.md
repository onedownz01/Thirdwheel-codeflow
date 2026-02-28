# Intent Spec v1

## Canonical ID Pattern
`<domain>.<action>[.<target>]`

Examples:
- `auth.signup.submit`
- `discovery.search.execute`
- `api.post.users`
- `network.post.checkout`

## Domains
- `auth`
- `discovery`
- `content`
- `profile`
- `payments`
- `admin`
- `api`
- `network`
- `actions`

## Evidence Weights
- `backend_route`: 0.88-0.95
- `ui_event`: 0.70-0.85
- `form_action`: 0.65-0.82
- `router_transition`: 0.60-0.80
- `network_mutation`: 0.40-0.65
- `symbol_heuristic`: 0.30-0.55

## Confidence Policy
- `>= 0.85`: `verified`
- `>= 0.50 and < 0.85`: `observed`
- `< 0.50`: `candidate`

## KPI Baseline
- recall target: `>= 0.90`
- precision floor: `>= 0.75`
- intent-to-trace linkage: `>= 0.95`
- secret leakage: `0`
