# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""The model's stated reason: recorded for display, never part of the authorized action."""
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: From types, import SimpleNamespace as NS (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace as NS
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.vision, import MAX_REASON_CHARS (a dependency used below); VISION_TOOLS (a
# dependency used below); GroqVision (adapts screenshot observations to Groq vision requests); Proposal
# (pairs the proposed action with an untrusted display reason); Screenshot (validates the PNG container and
# dimensions at the image boundary); clean_reason (a dependency used below).
from crescendo_agent.vision import (MAX_REASON_CHARS, VISION_TOOLS, GroqVision, Proposal,
                                    # Learn: Continue the expression Screenshot, clean_reason); brackets
                                    # keep it part of the statement above.
                                    Screenshot, clean_reason)
# Learn: From crescendo_agent.vision_loop, import run_vision_agent (runs the bounded
# screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import run_vision_agent
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Learn: Set GRANT to TaskGrant('vision', frozenset({'screenshot', 'scroll', 'finish'}), frozenset()).
GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())
# Learn: Set PNG to
# Screenshot(bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c020000000b4944415478da63fcff1f0003030200ef....
PNG = Screenshot(bytes.fromhex(
    # Learn: Supply literal text
    # '89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c020000000b4944415478da63fcff1f0003030200efa3875b0000000049454e...;
    # adjacent string literals are concatenated without adding whitespace.
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
    # Learn: Supply the next argument to bytes.fromhex:
    # "0000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082")).
    "0000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082"))


# Learn: Define reply(name, args). The body runs when called, not when defined.
def reply(name, args):
    # Learn: Return NS(choices=[NS(finish_reason='tool_calls', message=NS(tool_calls=[NS(type='function',
    # function=NS(name=name, arguments=json.dumps(ar... to the caller and stop this function.
    return NS(choices=[NS(finish_reason="tool_calls", message=NS(tool_calls=[
        # Learn: Pass keyword type = 'function'.
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))]))])


# Learn: Define decide(name, args). The body runs when called, not when defined.
def decide(name, args):
    # Learn: Set client to Mock(); the HTTP/model client, often injectable so tests avoid live calls.
    client = Mock()
    # Learn: Set client.chat.completions.create.return_value to reply(name, args).
    client.chat.completions.create.return_value = reply(name, args)
    # Learn: Return GroqVision(client=client).decide(PNG, []) to the caller and stop this function.
    return GroqVision(client=client).decide(PNG, [])


# Learn: Test every tool asks for a reason. pytest supplies named fixtures and checks assertions below.
def test_every_tool_asks_for_a_reason():
    # Learn: Iterate over VISION_TOOLS, binding tool for each item.
    for tool in VISION_TOOLS:
        # Learn: Set parameters to tool['function']['parameters'].
        parameters = tool["function"]["parameters"]
        # Learn: Assert that 'reason' is in parameters['required']. If false, this check fails with
        # AssertionError.
        assert "reason" in parameters["required"]
        # Learn: Assert that parameters['properties']['reason']['maxLength'] equals MAX_REASON_CHARS. If
        # false, this check fails with AssertionError.
        assert parameters["properties"]["reason"]["maxLength"] == MAX_REASON_CHARS


