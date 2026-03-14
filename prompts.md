# Prompts Log

A running log of all prompts used in this project's development conversation.

---

## 2026-03-14

**[1]** `/init`
> Analyze this codebase and create a CLAUDE.md file.

**[2]**
> From now on, I want you to create a Git repository for this project. I would like you to make clean commit messages, save them locally and then push them to GitHub, so that we always have a saved version of the project and its easier for us to revert back in case we make any changes. Set up a GitHub repository, configure everything and just use Git and GitHub for the rest of the project.

**[3]**
> I want to create a file that will store all the prompts i will use during the conversation. UPDATE the file, when you update, dont override its currnt content.

**[4]**
> You are a senior software engineer and AI systems engineer. We are going to build a real prototype application gradually and rigorously. [Full product vision prompt — architecture analysis requested: compare web app, iOS native, and other options across 6 criteria and recommend one. No code yet.]

---

> **Note:** Starting from Prompt 6, each entry stores the full user prompt, full Claude response, and a change note, per the documentation rules established in Prompt 7.

---

## Prompt 6 — 2026-03-14

### User Prompt
I want to refine the backend behavior and the backend test strategy.

Important clarification:
The classifier and reformulation logic are existing validated components from my research. This phase is not intended to evaluate their ML/NLP quality.

Instead, this phase should focus on the backend layer: how the backend integrates with the pipeline, validates its outputs, and returns safe responses.

Requirements:

1. Do not focus tests on whether the classifier predicted the correct intent or whether the reformulation itself is optimal.
2. Focus on backend behavior, API response structure, and error handling.
3. The backend should validate pipeline outputs before returning a successful result.
4. In some cases, downstream extraction may return unusable values, for example:
   - placeholder-like values such as ####
   - invalid or suspicious characters
   - malformed extracted values
   - empty required values

If the pipeline output is unusable, the backend should not return a normal success result.

The API response should remain generic and should not expose internal failure causes.

Before implementing any changes, first explain:

- where output validation should happen in the backend pipeline
- what the response schema should look like for success vs failure
- whether unsuccessful processing should return HTTP 200 with a failure status or a different HTTP code
- how the tests should be adapted to validate backend behavior instead of model quality

Provide the options, trade-offs, and your recommendation.

Do not implement yet. Wait for my approval before proceeding.

After approval, you will:
- update the backend logic
- refine the tests
- run the full test suite
- produce a structured report including:
  - input
  - predicted intent
  - reformulated output
  - backend status
  - HTTP status code
  - pass/fail result

Additional requirements:
- keep all code fully documented
- update prompts.md with the FULL prompt
- validate the build after changes
- do not skip tests

### Claude Response
Design proposal presented (no code written). Key decisions proposed:
- Validation in dedicated `validators.py`, called from `pipeline.py`
- HTTP 200 unified response with `status: success / failed` field
- `reformulated: null` when status is failed
- HTTP 400/422/500 reserved for true errors
- No mocking; validator unit tests + real-pipeline API tests

### Notes
Design-only response. No code changes. Awaiting approval.

---

## Prompt 7 — 2026-03-14

### User Prompt
Your proposal is mostly aligned with what I want, but I want to refine a few points before implementation.

Approved decisions:
- Validation should be implemented in a dedicated validators.py module.
- The validation logic should be called from the pipeline layer.
- Use a unified API response schema with a status field (success / failed).
- The API must not expose internal failure reasons to the client.
- Keep HTTP 400 / 422 / 500 for true request or server errors.

Changes and clarifications:

1. Shared validation rules for input and output

Input validation and output validation must follow the same rule set.

Both the user input and the reformulated output must contain only characters allowed by the command templates.

Allowed characters:
- Hebrew letters
- spaces
- punctuation characters that appear in the command templates

Invalid characters include:
- English letters
- digits
- characters such as #
- any character not present in the allowed template character set.

If even one invalid character appears, the text must be treated as invalid.

Do not guess the allowed character set.
Instead, analyze the command templates and propose the explicit allowed character set before implementing the validation rule.

Use a shared validation function for both stages.

2. Validation stages

Validation must occur in two stages:

Stage 1 — Input validation
Runs before the pipeline executes.

Stage 2 — Output validation
Runs after the pipeline produces the reformulated command.

For output validation, also verify that:
- the output is not None
- the output is not empty or whitespace-only
- the output contains at least one Hebrew letter

