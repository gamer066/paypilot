"""Records the PayPilot demo video by itself: drives the real app in Chrome,
adds a computer voice-over and captions, saves demo_backup.mp4.
Run:  python make_demo_video.py
"""
import json
import os
import re
import subprocess
import sys
import time
import wave

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PORT = 8766
APP = f"http://localhost:{PORT}"
SITE = "https://paypilotai.pages.dev/"
W, H = 1280, 720
TMP = os.path.join(HERE, "_video_tmp")
os.makedirs(TMP, exist_ok=True)

# ---- narration ---------------------------------------------------------
SCRIPT = {
    "intro": "Hi, I'm Salman. This is PayPilot, an A.I. agent that chases unpaid invoices for small U.A.E. businesses. "
             "And it never sends a message without a human approving it.",
    "invoices": "Here are ten sample invoices. All the companies are fake. The agent has already checked each one. "
                "Invoice ten oh six is flagged because the VAT is ten percent, but U.A.E. VAT is five. "
                "Invoice ten oh seven has no tax registration number. These two will not be chased until a person fixes them.",
    "run": "Now I click run agent. It finds the overdue invoices and the one due soon, and writes a reminder for each. "
           "Polite first, firmer later. The two invoices with errors are sent to a human instead.",
    "approve": "Nothing has been sent yet. Every reminder waits here for the manager. I can read it, edit it, and click approve. "
               "Only now does the email go out. Here it is in the outbox. Even if the A.I. tried to send early, the code refuses.",
    "reply": "Now customers reply. This one says, we will pay Friday. The agent updates the status to promised and pauses reminders.",
    "dispute": "This customer says the invoice is wrong. The agent marks it disputed, stops chasing, and alerts a human.",
    "report": "Every week the agent writes a plain English cash summary for the owner, with a download button.",
    "audit": "And here is the audit log. Every action, who did it, and when. Approvals, edits, replies and escalations are all recorded.",
    "outro": "PayPilot. Get paid, and stay in control. Thank you.",
}


def make_wavs():
    with open(os.path.join(TMP, "script.json"), "w", encoding="utf-8") as f:
        json.dump(SCRIPT, f)
    ps = r"""
Add-Type -AssemblyName System.Speech
$d = Get-Content -Raw -Encoding UTF8 '__TMP__\script.json' | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = 0
foreach ($p in $d.PSObject.Properties) {
  $s.SetOutputToWaveFile('__TMP__\' + $p.Name + '.wav')
  $s.Speak($p.Value)
}
$s.Dispose()
""".replace("__TMP__", TMP)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return {k: wave_len(os.path.join(TMP, k + ".wav")) for k in SCRIPT}


