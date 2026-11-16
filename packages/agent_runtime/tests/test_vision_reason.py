"""The model's stated reason: recorded for display, never part of the authorized action."""
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import from types: SimpleNamespace as NS (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace as NS
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.vision: MAX_REASON_CHARS (a dependency used below); VISION_TOOLS (a
# dependency used below); GroqVision (adapts screenshot observations to Groq vision requests);
# Proposal (pairs the proposed action with an untrusted display reason); Screenshot (validates the
# PNG container and dimensions at the image boundary); clean_reason (a dependency used below).
from crescendo_agent.vision import (MAX_REASON_CHARS, VISION_TOOLS, GroqVision, Proposal,
                                    # Continue the expression Screenshot, clean_reason); brackets
                                    # keep it part of the statement above.
                                    Screenshot, clean_reason)
# Import from crescendo_agent.vision_loop: run_vision_agent (runs the bounded
# screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import run_vision_agent
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Set GRANT to TaskGrant('vision', frozenset({'screenshot', 'scroll', 'finish'}), frozenset()).
GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())
# Set PNG to
# Screenshot(bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c020000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082')).
PNG = Screenshot(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
    "0000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082"))


# Define reply with parameters name, args.
def reply(name, args):
    return NS(choices=[NS(finish_reason="tool_calls", message=NS(tool_calls=[
        # Pass keyword type = 'function'.
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))]))])


# Define decide with parameters name, args.
def decide(name, args):
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.return_value to reply(name, args).
    client.chat.completions.create.return_value = reply(name, args)
    # Return GroqVision(client=client).decide(PNG, []).
    return GroqVision(client=client).decide(PNG, [])


# Define test_every_tool_asks_for_a_reason with no parameters.
def test_every_tool_asks_for_a_reason():
    # Iterate over VISION_TOOLS, binding tool for each item.
    for tool in VISION_TOOLS:
        # Set parameters to tool['function']['parameters'].
        parameters = tool["function"]["parameters"]
        # Assert that 'reason' is in parameters['required']. If false, this check fails with
        # AssertionError.
        assert "reason" in parameters["required"]
        # Assert that parameters['properties']['reason']['maxLength'] equals MAX_REASON_CHARS. If
        # false, this check fails with AssertionError.
        assert parameters["properties"]["reason"]["maxLength"] == MAX_REASON_CHARS


# Define test_reason_is_separated_from_the_action_arguments with no parameters.
def test_reason_is_separated_from_the_action_arguments():
    # Set proposal to decide('scroll', {'direction': 'down', 'amount': 5, 'reason': 'Infobox
    # continues below'}).
    proposal = decide("scroll", {"direction": "down", "amount": 5, "reason": "Infobox continues below"})
    # Assert that proposal equals Proposal(ToolCall('scroll', {'direction': 'down', 'amount': 5}),
    # 'Infobox continues below'). If false, this check fails with AssertionError.
    assert proposal == Proposal(ToolCall("scroll", {"direction": "down", "amount": 5}), "Infobox continues below")
    # Set finish to decide('finish', {'answer': '617565', 'reason': 'GNIS feature ID is visible'}).
    finish = decide("finish", {"answer": "617565", "reason": "GNIS feature ID is visible"})
    # Assert that finish.call.args equals a new dictionary with keys 'answer'. If false, this check
    # fails with AssertionError.
    assert finish.call.args == {"answer": "617565"}


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("args", [
    # Add this item to the surrounding list: {"direction": "down", "amount": 5}, # missing.
    {"direction": "down", "amount": 5},                 # missing
    # Add this item to the surrounding list: {"direction": "down", "amount": 5, "reason": 7}, #
    # wrong type.
    {"direction": "down", "amount": 5, "reason": 7},     # wrong type
    # Add this item to the surrounding list: {"direction": "down", "amount": 5, "reason": " "}, #
    # blank.
    {"direction": "down", "amount": 5, "reason": "  "},  # blank
])
# Define test_unusable_reason_never_fails_the_step with parameters args.
def test_unusable_reason_never_fails_the_step(args):
    # Set proposal to decide('scroll', args).
    proposal = decide("scroll", args)
    # Assert that proposal.call equals ToolCall('scroll', {'direction': 'down', 'amount': 5}). If
    # false, this check fails with AssertionError.
    assert proposal.call == ToolCall("scroll", {"direction": "down", "amount": 5})
    # Assert that proposal.reason is None (no value). If false, this check fails with
    # AssertionError.
    assert proposal.reason is None


# Define test_clean_reason_is_one_bounded_line with no parameters.
def test_clean_reason_is_one_bounded_line():
    # Assert that clean_reason('Infobox\n\tcontinues below') equals 'Infobox continues below'. If
    # false, this check fails with AssertionError.
    assert clean_reason("Infobox\n\tcontinues   below") == "Infobox continues below"
    # Assert that the number of items/characters in clean_reason('x' * 500) equals MAX_REASON_CHARS.
    # If false, this check fails with AssertionError.
    assert len(clean_reason("x" * 500)) == MAX_REASON_CHARS


# Define test_extra_unknown_arguments_are_still_rejected with no parameters.
def test_extra_unknown_arguments_are_still_rejected():
    # Use pytest.raises(ValueError); leave the context and run its cleanup when this block ends.
    with pytest.raises(ValueError):
        # Call decide with 'scroll', {'direction': 'down', 'amount': 5, 'reason': 'ok', 'command':
        # 'rm -rf /'}.
        decide("scroll", {"direction": "down", "amount": 5, "reason": "ok", "command": "rm -rf /"})


# Define test_loop_records_reason_but_authorizes_only_the_action with no parameters.
def test_loop_records_reason_but_authorizes_only_the_action():
    # Set desktop to Mock().
    desktop = Mock()
    # Set desktop.capture_screen.return_value to PNG.
    desktop.capture_screen.return_value = PNG
    # Set model to Mock().
    model = Mock()
    # Build model.decide.side_effect from the entries below.
    model.decide.side_effect = [
        # Call Proposal with the arguments shown.
        Proposal(ToolCall("scroll", {"direction": "down", "amount": 9}), "Too far, on purpose"),
        # Call Proposal with the arguments shown.
        Proposal(ToolCall("scroll", {"direction": "down", "amount": 2}), "Infobox continues below"),
        # Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "617565"}),  # A bare ToolCall still works.
    ]
    # Set result to run_vision_agent('g', GRANT, desktop, model).
    result = run_vision_agent("g", GRANT, desktop, model)
    # Set actions to [json.loads(e.text) for e in result.transcript if e.kind == 'action'].
    actions = [json.loads(e.text) for e in result.transcript if e.kind == "action"]
    # Assert that actions[0]['reason'] equals 'Too far, on purpose' AND the number of
    # items/characters in result.denied equals 1. If false, this check fails with AssertionError.
    assert actions[0]["reason"] == "Too far, on purpose" and len(result.denied) == 1
    # Assert that actions[1] equals a new dictionary with keys 'tool', 'args', 'reason'. If false,
    # this check fails with AssertionError.
    assert actions[1] == {"tool": "scroll", "args": {"direction": "down", "amount": 2},
                          # Include reason in this dictionary.
                          "reason": "Infobox continues below"}
    # Assert that 'reason' is not in actions[2]. If false, this check fails with AssertionError.
    assert "reason" not in actions[2]
    # Call desktop.scroll.assert_called_once_with with 'down', 2.
    desktop.scroll.assert_called_once_with("down", 2)
    # Assert that result.answer equals '617565'. If false, this check fails with AssertionError.
    assert result.answer == "617565"
