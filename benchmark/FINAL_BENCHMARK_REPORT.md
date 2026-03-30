# Codeflow Benchmark Report

> **Run date:** 2026-03-30 03:58 UTC  
> **Repos tested:** 14/15  
> **Passes:** Token Efficiency · Comprehension Quality · LLM Judge (Gemini 2.5 Flash)  
> **Functions judged:** 70 (5/repo)  
> **Tokenizer:** `cl100k_base` (tiktoken — GPT-4/Claude proxy ±5%)  

---

## Abstract

Codeflow converts raw source repositories into structured `ParsedRepo` JSON for LLM agents.
This report quantifies two complementary questions:

1. **How many tokens does it save?** (Pass 1 — Token Efficiency)
2. **How much does an agent actually understand?** (Pass 2 + 3 — Comprehension Quality + LLM Judge)

Key findings across all repos:
- **Average token reduction:** 30.4%
- **Average function recall:** 100%
- **Average comprehension retention (LLM judge):** 69%

## 1. Token Efficiency

| # | Repo | Cat | Raw Tokens | CF Tokens | Saved | Ratio | Regime |
|---|------|:---:|:----------:|:---------:|:-----:|:-----:|--------|
| 1 | `fastapi/full-stack-fastapi-template` | A | 75,035 | 31,286 | **58.3%** | 2.40× | High compression |
| 2 | `zauberzeug/nicegui` | A | 81,128 | 47,034 | **42.0%** | 1.72× | High compression |
| 3 | `tiangolo/fastapi` | B | 31,506 | 33,527 | **-6.4%** | 0.94× | Near-parity |
| 4 | `pallets/flask` | B | 135,633 | 114,082 | **15.9%** | 1.19× | Moderate compression |
| 5 | `encode/starlette` | B | 141,009 | 135,492 | **3.9%** | 1.04× | Near-parity |
| 6 | `anthropics/anthropic-sdk-python` | C | 191,843 | 145,706 | **24.0%** | 1.32× | Moderate compression |
| 7 | `openai/openai-python` | C | 183,840 | 181,780 | **1.1%** | 1.01× | Near-parity |
| 8 | `encode/httpx` | C | 134,082 | 80,663 | **39.8%** | 1.66× | Moderate compression |
| 9 | `psf/requests` | C | 85,992 | 58,957 | **31.4%** | 1.46× | Moderate compression |
| 10 | `httpie/httpie` | D | 119,789 | 93,546 | **21.9%** | 1.28× | Moderate compression |
| 11 | `pallets/click` | D | 166,675 | 126,972 | **23.8%** | 1.31× | Moderate compression |
| 12 | `Textualize/rich` | E | 292,337 | 63,449 | **78.3%** | 4.61× | High compression |
| 13 | `pydantic/pydantic` | E | 380,113 | 196,655 | **48.3%** | 1.93× | High compression |
| 14 | `sqlalchemy/sqlalchemy` | E | 281,448 | 161,589 | **42.6%** | 1.74× | High compression |
| | **TOTAL** | | **2,300,430** | **1,470,738** | **36.1%** | 1.56× | |

### Token Visualisation
```
  Repo                                        Savings  Bar (% saved)
  ────────────────────────────────────────── ────────  ─────────────────────────
  fastapi/full-stack-fastapi-template           58.3%  ███████████████░░░░░░░░░░
  zauberzeug/nicegui                            42.0%  ███████████░░░░░░░░░░░░░░
  tiangolo/fastapi                              -6.4%  ░░░░░░░░░░░░░░░░░░░░░░░░░░░
  pallets/flask                                 15.9%  ████░░░░░░░░░░░░░░░░░░░░░
  encode/starlette                               3.9%  █░░░░░░░░░░░░░░░░░░░░░░░░
  anthropics/anthropic-sdk-python               24.0%  ██████░░░░░░░░░░░░░░░░░░░
  openai/openai-python                           1.1%  ░░░░░░░░░░░░░░░░░░░░░░░░░
  encode/httpx                                  39.8%  ██████████░░░░░░░░░░░░░░░
  psf/requests                                  31.4%  ████████░░░░░░░░░░░░░░░░░
  httpie/httpie                                 21.9%  █████░░░░░░░░░░░░░░░░░░░░
  pallets/click                                 23.8%  ██████░░░░░░░░░░░░░░░░░░░
  Textualize/rich                               78.3%  ████████████████████░░░░░
  pydantic/pydantic                             48.3%  ████████████░░░░░░░░░░░░░
  sqlalchemy/sqlalchemy                         42.6%  ███████████░░░░░░░░░░░░░░
```

## 2. Comprehension Quality

Ground truth extracted via `ast.walk` (Python) and regex (routes, JS functions).

| Repo | Cat | Fns Found | Fn Recall | Route Recall | Return Type % | Docstring % | Intents |
|------|:---:|:---------:|:---------:|:------------:|:-------------:|:-----------:|:-------:|
| `fastapi/full-stack-fastapi-template` | A | 394/354 | 100% | 100% | 100% | 13% | 44 |
| `zauberzeug/nicegui` | A | 693/677 | 100% | 100% | 100% | 23% | 74 |
| `tiangolo/fastapi` | B | 393/393 | 100% | 70% | 100% | 3% | 122 |
| `pallets/flask` | B | 1466/1466 | 100% | 81% | 100% | 18% | 268 |
| `encode/starlette` | B | 1478/1478 | 100% | 50% | 100% | 5% | 341 |
| `anthropics/anthropic-sdk-python` | C | 1335/1335 | 100% | 100% | 100% | 17% | 396 |
| `openai/openai-python` | C | 1425/1425 | 100% | 50% | 100% | 7% | 675 |
| `encode/httpx` | C | 1134/1134 | 100% | 100% | 100% | 20% | 158 |
| `psf/requests` | C | 670/670 | 100% | 50% | 100% | 36% | 185 |
| `httpie/httpie` | D | 911/911 | 100% | 100% | 100% | 15% | 358 |
| `pallets/click` | D | 1412/1412 | 100% | 100% | 100% | 23% | 332 |
| `Textualize/rich` | E | 598/598 | 100% | 100% | 100% | 52% | 217 |
| `pydantic/pydantic` | E | 2032/2026 | 100% | 50% | 100% | 12% | 462 |
| `sqlalchemy/sqlalchemy` | E | 1548/1548 | 100% | 50% | 100% | 20% | 469 |

## 3. LLM Judge — Semantic Comprehension

**Judge:** Gemini 2.5 Flash (independent, not Claude — avoids circularity)

For each repo, 5 functions are judged in 3 passes:
- **Pass A** — Codeflow metadata only (name, type, params, return_type, docstring, calls)
- **Pass B** — Full raw source body
- **Meta-judge** — scores both descriptions against actual source

