"""Takes real screenshots of the running app for the website. Run: python make_screenshots.py"""
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("docs/img", exist_ok=True)
PORT = 8767
env = dict(os.environ)
env.pop("ANTHROPIC_API_KEY", None)
subprocess.run([sys.executable, "seed.py"], check=True, stdout=subprocess.DEVNULL)
srv = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(PORT),
                        "--server.headless", "true"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(8)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_context(viewport={"width": 1400, "height": 860}, device_scale_factor=1).new_page()
        pg.goto(f"http://localhost:{PORT}", wait_until="load")
        pg.get_by_role("tab").first.wait_for(timeout=40000)
        time.sleep(2)
        pg.get_by_role("button", name=re.compile("One-click demo")).click()
        time.sleep(6)
        shot = lambda n: pg.screenshot(path=f"docs/img/{n}.jpg", type="jpeg", quality=82)
        shot("invoices")
        pg.get_by_role("tab").nth(2).click(); time.sleep(2)
        pg.mouse.wheel(0, 120); time.sleep(1)
        shot("approvals")
        pg.get_by_role("tab").nth(4).click(); time.sleep(3)
        shot("report")
        pg.get_by_role("tab").nth(5).click(); time.sleep(2)
        shot("audit")
        b.close()
finally:
    srv.terminate()
print("screenshots saved")
