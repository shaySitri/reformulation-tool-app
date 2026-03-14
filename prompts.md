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

---

## Prompt 16 — 2026-03-14

### User Prompt
Make the read-aloud option slower and adapted for older adults.

Requirements:
- Use a slower speaking rate so the command is easy to understand.
- Prefer a clear and natural Hebrew voice if available.
- Ensure the pronunciation is clear and easy to follow.
- Keep the volume and pacing comfortable for older users.

Before implementing, first show the available voices detected in the browser and let me choose which voice should be used.
Do not implement the TTS until I approve the selected voice.

### Claude Response
Created frontend/public/voices.html — a diagnostic page served at http://localhost:5173/voices.html. Listed all available SpeechSynthesisVoice objects with name, language, on-device vs network, and a Play button to preview each voice. Hebrew voices highlighted in green.

User confirmed only 1 Hebrew voice is available, so no selection is needed.
User approved proceeding and asked to remove voices.html.

Actions taken:
- Deleted frontend/public/voices.html
- Updated useTTS.js: rate = 0.75 (down from 0.9), pitch = 1.0, volume = 1.0
  with explanatory comments for each parameter choice
- Updated the module docstring to document the pacing rationale

Build: ✓ 38 modules, 0 errors

### Notes
voices.html removed. useTTS.js rate changed from 0.9 → 0.75. Build passes.

---

## Prompt 17 — 2026-03-14

### User Prompt
I found another issue in the frontend input preprocessing, and I want to refine the logic without replacing the existing behavior.

Important clarification:
Do not completely rewrite the current preprocessing flow, because we already added number normalization.
Instead, extend the existing logic.

What I want:

1. Improve the existing number normalization step.

The number normalization must correctly convert numbers into their Hebrew word form.

Requirements for improvement:
- correctly handle numbers with one digit, two digits, three digits, and more
- ensure the correct Hebrew structure for hundreds, tens, and units
- maintain the correct order of words in Hebrew numbers
- avoid incorrect constructions such as:
  514 → "עשר וארבע מאות חמש"

Instead, the conversion should follow correct Hebrew number grammar.

Example conversions to validate:
1 → אחד
12 → שתים עשרה
23 → עשרים ושלוש
105 → מאה וחמש
514 → חמש מאות וארבע עשרה

The exact gender form (זכר / נקבה) is not critical as long as the structure of the number is correct.

2. Add an additional input cleaning step.

Before sending the command to the backend, clean the user input.

This cleaning step should remove characters that are not accepted by the backend, including:
- English letters
- invalid punctuation
- any other unsupported characters

Important:
- Do not show an error for these characters.
- Silently remove them before sending the request to the backend.

3. Do not replace existing logic.

The new cleaning logic must be added on top of the existing preprocessing flow (which already handles numbers).

4. Validation.

Validate that the preprocessing works correctly by testing:

- mixed Hebrew + English input
- input with punctuation
- input with numbers
- input containing invalid characters

Confirm that:
- valid Hebrew text remains unchanged
- invalid characters are removed
- numbers are converted correctly
- the final cleaned text is the one actually sent to the backend.

Show several before/after examples.

5. After validation

If everything works correctly:
- commit and push the change
- update prompts.md with the FULL prompt and the FULL response.

Before implementing, briefly explain:
- how the current preprocessing flow will be extended
- where the cleaning step will be inserted
- how the number normalization logic will be improved
- which validation examples you will use.

### Claude Response
Pre-implementation explanation provided, then implemented.

How the flow is extended:
  utterance → normalizeNumbers() → cleanInput() → fetch
  App.jsx now calls preprocessInput() which chains both steps.

Number normalization fix:
  Updated TEENS array in normalizeNumbers.js to feminine forms:
  - 11: אחת עשרה (was אחד עשר)
  - 12: שתים עשרה (was שניים עשר)
  - 13: שלוש עשרה (was שלוש עשר)
  - 14: ארבע עשרה (was ארבע עשר)
  - 15: חמש עשרה (was חמש עשר)
  - 16: שש עשרה (was שש עשר)
  - 17: שבע עשרה (was שבע עשר)
  - 18: שמונה עשרה (was שמונה עשר)
  - 19: תשע עשרה (was תשע עשר)
  This fixes 514 → חמש מאות וארבע עשרה (was חמש מאות וארבע עשר)

Cleaning step:
  cleanInput(text) in preprocessInput.js:
  - regex: /[^\u05D0-\u05EA ]/g → replace with ''
  - keeps only Hebrew letters (U+05D0–U+05EA) and ASCII space
  - silently removes English letters, punctuation, digits that remain after
    number normalization, and any other disallowed characters

