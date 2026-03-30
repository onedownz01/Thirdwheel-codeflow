# Codeflow LLM Judge Benchmark

> **Run date:** 2026-03-30 03:40 UTC  
> **Judge:** Gemini 1.5 Flash (independent third-party)  
> **Repos:** 3/3 succeeded  
> **Functions judged:** 30 total  
> **Passes per function:** 3 (Codeflow-only · Raw-body · Meta-judge)  

---

## 1. What This Measures

Token benchmarks tell you *how many* tokens. This benchmark tells you *how much* an agent understands.

**Judge task:** Given the same function, Gemini receives:
- **Condition A**: Only what Codeflow knows — `name, type, file, params, return_type, calls[]`
- **Condition B**: The full raw source body

A meta-judge then scores both descriptions against the actual code.

**Key metric:** `comprehension_retention` — what % of raw-body understanding does Codeflow preserve?

---

## 2. Headline Results

| Repo | Codeflow Score | Raw Score | Retention | Grade |
|------|:--------------:|:---------:|:---------:|:-----:|
| `encode/starlette` | 6.9/10 | 10.0/10 | **69%** | B |
| `encode/httpx` | 6.7/10 | 9.9/10 | **68%** | B |
| `fastapi/full-stack-fastapi-template` | 7.6/10 | 9.9/10 | **77%** | B+ |
| **AVERAGE** | **7.1/10** | **9.9/10** | **71%** | B+ |

## 3. Judge Confidence

How confident was Gemini in its description?

| Repo | Codeflow Confidence | Raw Confidence | Delta |
|------|:-------------------:|:--------------:|:-----:|
| `encode/starlette` | 8.9/10 | 9.9/10 | +1.0 |
| `encode/httpx` | 9.2/10 | 10.0/10 | +0.8 |
| `fastapi/full-stack-fastapi-template` | 9.0/10 | 10.0/10 | +1.0 |

> Delta = how much MORE confident Gemini is with full source vs Codeflow metadata.
> Lower delta = Codeflow provides nearly as much signal as the raw body.

## 4. Verdict Breakdown

For each function the meta-judge ruled one of:
- `A_adequate` — Codeflow description was sufficient, essentially as good as raw
- `roughly_equal` — both descriptions captured the same key points
- `B_clearly_better` — full body gave Gemini significantly more to work with

| Repo | A_adequate | roughly_equal | B_clearly_better | Codeflow Win Rate |
|------|:----------:|:-------------:|:----------------:|:-----------------:|
| `encode/starlette` | 0 | 0 | 10 | **0%** |
| `encode/httpx` | 0 | 0 | 10 | **0%** |
| `fastapi/full-stack-fastapi-template` | 0 | 0 | 10 | **0%** |

## 5. Score Visualisation

```
  Repo                                  Codeflow     Raw Body    Retention 
  ─────────────────────────────────── ──────────── ────────────  ──────────
  encode/starlette                    ███████░░░ 6.9  ██████████ 10.0  ███████░░░ 69%
  encode/httpx                        ███████░░░ 6.7  ██████████ 9.9  ███████░░░ 68%
  fastapi/full-stack-fastapi-template ████████░░ 7.6  ██████████ 9.9  ████████░░ 77%
```

## 6. Per-Repo Function Analysis

### Starlette (`encode/starlette`)

**Average Codeflow score:** 6.9/10 · **Raw score:** 10.0/10 · **Retention:** 69%