| Repo | Cat | CF Score | Raw Score | Retention | Grade |
|------|:---:|:--------:|:---------:|:---------:|:-----:|
| `fastapi/full-stack-fastapi-template` | A | 7.2/10 | 9.4/10 | **77%** | B+ |
| `zauberzeug/nicegui` | A | 5.2/10 | 9.6/10 | **54%** | C |
| `tiangolo/fastapi` | B | 7.0/10 | 10.0/10 | **70%** | B+ |
| `pallets/flask` | B | 7.2/10 | 9.0/10 | **80%** | A |
| `encode/starlette` | B | 6.2/10 | 8.8/10 | **70%** | B+ |
| `anthropics/anthropic-sdk-python` | C | 7.0/10 | 9.4/10 | **74%** | B+ |
| `openai/openai-python` | C | 6.0/10 | 9.6/10 | **62%** | B |
| `encode/httpx` | C | 6.8/10 | 9.4/10 | **72%** | B+ |
| `psf/requests` | C | 7.0/10 | 7.8/10 | **90%** | A |
| `httpie/httpie` | D | 3.8/10 | 8.4/10 | **45%** | D |
| `pallets/click` | D | 6.6/10 | 9.4/10 | **70%** | B+ |
| `Textualize/rich` | E | 6.8/10 | 8.2/10 | **83%** | A |
| `pydantic/pydantic` | E | 5.6/10 | 10.0/10 | **56%** | C |
| `sqlalchemy/sqlalchemy` | E | 5.6/10 | 8.8/10 | **64%** | B |
| **AVERAGE** | | **6.3/10** | **9.1/10** | **69%** | B |

### Verdict Distribution

```
  A_adequate               2  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  3%  CF adequate — metadata sufficient
  roughly_equal            0  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%  Roughly equal — both captured it
  B_clearly_better        57  ████████████████████████░░░░░░  81%  Body clearly better — CF missed it
  ──────────────────────────────────────────────────────────────────────
  CF adequate rate: 2/70 = 3%
```

### Retention by Category

| Category | Repos | Avg CF | Avg Raw | Retention | Interpretation |
|----------|:-----:|:------:|:-------:|:---------:|----------------|
| **A — Python App Code** | 2 | 6.2 | 9.5 | **65%** | CF's sweet spot — app code with routes/services |
| **B — Python Frameworks** | 3 | 6.8 | 9.3 | **73%** | Framework code — moderate density, fewer routes |
| **C — Python Libraries / SDKs** | 4 | 6.7 | 9.1 | **74%** | Library/SDK — typed but implementation-heavy |
| **D — CLI Tools** | 2 | 5.2 | 8.9 | **58%** | CLI tools — command patterns well-captured |
| **E — Mixed / Large Libraries** | 3 | 6.0 | 9.0 | **67%** | Large libs — diverse, body logic matters more |

## 4. Per-Repo Detail

### `fastapi/full-stack-fastapi-template` — FastAPI Full-Stack App
> Category A · Full-stack app: FastAPI backend + React frontend; routes, services, auth

