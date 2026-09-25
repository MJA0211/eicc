"""Package the captured browser video, captions, gallery, and verification manifest.

Run from any directory after `npm --prefix frontend run demo:capture`.
Requires FFmpeg with libx264/libass and FFprobe, either on PATH or in Ubuntu WSL.
The original capture stays in ignored .local/. Repository outputs contain no sessions.
"""

import hashlib
import html
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs" / "demo"


def executable(name: str) -> list[str]:
    if name not in {"ffmpeg", "ffprobe"}:
        raise ValueError("Only the fixed media tools may be executed")
    resolved = shutil.which(name)
    if resolved:
        return [resolved]
    wsl = shutil.which("wsl")
    if wsl:
        result = subprocess.run(  # noqa: S603 - fixed tool allowlist, no shell
            [wsl, "-d", "Ubuntu", "-u", "root", "--", name, "-version"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return [wsl, "-d", "Ubuntu", "-u", "root", "--cd", str(ROOT), "--", name]
    raise SystemExit(f"Install {name} on PATH (or in Ubuntu WSL), then rerun this script.")


def run(name: str, *args: str, capture: bool = False) -> str:
    result = subprocess.run(  # noqa: S603 - local media arguments passed without a shell
        [*executable(name), *args],
        cwd=ROOT,
        check=True,
        capture_output=capture,
        text=True,
        encoding="utf-8",
    )
    return result.stdout if capture else ""


def timestamp(seconds: float, *, ass: bool = False) -> str:
    units = round(max(0, seconds) * (100 if ass else 1000))
    fraction_base = 100 if ass else 1000
    whole, fraction = divmod(units, fraction_base)
    hours, remainder = divmod(whole, 3600)
    minutes, sec = divmod(remainder, 60)
    if ass:
        return f"{hours}:{minutes:02}:{sec:02}.{fraction:02}"
    return f"{hours:02}:{minutes:02}:{sec:02}.{fraction:03}"


def short_time(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    return f"{minutes:02}:{sec:02}"


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main() -> None:
    capture = json.loads((MEDIA / "capture.json").read_text(encoding="utf-8"))
    raw = ".local/demo-raw/walkthrough.webm"
    probe = json.loads(run("ffprobe", "-v", "error", "-show_format", "-of", "json", raw, capture=True))
    duration = float(probe["format"]["duration"]) - capture["trimStart"]
    if duration <= 0 or capture["browserErrors"]:
        raise SystemExit("Recording is empty or contains browser errors.")
    chapters = []
    for index, chapter in enumerate(capture["chapters"]):
        start = max(0, chapter["start"] - capture["trimStart"])
        end = (
            capture["chapters"][index + 1]["start"] - capture["trimStart"]
            if index + 1 < len(capture["chapters"])
            else duration
        )
        if not 0 <= start < end <= duration:
            raise SystemExit(f"Invalid chapter timing: {chapter['title']}")
        chapters.append({**chapter, "start": round(start, 3), "end": round(end, 3)})
    vtt = ["WEBVTT", ""]
    metadata = [
        ";FFMETADATA1",
        "title=EICC - From integration failure to verified release",
        "comment=Fictional local demonstration. Real browser capture; no API mocks.",
    ]
    ass = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1600",
        "PlayResY: 1000",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Title,DejaVu Sans,24,&H00FFFFFF,&H00FFFFFF,&H00101A2D,&H00101A2D,-1,0,0,0,100,100,0,0,1,0,0,7,32,32,916,1",
        "Style: Caption,DejaVu Sans,20,&H00E5D7C5,&H00E5D7C5,&H00101A2D,&H00101A2D,0,0,0,0,100,100,0,0,1,0,0,7,32,32,956,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    transcript = [
        "# Recorded walkthrough",
        "",
        "A captioned recording of real browser interactions with the redesigned EICC application. The video is silent; the captions explain each chapter. All organizations and approvals are fictional. The release transitions record a local demonstration and do not deploy external software.",
        "",
        "[Play or download the MP4](eicc-walkthrough.mp4) · [Chapter player](index.html) · [Screenshot gallery](../screenshots/README.md)",
        "",
        "The opening tour uses seeded Northstar data. The qualification then uses a separate project whose test, defect, UAT, change, and release outcomes are created during the recording. Its definitions and reviewed requirements are prepared through the validated API before filming.",
        "",
        "## Chapters",
        "",
    ]
    for index, chapter in enumerate(chapters, 1):
        start, end = timestamp(chapter["start"]), timestamp(chapter["end"])
        vtt.extend([str(index), f"{start} --> {end}", f"{chapter['title']}: {chapter['caption']}", ""])
        metadata.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={round(chapter['start'] * 1000)}",
                f"END={round(chapter['end'] * 1000)}",
                f"title={chapter['title']}",
            ]
        )
        for style, text in [("Title", f"{index:02}  /  {chapter['title']}"), ("Caption", chapter["caption"])]:
            escaped = text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
            ass.append(
                f"Dialogue: 0,{timestamp(chapter['start'], ass=True)},{timestamp(chapter['end'], ass=True)},{style},,0,0,0,,{escaped}"
            )
        transcript.extend(
            [f"### {short_time(chapter['start'])} — {chapter['title']}", "", chapter["caption"], ""]
        )
    (MEDIA / "captions.vtt").write_text("\n".join(vtt), encoding="utf-8")
    (ROOT / ".local" / "demo-captions.ass").write_text("\n".join(ass), encoding="utf-8")
    (ROOT / ".local" / "demo-chapters.txt").write_text("\n".join(metadata) + "\n", encoding="utf-8")
    (MEDIA / "transcript.md").write_text("\n".join(transcript), encoding="utf-8")
    run(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        "-ss",
        str(capture["trimStart"]),
        "-i",
        raw,
        "-i",
        ".local/demo-chapters.txt",
        "-map",
        "0:v:0",
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-vf",
        "pad=iw:ih+100:0:0:color=0x101a2d,ass=.local/demo-captions.ass",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        "docs/demo/eicc-walkthrough.mp4",
    )
    final = json.loads(
        run(
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            "-of",
            "json",
            "docs/demo/eicc-walkthrough.mp4",
            capture=True,
        )
    )
    stream = next(stream for stream in final["streams"] if stream["codec_type"] == "video")
    if (stream["width"], stream["height"], stream["codec_name"]) != (1600, 1000, "h264"):
        raise SystemExit("Unexpected final video format.")
    if len(final["chapters"]) != len(chapters):
        raise SystemExit("The MP4 is missing chapter metadata.")
    run("ffmpeg", "-hide_banner", "-v", "error", "-i", "docs/demo/eicc-walkthrough.mp4", "-f", "null", "-")
    run(
        "ffmpeg",
        "-hide_banner",
        "-v",
        "error",
        "-y",
        "-ss",
        str(chapters[1]["start"] + 2),
        "-i",
        "docs/demo/eicc-walkthrough.mp4",
        "-frames:v",
        "1",
        "docs/demo/poster.png",
    )
    buttons = "\n".join(
        f'<button type="button" data-start="{chapter["start"]}"><time>{short_time(chapter["start"])}</time><span>{html.escape(chapter["title"])}</span></button>'
        for chapter in chapters
    )
    player = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EICC — Recorded demonstration</title><link rel="stylesheet" href="player.css"></head>
