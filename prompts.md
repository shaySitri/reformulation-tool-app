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