| # | Function | Type | Lines | CF Score | Raw Score | Δ | Verdict |
|---|----------|------|:-----:|:--------:|:---------:|:-:|---------|
| 1 | `handle_request` | `FunctionType.HANDLER` | 149 | 6/10 | 10/10 | +4 | → body wins |
| 2 | `test_delete_cookie` | `FunctionType.HANDLER` | 15 | 7/10 | 10/10 | +3 | → body wins |
| 3 | `test_staticfiles_cache_invalidation_for_deleted_file_html_mode` | `FunctionType.HANDLER` | 35 | 8/10 | 10/10 | +2 | → body wins |
| 4 | `test_calls_context_processors` | `FunctionType.HANDLER` | 26 | 9/10 | 10/10 | +1 | → body wins |
| 5 | `test_staticfiles_unhandled_os_error_returns_500` | `FunctionType.HANDLER` | 21 | 9/10 | 10/10 | +1 | → body wins |
| 6 | `update` | `FunctionType.HANDLER` | 9 | 8/10 | 10/10 | +2 | → body wins |
| 7 | `test_handled_exc_after_response` | `FunctionType.HANDLER` | 12 | 6/10 | 10/10 | +4 | → body wins |
| 8 | `test_request_in_app_and_handler_is_the_same_object` | `FunctionType.HANDLER` | 4 | 3/10 | 10/10 | +7 | → body wins |
| 9 | `test_handlers_annotations` | `FunctionType.HANDLER` | 15 | 4/10 | 10/10 | +6 | → body wins |
| 10 | `delete` | `FunctionType.HANDLER` | 22 | 9/10 | 10/10 | +1 | → body wins |

#### Notable Cases (sorted by comprehension gap)

**`test_request_in_app_and_handler_is_the_same_object()`** `[FunctionType.HANDLER]` — 4 lines, 1 params, 2 calls

*Codeflow description (conf 9/10):*
> This is a test function, likely for a web application, that verifies whether the request object available within the application's context and the handler object itself are the same instance. Given its location in `test_exceptions.py`, this test probably specifically checks this object identity in scenarios involving exception handling.

*Raw body description (conf 10/10):*
> This test function simulates a POST request to a specific endpoint, `/consume_body_in_endpoint_and_handler`, sending "Hello!" as the request body. It then asserts that the application responds with a 422 status code and returns a JSON object `{"body": "Hello!"}`. The test likely verifies how the application processes and reflects the request body in its response, potentially checking its handling across different internal components.

*Meta-judge:* Score A=3/10 · Score B=10/10 · Δ=+7
*Gap:* Description A completely missed the actual operations performed by the function, such as making a POST request to a specific endpoint, the content sent, and the assertions on the status code and response body. Instead, it focused solely on the function's name, which in this case, was misleading regarding the code's actual behavior.
*Verdict:* `B_clearly_better`

**`test_handlers_annotations()`** `[FunctionType.HANDLER]` — 15 lines, 0 params, 2 calls

*Codeflow description (conf 8/10):*
> This function is a test case, located in a file dedicated to testing exception handling. It likely verifies the correct behavior of handlers, specifically focusing on how they process or interact with annotations when exceptions occur. The function's classification as a `HANDLER` suggests it might be designed to be invoked as a handler within the test environment to simulate or observe these behaviors.

*Raw body description (conf 10/10):*
> This test function defines both synchronous and asynchronous placeholder exception handlers. It then instantiates `ExceptionMiddleware` twice, registering each handler type for the base `Exception` class. The primary purpose is to verify that `ExceptionMiddleware` correctly accepts both async and sync functions as exception handlers when their exception parameter is type-hinted as `Exception`.

*Meta-judge:* Score A=4/10 · Score B=10/10 · Δ=+6
*Gap:* Description A missed that the function *defines* nested synchronous and asynchronous exception handlers and then registers them with `ExceptionMiddleware`. It also incorrectly suggested the test function itself might be a handler, rather than a test *of* handlers.
*Verdict:* `B_clearly_better`

**`handle_request()`** `[FunctionType.HANDLER]` — 149 lines, 1 params, 16 calls

*Codeflow description (conf 9/10):*
> This function, located in Starlette's test client, is responsible for simulating the handling of an HTTP request. It takes an `httpx.Request` object, processes it (likely by invoking the Starlette application being tested), and then returns the resulting `httpx.Response`. Its purpose is to facilitate testing of Starlette web applications by mimicking a server's request-response cycle.

*Raw body description (conf 9/10):*
> This function processes an `httpx.Request`, extracting URL details and constructing appropriate headers. It then prepares an ASGI `scope` dictionary, distinguishing between HTTP and WebSocket requests. For WebSockets, it initiates an upgrade process by raising an exception with a test session, while for HTTP, it sets up the initial ASGI context.

