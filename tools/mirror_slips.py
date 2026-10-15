"""Copies new bet-slip screenshots from Cloudinary into slips/ (run by GitHub Actions).
Reads slips/config.json: {"cloud_name": "...", "tag": "rvd-slip"}.
Writes the images to slips/week-<n>/<player>/ and keeps slips/index.json up to date."""
import json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "slips", "config.json")))
cloud = CFG.get("cloud_name", "").strip()
tag = CFG.get("tag", "rvd-slip")
if not cloud:
    print("No cloud_name configured yet; nothing to do.")
    raise SystemExit(0)

idx_path = os.path.join(ROOT, "slips", "index.json")
index = json.load(open(idx_path)) if os.path.exists(idx_path) else []
known = {e["public_id"] for e in index}

url = f"https://res.cloudinary.com/{cloud}/image/list/{tag}.json"
try:
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "rvd-mirror"}), timeout=30))
except Exception as e:  # list not enabled yet, or no uploads with the tag
    print("Could not read the upload list:", e)
    raise SystemExit(0)

added = 0
for r in sorted(data.get("resources", []), key=lambda r: r.get("created_at", "")):
    pid = r["public_id"]
    if pid in known:
        continue
    ctx = (r.get("context") or {}).get("custom", {})
    player = ctx.get("player", "unknown")
    player = player if player in ("Roscoe", "Dom") else "unknown"
    week = re.sub(r"[^0-9]", "", str(ctx.get("week", ""))) or "0"
    fmt = r.get("format", "jpg")
    src = f"https://res.cloudinary.com/{cloud}/image/upload/v{r['version']}/{pid}.{fmt}"
    folder = os.path.join("slips", f"week-{week}", player)
    os.makedirs(os.path.join(ROOT, folder), exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", pid.split("/")[-1])[:60]
    rel = f"{folder}/{r.get('created_at', '')[:19].replace(':', '').replace('T', '_')}_{name}.{fmt}"
    with urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": "rvd-mirror"}), timeout=60) as resp:
        open(os.path.join(ROOT, rel), "wb").write(resp.read())
    index.append({"public_id": pid, "player": player, "week": int(week), "uploaded_at": r.get("created_at"),
                  "path": rel, "note": ctx.get("note", "")})
    added += 1

json.dump(index, open(idx_path, "w"), indent=1)
print(f"Added {added} new slip(s).")
