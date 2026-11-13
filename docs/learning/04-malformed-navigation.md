# Review exercise: malformed navigation proposals

Date: November 13, 2026

Problem: the gateway denied invalid ports, but `urlsplit` itself could raise `ValueError` for malformed bracketed hosts or unsafe Unicode delimiters. The browser interceptor caught this exception; the agent loop called the gateway directly and crashed instead of receiving a denial.

Prediction and reproduction: added three malformed URL cases to the policy tests and a scripted agent case proposing an invalid URL, then a permitted URL, then finishing. Before the fix, all four new cases failed with parser exceptions; 20 existing targeted cases passed.

Decision: catch only `ValueError` around URL parsing and return a denied decision with a stable reason. Keep unrelated programming errors visible. Reuse the existing denial transcript and bounded replanning behavior instead of adding a separate recovery mechanism. No desktop or model API calls are required for this change.

Review the small change in `packages/security/crescendo_security/policy.py`, then the tests in `packages/security/tests/test_policy.py` and `packages/agent_runtime/tests/test_loop.py`. The loop test checks that only the permitted page was visited, the malformed proposal was recorded as denied, the model saw the denial, and the run finished.

Limit: this handles URL parser errors. It does not establish complete URL/browser parsing equivalence, network isolation, or real E2B behavior. Those still need separate validation.

Result: after the fix, all 90 Python test cases passed, including the four new regression cases. `git diff --check` passed. The suite emitted the existing Starlette/httpx deprecation warning.