| Metric | Value |
|--------|------:|
| Files fetched | 45 py + 75 js/ts |
| Source lines | 11,129 |
| Ground truth fns | 141 py + 213 js |
| Codeflow fns | 394 (100% recall) |
| Intents | 44 (100% route recall) |
| Docstrings captured | 52 (13% coverage) |
| Raw tokens | 75,035 |
| Codeflow tokens | 31,286 |
| Token saving | **58.3%** (2.40×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 92, <FunctionType.ROUTE: 'route'>: 21, <FunctionType.COMPONENT: 'component'>: 163, <FunctionType.HANDLER: 'handler'>: 42, <FunctionType.HOOK: 'hook'>: 3}` |
| Parse time | 0.10s |

**LLM Judge:** CF 7.2/10 · Raw 9.4/10 · Retention **77%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `recover_password` | `FunctionType.ROUTE` | ✓ | 6/10 | 10/10 | +4 | body wins |
| `create_user` | `FunctionType.ROUTE` | ✓ | 7/10 | 10/10 | +3 | body wins |
| `reset_password` | `FunctionType.ROUTE` | ✓ | 7/10 | 9/10 | +2 | body wins |
| `recover_password_html_content` | `FunctionType.ROUTE` | ✓ | 8/10 | 9/10 | +1 | B_clearly_better

**Explanation:**

*   **Description A (Score: 8/10)**
    *   **Strengths:** Accurately infers it's an "API route function" and correctly identifies that it "generates and returns the HTML content" for password recovery. The phrase "page or email" is a good guess given the ambiguity of the docstring and the `Any` return type, hinting at the dual nature of returning email content via a web endpoint. It correctly identifies the use of `email` and `session` for backend operations.
    *   **Weaknesses:** It doesn't explicitly state "HTTP response" (though implied by "API route function"). "Page or email" is slightly less precise than B's description of the content's origin.

*   **Description B (Score: 9/10)**
    *   **Strengths:** Provides a highly accurate and step-by-step description of the function's logic: retrieving the user, generating a token, constructing an HTML email, and explicitly stating that it "returns the HTML content of this password reset email as an HTTP response." The mention of "HTTP response" is a direct observation from the `HTMLResponse` return type in the source.
    *   **Weaknesses:** While very accurate in describing *what* the function does, it shares the same key gap as A regarding the *implication* of returning email content as an HTTP response.

**Key Gap:**
Both descriptions accurately state that the function generates HTML content for a password recovery email and returns it. However, neither explicitly clarifies that the function *itself does not send the email*. Instead, it provides the email's HTML content (and subject) as an HTTP response to the *client* that called the API endpoint. This implies that the actual email sending would be handled by a separate service or process that consumes this HTTP response, or that the endpoint is intended for previewing the email content.

**Verdict: B_clearly_better**
Description B is more precise and detailed, directly observing the `HTMLResponse` return type and clearly outlining the sequence of operations. Description A is excellent given it was generated from metadata only, but B's access to the full source allowed for greater accuracy and specificity regarding the return type and the content's origin. |
| `login_access_token` | `FunctionType.ROUTE` | ✓ | 8/10 | 9/10 | +1 | body wins |

**Biggest gap** — `recover_password()` (Δ=+4):
> CF: This function is an API endpoint designed to initiate the password recovery process. It likely takes a user's email, generates a secure password reset token, and then sends an email containing instruc
> Raw: This function handles password recovery requests by attempting to find a user based on the provided email. If a user is found, it generates a password reset token and sends a recovery email containing
> Gap: Description A completely misses the critical security measure implemented to prevent email enumeration attacks, which involves always returning a generic success message to the client regardless of whether the email address is registered or an email was actually sent.

**Best case** — `recover_password_html_content()` (Δ=+1): Codeflow metadata was essentially as good as the body.

---

### `zauberzeug/nicegui` — NiceGUI — Python UI Framework
> Category A · FastAPI-based Python UI framework; components, routing, event handlers

| Metric | Value |
|--------|------:|
| Files fetched | 113 py + 6 js/ts |
| Source lines | 9,196 |
| Ground truth fns | 663 py + 14 js |
| Codeflow fns | 693 (100% recall) |
| Intents | 74 (100% route recall) |
| Docstrings captured | 156 (23% coverage) |
| Raw tokens | 81,128 |
| Codeflow tokens | 47,034 |
| Token saving | **42.0%** (1.72×) |
| fn_type_index | `{<FunctionType.AUTH: 'auth'>: 17, <FunctionType.OTHER: 'other'>: 625, <FunctionType.HANDLER: 'handler'>: 34, <FunctionType.ROUTE: 'route'>: 13, <FunctionType.DB: 'db'>: 4}` |
| Parse time | 0.07s |

**LLM Judge:** CF 5.2/10 · Raw 9.6/10 · Retention **54%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `example_page` | `FunctionType.ROUTE` | ✗ | 4/10 | 10/10 | +6 | body wins |
| `google_oauth` | `FunctionType.ROUTE` | ✗ | 2/10 | 9/10 | +7 | body wins |
| `google_auth` | `FunctionType.ROUTE` | ✗ | 8/10 | 9/10 | +1 | body wins |
| `item` | `FunctionType.ROUTE` | ✗ | 3/10 | 10/10 | +7 | body wins |
| `checkout` | `FunctionType.ROUTE` | ✗ | 9/10 | 10/10 | +1 | body wins |

**Biggest gap** — `google_oauth()` (Δ=+7):
> CF: This function most likely initiates the Google OAuth 2.0 authentication process. As a web route, it receives an incoming request and then redirects the user's browser to Google's authorization endpoin
> Raw: This asynchronous function handles the callback from a Google OAuth authorization flow. It attempts to authorize the access token and retrieve user information; if successful and valid, it stores this
> Gap: Description A fundamentally misunderstands the function's role in the OAuth flow, incorrectly stating it initiates the process by redirecting to Google. Description B correctly identifies it as the callback handler that processes the response *from* Google.

**Best case** — `google_auth()` (Δ=+1): Codeflow metadata was essentially as good as the body.

---

### `tiangolo/fastapi` — FastAPI — ASGI Framework
> Category B · FastAPI itself; routing, dependency injection, OpenAPI generation

| Metric | Value |
|--------|------:|
| Files fetched | 119 py + 1 js/ts |
| Source lines | 4,972 |
| Ground truth fns | 392 py + 1 js |
| Codeflow fns | 393 (100% recall) |
| Intents | 122 (70% route recall) |
| Docstrings captured | 11 (3% coverage) |
| Raw tokens | 31,506 |
| Codeflow tokens | 33,527 |
| Token saving | **-6.4%** (0.94×) |
| fn_type_index | `{<FunctionType.ROUTE: 'route'>: 126, <FunctionType.OTHER: 'other'>: 253, <FunctionType.HANDLER: 'handler'>: 9, <FunctionType.DB: 'db'>: 4, <FunctionType.SERVICE: 'service'>: 1}` |
| Parse time | 0.03s |

**LLM Judge:** CF 7.0/10 · Raw 10.0/10 · Retention **70%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `read_main` | `FunctionType.ROUTE` | ✗ | 9/10 | 10/10 | +1 | body wins |
| `create_item` | `FunctionType.ROUTE` | ✗ | 8/10 | 10/10 | +2 | body wins |
| `read_item` | `FunctionType.ROUTE` | ✗ | 8/10 | 10/10 | +2 | body wins |
| `update_item` | `FunctionType.ROUTE` | ✗ | 4/10 | 10/10 | +6 | body wins |
| `info` | `FunctionType.ROUTE` | ✗ | 6/10 | 10/10 | +4 | body wins |

**Biggest gap** — `update_item()` (Δ=+6):
> CF: This function is an API route designed to update an existing item. It uses the `item_id` provided as a parameter to identify which item to modify, likely receiving the updated item data in the request
> Raw: This asynchronous function attempts to "update" an item, but it strictly enforces that only the item with `item_id` "plumbus" can be processed. If any other `item_id` is provided, it raises an HTTP 40
> Gap: Description A makes a general assumption about how an update function would work, specifically that it would process new data from a request body, which is not true for this function. Description B correctly identifies the function's unique and strict constraint that only a specific item ("plumbus") can be "updated," and even then, it returns hardcoded data rather than processing new input.

**Best case** — `read_main()` (Δ=+1): Codeflow metadata was essentially as good as the body.

---

### `pallets/flask` — Flask — WSGI Framework
> Category B · Classic Python web framework; blueprints, context, routing

| Metric | Value |
|--------|------:|
| Files fetched | 83 py + 0 js/ts |
| Source lines | 18,390 |
| Ground truth fns | 1466 py + 0 js |
| Codeflow fns | 1466 (100% recall) |
| Intents | 268 (81% route recall) |
| Docstrings captured | 260 (18% coverage) |
| Raw tokens | 135,633 |
| Codeflow tokens | 114,082 |
| Token saving | **15.9%** (1.19×) |
| fn_type_index | `{<FunctionType.ROUTE: 'route'>: 41, <FunctionType.OTHER: 'other'>: 1333, <FunctionType.HANDLER: 'handler'>: 40, <FunctionType.DB: 'db'>: 6, <FunctionType.AUTH: 'auth'>: 2}` |
| Parse time | 0.16s |

**LLM Judge:** CF 7.2/10 · Raw 9.0/10 · Retention **80%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `register` | `FunctionType.ROUTE` | ✓ | 7/10 | 10/10 | +3 | body wins |
| `login` | `FunctionType.ROUTE` | ✓ | 7/10 | 9/10 | +2 | body wins |
| `create` | `FunctionType.ROUTE` | ✓ | 8/10 | 10/10 | +2 | body wins |
| `update` | `FunctionType.ROUTE` | ✓ | 9/10 | 7/10 | -2 | ✓ CF ok |
| `delete` | `FunctionType.ROUTE` | ✓ | 5/10 | 9/10 | +4 | body wins |

**Biggest gap** — `delete()` (Δ=+4):
> CF: This function is a web route within a Flask blog application, specifically designed to delete a blog post. It takes an `id` parameter, which it uses to identify and remove the specified post.
> Raw: This function deletes a specific post from the database, identified by its `id`. It first verifies that the post exists and that the current user is authorized to delete it. After successfully removin
> Gap: Description A completely omits the crucial pre-conditions that the function first verifies the post exists and that the logged-in user is authorized to delete it, which is explicitly stated in the source's docstring.

**Best case** — `update()` (Δ=-2): Codeflow metadata was essentially as good as the body.

---

### `encode/starlette` — Starlette — ASGI Toolkit
> Category B · Low-level ASGI toolkit; middleware, routing, websockets

| Metric | Value |
|--------|------:|
| Files fetched | 67 py + 1 js/ts |
| Source lines | 17,515 |
| Ground truth fns | 1474 py + 4 js |
| Codeflow fns | 1478 (100% recall) |
| Intents | 341 (50% route recall) |
| Docstrings captured | 70 (5% coverage) |
| Raw tokens | 141,009 |
| Codeflow tokens | 135,492 |
| Token saving | **3.9%** (1.04×) |
| fn_type_index | `{<FunctionType.UTIL: 'util'>: 26, <FunctionType.OTHER: 'other'>: 1324, <FunctionType.AUTH: 'auth'>: 91, <FunctionType.HANDLER: 'handler'>: 29, <FunctionType.DB: 'db'>: 8}` |
| Parse time | 0.23s |

**LLM Judge:** CF 6.2/10 · Raw 8.8/10 · Retention **70%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `send_with_compression` | `FunctionType.AUTH` | ✗ | 6/10 | 9/10 | +3 | body wins |
| `requires` | `FunctionType.AUTH` | ✗ | 5/10 | 9/10 | +4 | body wins |
| `decorator` | `FunctionType.AUTH` | ✗ | 6/10 | 9/10 | +3 | body wins |
| `call_next` | `FunctionType.AUTH` | ✗ | 5/10 | 9/10 | +4 | B_clearly_better

---

**Explanation:**

**Description A Analysis:**
*   **"part of Starlette's middleware system"**: Correct, the context strongly suggests this.
*   **"likely handles the next step in an authentication chain"**: This is a guess based on common middleware patterns. While it *could* be used in an auth middleware, the function itself doesn't perform authentication checks. It's a generic mechanism for calling the next app.
*   **"It receives a request"**: Correct, `request: Request` is an argument.
*   **"potentially performs authentication checks"**: Incorrect. The code provided does not perform any authentication logic. It's a plumbing function.
*   **"then calls the subsequent middleware or route handler"**: Correct, `await self.app(...)` does this.
*   **"and finally returns the response"**: Partially correct. The function signature `-> Response` indicates it should return a response, but the provided snippet focuses on managing the ASGI communication streams rather than a direct `return Response` statement.

Description A correctly identifies the high-level purpose of calling the next handler in a middleware chain but makes an unverified assumption about "authentication checks" and completely misses the intricate asynchronous mechanisms (task groups, stream wrapping) that are central to *how* it achieves its goal.

**Description B Analysis (Self-generated based on full source):**
"This `call_next` function is a sophisticated ASGI middleware utility. Its primary role is to asynchronously invoke the subsequent ASGI application (`self.app`) in the request-response chain. It achieves this by launching `self.app` within a dedicated `anyio` task group, allowing for concurrent execution. Crucially, it intercepts and customizes the `receive` and `send` callables that are passed to the inner application. The `receive_or_disconnect` wrapper manages message reception for the inner app, potentially signaling a disconnect if an outer response has already been sent. The `send_no_error` wrapper ensures robust message transmission by gracefully handling `anyio.BrokenResourceError`. This design provides the outer middleware with fine-grained control over the inner application's lifecycle, enabling scenarios like early response generation, exception handling, and precise stream management."

*   **"sophisticated ASGI middleware utility"**: Correct.
*   **"asynchronously invoke the subsequent ASGI application (`self.app`)"**: Correct and precise.
*   **"launching `self.app` within a dedicated `anyio` task group, allowing for concurrent execution"**: Crucial detail, accurately described.
*   **"intercepts and customizes the `receive` and `send` callables"**: This is the most important technical detail, correctly identified.
*   **"The `receive_or_disconnect` wrapper manages message reception... signaling a disconnect"**: Correctly explains the purpose of this wrapper.
*   **"The `send_no_error` wrapper ensures robust message transmission by gracefully handling `anyio.BrokenResourceError`"**: Correctly explains the purpose of this wrapper.
*   **"provides the outer middleware with fine-grained control... enabling scenarios like early response generation, exception handling, and precise stream management"**: Accurately summarizes the benefits of this design.

Description B accurately captures the core mechanisms, including the use of `anyio` task groups and, most importantly, the wrapping of the `receive` and `send` callables, which is fundamental to how ASGI middleware operates. It explains *how* the function works, not just *what* it might be used for. The only minor omission is the specific handling of `http.response.debug` messages, which is a small detail compared to the overall architecture. |
| `build_environ` | `FunctionType.AUTH` | ✓ | 9/10 | 8/10 | -1 | B_clearly_better

**Explanation:**

*   **Description A (Metadata Only):** This description is remarkably accurate and insightful given it only had metadata. It correctly identifies the function's purpose (ASGI to WSGI conversion) and even infers its likely context within Starlette's WSGI middleware, which is an excellent deduction. It's concise and hits all the high-level points. Its score is high because it excels within its constraints.

*   **Description B (Full Source):** This description provides more specific details about the conversion process, as expected from having access to the full source. It accurately highlights the population of standard WSGI keys like request method, paths, query string, and server details. Crucially, it correctly identifies the complex header processing logic, including the transformation into `HTTP_` prefixed or special `CONTENT_` keys.

*   **Key Gap:** Both descriptions miss the explicit mention of the `wsgi.*` keys (e.g., `wsgi.version`, `wsgi.url_scheme`, `wsgi.input`, `wsgi.errors`, etc.). These are fundamental components of a WSGI `environ` and are explicitly set in the source code. For Description B, which had the full source and aims for more detail, this omission is more significant. It also misses the `REMOTE_ADDR` key and the detail about concatenating multiple header values with a comma.

*   **Verdict:** Description B is "clearly better" because it provides a much deeper and more specific understanding of *how* the conversion is performed, detailing the processing of paths, query strings, server information, and especially the complex header transformation. While it has a notable omission (the `wsgi.*` keys), the additional accurate detail it provides about the core conversion logic makes it more informative than Description A, which is necessarily high-level. |

**Biggest gap** — `requires()` (Δ=+4):
> CF: This function is a decorator within Starlette's authentication module, designed to enforce authorization requirements on endpoints. It checks if the incoming request has the specified `scopes` (permis
> Raw: This function is a decorator factory that enforces authorization based on required scopes for web endpoints. It inspects the decorated function for a 'request' or 'websocket' argument, then wraps it t
> Gap: Description A completely misses that the function also handles and secures WebSocket connections, and how it responds differently (closing the connection) compared to HTTP requests.

**Best case** — `build_environ()` (Δ=-1): Codeflow metadata was essentially as good as the body.

---

### `anthropics/anthropic-sdk-python` — Anthropic Python SDK
> Category C · Official Anthropic SDK; typed resources, sync+async client

| Metric | Value |
|--------|------:|
| Files fetched | 120 py + 0 js/ts |
| Source lines | 24,860 |
| Ground truth fns | 1335 py + 0 js |
| Codeflow fns | 1335 (100% recall) |
| Intents | 396 (100% route recall) |
| Docstrings captured | 230 (17% coverage) |
| Raw tokens | 191,843 |
| Codeflow tokens | 145,706 |
| Token saving | **24.0%** (1.32×) |
| fn_type_index | `{<FunctionType.DB: 'db'>: 57, <FunctionType.OTHER: 'other'>: 897, <FunctionType.AUTH: 'auth'>: 15, <FunctionType.UTIL: 'util'>: 352, <FunctionType.HANDLER: 'handler'>: 14}` |
| Parse time | 0.20s |

**LLM Judge:** CF 7.0/10 · Raw 9.4/10 · Retention **74%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `get_auth_headers` | `FunctionType.AUTH` | ✗ | 8/10 | 9/10 | +1 | body wins |
| `get_next_page` | `FunctionType.HANDLER` | ✗ | 8/10 | 10/10 | +2 | body wins |
| `get_api_list` | `FunctionType.HANDLER` | ✗ | 7/10 | 9/10 | +2 | body wins |
| `get_platform` | `FunctionType.HANDLER` | ✗ | 6/10 | 9/10 | +3 | body wins |
| `get_python_runtime` | `FunctionType.HANDLER` | ✗ | 6/10 | 10/10 | +4 | body wins |

**Biggest gap** — `get_python_runtime()` (Δ=+4):
> CF: This function most likely retrieves a string representing the current Python runtime environment. It probably queries system information to obtain details like the Python version or interpreter path, 
> Raw: This function attempts to identify and return the name of the current Python interpreter implementation (e.g., 'CPython', 'PyPy'). It uses the `platform.python_implementation()` method for this purpos
> Gap: Description A fails to mention the specific `platform.python_implementation()` method used and completely misses the crucial error handling mechanism that returns "unknown" on failure.

**Best case** — `get_auth_headers()` (Δ=+1): Codeflow metadata was essentially as good as the body.

---

### `openai/openai-python` — OpenAI Python SDK
> Category C · Official OpenAI SDK; typed resources, extensive API surface

| Metric | Value |
|--------|------:|
| Files fetched | 120 py + 0 js/ts |
| Source lines | 22,884 |
| Ground truth fns | 1425 py + 0 js |
| Codeflow fns | 1425 (100% recall) |
| Intents | 675 (50% route recall) |
| Docstrings captured | 103 (7% coverage) |
| Raw tokens | 183,840 |
| Codeflow tokens | 181,780 |
| Token saving | **1.1%** (1.01×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 1359, <FunctionType.HANDLER: 'handler'>: 13, <FunctionType.AUTH: 'auth'>: 4, <FunctionType.DB: 'db'>: 45, <FunctionType.UTIL: 'util'>: 4}` |
| Parse time | 0.21s |

