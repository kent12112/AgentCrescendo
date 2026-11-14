"""The model's stated reason: recorded for display, never part of the authorized action."""
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from crescendo_agent.vision import (MAX_REASON_CHARS, VISION_TOOLS, GroqVision, Proposal,
                                    Screenshot, clean_reason)
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant, ToolCall

GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())
PNG = Screenshot(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
    "0000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082"))


def reply(name, args):
    return NS(choices=[NS(finish_reason="tool_calls", message=NS(tool_calls=[
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))]))])


def decide(name, args):
    client = Mock()
    client.chat.completions.create.return_value = reply(name, args)
    return GroqVision(client=client).decide(PNG, [])


def test_every_tool_asks_for_a_reason():
    for tool in VISION_TOOLS:
        parameters = tool["function"]["parameters"]
        assert "reason" in parameters["required"]
        assert parameters["properties"]["reason"]["maxLength"] == MAX_REASON_CHARS


def test_reason_is_separated_from_the_action_arguments():
    proposal = decide("scroll", {"direction": "down", "amount": 5, "reason": "Infobox continues below"})
    assert proposal == Proposal(ToolCall("scroll", {"direction": "down", "amount": 5}), "Infobox continues below")
    finish = decide("finish", {"answer": "617565", "reason": "GNIS feature ID is visible"})
    assert finish.call.args == {"answer": "617565"}


@pytest.mark.parametrize("args", [
    {"direction": "down", "amount": 5},                 # missing
    {"direction": "down", "amount": 5, "reason": 7},     # wrong type
    {"direction": "down", "amount": 5, "reason": "  "},  # blank
])
def test_unusable_reason_never_fails_the_step(args):
    proposal = decide("scroll", args)
    assert proposal.call == ToolCall("scroll", {"direction": "down", "amount": 5})
    assert proposal.reason is None


def test_clean_reason_is_one_bounded_line():
    assert clean_reason("Infobox\n\tcontinues   below") == "Infobox continues below"
    assert len(clean_reason("x" * 500)) == MAX_REASON_CHARS


def test_extra_unknown_arguments_are_still_rejected():
    with pytest.raises(ValueError):
        decide("scroll", {"direction": "down", "amount": 5, "reason": "ok", "command": "rm -rf /"})


def test_loop_records_reason_but_authorizes_only_the_action():
    desktop = Mock()
    desktop.capture_screen.return_value = PNG
    model = Mock()
    model.decide.side_effect = [
        Proposal(ToolCall("scroll", {"direction": "down", "amount": 9}), "Too far, on purpose"),
        Proposal(ToolCall("scroll", {"direction": "down", "amount": 2}), "Infobox continues below"),
        ToolCall("finish", {"answer": "617565"}),  # A bare ToolCall still works.
    ]
    result = run_vision_agent("g", GRANT, desktop, model)
    actions = [json.loads(e.text) for e in result.transcript if e.kind == "action"]
    assert actions[0]["reason"] == "Too far, on purpose" and len(result.denied) == 1
    assert actions[1] == {"tool": "scroll", "args": {"direction": "down", "amount": 2},
                          "reason": "Infobox continues below"}
    assert "reason" not in actions[2]
    desktop.scroll.assert_called_once_with("down", 2)
    assert result.answer == "617565"