# Learn: Test reason is separated from the action arguments. pytest supplies named fixtures and checks
# assertions below.
def test_reason_is_separated_from_the_action_arguments():
    # Learn: Set proposal to decide('scroll', {'direction': 'down', 'amount': 5, 'reason': 'Infobox
    # continues below'}); the model action plus its optional, untrusted display reason. Ask the adapter for
    # a proposal; this does not itself execute a tool.
    proposal = decide("scroll", {"direction": "down", "amount": 5, "reason": "Infobox continues below"})
    # Learn: Assert that proposal equals Proposal(ToolCall('scroll', {'direction': 'down', 'amount': 5}),
    # 'Infobox continues below'). If false, this check fails with AssertionError.
    assert proposal == Proposal(ToolCall("scroll", {"direction": "down", "amount": 5}), "Infobox continues below")
    # Learn: Set finish to decide('finish', {'answer': '617565', 'reason': 'GNIS feature ID is visible'}).
    # Ask the adapter for a proposal; this does not itself execute a tool.
    finish = decide("finish", {"answer": "617565", "reason": "GNIS feature ID is visible"})
    # Learn: Assert that finish.call.args equals a new dictionary with keys 'answer'. If false, this check
    # fails with AssertionError.
    assert finish.call.args == {"answer": "617565"}


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("args", [
    # Learn: Add this item to the surrounding list: {"direction": "down", "amount": 5}, # missing.
    {"direction": "down", "amount": 5},                 # missing
    # Learn: Add this item to the surrounding list: {"direction": "down", "amount": 5, "reason": 7}, # wrong
    # type.
    {"direction": "down", "amount": 5, "reason": 7},     # wrong type
    # Learn: Add this item to the surrounding list: {"direction": "down", "amount": 5, "reason": " "}, #
    # blank.
    {"direction": "down", "amount": 5, "reason": "  "},  # blank
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test unusable reason never fails the step. pytest supplies named fixtures and checks assertions
# below.
def test_unusable_reason_never_fails_the_step(args):
    # Learn: Set proposal to decide('scroll', args); the model action plus its optional, untrusted display
    # reason. Ask the adapter for a proposal; this does not itself execute a tool.
    proposal = decide("scroll", args)
    # Learn: Assert that proposal.call equals ToolCall('scroll', {'direction': 'down', 'amount': 5}). If
    # false, this check fails with AssertionError.
    assert proposal.call == ToolCall("scroll", {"direction": "down", "amount": 5})
    # Learn: Assert that proposal.reason is None (no value). If false, this check fails with AssertionError.
    assert proposal.reason is None


# Learn: Test clean reason is one bounded line. pytest supplies named fixtures and checks assertions below.
def test_clean_reason_is_one_bounded_line():
    # Learn: Assert that clean_reason('Infobox\n\tcontinues below') equals 'Infobox continues below'. If
    # false, this check fails with AssertionError.
    assert clean_reason("Infobox\n\tcontinues   below") == "Infobox continues below"
    # Learn: Assert that the number of items/characters in clean_reason('x' * 500) equals MAX_REASON_CHARS.
    # If false, this check fails with AssertionError.
    assert len(clean_reason("x" * 500)) == MAX_REASON_CHARS


# Learn: Test extra unknown arguments are still rejected. pytest supplies named fixtures and checks
# assertions below.
def test_extra_unknown_arguments_are_still_rejected():
    # Learn: Enter pytest.raises(ValueError). The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with pytest.raises(ValueError):
        # Learn: Ask the adapter for a proposal; this does not itself execute a tool; inputs: 'scroll', a
        # new dictionary with keys 'direction', 'amount', 'reason', 'command'.
        decide("scroll", {"direction": "down", "amount": 5, "reason": "ok", "command": "rm -rf /"})


# Learn: Test loop records reason but authorizes only the action. pytest supplies named fixtures and checks
# assertions below.
def test_loop_records_reason_but_authorizes_only_the_action():
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set desktop.capture_screen.return_value to PNG.
    desktop.capture_screen.return_value = PNG
    # Learn: Set model to Mock(); the provider adapter or scripted test model used to propose actions.
    model = Mock()
    # Learn: Set model.decide.side_effect to a new list containing Proposal(ToolCall('scroll', {'direction':
    # 'down', 'amount': 9}), 'Too far, on purpose'), Proposal(ToolCall('scroll', {'direction': '....
    model.decide.side_effect = [
        # Learn: Call Proposal with the arguments shown.
        Proposal(ToolCall("scroll", {"direction": "down", "amount": 9}), "Too far, on purpose"),
        # Learn: Call Proposal with the arguments shown.
        Proposal(ToolCall("scroll", {"direction": "down", "amount": 2}), "Infobox continues below"),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "617565"}),  # A bare ToolCall still works.
    # Learn: Close this list literal; delimiters group the values into one object.
    ]
    # Learn: Set result to run_vision_agent('g', GRANT, desktop, model); the operation outcome for
    # subsequent checks or reporting.
    result = run_vision_agent("g", GRANT, desktop, model)
    # Learn: Set actions to a list built from result.transcript by the comprehension with its filter.
    actions = [json.loads(e.text) for e in result.transcript if e.kind == "action"]
    # Learn: Assert that actions[0]['reason'] equals 'Too far, on purpose' AND the number of
    # items/characters in result.denied equals 1. If false, this check fails with AssertionError.
    assert actions[0]["reason"] == "Too far, on purpose" and len(result.denied) == 1
    # Learn: Assert that actions[1] equals a new dictionary with keys 'tool', 'args', 'reason'. If false,
    # this check fails with AssertionError.
    assert actions[1] == {"tool": "scroll", "args": {"direction": "down", "amount": 2},
                          # Learn: Define this named mapping field: "reason": "Infobox continues below"}.
                          # The key selects the schema/configuration value.
                          "reason": "Infobox continues below"}
    # Learn: Assert that 'reason' is not in actions[2]. If false, this check fails with AssertionError.
    assert "reason" not in actions[2]
    # Learn: Verify the fake dependency ran exactly once with these arguments on desktop.scroll; inputs:
    # 'down', 2.
    desktop.scroll.assert_called_once_with("down", 2)
    # Learn: Assert that result.answer equals '617565'. If false, this check fails with AssertionError.
    assert result.answer == "617565"
