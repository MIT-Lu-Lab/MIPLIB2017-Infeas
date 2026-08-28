"""Render the card a shared link shows, from the site's own stylesheet.

Slack, X, LinkedIn, Discord and the rest read og:image and draw it above the
title. Without one a link to a published dataset looks like a pasted URL, which
is most of what a reader sees before deciding whether to open it.

The site follows the reader's colour scheme; a card cannot, so it is drawn
dark. data-theme is what a manual choice sets, and light-dark() resolves the
same tokens against it, so the card takes the site's own dark palette rather
than a second set of colours.

The card carries no counts. A number rendered into a committed PNG goes stale
the moment the collection changes, and no test can read it back out, so what is
drawn is only what does not expire: the name, what the collection is, and the
two colours the site uses to tell its halves apart.

Run offline; the result is committed. The build copies it and takes no
dependency on this.

    pip install --group og              # and a Chrome to drive
    python -m scripts.make_og_image

The template links the built stylesheet, so the card is drawn with the same
tokens, the same typefaces and the same hairline as the pages.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from website import INDEX_FILE, MIPLIB_FILE, ROOT, assets, content
from website import build as builder

DEFAULT_OUT = ROOT / assets.OG_IMAGE

# What a card is expected to be. Platforms crop to about 1.91:1 and downscale,
# so it is drawn at twice this and declared at this.
WIDTH, HEIGHT = assets.OG_IMAGE_SIZE
SCALE = 2

TEMPLATE = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="assets/{css}">
<style>
  /* prefixed, because the stylesheet this links already gives .card and .name
     to components of the site and a card is not one of them */
  body{{margin:0;width:{width}px;height:{height}px;overflow:hidden;
       background:var(--paper);display:flex;flex-direction:column}}
  /* the hairline takes its colours from body[data-view] on a page, which says
     which half you are looking at. A card is about both, so it says so */
  .hairline{{height:16px}}
  .hairline span:first-child{{background:var(--primal)}}
  .hairline span:last-child{{background:var(--dual)}}
  .og-body{{flex:1;display:flex;flex-direction:column;justify-content:center;
           gap:30px;padding:0 88px}}
  .og-name{{font-family:var(--f-mono);font-weight:600;font-size:82px;
           letter-spacing:-.03em;color:var(--ink)}}
  .og-name .dash{{color:var(--muted)}}
  .og-tagline{{font-family:var(--f-serif);font-size:40px;line-height:1.25;
              color:var(--muted);max-width:940px;margin:0}}
  .og-foot{{font-family:var(--f-mono);font-size:24px;color:var(--muted);
           padding:0 88px 60px}}
</style>
</head>
<body>
<div class="hairline"><span></span><span></span></div>
<div class="og-body">
  <div class="og-name">{name}</div>
  <p class="og-tagline">{tagline}</p>
</div>
<div class="og-foot">{host}</div>
</body>
</html>
"""


def _wait_for_target(port: int) -> dict:
    for _ in range(200):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=0.5
            ) as response:
                for target in json.load(response):
                    if target.get("type") == "page":
                        return target
        except OSError, ValueError:
            pass
        time.sleep(0.05)
    raise SystemExit("Chrome did not open a DevTools target")


class _DevTools:
    def __init__(self, url: str) -> None:
        # websocket-client is used only by this manual script, whose result is
        # committed. It is not part of the site build or CI environment, so the
        # type checker does not require it there.
        try:
            from websocket import (  # pyright: ignore[reportMissingImports]
                create_connection,
            )
        except ImportError:
            raise SystemExit("this script needs websocket-client: pip install --group og") from None

        self.socket = create_connection(url, timeout=20, suppress_origin=True)
        self.count = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.count += 1
        self.socket.send(json.dumps({"id": self.count, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") != self.count:
                continue
            if "error" in message:
                raise SystemExit(f"{method}: {message['error']}")
            return message.get("result", {})

    def evaluate(self, expression: str) -> object:
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in result:
            raise SystemExit(str(result["exceptionDetails"]))
        return result["result"].get("value")


def _card_html() -> str:
    host = content.PUBLIC_SITE_URL.split("//", 1)[-1].rstrip("/")
    name = content.NAME.replace("-", '<span class="dash">-</span>')
    return TEMPLATE.format(
        css=assets.CSS_NAME,
        width=WIDTH,
        height=HEIGHT,
        name=name,
        tagline=content.TAGLINE,
        host=host,
    )


def render(chrome: Path, out: Path, port: int) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        builder.build(INDEX_FILE, site, miplib_path=MIPLIB_FILE)
        card = site / "_og-card.html"
        card.write_text(_card_html(), encoding="utf-8", newline="\n")

        profile = Path(tmp) / "profile"
        process = subprocess.Popen(
            [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                f"--remote-debugging-port={port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            devtools = _DevTools(str(_wait_for_target(port)["webSocketDebuggerUrl"]))
            devtools.call("Page.enable")
            devtools.call("Runtime.enable")
            # layout in CSS pixels, and let the capture do the scaling: a
            # deviceScaleFactor here plus fromSurface returns a partly painted
            # buffer under headless
            devtools.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": WIDTH, "height": HEIGHT, "deviceScaleFactor": 1, "mobile": False},
            )
            devtools.call("Page.navigate", {"url": card.as_uri()})
            for _ in range(400):
                ready = devtools.evaluate(
                    "document.readyState === 'complete' && document.fonts.status === 'loaded'"
                )
                if ready:
                    break
                time.sleep(0.02)
            else:
                raise SystemExit("the card never finished loading its fonts")
            shot = devtools.call(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "captureBeyondViewport": True,
                    "clip": {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT, "scale": SCALE},
                },
            )
            out.write_bytes(base64.b64decode(str(shot["data"])))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--chrome",
        type=Path,
        default=Path(
            r"C:\Program Files\Google\Chrome"
            r"\Application\chrome.exe"
        ),
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--port", type=int, default=9422)
    args = parser.parse_args()
    if not args.chrome.is_file():
        raise SystemExit(f"{args.chrome}: no Chrome there. Pass --chrome.")
    render(args.chrome, args.out, args.port)
    print(
        f"{args.out}: {args.out.stat().st_size:,} bytes, "
        f"{WIDTH * SCALE}x{HEIGHT * SCALE} for a {WIDTH}x{HEIGHT} card"
    )


if __name__ == "__main__":
    main()