def wave_len(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


# ---- helpers -----------------------------------------------------------
CAPTION_JS = """(t) => {
  let d = document.getElementById('pp-cap');
  if (!d) { d = document.createElement('div'); d.id = 'pp-cap';
    d.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);max-width:82%;z-index:999999;'
      + 'background:rgba(5,11,24,.92);color:#fff;border:1px solid #19e6c9;border-radius:14px;padding:12px 22px;'
      + 'font:600 19px system-ui,sans-serif;text-align:center;box-shadow:0 0 30px rgba(25,230,201,.35)';
    document.body.appendChild(d); }
  d.textContent = t; }"""


def caption(page, text):
    try:
        page.evaluate(CAPTION_JS, text)
    except Exception:
        pass


def main():
    durs = make_wavs()
    print("narration lengths:", {k: round(v, 1) for k, v in durs.items()})

    # fresh fake data + local server
    subprocess.run([sys.executable, "seed.py"], check=True)
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(PORT),
                               "--server.headless", "true"], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8)

    cues = []  # (name, start_seconds)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": W, "height": H})
        page = ctx.new_page()
        t0 = time.monotonic()
        frames = []

        def grab():
            path = os.path.join(TMP, "f%05d.jpg" % len(frames))
            page.screenshot(path=path, type="jpeg", quality=72)
            frames.append((time.monotonic() - t0, path))

        def wait(sec):
            end = time.monotonic() + sec
            while time.monotonic() < end:
                grab()

        def now():
            return time.monotonic() - t0

        def scene(name, action=None):
            start = now()
            cues.append((name, start))
            caption(page, SCRIPT[name])
            if action:
                action()
            left = durs[name] + 0.8 - (now() - start)
            if left > 0:
                wait(left)

        def tab(i):
            page.get_by_role("tab").nth(i).click()
            wait(0.8)
            caption(page, current[0])

        current = [""]

        # --- intro on the website
        page.goto(SITE, wait_until="load")
        wait(1.5)
        current[0] = SCRIPT["intro"]
        scene("intro")

        # --- app
        page.goto(APP, wait_until="load")
        page.get_by_role("tab").first.wait_for(timeout=40000)
        wait(2)

        def a_invoices():
            page.mouse.wheel(0, 380)
            wait(3)
            page.mouse.wheel(0, 500)
            wait(2)
            page.mouse.wheel(0, -900)
        current[0] = SCRIPT["invoices"]
        scene("invoices", a_invoices)

        def a_run():
            tab(1)
            page.get_by_role("button", name=re.compile("Run agent now")).click()
            wait(3)
        current[0] = SCRIPT["run"]
        scene("run", a_run)

        def a_approve():
            tab(2)
            wait(2)
            page.mouse.wheel(0, 250)
            wait(3)
            page.get_by_role("button", name=re.compile("Approve and send")).first.click()
            wait(2.5)
            page.mouse.wheel(0, 900)
            wait(1)
            try:
                page.get_by_text(re.compile("accounts@")).first.click()
            except Exception:
                pass
        current[0] = SCRIPT["approve"]
        scene("approve", a_approve)

        def reply(inv_id, example):
            page.get_by_role("combobox").first.click()
            wait(0.6)
            page.get_by_role("option", name=re.compile(inv_id)).click()
            wait(0.6)
            page.get_by_text(example).first.click()
            wait(1.2)
            page.get_by_role("button", name="Process reply").click()
            wait(1.5)

        def a_reply():
            tab(3)
            reply("INV-1004", "We will pay Friday")
        current[0] = SCRIPT["reply"]
        scene("reply", a_reply)

        current[0] = SCRIPT["dispute"]
        scene("dispute", lambda: reply("INV-1002", "This invoice is wrong"))

        def a_report():
            tab(4)
            wait(2)
            page.mouse.wheel(0, 300)
        current[0] = SCRIPT["report"]
        scene("report", a_report)

        def a_audit():
            tab(5)
            wait(2)
        current[0] = SCRIPT["audit"]
        scene("audit", a_audit)

        # --- outro on the website
        page.goto(SITE, wait_until="load")
        wait(1)
        current[0] = SCRIPT["outro"]
        scene("outro")
        wait(1)

        grab()
        ctx.close()
        browser.close()
    server.terminate()

    # ---- mix audio with video
    out = os.path.join(HERE, "demo_backup.mp4")
    with open(os.path.join(TMP, "frames.txt"), "w") as f:
        for i, (t, path) in enumerate(frames):
            d = (frames[i + 1][0] - t) if i + 1 < len(frames) else 1.0
            f.write("file '%s'\nduration %.3f\n" % (path.replace("\\", "/"), d))
        f.write("file '%s'\n" % frames[-1][1].replace("\\", "/"))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(TMP, "frames.txt")]
    filters, labels = [], []
    for i, (name, start) in enumerate(cues):
        cmd += ["-i", os.path.join(TMP, name + ".wav")]
        ms = int(start * 1000) + 300
        filters.append(f"[{i + 1}:a]adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    filters.append("".join(labels) + f"amix=inputs={len(cues)}:normalize=0[a]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[a]", "-r", "12", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("DONE", out, round(now_len(out), 1), "seconds")


def now_len(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


if __name__ == "__main__":
    main()
