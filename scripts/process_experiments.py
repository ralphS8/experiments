#!/usr/bin/env python3
"""
Prepares experiments for the website and rebuilds the list the Experiments page reads.

Folders
  add-experiments/              Drop full-size files here, named   2025 - Title - Medium.mp4
                                Add " - sound" to the end of a video's name to keep its audio.
  media/                        Web-sized versions the page shows (made by this script).
  experiments.json              The list of pieces, rebuilt from the filenames in media/.

Changing pieces later
  Remove a piece:   delete its file from media/
  Rename a piece:   rename its file in media/ (its still frame is remade to match)

Runs automatically on GitHub after every upload (see .github/workflows/site.yml).
Needs ffmpeg and Pillow:  python3 scripts/process_experiments.py
"""
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "add-experiments"
MEDIA = ROOT / "media"
LIST = ROOT / "experiments.json"

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
POSTER = ".poster.jpg"
THUMB = ".thumb"            # small preview the page loads first: name.thumb.jpg (or .png if transparent)
KEEP = {".gitkeep", "readme.md", ".ds_store"}

VIDEO_LONG_EDGE = 1280      # px
VIDEO_MAX_MB = 12           # re-encode smaller if a video comes out bigger than this
IMAGE_LONG_EDGE = 2000      # px
THUMB_LONG_EDGE = 800       # px, enough for the canvas until a piece is in focus


# ---------- names ----------

def split_name(stem):
    """'2025 - Night crowd - Video - sound' -> year, title, medium, sound"""
    parts = [p.strip() for p in re.split(r"\s+-\s+", stem) if p.strip()]
    sound = bool(parts) and parts[-1].lower() == "sound"
    if sound:
        parts = parts[:-1]
    year = ""
    if parts and re.fullmatch(r"(19|20)\d\d", parts[0]):
        year = parts.pop(0)
    if len(parts) >= 2:
        title, medium = " - ".join(parts[:-1]), parts[-1]
    else:
        title, medium = (parts[0] if parts else stem), ""
    # a Mac stores "/" in a filename as ":"; the web copies use "_" in its place
    medium = re.sub(r"\s*[:_]\s*", " / ", medium)
    return year, title, medium, sound


def web_stem(stem):
    """A filename that is safe on every system, keeping it readable."""
    stem = stem.replace(":", "_").replace("/", "_")
    return re.sub(r"[\\*?\"<>|]", "", stem).strip()


# ---------- tools ----------

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-2000:]}")
    return r.stdout


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,width,height:format=duration", "-of", "json", str(path)])
    data = json.loads(out)
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    dur = float(data.get("format", {}).get("duration") or 0)
    if not v:
        raise RuntimeError(f"{path.name} has no video track")
    return int(v["width"]), int(v["height"]), dur, has_audio


