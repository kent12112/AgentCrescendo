"""Read visible link geometry without asking the model to estimate pixels.

The browser retains element references privately. Only IDs and visible labels go
to the model. Resolving an ID checks that the same element still occupies the
saved point and has the same text and destination. Execution still uses click().
"""

MAX_VISIBLE_LINKS = 120

# Geometry is in viewport pixels; page.left/top translate it to desktop pixels.
# Client rects handle wrapped inline links; bounding-box centers can hit empty space.
READ_LINK_TARGETS = """({page, firstId, limit}) => {
    const targets = [];
    for (const element of document.querySelectorAll('a[href]')) {
        let transparent = false;
        for (let node = element; node; node = node.parentElement) {
            if (Number(getComputedStyle(node).opacity) === 0) { transparent = true; break; }
        }
        if (transparent) continue;
        const label = (element.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 160);
        if (!label) continue;
        let point = null;
        for (const rect of element.getClientRects()) {
            const left = Math.max(0, rect.left), top = Math.max(0, rect.top);
            const right = Math.min(page.right - page.left, rect.right);
            const bottom = Math.min(page.bottom - page.top, rect.bottom);
            if (right - left < 2 || bottom - top < 2) continue;
            const x = Math.floor((left + right) / 2), y = Math.floor((top + bottom) / 2);
            const hit = document.elementFromPoint(x, y);
            if (hit && hit.closest('a[href]') === element) {
                point = {x, y};
                break;
            }
        }
        if (!point) continue;
        targets.push({id: firstId + targets.length, label, element,
                      href: element.href, point,
                      x: point.x + page.left, y: point.y + page.top});
        if (targets.length >= limit) break;
    }
    return targets;
}"""

LINK_LABELS = "targets => targets.map(({id, label}) => ({id, label}))"

# Do not silently move an old selection onto a different element after a reflow.
RESOLVE_LINK_TARGET = """(targets, id) => {
    const target = targets.find(target => target.id === id);
    if (!target || !target.element.isConnected) return null;
    const {element, point} = target;
    for (let node = element; node; node = node.parentElement) {
        if (Number(getComputedStyle(node).opacity) === 0) return null;
    }
    if (element.ownerDocument !== document || element.href !== target.href ||
        (element.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 160) !== target.label) return null;
    const hit = document.elementFromPoint(point.x, point.y);
    if (!hit || hit.closest('a[href]') !== element) return null;
    return {x: target.x, y: target.y};
}"""