<body><main><header><a class="brand" href="../../README.md">EICC <span>Enterprise Integration Control Center</span></a><p class="eyebrow">RECORDED PRODUCT WALKTHROUGH</p><h1>From integration failure<br>to a verified release.</h1><p class="intro">Explore the redesigned workspace, follow a real SOAP mapping correction, and see the evidence carried through acceptance and release.</p></header>
<div class="watch-layout"><section aria-label="Video demonstration"><video id="demo" controls playsinline preload="metadata" poster="poster.png"><source src="eicc-walkthrough.mp4" type="video/mp4"><track kind="captions" src="captions.vtt" srclang="en" label="English descriptions"><p><a href="eicc-walkthrough.mp4">Download the MP4</a></p></video><div class="video-details"><span>{short_time(duration)} · 1600 × 1000 · Captioned, silent</span><a href="eicc-walkthrough.mp4" download>Download MP4 ↓</a></div><p class="note">Captured in Chromium against a disposable database and the actual local API. All organizations and decisions are fictional. Release transitions do not deploy external software.</p><nav class="resources" aria-label="Related resources"><a href="transcript.md">Read transcript</a><a href="../screenshots/README.md">Browse screenshots</a><a href="README.md">Capture details</a></nav></section><aside aria-label="Video chapters"><h2>In this walkthrough</h2><div class="chapters">{buttons}</div></aside></div></main>
<script>
const video = document.querySelector("video");
const chapters = [...document.querySelectorAll("[data-start]")];
chapters.forEach(button => button.addEventListener("click", () => {{ video.currentTime = Number(button.dataset.start); video.play().catch(() => {{}}); }}));
video.addEventListener("timeupdate", () => {{ let current = chapters[0]; for (const button of chapters) if (video.currentTime >= Number(button.dataset.start)) current = button; for (const button of chapters) {{ if (button === current) button.setAttribute("aria-current", "true"); else button.removeAttribute("aria-current"); }} }});
</script></body></html>
"""
    (MEDIA / "index.html").write_text(player, encoding="utf-8")
    gallery = [
        "# EICC screenshot gallery",
        "",
        f"Fresh captures of the redesigned application, recorded {capture['capturedAt'][:10]}. Desktop captures use a 1600 × 900 viewport; mobile captures use 390 × 844. Selected detail pages include the full page so evidence and gates remain visible.",
        "",
        "[Watch the captioned demo](../demo/eicc-walkthrough.mp4) · [Demo chapters and transcript](../demo/transcript.md) · [UI design notes](../ui-design.md)",
        "",
        "These are unaltered browser screenshots. The dashboard and pilot gates use seeded Northstar records. The correction, acceptance, and completed-release screens come from the connected qualification scenario executed during recording.",
        "",
    ]
    for screenshot in capture["screenshots"]:
        gallery.extend(
            [f"## {screenshot['title']}", "", f"![{screenshot['title']}]({screenshot['file']})", ""]
        )
    (ROOT / "docs" / "screenshots" / "README.md").write_text("\n".join(gallery), encoding="utf-8")
    outputs = [MEDIA / "eicc-walkthrough.mp4", MEDIA / "poster.png", MEDIA / "captions.vtt"]
    outputs += [ROOT / "docs" / "screenshots" / shot["file"] for shot in capture["screenshots"]]
    manifest = {
        "capturedAt": capture["capturedAt"],
        "durationSeconds": float(final["format"]["duration"]),
        "video": {
            "file": "eicc-walkthrough.mp4",
            "codec": stream["codec_name"],
            "width": stream["width"],
            "height": stream["height"],
            "frameRate": stream["avg_frame_rate"],
            "frames": int(stream["nb_frames"]),
            "silent": True,
            "captions": "Burned into a separate footer below the unmodified app viewport; also provided as WebVTT.",
        },
        "checks": [
            *capture["checks"],
            "Full MP4 decoded without errors.",
            "MP4 contains every chapter marker and H.264/yuv420p video.",
        ],
        "browserErrors": capture["browserErrors"],
        "chapters": chapters,
        "artifacts": [
            {"file": file.relative_to(ROOT).as_posix(), "bytes": file.stat().st_size, "sha256": digest(file)}
            for file in outputs
        ],
    }
    (MEDIA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Packaged {len(capture['screenshots'])} screenshots and a {duration:.1f}s MP4 with {len(chapters)} chapters."
    )


if __name__ == "__main__":
    main()
