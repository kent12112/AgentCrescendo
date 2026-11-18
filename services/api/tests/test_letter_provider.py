"""Exercise the Thinker/Worker/Verifier adapter at its SDK boundary without paid requests or private data."""
import json
import sys
from types import SimpleNamespace

import pytest

from crescendo_api import letters
from crescendo_api.letters import DraftUnavailable, generate_draft

INPUTS = {"model": "openai/gpt-oss-120b", "resume": "[NAME]\nBuilt Python data pipelines for 3 years."}
RESEARCH = {"status": "done", "facts": [{"topic": "product", "claim": "Builds a profiler.",
            "quote": "Our profiler shows developers where their code spends time.", "url": "https://fictional.example/about"}]}
POSTING = {"company": "Fictional Co", "title": "AI Engineer", "description": "We build tools for developers.",
           "company_notes": "", "company_research": RESEARCH}
FILLER = "This matters to me because the work and the tools are tied to the same everyday developer problem."
WORKER_OUT = {"paragraphs": [[
    {"text": "Fictional Co's profiler shows developers where their code spends time.", "source": "company_research",
     "quote": "Our profiler shows developers where their code spends time.", "supporting_quotes": []},
    {"text": "I built Python data pipelines for 3 years.", "source": "resume",
     "quote": "Built Python data pipelines for 3 years.", "supporting_quotes": []},
    {"text": "Your team builds tools for developers.", "source": "posting",
     "quote": "We build tools for developers.", "supporting_quotes": []},
    {"text": FILLER, "source": "none", "quote": "", "supporting_quotes": []}],
    [{"text": FILLER, "source": "none", "quote": "", "supporting_quotes": []}] * 3]}
PLAN = {"company_hooks": [{"source": "company_research", "quote": RESEARCH["facts"][0]["quote"], "why": "specific"}],
        "candidate_evidence": [{"quote": "Built Python data pipelines for 3 years.", "relevance": "data tooling"}],
        "connection": "Pipeline work meets profiling.", "outline": ["hook", "evidence"], "avoid": ["hype"]}
ACCEPT = {"accept": True, "issues": [], "summary": "Specific and supported."}
REJECT = {"accept": False, "issues": [{"sentence": 2, "problem": "Too thin.", "fix": "Explain the link."}], "summary": "Needs a link."}
PRIVATE = "private-source-or-provider-body-must-never-be-relayed"


def role_of(request):
    return request["messages"][0]["content"].split("You are the ")[1].split(" ")[0].lower()


@pytest.fixture
def sdk(monkeypatch):
    """Each role gets a queue of replies; the last reply repeats."""
    calls, options = [], []
    replies = {"thinker": [PLAN], "worker": [WORKER_OUT], "verifier": [ACCEPT]}
    state = {"finish": "stop", "error": None, "raw": {}}

    class FakeClient:
        def __init__(self, **kwargs):
            options.append(kwargs)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def create(self, **kwargs):
            calls.append(kwargs)
            role = role_of(kwargs)
            if state["error"]:
                raise state["error"]
            queue = replies[role]
            reply = queue.pop(0) if len(queue) > 1 else queue[0]
            content = state["raw"].get(role, json.dumps(reply))
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason=state["finish"],
                                                            message=SimpleNamespace(content=content))])

    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=FakeClient))
    return SimpleNamespace(replies=replies, state=state, calls=calls, options=options)