**LLM Judge:** CF 6.0/10 · Raw 9.6/10 · Retention **62%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `auth_headers` | `FunctionType.AUTH` | ✗ | 4/10 | 10/10 | +6 | body wins |
| `get_next_page` | `FunctionType.HANDLER` | ✗ | 7/10 | 9/10 | +2 | body wins |
| `send_mic_audio` | `FunctionType.HANDLER` | ✗ | 8/10 | 10/10 | +2 | body wins |
| `on_key` | `FunctionType.HANDLER` | ✓ | 3/10 | 9/10 | +6 | body wins |
| `get_api_list` | `FunctionType.HANDLER` | ✗ | 8/10 | 10/10 | +2 | body wins |

**Biggest gap** — `auth_headers()` (Δ=+6):
> CF: This function most likely generates and returns a dictionary of HTTP headers necessary for authenticating requests to the OpenAI API. It probably retrieves an API key from an environment variable or c
> Raw: This function generates a dictionary representing HTTP authorization headers. It retrieves an API key from the object's instance and, if the key is present and not empty, formats it into a "Bearer" to
> Gap: Description A incorrectly assumes the API key is retrieved from an environment variable or client configuration, rather than correctly identifying it as an instance attribute (`self.api_key`). It also completely misses the crucial conditional logic of returning an empty dictionary if the API key is missing or empty.