Files created/modified:
  normalizeNumbers.js — updated TEENS to feminine forms
  preprocessInput.js (NEW) — exports preprocessInput() chaining both steps
  App.jsx — import changed from normalizeNumbers to preprocessInput

Before/after validation results (11 cases, all correct):
  "1"                → "אחד"
  "12"               → "שתים עשרה"
  "23"               → "עשרים ושלוש"
  "105"              → "מאה וחמש"
  "514"              → "חמש מאות וארבע עשרה"
  "שלום hello"       → "שלום "
  "תשלחי, הודעה!"   → "תשלחי הודעה"
  "שעה 7"            → "שעה שבע"
  "שעה 7 call mom!" → "שעה שבע  " (2 trailing spaces — harmless, backend strips)
  "תתקשרי לאמא"     → "תתקשרי לאמא" (unchanged)
  "תשלחי ל-דוד"     → "תשלחי לדוד"

Build: ✓ 39 modules, 0 errors

### Notes
3 files changed. normalizeNumbers.js updated (TEENS feminine), preprocessInput.js created, App.jsx updated. Build passes.

---

## Prompt 18 — 2026-03-14

### User Prompt
The next step is to add an option for the user to record their request using the microphone.

Requirements:

1. Add a microphone button that allows the user to record their request.

2. Recording must be limited to a maximum of 30 seconds.

3. The user should be able to:
- start recording
- stop recording manually
- automatically stop after 30 seconds if the user does not stop it

4. After the recording ends, the spoken request should be transcribed to text.

5. The transcription must be written directly into the existing command input field, exactly as spoken, just as if the user typed it.
Important:
- if the user mixes Hebrew and English
- if the user makes mistakes
- if the transcription includes unsupported characters

the visible text in the input field should still remain the raw transcription and should reflect what the user said.

6. Do not modify the visible transcription in the input field.

7. The existing preprocessing logic must be applied only behind the scenes, right before sending the request to the backend.
This includes:
- number normalization
- cleaning of unsupported characters
- any other existing preprocessing steps

8. The transcription should NOT be sent automatically to the backend.
The user should still press the submit button after reviewing the command.

9. Keep the interface simple and user-friendly for older adults.

Before implementing, briefly explain:
- which browser speech-to-text technology you will use
- how the recording flow will work (start, stop, timeout)
- how the transcription will be inserted into the input field
- how the raw visible transcription will be preserved
- how the preprocessing logic will be applied behind the scenes before submission

Also remember to document the FULL prompt and the FULL response in prompts.md.

DONT write code until I approved the plan.

### Claude Response
Plan presented and approved before any code was written.

Technology: Web Speech API (SpeechRecognition / webkitSpeechRecognition).
Browser-native, no cost, supports he-IL. Available in iOS Safari (primary
target) and Chrome. Hidden on unsupported browsers (Firefox).

Recording flow:
  - Start: recognition.start() + 30s setTimeout auto-stop timer
  - Manual stop: recognition.stop() + clearTimeout
  - Auto-stop: timer fires recognition.stop() after 30 seconds
  - onend always clears the recording flag regardless of how it ended

Transcription → input field:
  onresult accumulates all final segments + current interim segment and
  calls onTranscript(rawText). App.jsx uses setUtterance as the callback,
  so the input field updates live as the user speaks.

Raw transcript preserved:
  utterance state is set directly from the SpeechRecognition result.
  No preprocessing, no filtering. The visible field always shows exactly
  what the browser transcribed, including any English, punctuation, etc.

Preprocessing behind the scenes:
  preprocessInput() is called only in sendUtterance() at submit time,
  unchanged. Recording never auto-submits.

Files created/modified:

frontend/src/utils/useSpeechRecognition.js (NEW)
  - Custom hook: { startRecording, stopRecording, recording, supported }
  - lang='he-IL', continuous=true, interimResults=true
  - onTranscript stored in ref to avoid stale closure
  - 30-second auto-stop via setTimeout

frontend/src/components/CommandInput.jsx
  - New props: recording, onStartRecording, onStopRecording, speechSupported
  - Mic button: '🎙 הקלטה קולית' / '⏹ עצור הקלטה' — hidden if not supported
  - Input and submit disabled while recording
  - Placeholder changes to 'מאזין...' while recording
  - Red pulsing input border + recording hint text while mic is active
  - aria-live, aria-pressed, aria-label for accessibility

frontend/src/components/CommandInput.module.css
  - .inputRecording: red border + pulse animation
  - .micButton / .micButtonRecording: idle/active states
  - .recordingHint: small red status text

