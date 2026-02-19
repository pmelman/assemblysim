# Assembly Sim Bug Tracker

Remaining issues from security & code review (Feb 2026). Priority fixes 1-7 and HIGH H1-H5 have been implemented.

---

## HIGH — All fixed

### ~~H1. Prompt injection via assembly topic~~ FIXED
Added `input_sanitizer.py` with topic sanitization (control char stripping, encoded data detection for base64/hex/unicode/URL-encoding, length cap) and `wrap_topic_for_prompt()` XML delimiters. Applied to API entry point, moderator agent, recorder agent, and Perplexity client.

### ~~H2. Unbounded transcript sent to LLM~~ FIXED
`_get_full_transcript()` now accepts `max_chars` (default 80k) and truncates from the middle, keeping first 60% and last 40%.

### ~~H3. New httpx client per Perplexity call~~ FIXED
Perplexity client now reuses a singleton `AsyncClient` with lazy init, matching the LLM client pattern.

### ~~H4. Unrestricted setattr on models~~ FIXED
Added explicit `UPDATABLE_FIELDS` allowlists in `api/settings.py` and `api/custom_citizens.py`.

### ~~H5. No ownership on custom citizen templates~~ FIXED
Added `user_id` FK to `CustomCitizenTemplate`, ownership checks on all CRUD endpoints, and user-scoped listing (admins see all).

---

## MEDIUM

### M1. No rate limiting on auth endpoints
**File:** `api/auth.py:101-169`
`/auth/login` and `/auth/register` have no rate limiting. Brute-force attacks possible.
**Fix:** Add `slowapi` or similar rate limiting middleware.

### M2. Race conditions on assembly status transitions
**File:** `api/assemblies.py:265-317`
Read-then-write on assembly status allows duplicate background tasks from rapid concurrent requests.
**Fix:** Use atomic `UPDATE ... WHERE status = ?` and check rows affected.

### M3. Error messages leak internal details
**Files:** `api/services.py:194`, `main.py:167-177`
Raw exception strings stored in `assembly.error_message` and returned to clients. Can include file paths, SQL, or API details.
**Fix:** Sanitize error messages before storing/returning.

### M4. Email not validated as EmailStr
**File:** `models/schemas.py:20`
`email: str` instead of `email: EmailStr` (which is imported but unused). Users can register with any string.
**Fix:** Change to `email: EmailStr` in `RegisterRequest` and `LoginRequest`.

### M5. Global np.random.seed() side effect
**File:** `citizen_forge/sampler.py:147`
Sets global NumPy seed, affecting all concurrent requests.
**Fix:** Use `np.random.default_rng(seed)` for a local generator.

### M6. _parse_vote_response case mismatch
**File:** `agents/citizen_agent.py:422-428`
Checks lowercase `"reasoning:"` but splits original on `"REASONING:"`. Mixed-case LLM output breaks parsing.
**Fix:** Use case-insensitive split: `re.split(r'reasoning:', response, flags=re.IGNORECASE)`.

### M7. Spoofed browser headers to Perplexity
**File:** `knowledge/perplexity_client.py:122-125`
Sends fake User-Agent/Origin/Referer mimicking the Perplexity web UI. Potential ToS violation.
**Fix:** Use an honest User-Agent identifying the application.

### M8. Unvalidated URLs rendered as links (frontend)
**File:** `frontend/app/assemblies/[id]/page.tsx:186-194`
Perplexity source URLs rendered as `<a href>` without protocol validation. `javascript:` URLs possible.
**Fix:** Validate URLs start with `http://` or `https://` before rendering.

### M9. Anthropic API response not handled defensively
**File:** `llm_client.py:214`
Fixed in priority item 7 but monitor for similar patterns in other API clients.

### M10. Uninitialized instance attributes in DeliberationEngine
**File:** `orchestration/deliberation_engine.py:1060`
`self.deduplicated_proposals`, `self.discussion_summary`, etc. set mid-flow but not in `__init__`.
**Fix:** Initialize all instance attributes in `__init__`.

### M11. WebSocket connection manager not thread-safe
**File:** `api/websocket.py:19-131`
`active_connections` dict has no locking. Background tasks in thread pools could cause contention.
**Fix:** Use asyncio.Lock for connection list operations.

### M12. Score parsing regex too greedy
**File:** `agents/citizen_agent.py:387-392`
The regex `.*?:\s*(\d)` captures only a single digit and may match the wrong colon.
**Fix:** Use `r'\s*(\d+)\.\s*.*:\s*(\d+)\s*(?:/5)?'` to be more specific.