---

### `encode/httpx` — HTTPX — HTTP Client
> Category C · Full-featured HTTP client; typed, async/sync, transport abstraction

| Metric | Value |
|--------|------:|
| Files fetched | 60 py + 0 js/ts |
| Source lines | 17,753 |
| Ground truth fns | 1134 py + 0 js |
| Codeflow fns | 1134 (100% recall) |
| Intents | 158 (100% route recall) |
| Docstrings captured | 225 (20% coverage) |
| Raw tokens | 134,082 |
| Codeflow tokens | 80,663 |
| Token saving | **39.8%** (1.66×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 932, <FunctionType.DB: 'db'>: 95, <FunctionType.AUTH: 'auth'>: 29, <FunctionType.HANDLER: 'handler'>: 9, <FunctionType.UTIL: 'util'>: 69}` |
| Parse time | 0.14s |

**LLM Judge:** CF 6.8/10 · Raw 9.4/10 · Retention **72%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `sync_auth_flow` | `FunctionType.AUTH` | ✓ | 7/10 | 9/10 | +2 | B_clearly_better

**Reasoning:**

*   **Description A (Score 7):** This description accurately captures the high-level purpose and interaction pattern of the function. It correctly identifies it as a synchronous, multi-step authentication flow that modifies requests, yields them, processes responses, and repeats the cycle. It also provides good contextual examples (challenges, token refresh). However, it misses several key implementation details:
    *   It doesn't explicitly state that `sync_auth_flow` is itself a generator function, though "yields it for sending" implies it.
    *   Crucially, it completely omits the fact that this function *wraps* and orchestrates an *internal* generator (`self.auth_flow`), which is the core mechanism of its design.
    *   It also misses the handling of request and response body reads.

*   **Description B (Score 9):** This description is highly accurate and detailed. It correctly identifies the function as a "generator function" and immediately highlights its primary structural characteristic: "wrapping an internal generator (`self.auth_flow`)". It precisely describes the generator's interaction pattern (yielding requests, expecting responses, feeding them back into the internal flow) and correctly notes that this continues until the internal flow completes. Furthermore, it accurately includes the handling of "necessary request and response body reads." The only minor omissions are explicit mention of "HTTP" (though `Request`/`Response` imply it) and specific examples of multi-step scenarios, which are less critical for a function's technical description than its operational mechanics.

**Conclusion:** Description B is significantly better because it accurately describes the function's internal mechanics, particularly its role as a wrapper for another generator, which is central to understanding how `sync_auth_flow` works. Description A provides a good high-level overview but misses these critical implementation details. |
| `async_auth_flow` | `FunctionType.AUTH` | ✓ | 7/10 | 9/10 | +2 | body wins |
| `auth_flow` | `FunctionType.AUTH` | ✗ | 5/10 | 9/10 | +4 | body wins |
| `authority` | `FunctionType.AUTH` | ✗ | 6/10 | 10/10 | +4 | body wins |
| `auth` | `FunctionType.AUTH` | ✓ | 9/10 | 10/10 | +1 | body wins |

**Biggest gap** — `auth_flow()` (Δ=+4):
> CF: This function, `auth_flow`, likely implements a multi-step authentication process for HTTP requests within the httpx library. It takes an initial `Request` and, as a generator, yields subsequent `Requ
> Raw: This generator function implements a client-side HTTP Digest authentication flow. It first sends a request, and if the server responds with a 401 Unauthorized and a "WWW-Authenticate: Digest" header, 
> Gap: Description A incorrectly implies that the function iterates or loops to complete a multi-step authentication process "until authentication is successfully completed or fails." In reality, the function handles only a single challenge-response round, yielding at most two requests before returning.

