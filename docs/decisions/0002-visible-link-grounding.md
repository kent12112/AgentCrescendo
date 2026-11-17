# Decision: browser-grounded link selection

Date: November 16, 2026. Scope: W1X-F01 link-following demo.

## Context

Four live Qwen runs missed the Massachusetts link on the Boston article even
though the real pointer landed at the requested coordinates. Full-size images,
pixel grids, and an explicit target name did not solve it. A saved-image replay
with normalized coordinates also missed. Repeating coordinate prompts would not
provide a supported fix.

## Decision

Add opt-in `click_link(target_id)` using a bounded inventory of browser-measured
visible text links. The model receives visible labels and IDs alongside the
screenshot. The runtime privately retains element identity, destination, and a
hittable screen point. It rejects expired or changed targets, then resolves the
selection into the existing authorized `click(x, y)` path with the real pointer.

The click demo defaults to this mode. Raw pixel clicking and other demos remain
available with their existing interfaces. The inventory never supplies URLs to
the model and never navigates through a locator or synthetic DOM click.

## Consequences

This deliberately changes the model-facing observation/action interface. It
demonstrates DOM-assisted link interaction, not screenshot-only pixel grounding.
The gateway still requires the click grant and safe page area; adapter target
checks and network filtering still apply. Snapshot IDs expire and cannot be
reused across observations. Canvas controls and non-link widgets need separate
grounding work.

Evidence and failed experiments: [clicking](../e2b-clicking.md).