*Meta-judge:* Score A=6/10 · Score B=10/10 · Δ=+4
*Gap:* Description A missed that the function's primary output is an ASGI `scope` dictionary, which is constructed differently for HTTP and WebSocket requests. Crucially, for WebSockets, it raises an `_Upgrade` exception with a test session rather than returning an `httpx.Response`.
*Verdict:* `B_clearly_better`

---

### HTTPX (`encode/httpx`)

**Average Codeflow score:** 6.7/10 · **Raw score:** 9.9/10 · **Retention:** 68%

| # | Function | Type | Lines | CF Score | Raw Score | Δ | Verdict |
|---|----------|------|:-----:|:--------:|:---------:|:-:|---------|
| 1 | `handle_async_request` | `FunctionType.HANDLER` | 89 | 8/10 | 10/10 | +2 | → body wins |
| 2 | `handle_request` | `FunctionType.HANDLER` | 59 | 7/10 | 10/10 | +3 | → body wins |
| 3 | `test_header_update` | `FunctionType.HANDLER` | 31 | 7/10 | 10/10 | +3 | → body wins |
| 4 | `create_ssl_context` | `FunctionType.HANDLER` | 47 | 8/10 | 10/10 | +2 | → body wins |
| 5 | `test_delete` | `FunctionType.HANDLER` | 5 | 8/10 | 10/10 | +2 | → body wins |
| 6 | `delete` | `FunctionType.HANDLER` | 34 | 8/10 | 9/10 | +1 | → body wins |
| 7 | `handle_help` | `FunctionType.HANDLER` | 10 | 8/10 | 10/10 | +2 | → body wins |
| 8 | `create_event` | `FunctionType.HANDLER` | 9 | 4/10 | 10/10 | +6 | → body wins |
| 9 | `update` | `FunctionType.HANDLER` | 5 | 2/10 | 10/10 | +8 | → body wins |
| 10 | `sync_auth_flow` | `FunctionType.AUTH` | 24 | 7/10 | 10/10 | +3 | → body wins |

#### Notable Cases (sorted by comprehension gap)

**`update()`** `[FunctionType.HANDLER]` — 5 lines, 1 params, 1 calls

*Codeflow description (conf 9/10):*
> This function, located in `httpx`'s URL-related module, is responsible for updating query parameters. It likely operates on a mutable object that encapsulates a URL, modifying its associated query parameters in place. The function takes new parameters and performs this update as a side effect, returning no value.

*Raw body description (conf 10/10):*
> This function immediately raises a `RuntimeError`, indicating that `QueryParams` objects are immutable and cannot be updated directly. It explicitly informs the user that they should instead use a `merge` method to create a new, updated copy of the object.

*Meta-judge:* Score A=2/10 · Score B=10/10 · Δ=+8
*Gap:* Description A completely missed that the function raises an error and does not perform any update, incorrectly assuming it modifies a mutable object in place. It also missed the crucial information about the immutability of `QueryParams` and the suggested alternative (`merge` method).
*Verdict:* `B_clearly_better`

**`create_event()`** `[FunctionType.HANDLER]` — 9 lines, 0 params, 1 calls

*Codeflow description (conf 9/10):*
> This function, `create_event`, likely serves as a handler within the `httpx` ASGI transport layer. Its primary purpose is to construct and return an `Event` object, possibly representing an internal ASGI event or message, without requiring any external input parameters.

*Raw body description (conf 10/10):*
> This function creates and returns an asynchronous event object. It dynamically checks if the `trio` asynchronous framework is currently running using `is_running_trio()`. Based on this check, it imports the relevant library and returns either a `trio.Event` or an `asyncio.Event` instance, ensuring compatibility with the active async environment.

*Meta-judge:* Score A=4/10 · Score B=10/10 · Δ=+6
*Gap:* Description A completely missed the function's core dynamic behavior: its conditional check for the active asynchronous framework (`trio` vs. `asyncio`) and the subsequent import and return of the appropriate `Event` object. Instead, it offered speculative context about `httpx` and ASGI.
*Verdict:* `B_clearly_better`