**Best case** — `auth()` (Δ=+1): Codeflow metadata was essentially as good as the body.

---

### `psf/requests` — Requests — HTTP Library
> Category C · De-facto standard Python HTTP library; sessions, adapters, auth

| Metric | Value |
|--------|------:|
| Files fetched | 36 py + 0 js/ts |
| Source lines | 11,165 |
| Ground truth fns | 670 py + 0 js |
| Codeflow fns | 670 (100% recall) |
| Intents | 185 (50% route recall) |
| Docstrings captured | 238 (36% coverage) |
| Raw tokens | 85,992 |
| Codeflow tokens | 58,957 |
| Token saving | **31.4%** (1.46×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 543, <FunctionType.AUTH: 'auth'>: 26, <FunctionType.HANDLER: 'handler'>: 15, <FunctionType.UTIL: 'util'>: 43, <FunctionType.DB: 'db'>: 43}` |
| Parse time | 0.13s |

**LLM Judge:** CF 7.0/10 · Raw 7.8/10 · Retention **90%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `handle_401` | `FunctionType.AUTH` | ✓ | 5/10 | 5/10 | +0 |  |
| `build_digest_header` | `FunctionType.AUTH` | ✓ | 9/10 | 6/10 | -3 | ✓ CF ok |
| `prepare_auth` | `FunctionType.AUTH` | ✓ | 6/10 | 10/10 | +4 | body wins |
| `rebuild_auth` | `FunctionType.AUTH` | ✓ | 6/10 | 10/10 | +4 | body wins |
| `get_netrc_auth` | `FunctionType.AUTH` | ✓ | 9/10 | 8/10 | -1 | roughly_equal

**Reasoning:**

*   **Description A (Score 9):** This description is remarkably accurate given it was generated from "metadata only." It correctly identifies the function's purpose, input, output format, and the `raise_errors` parameter. Crucially, it correctly infers and states that the output is "formatted for use with the `requests` library's authentication mechanisms," which is explicitly mentioned in the actual docstring (`"Returns the Requests tuple auth..."`). This shows excellent understanding of the function's intended use. It lacks details on how the `netrc` file is located or the explicit `None` return for all failure cases, but this is understandable given the limited input.

*   **Description B (Score 8):** This description, generated from the "full source," provides more detail on the `netrc` file location (environment variable or standard locations) and explicitly states that it returns `None` if credentials are not found or errors occur. It also accurately describes the silent handling of parsing errors unless `raise_errors` is true. However, it misses the important context that the returned tuple is "formatted for use with the `requests` library," a detail explicitly present in the function's docstring. Missing this context, despite having full source access, is a notable oversight compared to Description A which correctly inferred it.

**Verdict:**

While Description B provides more granular detail on file location and explicit `None` returns, Description A's ability to capture the crucial "requests library" context from metadata (likely the docstring) gives it a slight edge in conveying the function's overall purpose and utility. However, both are competent descriptions, and the difference isn't "clearly better," making "roughly_equal" the most appropriate verdict among the given options. |

**Biggest gap** — `prepare_auth()` (Δ=+4):
> CF: This function likely takes raw authentication credentials and a target URL, then processes or formats the authentication data to be ready for an HTTP request. It probably configures headers, parameter
> Raw: This function prepares HTTP authentication for a request object (`self`), first attempting to extract auth details from the URL if none are explicitly provided. If authentication is present, it handle
> Gap: Description A fails to capture the specific, dynamic mechanism by which the `auth` object modifies the request. It misses that `auth` is treated as a callable (`auth(self)`) that returns an object whose attributes are then merged into the request object (`self.__dict__.update(r.__dict__)`).

**Best case** — `build_digest_header()` (Δ=-3): Codeflow metadata was essentially as good as the body.

---

### `httpie/httpie` — HTTPie — CLI HTTP Client
> Category D · User-friendly CLI HTTP client; plugins, sessions, formatting

| Metric | Value |
|--------|------:|
| Files fetched | 120 py + 0 js/ts |
| Source lines | 16,818 |
| Ground truth fns | 911 py + 0 js |
| Codeflow fns | 911 (100% recall) |
| Intents | 358 (100% route recall) |
| Docstrings captured | 141 (15% coverage) |
| Raw tokens | 119,789 |
| Codeflow tokens | 93,546 |
| Token saving | **21.9%** (1.28×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 754, <FunctionType.DB: 'db'>: 22, <FunctionType.HANDLER: 'handler'>: 58, <FunctionType.AUTH: 'auth'>: 19, <FunctionType.UTIL: 'util'>: 58}` |
| Parse time | 0.12s |

**LLM Judge:** CF 3.8/10 · Raw 8.4/10 · Retention **45%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `tokenize` | `FunctionType.AUTH` | ✗ | 2/10 | 9/10 | +7 | B_clearly_better

**Explanation:**

**Description A Score (2/10):**
Description A makes several significant assumptions and contains a direct factual error when compared to the provided source code.
*   **Incorrect Assumptions:** It speculates about "nested JSON data" and the "httpie CLI tool," neither of which is supported by the generic tokenization logic in the source.
*   **Factual Error:** The most critical flaw is the mention of "`AUTH` type." The actual source code explicitly uses `TokenKind.NUMBER` and `TokenKind.TEXT`, with no reference to `AUTH`. This indicates a major inaccuracy, likely due to relying on potentially outdated or incorrect metadata.
*   **Only partially correct:** It correctly identifies that the function breaks input into tokens, but the context and details are largely wrong.

**Description B Score (9/10):**
Description B is highly accurate and directly reflects the functionality described in the source code.
*   **Accurate Core Function:** It correctly identifies the function's purpose as tokenizing an input string into `Token` objects.
*   **Detailed Logic:** It accurately describes the handling of operators, the accumulation of characters into a buffer, and the nuanced backslash escape sequence logic (counting for special characters vs. including in value).
*   **Correct Classification:** It correctly states that buffered sequences are classified as numbers or text, and notes the "special handling for escaped values" (referring to `check_escaped_int`).
*   **No Assumptions:** It avoids making speculative claims about the input data type or external tools, sticking strictly to what the code reveals.
*   **Minor Omission:** It doesn't explicitly detail the `start`/`end` calculation or the exact priority of `int` vs `check_escaped_int` within the `if not backslashes` block, but these are minor details compared to the overall accuracy.

**Key Gap:**
While Description B mentions "special handling for escaped values" and that tokens are classified as "numbers or text," it doesn't explicitly state the crucial role of the `backslashes` count in this classification. Specifically, if `backslashes` are present (meaning a backslash was encountered before a `SPECIAL_CHARS` character), the `if not backslashes` block is skipped, and the buffered sequence is *automatically* classified as `TokenKind.TEXT`, bypassing any attempts to parse it as an `int` or `check_escaped_int`. This is a significant control flow detail missed by both.