---

## LOW

### L1. datetime.utcnow() deprecated
**Files:** Multiple (auth.py, models.py, websocket.py)
Deprecated in Python 3.12+. Returns naive datetime without timezone info.
**Fix:** Use `datetime.now(datetime.timezone.utc)`.

### L2. JWT has no jti/iat claims
**File:** `api/auth.py:52-56`
No way to revoke tokens; password changes don't invalidate existing tokens.
**Fix:** Add `jti` and `iat` claims; track issued-at for revocation.

### L3. 24-hour token expiry with no refresh
**File:** `config.py:79`
Long window for stolen tokens with no revocation mechanism.
**Fix:** Shorter expiry + refresh token flow.

### L4. delete_briefing returns body with 204
**File:** `api/assemblies.py:418`
HTTP 204 should have no body.
**Fix:** Return `None` instead of the deleted object.

### L5. N+1 query in list_invite_codes
**File:** `api/auth.py:229-243`
Each invite code's `used_by` user triggers a separate query.
**Fix:** Use `joinedload` or a single join query.

### L6. No React Error Boundaries (frontend)
**Files:** All frontend components
Rendering errors crash the entire app with a white screen.
**Fix:** Add Error Boundary wrappers around key component trees.

### L7. WebSocket reconnect timer not cleared on disconnect
**File:** `frontend/lib/websocket.ts:138`
`disconnect()` doesn't cancel pending `setTimeout`, causing reconnects after unmount.
**Fix:** Store timeout ID and clear it in `disconnect()`.

### L8. complete_sync can deadlock
**File:** `llm_client.py:226-243`
Blocks event loop thread when called from async context.
**Fix:** Callers in async contexts should use `await self.complete()` directly.

### L9. generate_batch ordering
**File:** `citizen_forge/persona_generator.py:176`
`asyncio.as_completed` returns results in completion order, not submission order.
**Fix:** Use `asyncio.gather` to preserve order.

### L10. _quota_sample can oversample
**File:** `citizen_forge/sampler.py:243-280`
No final cap at `target_n`; same respondent counted in multiple quota categories.
**Fix:** Add final truncation to `target_n`.

### L11. Middleware is a no-op (frontend)
**File:** `frontend/middleware.ts:28`
Always returns `NextResponse.next()`. Protected page shells flash to unauthenticated users.
**Fix:** Check for auth cookie or remove middleware file.

### L12. Assembly ID parsed without NaN check (frontend)
**File:** `frontend/app/assemblies/[id]/page.tsx:21`
`parseInt` on non-numeric string produces `NaN` passed to API calls.
**Fix:** Add `isNaN` check and show error.

### L13. Unused original_titles variable
**File:** `orchestration/deliberation_engine.py:1031`
`original_titles` computed but never used.
**Fix:** Remove dead code.

### L14. _get_round_transcript returns unscoped messages in group mode
**File:** `orchestration/deliberation_engine.py:1381-1384`
Returns messages from ALL groups for a round, mixing separate conversations.
**Fix:** Filter by group in group mode.

### L15. _select_group_representative always picks first citizen
**File:** `orchestration/deliberation_engine.py:750-776`
All citizens have equal message counts, so selection falls through to first citizen.
**Fix:** Consider random selection or rotation.

### L16. API key exposure risk in error logs
**Files:** `llm_client.py:147`, `knowledge/perplexity_client.py:163`
API error responses may echo back authorization headers.
**Fix:** Truncate/redact error response bodies before logging.

### L17. _repair_truncated_json can produce invalid JSON
**File:** `knowledge/perplexity_client.py:264-313`
Truncating at a quote inside a string value produces unbalanced quotes.
**Fix:** More robust repair logic or just catch and return empty.

### L18. sampling_strategy/depth fields have no enum validation
**Files:** `models/schemas.py:85, 112`
Arbitrary strings accepted for `sampling_strategy` and `depth`.
**Fix:** Use `Literal["stratified", "quota", "random"]` and `Literal["quick", "standard", "detailed"]`.

### L19. No CSRF protection (frontend)
**File:** `frontend/lib/api.ts`
Safe currently (token in localStorage, not cookies), but would be immediately exploitable if migrated to cookies.
**Fix:** Add CSRF tokens if switching to cookie-based auth.

### L20. Frontend ws:// default (unencrypted)
**File:** `frontend/lib/websocket.ts:14`
Default WebSocket URL uses `ws://`. Production should use `wss://`.
**Fix:** Default should detect protocol from window.location or require explicit config.
