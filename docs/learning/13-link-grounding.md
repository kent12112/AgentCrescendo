# Link selection and pixel grounding are different tasks

The model knew the word “Massachusetts” but missed its position. The pointer
followed the requested coordinates exactly. That separates **planning** (choose
the right link), **grounding** (find its pixels), **authorization** (may this
action run?), and **execution** (move and press).

A deterministic mouse test proves execution, not model grounding. A model reason
such as “Massachusetts” proves neither that it pointed at that word nor that a
navigation occurred. Check the recorded browser destination and the next image.

Permission checks should name the operation they protect. `visible_links()`
previously checked `ToolCall("screenshot")` despite reading DOM metadata rather
than taking an image. It now checks `ToolCall("read_visible_links")`; the adapter
also requires click permission because this inventory supplies click targets.
Creating a `ToolCall` describes an operation for authorization; it does not run
that operation. Screenshot capture remains a separate call and permission.

The fix gives the worker the camera image plus an inventory of visible links.
The worker chooses an inventory ID. The browser measures the point. The guard
still checks the point and target before allowing the robot hand to click. This
adds DOM assistance; it does not improve the model's raw pixel estimation.

An inventory is a snapshot, not a permanent map. IDs expire on the next
observation. Before using a selection, verify that its original element is still
attached with the same text/destination and still lies under the saved point.
The live fixture deliberately changes each of these conditions and observes a
refusal. Hidden, transparent, covered, and off-screen links are excluded.

We tested the coordinate-convention hypothesis first. Both an explicit pixel
prompt and a normalized-coordinate prompt missed the saved target. We removed
the normalized prototype instead of presenting it as a fix. The grounded live
run then clicked the target on its first choice and opened Massachusetts. Its
first full-demo attempt still failed because the provider throttled the final
answer. The next run passed with one bounded wait. A correct action and a fully
completed task are separate outcomes.

Use `.venv/bin/python -m pytest -q` for local contract and refusal checks; `-m`
runs pytest inside the project interpreter, and `-q` reduces routine output.
Those tests do not prove the browser's actual geometry or the model's choice.
`scripts/e2b_click_check.py` exercises real browser geometry/security without a
model; `scripts/e2b_click_demo.py --save-screenshots` exercises model selection,
real navigation, and final answer. Both live scripts create metered E2B resources;
the demo also calls Groq and saves ignored diagnostic artifacts.

See [decision](../decisions/0002-visible-link-grounding.md) and
[evidence](../e2b-clicking.md).
