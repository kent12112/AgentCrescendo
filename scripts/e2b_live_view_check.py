"""Check real noVNC rendering in local Edge with controlled asset failures.

Creates one metered E2B desktop, without Wikipedia or model calls. Requires local
Microsoft Edge, as does smoke_live_view.py. Logs only sanitized paths/categories;
private viewer URLs, VNC passwords, and traffic tokens remain in memory.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import sync_playwright
from crescendo_agent import live_view
from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_agent.local_env import load_local_env
from crescendo_security.policy import TaskGrant


def safe_path(url):
    path = urlsplit(str(url)).path
    return '/watch/[redacted]' if path.startswith('/watch/') else path


def main():
    load_local_env()
    folder = Path('.demo-artifacts') / ('viewer-probe-' + uuid4().hex)
    folder.mkdir(parents=True)
    metrics = []
    injected = {'required': 0, 'optional': 0}
    base_client = httpx.AsyncClient

    class LoggedClient(base_client):
        async def get(self, url, **kwargs):
            started = time.monotonic()
            path = safe_path(url)
            if path == '/core/rfb.js' and injected['required'] == 0:
                injected['required'] += 1
                metrics.append({'path': path, 'injected': 'single_connect_error'})
                raise httpx.ConnectError('controlled test failure')
            if path.endswith('/favicon.ico'):
                injected['optional'] += 1
                metrics.append({'path': path, 'injected': 'persistent_connect_error'})
                raise httpx.ConnectError('controlled optional asset failure')
            try:
                response = await super().get(url, **kwargs)
            except httpx.HTTPError as error:
                metrics.append({'path': safe_path(url), 'error_type': type(error).__name__,
                                'seconds': round(time.monotonic() - started, 2)})
                raise
            metrics.append({'path': safe_path(url), 'status': response.status_code,
                            'seconds': round(time.monotonic() - started, 2)})
            return response

    grant = TaskGrant('viewer-probe', frozenset({'navigate', 'screenshot', 'view_desktop'}),
                      frozenset({'en.wikipedia.org'}))
    result = {'artifacts': str(folder), 'vnc_connected': False, 'desktop_pixels_rendered': False}
    with open_e2b_desktop(grant, lifetime_seconds=180) as desktop:
        desktop.page.set_content('<main style="font:36px Arial;padding:60px">VIEWER CONNECTION PROBE</main>', wait_until='load')
        (folder / 'remote.png').write_bytes(desktop.capture_screen().png)
        with patch.object(live_view.httpx, 'AsyncClient', LoggedClient):
            with desktop.live_view() as viewer:
                def browser_probe():
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(channel='msedge', headless=True)
                        page = browser.new_page()
                        page.on('requestfailed', lambda request: metrics.append({
                            'browser_path': safe_path(request.url), 'failure': 'BROWSER_REQUEST_FAILED'}))
                        try:
                            page.goto(viewer.url, wait_until='domcontentloaded', timeout=35000)
                            page.wait_for_function("document.documentElement.classList.contains('noVNC_connected')", timeout=35000)
                            result['vnc_connected'] = True
                            page.wait_for_function('''() => {
                                const canvas = document.querySelector('#noVNC_container canvas');
                                if (!canvas || !canvas.width || !canvas.height) return false;
                                const context = canvas.getContext('2d');
                                if (!context) return false;
                                const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
                                let painted = 0;
                                for (let index = 0; index < pixels.length; index += 64) {
                                    if (pixels[index] > 40 || pixels[index+1] > 40 || pixels[index+2] > 40) painted++;
                                }
                                return painted > 1000;
                            }''', timeout=15000, polling=250)
                            result['desktop_pixels_rendered'] = True
                        except Exception as error:
                            result['browser_error_type'] = type(error).__name__
                        finally:
                            try:
                                result['status_text'] = page.locator('#noVNC_status').inner_text(timeout=1000)
                                page.screenshot(path=str(folder / 'viewer.png'))
                            except Exception:
                                pass
                            browser.close()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(browser_probe).result(timeout=80)
                result['transport_connected_after_browser_close'] = viewer.connected.is_set()
                result['viewer_errors'] = list(viewer.errors)
    result['requests'] = metrics
    result['injected_failures'] = injected
    (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'requests'}, indent=2), flush=True)
    if not result['vnc_connected'] or not result['desktop_pixels_rendered'] or result['viewer_errors']:
        raise SystemExit('FAIL: the live viewer did not render the controlled desktop.')
    print('PASS: the authenticated live viewer rendered the desktop despite controlled asset failures.')


if __name__ == '__main__':
    main()
