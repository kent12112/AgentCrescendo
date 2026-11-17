"""Gateway rules for type_text (W1X-F03): argument shape, text limits, page area."""
import pytest

from crescendo_security.policy import (MAX_TYPED_CHARS, ScreenArea, TaskGrant, ToolCall,
                                       authorize)

GRANT = TaskGrant("t", frozenset({"type_text"}), frozenset(), public_web=True)
AREA = ScreenArea(left=0, top=114, right=1024, bottom=700)


def typing(**overrides):
    args = {"x": 300, "y": 200, "text": "Boston Common", "submit": True}
    args.update(overrides)
    return ToolCall("type_text", args)


def test_one_line_of_text_into_the_page_is_allowed():
    assert authorize(GRANT, typing(), click_area=AREA).allowed
    assert authorize(GRANT, typing(submit=False, text="x" * MAX_TYPED_CHARS), click_area=AREA).allowed
    assert authorize(GRANT, typing(text="café 東京"), click_area=AREA).allowed


def test_tool_must_be_granted():
    other = TaskGrant("o", frozenset({"click"}), frozenset(), public_web=True)
    assert not authorize(other, typing(), click_area=AREA).allowed


@pytest.mark.parametrize("text", [
    "", "   ", "x" * (MAX_TYPED_CHARS + 1), 42, None,
    "line one\nline two",        # newline would submit on its own
    "a\tb",                      # tab would move focus to another control
    "bell\x07", "esc\x1b[",      # other control characters
])
def test_bad_text_is_refused(text):
    decision = authorize(GRANT, typing(text=text), click_area=AREA)
    assert not decision.allowed and "printable" in decision.reason


@pytest.mark.parametrize("args", [
    {"x": 300, "y": 200, "text": "a"},                                  # missing submit
    {"x": 300, "y": 200, "text": "a", "submit": True, "url": "x"},      # extra key
    {"x": True, "y": 200, "text": "a", "submit": True},                 # bool is not an int
    {"x": "300", "y": 200, "text": "a", "submit": True},
    {"x": -1, "y": 200, "text": "a", "submit": True},
])
def test_malformed_arguments_are_refused(args):
    assert not authorize(GRANT, ToolCall("type_text", args), click_area=AREA).allowed


def test_submit_must_be_a_real_bool():
    assert "submit" in authorize(GRANT, typing(submit="yes"), click_area=AREA).reason
    assert not authorize(GRANT, typing(submit=1), click_area=AREA).allowed


def test_field_must_be_inside_the_known_page_area():
    # y=60 is Chrome's address bar: typing there is exactly what must never happen.
    assert "outside" in authorize(GRANT, typing(y=60), click_area=AREA).reason
    assert "unknown" in authorize(GRANT, typing()).reason