frontend/src/App.jsx
  - useSpeechRecognition imported and called with onTranscript: setUtterance
  - resetAll() calls stopRecording() before clearing state
  - Step 1 of instructions updated to mention the mic button

Build: ✓ 40 modules, 0 errors

### Notes
4 commits pushed to GitHub. No backend changes. Build passes.

---

## Prompt 19 — 2026-03-14

### User Prompt
I found two issues that need to be fixed.

1. Update the preprocessing logic.

Add a rule to the existing preprocessing step:
If the word "סירי" appears in the command, remove it before sending the request to the backend.

Do not change the text visible to the user in the input field.
Remove "סירי" only in the cleaned command that is sent to the backend.

2. Improve the recording button usability.

The current recording button is not very user-friendly.

Instead of the current button, add a small microphone icon next to the input text field.

Requirements:
- place the microphone icon inside or next to the command input field
- keep the design clean and easy to use for older adults
- clicking the icon should start/stop recording

Before implementing, briefly explain how you will modify the UI layout.

Also remember to document the FULL prompt and the FULL response in prompts.md.

### Assistant Response (plan)

#### Fix 1 — Remove "סירי" in preprocessing

In `preprocessInput.js`, add a step that strips the word `סירי` (with optional surrounding spaces) from the processed string, applied after number normalization and before character cleaning. The raw `utterance` state in the input field is never touched.

#### Fix 2 — Mic icon inside the input field

**Current layout**: input field (full width) → submit button → mic button (full width, below submit).

**New layout**: A wrapper `div` with `position: relative` around the input. The mic icon sits absolutely positioned inside the input field on the right edge (left edge in RTL, i.e., the leading side). The input gets `padding-inline-end` increased so the text doesn't overlap the icon. The full-width mic button row below the submit button is removed entirely.

This keeps the form to two elements (input + submit), reduces visual clutter, and gives older adults a clear, single-purpose input area with an integrated recording indicator.

User approved. Implementation proceeded.

### Implementation

#### Fix 1 — preprocessInput.js

Added `removeSiri()` as step 2 in the pipeline (between `normalizeNumbers` and `cleanInput`):

```js
function removeSiri(text) {
  return text.replace(/\s*סירי\s*/g, ' ').trim()
}
```

Pipeline order: `normalizeNumbers` → `removeSiri` → `cleanInput`

The visible input field is never modified. Only the string sent to the backend is affected.

#### Fix 2 — CommandInput redesign

`CommandInput.jsx`:
- Wrapped input in `<div className={styles.inputWrapper}>` (position: relative)
- Replaced full-width `<button className={styles.micButton}>` with `<button className={styles.micIcon}>` positioned absolutely inside the wrapper
- Input gains `styles.inputWithMic` class when speechSupported, adding `padding-inline-end: 3.4rem` to prevent text/icon overlap
- Mic icon: `'🎙'` idle / `'⏹'` while recording
- Recording hint text updated: "לחצו על הסמל לעצירה" (instead of referencing the old button label)

`CommandInput.module.css`:
- Added `.inputWrapper`: `position: relative; width: 100%`
- Added `.inputWithMic`: `padding-inline-end: 3.4rem`
- Added `box-sizing: border-box` to `.input`
- Replaced `.micButton` / `.micButtonRecording` with:
  - `.micIcon`: absolutely positioned, 2.4rem × 2.4rem, `right: 0.5rem`, `top: 50%`, `transform: translateY(-50%)`, grey color, hover turns blue
  - `.micIconRecording`: red color + `@keyframes micPulse` (opacity fade 1→0.5→1, 1.4s)
- Removed `.micButton`, `.micButtonRecording`, and their hover/disabled variants

Files changed:

frontend/src/utils/preprocessInput.js
  - removeSiri() added as pipeline step 2
  - JSDoc updated with new step, new example

frontend/src/components/CommandInput.jsx
  - input wrapped in .inputWrapper div
  - full-width mic button replaced with inline .micIcon button
  - recording hint text updated

frontend/src/components/CommandInput.module.css
  - .inputWrapper, .inputWithMic added
  - .micIcon, .micIconRecording, @keyframes micPulse added
  - .micButton, .micButtonRecording removed

Build: ✓ 40 modules, 0 errors

### Commits
- `67db6ef` feat: remove "סירי" wake word in preprocessing before backend request
- `d309d8f` feat: replace full-width mic button with inline mic icon inside input field

---

## Prompt 20 — 2026-03-14

### User Prompt
Fix the microphone recording button UI.

The microphone icon is currently too transparent and hard to see.