def test_accepting_verifier_ends_after_three_strict_turns(sdk):
    traces = []
    text, checks = generate_draft(INPUTS, POSTING, "fake-key", on_turn=traces.append)
    assert [role_of(c) for c in sdk.calls] == ["thinker", "worker", "verifier"]
    assert sdk.options == [{"api_key": "fake-key", "timeout": letters.TURN_TIMEOUT, "max_retries": 0}]
    for request in sdk.calls:
        assert request["reasoning_effort"] == "low"
        assert request["response_format"]["type"] == "json_schema"
        assert request["response_format"]["json_schema"]["strict"] is True
    worker = sdk.calls[1]
    sentence = worker["response_format"]["json_schema"]["schema"]["$defs"]["Sentence"]
    assert set(sentence["required"]) == {"text", "source", "quote", "supporting_quotes"}
    assert "company_research" in sentence["properties"]["source"]["enum"]
    assert "maxLength" not in sentence["properties"]["text"]
    payload = json.loads(worker["messages"][1]["content"])
    assert payload["question"] == "Why do you want to work at Fictional Co?"
    assert RESEARCH["facts"][0]["quote"] in payload["company_research"]
    assert payload["plan"]["connection"] == PLAN["connection"]
    # A form answer: no greeting or signature, and the research quote is checked.
    assert not text.startswith("Dear") and "[NAME]" not in text
    assert checks[0]["source"] == "company_research" and checks[0]["quote_found"] is True
    assert checks[-1]["source"] == "verifier" and "accepted" in checks[-1]["text"]
    assert [len(t) for t in traces] == [1, 2, 3]
    assert [t["role"] for t in traces[-1]] == ["thinker", "worker", "verifier"]
    assert traces[-1][2]["detail"]["accepted"] is True


def test_rejection_sends_feedback_and_revision_is_rechecked(sdk):
    revised = json.loads(json.dumps(WORKER_OUT))
    revised["paragraphs"][0][3]["text"] = "Pipelines and profilers both show developers where time goes."
    sdk.replies.update(worker=[WORKER_OUT, revised], verifier=[REJECT, ACCEPT])
    text, checks = generate_draft(INPUTS, POSTING, "fake-key")
    assert [role_of(c) for c in sdk.calls] == ["thinker", "worker", "verifier", "worker", "verifier"]
    revision = json.loads(sdk.calls[3]["messages"][1]["content"])
    assert revision["verifier_feedback"]["issues"] == REJECT["issues"]
    assert revision["previous_draft"][1]["text"] == "I built Python data pipelines for 3 years."
    assert "where time goes" in text
    assert checks[-1]["text"] == "The Verifier accepted this answer on turn 5."


def test_host_check_failure_overrides_an_accepting_verifier(sdk):
    bad = json.loads(json.dumps(WORKER_OUT))
    bad["paragraphs"][0][1] = {"text": "I built Python pipelines for 9 years.", "source": "resume",
                               "quote": "Built Python pipelines for 9 years.", "supporting_quotes": []}
    sdk.replies.update(worker=[bad])
    text, checks = generate_draft(INPUTS, POSTING, "fake-key")
    assert len(sdk.calls) == 5  # accept + failed host check is not accepted; revise once more
    verifier = json.loads(sdk.calls[2]["messages"][1]["content"])
    assert any("Sentence 2" in p and "not found" in p for p in verifier["host_checks"])
    assert checks[-1]["source"] == "verifier" and "schedule ended" in checks[-1]["text"]
    assert any("Sentence 2" in flag for flag in checks[-1]["flags"])


def test_unusable_plan_is_skipped_but_provider_outage_stops(sdk):
    sdk.state["raw"]["thinker"] = '{"oops": '
    text, _ = generate_draft(INPUTS, POSTING, "fake-key")
    assert "profiler" in text
    assert json.loads(sdk.calls[1]["messages"][1]["content"])["plan"] is None


def test_failed_revision_keeps_previous_checked_draft(sdk):
    sdk.replies.update(verifier=[REJECT])
    sdk.replies["worker"] = [WORKER_OUT, {"paragraphs": "not a list"}]
    text, checks = generate_draft(INPUTS, POSTING, "fake-key")
    assert len(sdk.calls) == 4 and "profiler" in text
    assert "previous draft is kept" in checks[-1]["text"]