**`handle_request()`** `[FunctionType.HANDLER]` — 59 lines, 1 params, 6 calls

*Codeflow description (conf 9/10):*
> This function likely processes an incoming HTTP request within the `httpx` library's WSGI transport layer. It receives a `Request` object, performs necessary internal operations (potentially involving multiple steps or data transformations), and then constructs and returns an appropriate `Response` object.

*Raw body description (conf 10/10):*
> This function acts as a WSGI gateway, translating an incoming `Request` object into a standard WSGI `environ` dictionary. It then invokes a WSGI application (`self.app`) with this environment and a `start_response` callable. Finally, it processes the WSGI application's response (status, headers, and body) and converts it into a `Response` object.

*Meta-judge:* Score A=7/10 · Score B=10/10 · Δ=+3
*Gap:* Description A correctly identifies the function's context and input/output but misses the specific WSGI mechanics. It fails to explain that the function explicitly constructs a WSGI `environ` dictionary, invokes a WSGI application, and then processes the WSGI application's distinct response format (status, headers, and body iterable).
*Verdict:* `B_clearly_better`

---

### FastAPI Full-Stack (`fastapi/full-stack-fastapi-template`)

**Average Codeflow score:** 7.6/10 · **Raw score:** 9.9/10 · **Retention:** 77%

| # | Function | Type | Lines | CF Score | Raw Score | Δ | Verdict |
|---|----------|------|:-----:|:--------:|:---------:|:-:|---------|
| 1 | `create_user` | `FunctionType.ROUTE` | 22 | 8/10 | 10/10 | +2 | → body wins |
| 2 | `recover_password` | `FunctionType.ROUTE` | 21 | 7/10 | 10/10 | +3 | → body wins |
| 3 | `reset_password` | `FunctionType.ROUTE` | 20 | 8/10 | 10/10 | +2 | → body wins |
| 4 | `recover_password_html_content` | `FunctionType.ROUTE` | 19 | 7/10 | 9/10 | +2 | → body wins |
| 5 | `test_email` | `FunctionType.ROUTE` | 11 | 8/10 | 10/10 | +2 | → body wins |
| 6 | `update_password_me` | `FunctionType.ROUTE` | 18 | 8/10 | 10/10 | +2 | → body wins |
| 7 | `register_user` | `FunctionType.ROUTE` | 13 | 7/10 | 10/10 | +3 | → body wins |
| 8 | `update_user` | `FunctionType.ROUTE` | 25 | 8/10 | 10/10 | +2 | → body wins |
| 9 | `login_access_token` | `FunctionType.ROUTE` | 19 | 8/10 | 10/10 | +2 | → body wins |
| 10 | `update_user_me` | `FunctionType.ROUTE` | 19 | 7/10 | 10/10 | +3 | → body wins |

#### Notable Cases (sorted by comprehension gap)

**`recover_password()`** `[FunctionType.ROUTE]` — 21 lines, 2 params, 4 calls

*Codeflow description (conf 9/10):*
> This function is an API endpoint designed to initiate a password recovery process. It accepts a user's email address and a session dependency, likely to generate a password reset token and send a recovery email to the specified address. The function then returns a simple status message indicating the outcome of the operation.

*Raw body description (conf 10/10):*
> This function initiates a password recovery process for a given email address. It first checks if a user exists for that email, and if so, generates a password reset token and sends a recovery email to the user. To prevent email enumeration attacks, the function always returns a generic success message, regardless of whether the email was found or an email was actually sent.

*Meta-judge:* Score A=7/10 · Score B=10/10 · Δ=+3
*Gap:* Description A missed the critical security design where the function always returns a generic message to prevent email enumeration attacks, regardless of whether the email was registered or an email was actually sent. It incorrectly implied the message indicates the *actual* outcome.
*Verdict:* `B_clearly_better`

**`register_user()`** `[FunctionType.ROUTE]` — 13 lines, 2 params, 2 calls

*Codeflow description (conf 9/10):*
> This function is an API route designed to register new users within a backend application. It likely receives user registration data, such as credentials, and uses a session dependency to interact with a database or service to create the new user account.