def displayed_size(path):
    """Width and height as shown (accounts for phone videos stored sideways)."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height:stream_side_data=rotation:stream_tags=rotate", "-of", "json", str(path)])
    s = json.loads(out)["streams"][0]
    w, h = int(s["width"]), int(s["height"])
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(s.get("tags", {}).get("rotate", 0) or 0)
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


# ---------- processing ----------

def encode_video(src, dst, keep_sound):
    _, _, _, has_audio = probe(src)
    tries = [(VIDEO_LONG_EDGE, 25), (960, 29), (720, 32)]
    for edge, crf in tries:
        scale = (f"scale='if(gte(iw,ih),min({edge},iw),-2)':'if(gte(iw,ih),-2,min({edge},ih))'")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0:v:0",
               "-vf", scale, "-fpsmax", "30",
               "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
               "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart"]
        if keep_sound and has_audio:
            cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k", "-ac", "2"]
        else:
            cmd += ["-an"]
        run(cmd + [str(dst)])
        if dst.stat().st_size <= VIDEO_MAX_MB * 1024 * 1024:
            break
    return keep_sound and has_audio


def make_poster(video, poster):
    _, _, dur, _ = probe(video)
    t = min(1.0, dur * 0.25) if dur else 0
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video),
         "-frames:v", "1", "-q:v", "3", str(poster)])


def encode_image(src, dst_stem):
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)
    im.thumbnail((IMAGE_LONG_EDGE, IMAGE_LONG_EDGE), Image.LANCZOS)
    transparent = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if transparent:
        dst = dst_stem.with_suffix(".png")
        im.convert("RGBA").save(dst, optimize=True)
    else:
        dst = dst_stem.with_suffix(".jpg")
        im.convert("RGB").save(dst, quality=84, optimize=True, progressive=True)
    return dst


def process_inbox():
    """Turn every new upload into a web copy, then remove the upload."""
    done = []
    if not INBOX.exists():
        return done
    MEDIA.mkdir(parents=True, exist_ok=True)
    for src in sorted(INBOX.iterdir()):
        if src.is_dir() or src.name.lower() in KEEP or src.name.startswith("."):
            continue
        ext = src.suffix.lower()
        stem = web_stem(src.stem)
        try:
            if ext in VIDEO_EXT:
                _, _, _, sound = split_name(src.stem)
                dst = MEDIA / f"{stem}.mp4"
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "out.mp4"
                    kept = encode_video(src, out, sound)
                    shutil.move(str(out), dst)
                # a sound flag on a video with no audio would show a useless control
                if sound and not kept:
                    plain = MEDIA / (web_stem(re.sub(r"(?i)\s+-\s+sound$", "", src.stem)) + ".mp4")
                    dst.rename(plain)
                    dst = plain
                make_poster(dst, dst.with_name(dst.stem + POSTER))
            elif ext in IMAGE_EXT:
                for old in MEDIA.glob(f"{glob_escape(stem)}.*"):
                    old.unlink()   # its preview is remade below
                dst = encode_image(src, MEDIA / stem)
            else:
                print(f"skipped  {src.name}  (not a video or image)")
                continue
        except Exception as e:  # keep going so one bad file doesn't block the rest
            # shows as a warning on the run in GitHub's Actions tab; the upload stays in add-experiments/
            print(f"::warning::Could not process {src.name}. The file may be damaged or in a format that is not supported.")
            print(f"FAILED   {src.name}: {e}", file=sys.stderr)
            continue
        size = dst.stat().st_size / 1024 / 1024
        print(f"added    {dst.name}  ({size:.1f} MB, from {src.stat().st_size/1024/1024:.1f} MB)")
        src.unlink()
        done.append(dst.name)
    return done


def glob_escape(s):
    return re.sub(r"([\[\]\*\?])", r"[\1]", s)


def is_derived(name):
    """Still frames and previews made by this script, not pieces themselves."""
    return name.endswith(POSTER) or (THUMB + ".") in name


def make_thumb(src_image, stem_path):
    """Small preview so the page loads quickly; transparent images stay transparent."""
    with Image.open(src_image) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((THUMB_LONG_EDGE, THUMB_LONG_EDGE), Image.LANCZOS)
        transparent = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        if transparent:
            out = stem_path.with_name(stem_path.name + THUMB + ".png")
            im.convert("RGBA").save(out, optimize=True)
        else:
            out = stem_path.with_name(stem_path.name + THUMB + ".jpg")
            im.convert("RGB").save(out, quality=78, optimize=True, progressive=True)
    return out


def find_thumb(stem_path):
    for ext in (".jpg", ".png"):
        t = stem_path.with_name(stem_path.name + THUMB + ext)
        if t.exists():
            return t
    return None


def build_list():
    """Rebuild experiments.json from whatever is in media/."""
    MEDIA.mkdir(parents=True, exist_ok=True)
    pieces, needed = [], set()
    for f in sorted(MEDIA.iterdir()):
        if is_derived(f.name) or f.name.startswith(".") or f.is_dir():
            continue
        ext = f.suffix.lower()
        year, title, medium, sound = split_name(f.stem)
        piece = {"title": title, "year": year, "medium": medium,
                 "src": "media/" + quote(f.name)}
        stem_path = f.with_name(f.stem)
        try:
            if ext in VIDEO_EXT:
                poster = f.with_name(f.stem + POSTER)
                if not poster.exists():
                    make_poster(f, poster)
                thumb = find_thumb(stem_path) or make_thumb(poster, stem_path)
                needed.update({poster.name, thumb.name})
                w, h = displayed_size(f)
                _, _, _, has_audio = probe(f)
                piece.update(type="video", poster="media/" + quote(poster.name),
                             thumb="media/" + quote(thumb.name),
                             w=w, h=h, sound=bool(sound and has_audio))
            elif ext in IMAGE_EXT:
                thumb = find_thumb(stem_path) or make_thumb(f, stem_path)
                needed.add(thumb.name)
                with Image.open(f) as im:
                    w, h = ImageOps.exif_transpose(im).size
                piece.update(type="image", thumb="media/" + quote(thumb.name), w=w, h=h, sound=False)
            else:
                continue
        except Exception as e:
            print(f"::warning::Could not read {f.name}: {str(e).splitlines()[0] if str(e) else e}")
            continue
        pieces.append(piece)
    # still frames and previews whose piece was deleted or renamed
    for d in MEDIA.iterdir():
        if is_derived(d.name) and d.name not in needed:
            d.unlink()
            print(f"removed  {d.name}  (its piece is gone)")
    pieces.sort(key=lambda p: (-(int(p["year"]) if p["year"] else 0), p["title"].lower()))
    LIST.write_text(json.dumps({
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pieces": pieces}, indent=2, ensure_ascii=False) + "\n")
    return pieces


if __name__ == "__main__":
    added = process_inbox()
    pieces = build_list()
    print(f"\n{len(added)} new, {len(pieces)} pieces on the page")
