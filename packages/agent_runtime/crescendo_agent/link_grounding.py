"""Read visible link geometry without asking the model to estimate pixels.

The browser retains element references privately. Only IDs and visible labels go
to the model. Resolving an ID checks that the same element still occupies the
saved point and has the same text and destination. Execution still uses click().
Text fields (W1X-F03) work the same way; execution uses type_text().
"""

MAX_VISIBLE_LINKS = 120
# Text fields listed alongside links when type_text is granted (W1X-F03).
MAX_VISIBLE_FIELDS = 10

# Field kinds type_text may fill: one-line text inputs and textareas. Never
# password, hidden, file, checkbox, or anything else. Shared by every field check
# below so listing, resolving, and typing agree on what a field is.
TEXT_FIELD = """const TEXT_TYPES = ['text', 'search', 'email', 'url', 'tel', 'number'];
const isTextField = el => !!el && !el.disabled && !el.readOnly && (
    el.tagName === 'TEXTAREA' ||
    (el.tagName === 'INPUT' && TEXT_TYPES.includes((el.getAttribute('type') || 'text').toLowerCase())));
const fieldLabel = el => ((el.labels && el.labels[0] && el.labels[0].innerText) ||
    el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('title') ||
    el.getAttribute('name') || 'text field').replace(/\\s+/g, ' ').trim().slice(0, 160);"""

# Geometry is in viewport pixels; page.left/top translate it to desktop pixels.
# Client rects handle wrapped inline links; bounding-box centers can hit empty space.
READ_LINK_TARGETS = """({page, firstId, limit, fieldLimit}) => {
    """ + TEXT_FIELD + """
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
    // Text fields (only when fieldLimit > 0). The model types into them by ID with
    // type_text; the adapter re-checks the field and its keyboard focus first.
    let fields = 0;
    for (const element of document.querySelectorAll('input, textarea')) {
        if (fields >= fieldLimit) break;
        if (!isTextField(element)) continue;
        let transparent = false;
        for (let node = element; node; node = node.parentElement) {
            if (Number(getComputedStyle(node).opacity) === 0) { transparent = true; break; }
        }
        if (transparent) continue;
        const rect = element.getBoundingClientRect();
        const left = Math.max(0, rect.left), top = Math.max(0, rect.top);
        const right = Math.min(page.right - page.left, rect.right);
        const bottom = Math.min(page.bottom - page.top, rect.bottom);
        if (right - left < 2 || bottom - top < 2) continue;
        const point = {x: Math.floor((left + right) / 2), y: Math.floor((top + bottom) / 2)};
        if (document.elementFromPoint(point.x, point.y) !== element) continue;
        targets.push({id: firstId + targets.length, label: fieldLabel(element), kind: 'field',
                      element, point, x: point.x + page.left, y: point.y + page.top});
        fields += 1;
    }
    return targets;
}"""

# Links keep their {id, label} shape; fields add kind so the model can tell them apart.
LINK_LABELS = ("targets => targets.map(({id, label, kind}) => "
               "kind === 'field' ? {id, label, kind} : {id, label})")

# Host-only (JOB-F01): the browser's own label and destination for chosen link IDs.
# Never sent to the model; used to turn a cited ID into a trusted offer record.
LINK_RECORDS = ("(targets, ids) => targets.filter(t => t.kind !== 'field' && ids.includes(t.id))"
                ".map(({id, label, href, x, y}) => ({id, label, href, x, y}))")

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

# Same idea for a field: still connected, still a text field with the same label,
# and still the element at the saved point. Returns the desktop point or null.
RESOLVE_FIELD_TARGET = """(targets, id) => {
    """ + TEXT_FIELD + """
    const target = targets.find(target => target.id === id && target.kind === 'field');
    if (!target || !target.element.isConnected) return null;
    const {element, point} = target;
    for (let node = element; node; node = node.parentElement) {
        if (Number(getComputedStyle(node).opacity) === 0) return null;
    }
    if (element.ownerDocument !== document || !isTextField(element) ||
        fieldLabel(element) !== target.label) return null;
    if (document.elementFromPoint(point.x, point.y) !== element) return null;
    return {x: target.x, y: target.y};
}"""