**Verdict:**
Description B is **clearly better**. Its description is a faithful and accurate summary of the provided source code, whereas Description A contains significant inaccuracies and unverified assumptions. |
| `speed_based_token` | `FunctionType.AUTH` | ✗ | 3/10 | 9/10 | +6 | body wins |
| `auth` | `FunctionType.AUTH` | ✗ | 7/10 | 9/10 | +2 | body wins |
| `cert_verify` | `FunctionType.AUTH` | ✗ | 5/10 | 5/10 | +0 |  |
| `to_name` | `FunctionType.AUTH` | ✗ | 2/10 | 10/10 | +8 | body wins |

**Biggest gap** — `to_name()` (Δ=+8):
> CF: This function, `to_name`, is responsible for generating or retrieving a string name associated with an authentication context. Given its `AUTH` type and location within `httpie/cli/nested_json/tokens.
> Raw: This function attempts to find the current object (`self`) within the values of the `OPERATORS` dictionary. If a match is found, it returns the string representation of the corresponding key. Otherwis
> Gap: Description A, relying solely on metadata, incorrectly infers an "authentication context" and completely misses the function's actual implementation details, specifically the use of the `OPERATORS` dictionary and `self.name` attribute.

**Best case** — `cert_verify()` (Δ=+0): Codeflow metadata was essentially as good as the body.

---

### `pallets/click` — Click — CLI Framework
> Category D · Composable CLI creation; decorators, types, groups, testing

| Metric | Value |
|--------|------:|
| Files fetched | 62 py + 0 js/ts |
| Source lines | 21,610 |
| Ground truth fns | 1412 py + 0 js |
| Codeflow fns | 1412 (100% recall) |
| Intents | 332 (100% route recall) |
| Docstrings captured | 326 (23% coverage) |
| Raw tokens | 166,675 |
| Codeflow tokens | 126,972 |
| Token saving | **23.8%** (1.31×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 1324, <FunctionType.HANDLER: 'handler'>: 56, <FunctionType.UTIL: 'util'>: 32}` |
| Parse time | 0.14s |

**LLM Judge:** CF 6.6/10 · Raw 9.4/10 · Retention **70%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `get_command` | `FunctionType.HANDLER` | ✗ | 7/10 | 10/10 | +3 | body wins |
| `process_value` | `FunctionType.HANDLER` | ✓ | 6/10 | 10/10 | +4 | body wins |
| `handle_parse_result` | `FunctionType.HANDLER` | ✓ | 7/10 | 8/10 | +1 | body wins |
| `get_help_record` | `FunctionType.HANDLER` | ✗ | 6/10 | 10/10 | +4 | body wins |
| `get_help_option` | `FunctionType.HANDLER` | ✓ | 7/10 | 9/10 | +2 | body wins |

**Biggest gap** — `process_value()` (Δ=+4):
> CF: This function, likely a parameter callback within the Click CLI framework, takes a context object and an input value. Its primary role is to process this parameter's value, potentially involving valid
> Raw: 
> Gap: Description A fundamentally misidentifies the function's role, stating it is "likely a parameter callback." In reality, `process_value` is a method that *processes* a parameter's value and *invokes* a user-defined callback, rather than being the callback itself.

**Best case** — `handle_parse_result()` (Δ=+1): Codeflow metadata was essentially as good as the body.

---

### `Textualize/rich` — Rich — Terminal Formatting
> Category E · Rich text in terminal; renderables, layout, live display, panels