If the output violates the validation rules, the backend should treat the result as unusable.

In that case the API should return:

status = "failed"
reformulated = null

The API must not expose the internal reason for the failure.

3. Tests

Do not use mocked tests.

All tests must run against:
- the real backend
- the real intent classifier model
- the real reformulation pipeline.

However, the tests should NOT evaluate whether the predicted intent is correct or whether the reformulation is linguistically correct.

Instead they should verify:

- the backend runs end-to-end without crashing
- the API response schema is correct
- the backend status field is correct
- invalid input is rejected correctly
- unusable pipeline output is handled correctly
- returned fields are well-formed.

Keep several real integration tests using representative inputs, including both valid and invalid cases.

4. Test report

After running the tests, produce a structured report table containing:

- input
- predicted intent
- reformulated output
- backend status
- HTTP status code
- pass/fail

5. Prompt documentation

From now on, every prompt I send and every response you generate must be documented.

Rules:

- Do not overwrite the file.
- Always append new entries.
- Store them in prompts.md.

Each entry must include:

timestamp
the full prompt I sent
your full response
a short note if the response led to a code or test change.

Use the following structure:

## Prompt <N> — <timestamp>

### User Prompt
<full prompt>

### Claude Response
<full response>

### Notes
(optional explanation of resulting changes)

Before implementing anything, revise your plan according to the points above and explain:

- the exact validation rules
- how the allowed character set will be derived from the templates
- where validation will occur in the pipeline
- the final response schema
- how the real (non-mocked) test suite will be structured.

Stop after presenting the revised design and wait for my approval before implementing.

### Claude Response
Revised design presented. Key decisions:
- Allowed character set derived by reading every template literal: Hebrew consonants (U+05D0–U+05EA) + ASCII space only. No punctuation survives into final output because create_command() strips all "- " hyphens.
- Stage 1 (input): validate_input() — rejects empty or invalid chars → HTTP 400
- Stage 2 (output): validate_output() — checks None, empty, min length, Hebrew presence, valid chars → status: failed
- Unified HTTP 200 response with status field; reformulated: null on failure
- No mocking: validator unit tests (Group A) + real-pipeline API tests (Groups B–E)
- MIN_OUTPUT_LENGTH = 6 (length of "תתקשרי", the shortest template output)

### Notes
Design-only response. No code changes. Awaiting approval.

---

## Prompt 8 — 2026-03-14

### User Prompt
Please fix the test "Minimum valid test" from group A. The minimum valid length is the minimum template length. Make sure you maintain the prompt file. Then you can start write the code.

### Claude Response
Implemented all backend changes and tests. Changes made:
- Created backend/validators.py with is_valid_text(), has_hebrew_letter(), validate_input(), validate_output(), MIN_OUTPUT_LENGTH=6
- Updated backend/schemas.py: added status: Literal["success","failed"], made reformulated: Optional[str]
- Updated backend/pipeline.py: Stage 1 (validate_input before classifier), Stage 2 (validate_output after reformulate)
- Updated backend/main.py: generic error messages ("Invalid input.", "An internal error occurred.")
- Created tests/test_validators.py: 48 unit tests for validators (Group A)
- Rewrote tests/test_api.py: 34 integration tests, no mocking (Groups B–E)
Fixed minimum valid test: uses "תתקשרי" (6 chars = MIN_OUTPUT_LENGTH) instead of single letter "א".
Added below-minimum test: uses "תתקשר" (5 chars) which must be rejected.

### Notes
82/82 tests pass (48 validator unit tests + 34 API integration tests).