def test_time_budget_stops_new_turns_after_a_draft(sdk):
    sdk.replies.update(verifier=[REJECT])
    ticks = iter([0, 0, 1, 1, 2, 2, 3, 500, 500, 500, 500])
    _, checks = generate_draft(INPUTS, POSTING, "fake-key", clock=lambda: next(ticks))
    assert [role_of(c) for c in sdk.calls] == ["thinker", "worker", "verifier"]
    assert "time budget" in checks[-1]["text"]


def test_complete_json_at_length_limit_becomes_reviewable_draft(sdk):
    sdk.state["finish"] = "length"
    _, checks = generate_draft(INPUTS, POSTING, "fake-key")
    assert checks[-1]["source"] == "generation_limit"
    assert "completeness" in checks[-1]["flags"][0]


@pytest.mark.parametrize(("finish", "content", "expected"), [
    ("length", '{"paragraphs": [', "response limit before finishing"),
    ("stop", '{"paragraphs": [', "invalid structure"),
    ("stop", '{"paragraphs": ["wrong paragraph shape"]}', "invalid structure"),
    ("stop", json.dumps({"paragraphs": [[]]}), "unusable draft"),
])
def test_first_draft_failures_are_safe(sdk, finish, content, expected):
    sdk.state["finish"] = finish
    sdk.state["raw"]["worker"] = content
    with pytest.raises(DraftUnavailable, match=expected) as caught:
        generate_draft(INPUTS, POSTING, "fake-key")
    assert content not in str(caught.value)
    assert [role_of(c) for c in sdk.calls] == ["thinker", "worker"]


def test_non_stop_finish_is_a_safe_failure(sdk):
    sdk.state["finish"] = "content_filter"
    sdk.state["raw"]["thinker"] = json.dumps(PLAN)
    with pytest.raises(DraftUnavailable, match="did not return a completed worker"):
        generate_draft(INPUTS, POSTING, "fake-key")


@pytest.mark.parametrize(("status", "error_name", "retry", "expected"), [
    (429, "RateLimitError", "17", "Wait 18 seconds"),
    (429, "RateLimitError", "not-numeric-" + PRIVATE, "quota to reset"),
    (429, "RateLimitError", "NaN", "quota to reset"),
    (401, "AuthenticationError", "", "credentials or model access"),
    (403, "PermissionDeniedError", "", "credentials or model access"),
    (400, "BadRequestError", "", "rejected this answer request"),
    (404, "NotFoundError", "", "model was not found"),
    (503, "InternalServerError", "", "temporarily unavailable"),
    (None, "APITimeoutError", "", "took too long"),
    (None, "APIConnectionError", "", "Could not connect"),
    (None, "UnexpectedSDKError", "", "failed unexpectedly"),
])
def test_safe_provider_categories_never_relay_bodies(sdk, caplog, status, error_name, retry, expected):
    error = type(error_name, (Exception,), {})(PRIVATE)
    error.status_code = status
    error.body = {"error": {"message": PRIVATE}}
    error.response = SimpleNamespace(headers={"retry-after": retry})
    sdk.state["error"] = error
    with pytest.raises(DraftUnavailable, match=expected) as caught:
        generate_draft(INPUTS, POSTING, "fake-key")
    assert PRIVATE not in str(caught.value) and PRIVATE not in caplog.text
    assert len(str(caught.value)) < 300
    assert len(sdk.calls) == 1  # A quota failure must not become a hidden paid retry loop.


def test_other_models_keep_json_mode_without_unsupported_reasoning_option(sdk):
    generate_draft({**INPUTS, "model": "custom-other-model"}, POSTING, "fake-key")
    assert all(c["response_format"] == {"type": "json_object"} for c in sdk.calls)
    assert all("reasoning_effort" not in c for c in sdk.calls)


def test_posting_without_research_still_drafts(sdk):
    posting = {k: v for k, v in POSTING.items() if k != "company_research"}
    _, checks = generate_draft(INPUTS, posting, "fake-key")
    assert checks[0]["source"] == "company_research" and checks[0]["quote_found"] is False