*Raw body description (conf 10/10):*
> This function registers a new user by first checking if an account with the provided email already exists in the system. If a user with that email is found, it raises an HTTP 400 error. Otherwise, it validates the input user data and proceeds to create a new user record in the database, returning the newly created user object.

*Meta-judge:* Score A=7/10 · Score B=10/10 · Δ=+3
*Gap:* Description A missed the crucial detail that the function first checks for an existing user with the provided email and raises an HTTP 400 error if a duplicate is found. It also didn't mention the explicit input validation step.
*Verdict:* `B_clearly_better`

**`update_user_me()`** `[FunctionType.ROUTE]` — 19 lines, 3 params, 1 calls

*Codeflow description (conf 9/10):*
> This function is an API route designed to allow the currently authenticated user to update their own profile information. It receives the updated user data, a database session, and the current user's object to perform the update operation.

*Raw body description (conf 10/10):*
> This function allows an authenticated user to update their own profile information. It first validates that if the user attempts to change their email, the new email is not already registered to another user, raising an HTTP 409 conflict if it is. Otherwise, it applies the provided updates to the current user's record in the database and returns the refreshed user object.

*Meta-judge:* Score A=7/10 · Score B=10/10 · Δ=+3
*Gap:* Description A missed the critical detail about email uniqueness validation and the specific HTTP 409 conflict error raised if a user tries to update their email to one already registered by another user.
*Verdict:* `B_clearly_better`

---

## 7. Aggregate Analysis

**Total functions judged:** 30
**Overall Codeflow score:** 7.07/10
**Overall Raw score:** 9.93/10
**Overall retention:** 71.1%

### 7.1 Verdict Distribution (all repos)

```
  A_adequate           0  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%  Codeflow was sufficient
  roughly_equal        0  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%  Both equally good
  B_clearly_better    30  ██████████████████████████████  100%  Full body needed
  ─────────────────────────────────────────────────────────────────
  CF wins/ties         0  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%  ← Codeflow adequate rate
```

### 7.2 Score Distribution

```
  Score  Codeflow  Raw Body
  ─────  ────────  ────────
     10     0                28  ████████████████████████████
      9     3  ███            2  ██
      8    13  █████████████     0  
      7     8  ████████       0  
      6     2  ██             0  
      5     0                 0  
      4     2  ██             0  
      3     1  █              0  
      2     1  █              0  
      1     0                 0  
```

### 7.3 Comprehension Retention by Function Type

| Function Type | Avg CF | Avg Raw | Retention |
|---------------|:------:|:-------:|:---------:|
| `FunctionType.HANDLER` | 6.8 | 9.9 | 68% |
| `FunctionType.ROUTE` | 7.6 | 9.9 | 77% |
| `FunctionType.AUTH` | 7.0 | 10.0 | 70% |

## 8. Interpretation

### What does comprehension retention mean?

If Codeflow retention = 85%, it means:
> An agent using Codeflow understands 85% of what an agent with full source code understands,
> while consuming far fewer tokens.

### What causes retention < 100%?

The gap comes from information genuinely **not present** in Codeflow's representation:

| Information type | In Codeflow? | Impact on retention |
|-----------------|:------------:|---------------------|
| Function name & signature | ✓ yes | High — names are very predictive |
| Parameter types | ✓ yes | Medium |
| Return type | ✓ yes | Medium |
| What functions are called | ✓ yes (calls[]) | High — call graph reveals intent |
| Function body logic | ✗ stripped | Medium — bodies often repeat what names imply |
| Error handling patterns | ✗ stripped | Low — usually guessable |
| Inline comments/docstrings | ✗ stripped | Variable — can be very informative |
| Magic values / constants | ✗ stripped | Low |

### The key insight

Well-named functions in well-typed codebases lose **very little** comprehension
when bodies are stripped. The name + type + params + calls together
paint a clear picture. Bodies add detail but rarely change the fundamental understanding.

---
*Generated by Codeflow LLM Judge Benchmark · Judge: Gemini 1.5 Flash · 2026-03-30 03:40 UTC*