| Metric | Value |
|--------|------:|
| Files fetched | 120 py + 0 js/ts |
| Source lines | 31,030 |
| Ground truth fns | 598 py + 0 js |
| Codeflow fns | 598 (100% recall) |
| Intents | 217 (100% route recall) |
| Docstrings captured | 313 (52% coverage) |
| Raw tokens | 292,337 |
| Codeflow tokens | 63,449 |
| Token saving | **78.3%** (4.61×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 537, <FunctionType.HANDLER: 'handler'>: 58, <FunctionType.AUTH: 'auth'>: 3}` |
| Parse time | 0.16s |

**LLM Judge:** CF 6.8/10 · Raw 8.2/10 · Retention **83%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `iter_tokens` | `FunctionType.AUTH` | ✓ | 6/10 | 9/10 | +3 | body wins |
| `get_svg_style` | `FunctionType.HANDLER` | ✓ | 8/10 | 9/10 | +1 | body wins |
| `get_row` | `FunctionType.HANDLER` | ✓ | 5/10 | 5/10 | +0 |  |
| `get_top` | `FunctionType.HANDLER` | ✓ | 7/10 | 9/10 | +2 | body wins |
| `get_bottom` | `FunctionType.HANDLER` | ✓ | 8/10 | 9/10 | +1 | B_clearly_better

**Explanation:**

*   **Description A (Score: 8)**: This description is very good, especially considering it's generated from metadata only. It accurately identifies the function's purpose, correctly infers the input type (`Iterable[int]`) from the signature (even though the docstring specifies `List[int]`), and generally describes the output. Its main limitation is that it remains at a high level, not detailing the step-by-step construction process.

*   **Description B (Score: 9)**: This description is excellent. It accurately and concisely breaks down the function's logic step-by-step, explaining how the bottom-left corner, horizontal segments, dividers, and bottom-right corner are assembled. This level of detail provides a much clearer understanding of *how* the function operates. While it doesn't explicitly state the input type `Iterable[int]`, it accurately describes its use ("based on their specified widths").

*   **Key Gap**: Both descriptions miss a crucial design aspect: the specific characters used for the box parts (e.g., `self.bottom_left`, `self.bottom`) are instance attributes. This means the box's style (single line, double line, ASCII, etc.) is configurable by the `self` object, not hardcoded within this function. Mentioning this would highlight the flexibility and design pattern of the `rich` library's box drawing utilities.

*   **Verdict**: Description B is clearly better. Its detailed, step-by-step explanation of the function's construction logic provides a more comprehensive and useful understanding of the function's operation compared to Description A's higher-level summary, even though A is slightly more precise on the input type hint. |

**Biggest gap** — `iter_tokens()` (Δ=+3):
> CF: This function is a generator that yields a sequence of string tokens. It likely operates as a method on an object representing a "node" within a data structure or code, breaking it down into individua
> Raw: This function recursively generates a sequence of string tokens representing the current node and its descendants in a tree-like structure. It formats the output based on whether the node has a key, a
> Gap: Description A completely misses the recursive nature of the function, which is fundamental to how it processes nested nodes and their descendants. Description B accurately identifies this, along with providing much more specific detail about the conditional formatting logic for keys, values, children, and special tuple cases.

**Best case** — `get_row()` (Δ=+0): Codeflow metadata was essentially as good as the body.

---

### `pydantic/pydantic` — Pydantic — Data Validation
> Category E · Python data validation; models, validators, serialisation, JSON schema

| Metric | Value |
|--------|------:|
| Files fetched | 114 py + 6 js/ts |
| Source lines | 40,597 |
| Ground truth fns | 2014 py + 12 js |
| Codeflow fns | 2032 (100% recall) |
| Intents | 462 (50% route recall) |
| Docstrings captured | 234 (12% coverage) |
| Raw tokens | 380,113 |
| Codeflow tokens | 196,655 |
| Token saving | **48.3%** (1.93×) |
| fn_type_index | `{<FunctionType.OTHER: 'other'>: 1847, <FunctionType.HANDLER: 'handler'>: 24, <FunctionType.DB: 'db'>: 161}` |
| Parse time | 0.31s |

**LLM Judge:** CF 5.6/10 · Raw 10.0/10 · Retention **56%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `on_page_markdown` | `FunctionType.HANDLER` | ✓ | 7/10 | 10/10 | +3 | body wins |
| `update_lib` | `FunctionType.HANDLER` | ✗ | 3/10 | 10/10 | +7 | body wins |
| `on_page_content` | `FunctionType.HANDLER` | ✗ | 7/10 | 10/10 | +3 | body wins |
| `on_pre_build` | `FunctionType.HANDLER` | ✓ | 6/10 | 10/10 | +4 | body wins |
| `get_graphql_response` | `FunctionType.HANDLER` | ✓ | 5/10 | 10/10 | +5 | body wins |

**Biggest gap** — `update_lib()` (Δ=+7):
> CF: This function is a handler within a plugin system, likely responsible for orchestrating the update of a specified library object. It takes the library and a retry mechanism as parameters, suggesting i
> Raw: This function fetches the star count for a specified GitHub repository using the GitHub API. It implements a retry mechanism for 403 Forbidden errors, attempting up to three retries with a 5-second de
> Gap: Description A completely fails to identify the specific domain and purpose of the function, which is fetching GitHub repository star counts. Instead, it offers only generic observations about "orchestrating updates" and "handling failures" without any specific context.

---

### `sqlalchemy/sqlalchemy` — SQLAlchemy — Python ORM
> Category E · Python SQL toolkit and ORM; Core + ORM, dialects, sessions

| Metric | Value |
|--------|------:|
| Files fetched | 120 py + 0 js/ts |
| Source lines | 38,491 |
| Ground truth fns | 1548 py + 0 js |
| Codeflow fns | 1548 (100% recall) |
| Intents | 469 (50% route recall) |
| Docstrings captured | 312 (20% coverage) |
| Raw tokens | 281,448 |
| Codeflow tokens | 161,589 |
| Token saving | **42.6%** (1.74×) |
| fn_type_index | `{<FunctionType.DB: 'db'>: 262, <FunctionType.UTIL: 'util'>: 985, <FunctionType.OTHER: 'other'>: 294, <FunctionType.HANDLER: 'handler'>: 7}` |
| Parse time | 0.18s |

**LLM Judge:** CF 5.6/10 · Raw 8.8/10 · Retention **64%**

| Function | Type | Doc? | CF | Raw | Δ | Verdict |
|----------|------|:----:|:--:|:---:|:-:|---------|
| `update_state` | `FunctionType.HANDLER` | ✓ | 5/10 | 5/10 | +0 |  |
| `load_name_range` | `FunctionType.HANDLER` | ✓ | 7/10 | 9/10 | +2 | body wins |
| `execute_chooser` | `FunctionType.HANDLER` | ✓ | 3/10 | 10/10 | +7 | body wins |
| `create_version` | `FunctionType.HANDLER` | ✗ | 7/10 | 10/10 | +3 | body wins |
| `on_new_class` | `FunctionType.HANDLER` | ✓ | 6/10 | 10/10 | +4 | body wins |

**Biggest gap** — `execute_chooser()` (Δ=+7):
> CF: This function acts as a handler that determines the appropriate execution strategy for a given statement. It likely evaluates the provided `context` to choose between different execution paths, delega
> Raw: This function determines a list of relevant "shard IDs" for a given SQL statement. It inspects the statement's `WHERE` clause for equality or IN conditions on the `continent` column. If continent filt
> Gap: Description A fails to identify that the function's primary output is a list of "shard IDs" and that this list is determined by parsing the `WHERE` clause for conditions on a specific "continent" column. It remains at a high, abstract level, missing the concrete details of the function's operation.

**Best case** — `update_state()` (Δ=+0): Codeflow metadata was essentially as good as the body.

---

## 5. Regime Analysis

Three distinct regimes emerge from the token benchmark:

| Regime | Threshold | Repos | Characteristics |
|--------|:---------:|:-----:|-----------------|
| High compression | ≥40% savings | 5 | Full-stack apps; mixed Python+JS; large file counts |
| Moderate | 10–40% savings | 6 | Mid-size frameworks; typed libraries |
| Near-parity | <10% savings | 3 | Dense type-annotated libs; small repos |

**High compression:** `fastapi/full-stack-fastapi-template`, `zauberzeug/nicegui`, `Textualize/rich`, `pydantic/pydantic`, `sqlalchemy/sqlalchemy`
**Moderate:** `pallets/flask`, `anthropics/anthropic-sdk-python`, `encode/httpx`, `psf/requests`, `httpie/httpie`, `pallets/click`
**Near-parity:** `tiangolo/fastapi`, `encode/starlette`, `openai/openai-python`

## 6. Optimal Agent Strategy

```
Step 1: Agent calls POST /parse
        → receives ParsedRepo (~10–50K tokens)
        → knows: ALL functions, ALL routes, call graph, types, file layout

Step 2: Agent identifies functions it needs to inspect deeply
        → uses file_index to know exactly which file to fetch
        → fetches ONLY those 1–3 files (not all 60–120)

Result: architecture understanding at 10–40% of naive raw-read cost
        body detail on-demand at zero wasted tokens
```

| Agent Task | Best tool | Why |
|------------|:---------:|-----|
| Understand codebase architecture | Codeflow | fn_type_index + intents |
| Find all API entry points | Codeflow | intent_recall + fn_type_index["route"] |
| Trace a call chain | Codeflow | fn.calls[] graph |
| Read function body | Raw (targeted) | body not in ParsedRepo |
| First-pass orientation | Codeflow | compressed, structured |
| Deep bug in specific fn | Both | CF for context, raw for body |

## 7. Honest Limitations

| Limitation | Impact | Mitigation |
|------------|:------:|------------|
| Function bodies stripped | LLM cannot read implementation | Fetch targeted files on demand |
| Misleadingly-named functions | CF metadata leads agent astray | Docstrings partially compensate |
| JS/TS recall lower than Python | Tree-sitter coverage incomplete | Use raw for pure-JS repos |
| Tokenizer is GPT-4 proxy | ±5% vs Claude actual | Directionally correct |
| Judge is Gemini 2.5 Flash | One model's view | Sufficient for relative comparison |

---
*Codeflow Benchmark · Run 2026-03-30 03:58 UTC · Judge: Gemini 2.5 Flash*