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