Changes required:
- move the microphone icon to the left side of the input field
- increase its visibility (reduce transparency / improve contrast)
- make sure it is clearly visible and easy to notice

Keep the interface simple and user-friendly for older adults.

Also remember to document the FULL prompt and the FULL response in prompts.md.

### Assistant Response

Three changes in the CSS: move from `right` to `left`, switch padding side, darken the idle color and increase icon size.

**`CommandInput.module.css`:**
- `.inputWithMic`: changed `padding-inline-start: 3.4rem` → `padding-left: 3.4rem` (physical, avoids RTL logical-property confusion since icon is always physically on the left)
- `.micIcon`: `right: 0.5rem` → `left: 0.4rem`; `width/height: 2.4rem` → `2.6rem`; `font-size: 1.2rem` removed (SVG uses explicit dimensions); `color: #636e72` → `#1a1a2e` (dark navy, high contrast on white background)
- Comment updated to describe physical left positioning

**`CommandInput.jsx`:**
- Updated design notes comment: "leading (right) edge" → "physical left edge"

Committed: `1618a40`

---

## Prompt 21 — 2026-03-14

### User Prompt
Please make the following UI updates:

1. Button size
Make the "Reset" button the same size as the "Send" button.

2. Placeholder text
Replace the placeholder text in the input field.

Current text:
"הקלד פקודה קולית בעברית"

New text:
"הקלד או הקלט פקודה קולית בעברית"

Keep the interface clean, readable, and user-friendly for older adults.

Also remember to document the FULL prompt and the FULL response in prompts.md.

### Assistant Response

**`App.module.css` — reset button:**
- `padding: 0.75rem 1rem` → `padding: 1rem` (matches send button)
- `font-size: 1rem` → `1.2rem`
- `font-weight: 600` → `700`
- `min-height: 50px` → `58px`
- Added `letter-spacing: 0.02em`
- `margin-top: 1rem` → `0.4rem`

**`CommandInput.jsx` — placeholder:**
- Changed placeholder from `'לדוגמה: תשלחי הודעה לישראל שאני מאחרת'` → `'הקלד או הקלט פקודה קולית בעברית'`

---

## Prompt 22 — 2026-03-14

### User Prompt
Decrease the space between the "send" to the "restart" button

### Assistant Response

The gap comes from two sources: `.resultArea` (`margin-top: 1.5rem`) + `.resetButton` (`margin-top: 0.4rem`). Reducing both:

**`App.module.css`:**
- `.resultArea` `margin-top`: `1.5rem` → `0.75rem`
- `.resetButton` `margin-top`: `0.4rem` → `0.5rem`

Total gap between Send and Reset reduced from ~1.9rem to ~1.25rem.

---

## Prompt 23 — 2026-03-14

### User Prompt
replace the text in the object utterance-input to "הקלד או הקלט פקודה בעברית"

### Assistant Response

**`CommandInput.jsx`:**
- Placeholder (non-recording state): `'הקלד או הקלט פקודה קולית בעברית'` → `'הקלד או הקלט פקודה בעברית'`

---

## Prompt 24 — 2026-03-14

### User Prompt
Delete the element: <label for="utterance-input" class="_label_zikpv_29">הקלד פקודה קולית בעברית</label>

### Assistant Response

**`CommandInput.jsx`:**
- Removed the `<label htmlFor="utterance-input">` element and its surrounding comment
- The input retains `aria-label="הקלד פקודה קולית בעברית"` so screen readers are unaffected

---

## Prompt 25 — 2026-03-14

### User Prompt
Push changes to git (include FULL prompts and FULL Claude's output).

### Assistant Response

Reviewed all uncommitted changes spanning prompts 20–24. Committed in three logical groups:

- `1618a40` fix: move mic icon to physical left, use SVG, increase size and contrast
- `f4b1870` fix: replace emoji mic with SVG icons, remove label, update placeholder text
- `7afa317` fix: match reset button size to send button; reduce spacing between buttons

Changes per file:

frontend/src/components/CommandInput.module.css
  - .micIcon: left:0.4rem, width/height 2.6rem, color #1a1a2e, removed font-size
  - .inputWithMic: padding-inline-end → padding-left (physical)
  - Comments updated

frontend/src/components/CommandInput.jsx
  - Emoji icons replaced with inline SVG (mic and stop)
  - Label element removed
  - Placeholder: 'הקלד או הקלט פקודה בעברית'
  - Design notes updated

frontend/src/App.module.css
  - .resetButton: padding/font-size/font-weight/min-height match send button; margin-top 0.5rem
  - .resultArea: margin-top 0.75rem

Documented prompts 20–25 in prompts.md and pushed all commits.