**[5]**
> You are a senior software engineer helping me build this system in a structured, production-quality way.
> We already completed the architecture phase and approved the implementation plan.
> We will now proceed with **Step 2 of the implementation plan**.
>
> -------
> # Code Quality Requirements
>
> All code must be:
> * fully documented
> * clean and readable
> * properly modularized
>
> Each module must include:
> * docstrings
> * clear function descriptions
> * type hints
> * comments explaining important logic
> -------
> # Testing Requirements
>
> The tests must cover:
>
> ### Functional tests
> * examples representing all **10 intents**
>
> ### Edge cases
> * empty string
> * very long text
> * unsupported language
> * special characters
> * malformed input
> * anything you can think of
>
> ### Pipeline tests
> * verify classifier output
> * verify reformulation output
> * verify API response structure
>
> Each test must clearly explain what it verifies.
> ---
>
> # Validation
>
> After writing the code:
>
> 1. Validate the build succeeds
> 2. Run the test suite
> 3. Report test results
> 4. Fix issues if needed
>
> Do not proceed if tests fail.
>
> ---
>
> # Documentation
>
> All code must be fully documented.
>
> Additionally:
>
> Update `prompts.md` with the **FULL prompt used in this step**.
>
> Do NOT summarize the prompt.
>
> ---
>
> # Deliverables for this Step
>
> Provide:
>
> 1. Full backend implementation
> 2. Model loading logic
> 3. Reformulation script integration
> 4. `/reformulate` API endpoint
> 5. pytest test suite
> 6. Updated `prompts.md`
> 7. Explanation of the implementation
> 8. Test results
>
> ---
>
> # Important Reminder
>
> Follow the development workflow strictly:
>
> * implement
> * test
> * validate
> * explain
>
> Do not skip any step.
>
> If something is unclear, ask questions before proceeding.

---

## Prompt 9 — 2026-03-14

### User Prompt
A few additional requirements before continuing:

1. Prompt logging
Every prompt I send and every response you generate must be appended to prompts.md.

Requirements:
- Do not overwrite the file.
- Append new entries only.
- Store the FULL prompt and the FULL response (no summaries or truncation).

2. Local backend execution
After implementing the backend, make sure the server can run locally.

Provide the exact command to start the server so I can interact with it manually via localhost.

3. API documentation
Add basic documentation for the backend API, including:
- endpoint description
- request format
- response format
- example request and response

Stop after implementing these steps and confirm that the backend can be started locally.

### Claude Response
Created README.md with full API documentation covering:

- Local server startup command
- `GET /health` — endpoint description, response schema, curl example
- `POST /reformulate` — request format, full response schema (success + failed + 400 + 422 + 500), curl examples with real Hebrew input/output
- Intent map (IDs 0–9 with labels)
- Input validation rules (Stage 1 + Stage 2)
- Project structure overview

Verified server starts correctly:
- `uvicorn` and `fastapi` packages import successfully on Python 3.10
- `backend.main` app imports cleanly, all routes registered: `/health`, `/reformulate`, `/docs`, `/redoc`
- No import errors

**Command to start the server locally:**

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Run from the repository root with the Python 3.10 virtualenv active. Wait for `=== All models ready. Server accepting requests. ===` before sending requests.

Interactive docs available at `http://localhost:8000/docs` once the server is running.

### Notes
Created README.md. No code changes to backend or tests.

---

## Prompt 10 — 2026-03-14

### User Prompt
Run the command to start the backend server locally and verify that it starts successfully.

After the server is running, show me how I can interact with the backend directly from my browser using the URL bar.

Specifically, demonstrate how I can send a custom command and receive the backend response.

For example, I want to be able to type a URL in my browser that sends a command to the backend and returns the backend status and reformulated result.

Provide:
- the exact URL format I should use
- an example request
- the expected response format

Then update the backend API documentation to include clear instructions on how to interact with the server from a browser, including these examples.

Important: keep the server running after it starts so that I can manually test it through the browser. Do not stop the server unless I explicitly ask you to.

### Claude Response
Started the server in the background:

```bash
py -3.10 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Verified server is running and models are loaded by calling:

```
GET http://localhost:8000/health
→ {"status":"ok","models_loaded":true}
```

Also confirmed POST /reformulate works with a live Hebrew command:

```
POST /reformulate  {"utterance": "תצלם תמונה"}
→ {"status":"success","original":"תצלם תמונה","intent_id":6,"intent_label":"camera","reformulated":"תפתחי מצלמה"}
```

Explained that the browser URL bar only supports GET requests, so /reformulate (POST) cannot be called from the URL bar directly. Two browser-native options:

1. GET /health — paste http://localhost:8000/health directly into the URL bar.
2. POST /reformulate — use the built-in Swagger UI at http://localhost:8000/docs: click "POST /reformulate" → "Try it out" → type Hebrew utterance → "Execute".

Updated README.md with a new "Testing the API from Your Browser" section including step-by-step Swagger UI instructions and a real example (תצלם תמונה → תפתחי מצלמה).

Server is left running.

### Notes
README.md updated with browser interaction section. Server running on port 8000. No backend code changes.

---

## Prompt 11 — 2026-03-14

### User Prompt
We are ready to move to the next step.

The backend is implemented and running locally.
The next step is to build a minimal frontend interface that communicates with the backend.

Important clarifications:

1. The user should NOT see the backend status or any technical fields.
2. If the request succeeds, the UI should display only the reformulated command.
3. If the request fails, the UI should display only a generic message such as:
   "An error occurred. Please try again."
4. TTS should NOT be included in this step. We will add it later.
5. The interface should be visually clean, attractive, and especially user-friendly for older adults.
6. The UI must support Hebrew and RTL layout.

Before writing code, first propose the best approach for this frontend step.

Please explain:
- which technology you recommend for this stage
- the component structure
- how the frontend will communicate with the backend
- how success and failure should be handled in the UI
- what design choices you recommend to make the interface accessible and friendly for older adults

Keep the scope minimal and focused on a working prototype.

Do not implement yet. Wait for my approval before writing code.

Also remember to document the FULL prompt and the FULL response in prompts.md.

### Claude Response
Design proposal presented (no code written). Key decisions:

**Technology:** React + Vite (consistent with approved architecture plan). Vite dev server, fast hot reload, works on Windows with no friction.

**Component structure:**
- App (owns all state: utterance, result, error, loading)
  - CommandInput — Hebrew text field + submit button
  - ResultDisplay — shows reformulated string or generic error message

**Backend communication:**
- Single fetch() to POST http://localhost:8000/reformulate with JSON body {"utterance": <input>}
- Response handling:
  - HTTP 200 + status "success" → show reformulated string
  - HTTP 200 + status "failed" → show generic error
  - HTTP 400 → show generic error
  - HTTP 500 → show generic error
  - Network error → show generic error
- UI never reads status, intent_id, intent_label, or any technical field

**Error handling:** Single boolean error flag, single Hebrew message: "אירעה שגיאה. אנא נסה שוב."

**Design for older adults:**
- Font: 20px minimum body, 28px result output; system Hebrew font stack
- Layout: single column, centered, max 600px, generous padding, RTL (dir="rtl" lang="he")
- Input: full-width, min height 52px, Hebrew placeholder
- Button: full-width, min height 56px, high contrast, Hebrew label "שלח", disabled while loading
- Result card: success = light green background; error = light red background
- No technical labels or JSON exposed

**Excluded from this step:** TTS, voice input, routing, auth.

### Notes
Design-only response. No code written. Awaiting approval.

---

## Prompt 12 — 2026-03-14

### User Prompt
Approved, continue

### Claude Response
Implemented the React + Vite frontend in full. Files created/modified:

**Scaffolding:**
- Used `npm create vite@4` (Node 19 compatible) to scaffold `frontend/`
- Installed dependencies with `npm install`

**index.html** — set `lang="he"` and `dir="rtl"` at document level for global RTL + Hebrew

**vite.config.js** — added dev server proxy: `/api/*` → `http://127.0.0.1:8000/*` (IPv4 explicit to avoid Node 19 IPv6 resolution issue)

**src/index.css** — global base styles: Hebrew system font stack, 20px base font, light background, reset

**src/App.jsx** — root component owning all state:
- utterance (string), result (string|null), error (boolean), loading (boolean)
- sendUtterance(): POST /api/reformulate → on success+status="success" show result; all other outcomes set error=true
- No technical fields (status, intent_id, intent_label, HTTP code) ever passed to child components

**src/App.module.css** — page layout: centered single column, white card, max-width 620px

**src/App.css** — intentionally empty (all styles in CSS Modules)

**src/components/CommandInput.jsx** — controlled Hebrew text input + submit button; disabled while loading; Hebrew placeholder and label

**src/components/CommandInput.module.css** — large touch targets (54px input, 58px button), high-contrast button (#1a56db), focus ring

**src/components/ResultDisplay.jsx** — shows reformulated text (green card) OR "אירעה שגיאה. אנא נסה שוב." (red card); hidden until first response

**src/components/ResultDisplay.module.css** — success card (green tones), error card (red tones), slide-in animation, 1.6rem result font

Verified:
- Production build: `vite build` ✓ — 36 modules, 0 errors
- Dev server running at http://localhost:5173
- Proxy confirmed working: POST http://localhost:5173/api/reformulate → {"status":"success","reformulated":"תפתחי מצלמה"}

Both servers running:
- Backend: http://localhost:8000 (FastAPI)
- Frontend: http://localhost:5173 (Vite dev server)

### Notes
Frontend implemented and running. Build passes. Proxy tested end-to-end.

---

## Prompt 13 — 2026-03-14

### User Prompt
Please make the following UI refinements:

1. Replace the text "פקודה מומרת".
Instead, use a more natural user-facing instruction in Hebrew, for example:
"הפעילו את סירי ואמרו לה את הפקודה הבאה:"
Use polished and friendly Hebrew phrasing suitable for older adults.

2. Add a reset button.
The reset button should:
- clear the text input
- clear the displayed result
- clear any error message
- restore the interface to its initial state

3. Change the title font.
The current title font does not look good.
Please replace it with a cleaner, more pleasant, and more elegant Hebrew-friendly font that still remains highly readable for older adults.

4. Add short usage instructions for older adults.
The instructions should be simple, clear, and visually friendly.
For example, explain briefly:
- type a command
- send it
- if a result appears, activate Siri and say that sentence
Keep the wording minimal and accessible.

5. Keep the design clean, attractive, and user-friendly for older adults.
Do not overcomplicate the interface.

Before implementing, briefly describe the exact text changes and layout changes you plan to make.

### Claude Response
Described plan first, then implemented all four changes.

Plan summary:
1. ResultDisplay.jsx resultLabel: "הפקודה המומרת:" → "הפעילו את סירי ואמרו לה את הפקודה הבאה:"
2. Reset button: resetAll() in App.jsx clears utterance/result/error; ghost outlined button "התחל מחדש" visible when any state is non-empty; disabled while loading
3. Font: Heebo from Google Fonts added via <link> in index.html; applied to .title in App.module.css with font-family: 'Heebo', fallback
4. Instructions: <section> inside the white card above the input, light blue-gray box, three numbered steps

Files changed:
- frontend/index.html: added Google Fonts <link> for Heebo (weights 400/600/700/800)
- frontend/src/App.jsx: added resetAll(), showReset computed flag, instructions <section> with 3 steps, reset <button>; updated subtitle text
- frontend/src/App.module.css: .title now uses Heebo font; added .instructions, .instructionsTitle, .instructionsList, .resetButton styles
- frontend/src/components/ResultDisplay.jsx: label text updated
- frontend/src/components/ResultDisplay.module.css: .resultLabel font-size increased to 1rem, better line-height for longer sentence

Build: ✓ 36 modules, 0 errors

### Notes
UI-only changes. No backend code modified. Build passes.

---

## Prompt 14 — 2026-03-14

### User Prompt
Please make the following UI and logic refinements.

1. Numbered instructions
Use regular numbers (1, 2, 3) for the instructions instead of symbols like ①.

2. Update the usage instructions text
Do not use the wording "אם מופיעה תוצאה".

Instead, update the instructions so that the final step clearly says that the user should say the corrected command to Siri.

For example, the instructions should follow this idea:

1. הקלידו את הבקשה שלכם בתיבה.
2. לחצו על כפתור השליחה.
3. הפעילו את סירי ואמרו לה את הפקודה המתוקנת.

Use clear and simple Hebrew that is friendly for older adults.

3. Add number normalization for user input

Add a validation / preprocessing step after the user types a query and before the request is sent to the backend.

If the user types digits, convert them to their Hebrew word form.

Examples:
1 → אחד
2 → שניים
3 → שלוש
10 → עשר

Support both single-digit numbers and multi-digit numbers where possible.

This conversion should happen automatically before sending the request to the backend.

Explain briefly where in the frontend flow this preprocessing will occur, and then implement it.

Keep the interface simple and readable for older adults.

Also remember to document the FULL prompt and the FULL response in prompts.md.

### Claude Response
Preprocessing location: normalizeNumbers() is called in App.jsx sendUtterance(), immediately before the fetch call, on the utterance value. The input field is never mutated — the user always sees their original text. The preprocessed string is sent only in the request body.

Files created/modified:

frontend/src/utils/normalizeNumbers.js (NEW)
- normalizeNumbers(text): replaces all /\d+/g matches with intToHebrew(n)
- intToHebrew(n): supports 0–999
  - 0: אפס
  - 1–9: ONES table (אחד, שניים, שלוש, ארבע, חמש, שש, שבע, שמונה, תשע)
  - 10–19: TEENS table (עשר, אחד עשר, …, תשע עשר)
  - 20–99: TENS[tens] + optional " ו" + ONES[remainder]
  - 100–999: hundreds word (מאה/מאתיים/X מאות) + optional " ו" + recursive remainder
  - >999: left unchanged as digit string

frontend/src/App.jsx
- Import normalizeNumbers from ./utils/normalizeNumbers.js
- In sendUtterance(): const processedUtterance = normalizeNumbers(utterance) before fetch
- Instructions list: changed from ①②③ to standard <ol> with plain Hebrew text
  - "הקלידו את הבקשה שלכם בתיבה."
  - "לחצו על כפתור השליחה."
  - "הפעילו את סירי ואמרו לה את הפקודה המתוקנת."

frontend/src/App.module.css
- .instructionsList: changed from list-style: none to list-style-type: decimal, added RTL padding-right

Smoke tests (12 cases):
- 1→אחד, 2→שניים, 3→שלוש, 10→עשר ✓
- 7→שבע, 15→חמש עשר, 21→עשרים ואחד ✓
- 100→מאה, 200→מאתיים, 350→שלוש מאות וחמישים ✓
- "שעה 7"→"שעה שבע", "שלח הודעה ב 10 דקות"→"שלח הודעה ב עשר דקות" ✓
- 12/12 passed

Build: ✓ 37 modules, 0 errors

### Notes
normalizeNumbers utility created. App.jsx updated with preprocessing and new instruction text. CSS updated for RTL decimal list. Build passes.

---

## Prompt 15 — 2026-03-14

### User Prompt
Next step: add an option to read the corrected command aloud.

Requirements:

1. Add a button that allows the user to hear the corrected command using text-to-speech (TTS).

2. The TTS should run in the frontend (for example using the browser Web Speech API) and should read the reformulated command that was returned from the backend.

3. The button should appear only when a valid corrected command is displayed.

4. When the user presses the button, the system should read the corrected command aloud.

5. Update the usage instructions in the interface to explain this option to the user.

The instructions should now include something like:

1. הקלידו את הבקשה שלכם בתיבה.
2. לחצו על כפתור השליחה.
3. הפעילו את סירי ואמרו לה את הפקודה המתוקנת או לחצו על כפתור ההקראה כדי להשמיע לסירי את הפקודה.

Keep the interface simple, clear, and friendly for older adults.

Before implementing, briefly explain:

- how the TTS will be implemented
- which browser TTS options are available
- whether a specific voice can be selected
- whether a Hebrew voice is available
- where the button will appear in the UI

### Claude Response
Pre-implementation explanation provided:

- TTS: browser-native Web Speech API (SpeechSynthesis), no external service
- utterance.lang = 'he-IL' set always; speechSynthesis.getVoices() filtered for lang.startsWith('he')
- Hebrew voice availability: built-in on iOS Safari (primary target); varies on Windows Chrome
- Button placement: inside ResultDisplay success card, below result text, only when result !== null
- useTTS hook owns all TTS state; ResultDisplay uses it internally

Files created/modified:

frontend/src/utils/useTTS.js (NEW)
- Custom React hook: speak(text) + speaking boolean
- Loads voices via voiceschanged event (async on most browsers)
- Sets lang='he-IL', picks first Hebrew voice if available, rate=0.9
- Cancels prior speech before starting new utterance

frontend/src/components/ResultDisplay.jsx
- Imports useTTS(); calls speak(result) on button click
- Button label: '🔊 הקראת הפקודה' (idle) / '🔊 מקריא...' (speaking)
- Button disabled while speaking; aria-label set
- resultLabel simplified to 'הפקודה המתוקנת:'
- TTS button hidden on error card

frontend/src/components/ResultDisplay.module.css
- Added .ttsButton: full-width, 52px min-height, teal/green tones matching
  the success card, hover/active/disabled/focus-visible states

frontend/src/App.jsx
- Step 3 updated: 'הפעילו את סירי ואמרו לה את הפקודה המתוקנת, או לחצו
  על כפתור ההקראה כדי להשמיע אותה.'

Build: ✓ 38 modules, 0 errors

### Notes
4 commits pushed to GitHub. No backend changes.
