#!/usr/bin/env python3
"""Eye-align the learners' faces for the stomp piece, from their original posts or the scroll recording.

NOT stdlib: needs opencv-contrib-python-headless and numpy in a venv, plus the
YuNet face-landmark model (and EDSR x4 for the recording). This is the only
script in the repo with those needs. It runs once per source, and the rest of
the stomp piece reads its outputs.

Usage (preferred: the original posts, full resolution, frame included):
  python faces_prep.py --project <dir> --images <folder of JPG/PNG posts> \
      --yunet face_detection_yunet_2023mar.onnx [--pick-hold <file>] [--pick-hero <file>]

Usage (fallback: faces cut from the scroll recording, super-resolved):
  python faces_prep.py --project <dir> --scroll scroll.mp4 \
      --yunet face_detection_yunet_2023mar.onnx --edsr EDSR_x4.pb \
      [--candidates tiles_all.json] [--count 160]

Writes:
  motion/deekshaarambh-2026-stomp/faces.json   chosen faces + landmarks, and "order": distinct faces, sharpest
                                                first (committed: numbers only, no pixels)
  <project>/assets/faces/fNNN.jpg               400x400, every face's eyes at (145,170) and (255,170)
  <project>/assets/framed/fNNN.jpg              1000x1000, the whole post (frame and face), eyes at (400,430) and (600,430)
  <project>/assets/img/framed_sheet.jpg         the framed posts as a 10-column sprite of 300 px cells
  <project>/assets/img/faces_sheet.jpg          the aligned faces as a 10-column sprite of 400 px cells
  <project>/assets/img/face_cells.jpg           tight 128 px face crops, 20-column sprite (mosaic cells)
  <project>/assets/img/face_mosaic.jpg          1152x672 mosaic of tight face crops (fills type)

In --images mode faces.json lists each post's file name, pixel size and eye landmarks, plus
"hold" and "hero" (the faces compose.py holds on "each one." and grows the number from).
In the recording mode, with --candidates omitted it reuses faces.json (frame/col/top) and only
re-renders pixels. With --reuse it skips detection and rebuilds the sprites from assets/faces/.
"""
import argparse
import json
import pathlib
import subprocess

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
W, H = 624, 1186
COLS = [28, 180, 331, 484]
T = 116
OUT, E, EY = 400, 110, 170
FO, FE, FEY = 1000, 200, 430          # framed: the whole post around the face, eyes locked, navy beyond it
NAVY_BGR = (91, 28, 7)


def frames(src):
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def blockiness(frame, r):
    """8x8 compression blocking around the face in the source frame: edge energy on block
    boundaries over edge energy elsewhere (about 1.0 is clean, above 1.3 is visibly blocky)."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(float)
    (ex0, ey0), (ex1, ey1) = r["eyes"]
    ed = float(np.hypot(ex1 - ex0, ey1 - ey0))
    cx, cy = COLS[r["col"]] + (ex0 + ex1) / 2, r["top"] + (ey0 + ey1) / 2 + 0.5 * ed
    x0, x1, y0, y1 = int(cx - 1.1 * ed), int(cx + 1.1 * ed), int(cy - 1.3 * ed), int(cy + 1.1 * ed)
    dx = np.abs(np.diff(g[y0:y1, x0 - 1:x1 + 1], axis=1))
    dy = np.abs(np.diff(g[y0 - 1:y1 + 1, x0:x1], axis=0))
    xs, ys = np.arange(x0 - 1, x1), np.arange(y0 - 1, y1)
    bx = dx[:, xs % 8 == 7].mean() / (dx[:, xs % 8 != 7].mean() + 1e-6)
    by = dy[ys % 8 == 7, :].mean() / (dy[ys % 8 != 7, :].mean() + 1e-6)
    return round(float((bx + by) / 2), 3)


def warp_pair(img, eyes):
    """the two outputs for one face: the 400 px aligned face and the 1000 px framed post.
    Large sources are first reduced (area filter) so the warp never shrinks by more than 20%."""
    out = []
    ed = float(np.hypot(eyes[1][0] - eyes[0][0], eyes[1][1] - eyes[0][1]))
    for size, gap, ey, border in ((OUT, E, EY, cv2.BORDER_REPLICATE), (FO, FE, FEY, cv2.BORDER_CONSTANT)):
        pre = min(1.0, 1.25 * gap / ed)
        src_img = cv2.resize(img, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA) if pre < 1.0 else img
        src = np.array([[x * pre, y * pre] for x, y in eyes], np.float32)
        dst = np.array([[size / 2 - gap / 2, ey], [size / 2 + gap / 2, ey]], np.float32)
        M, _ = cv2.estimateAffinePartial2D(src, dst)
        w = cv2.warpAffine(src_img, M, (size, size), flags=cv2.INTER_CUBIC, borderMode=border, borderValue=NAVY_BGR)
        out.append(cv2.addWeighted(w, 1.15, cv2.GaussianBlur(w, (0, 0), 1.2), -0.15, 0))
    return out


def from_images(a, proj):
    """detect, align and render every post in a folder; returns (spec, aligned, framed)"""
    files = sorted(p for p in pathlib.Path(a.images).expanduser().iterdir()
                   if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    det = cv2.FaceDetectorYN.create(a.yunet, "", (320, 320), 0.6, 0.3, 5000)
    faces, aligned, framed = [], [], []
    for p in files:
        img = cv2.imread(str(p))
        if img is None:
            print(f"skip {p.name}: unreadable")
            continue
        h, w = img.shape[:2]
        sc = min(1.0, 900 / max(w, h))
        small = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc < 1.0 else img
        det.setInputSize((small.shape[1], small.shape[0]))
        _, found = det.detect(small)
        if found is None:
            print(f"skip {p.name}: no face")
            continue
        f = max(found, key=lambda f: f[2] * f[3] * f[14])          # the main person: biggest confident face
        eyes = sorted([(f[4] / sc, f[5] / sc), (f[6] / sc, f[7] / sc)])
        ed = float(np.hypot(eyes[1][0] - eyes[0][0], eyes[1][1] - eyes[0][1]))
        ang = float(np.degrees(np.arctan2(eyes[1][1] - eyes[0][1], eyes[1][0] - eyes[0][0])))
        if f[14] < 0.8 or abs(ang) > 15 or ed < 40:
            print(f"skip {p.name}: score {f[14]:.2f}, tilt {ang:.0f} deg, eye gap {ed:.0f}px")
            continue
        r = {"file": p.name, "size": [w, h], "score": round(float(f[14]), 3),
             "eyes": [[round(float(x), 1), round(float(y), 1)] for x, y in eyes]}
        k = len(faces)
        al, fr = warp_pair(img, r["eyes"])
        cv2.imwrite(str(proj / "assets" / "faces" / f"f{k:03d}.jpg"), al, [cv2.IMWRITE_JPEG_QUALITY, 93])
        cv2.imwrite(str(proj / "assets" / "framed" / f"f{k:03d}.jpg"), fr, [cv2.IMWRITE_JPEG_QUALITY, 92])
        faces.append(r)
        aligned.append(al)
        framed.append(fr)
    print(f"{len(faces)} of {len(files)} posts aligned")
    return {"source": "images", "out": OUT, "eye_gap": E, "eye_y": EY, "faces": faces}, aligned, framed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    ap.add_argument("--images", help="a folder of the learners' original posts (preferred source)")
    ap.add_argument("--pick-hold", help="file name of the post held on 'each one.' (default: the sharpest)")
    ap.add_argument("--pick-hero", help="file name of the post the number grows from (default: the second sharpest)")
    ap.add_argument("--scroll")
    ap.add_argument("--yunet")
    ap.add_argument("--edsr")
    ap.add_argument("--candidates")
    ap.add_argument("--count", type=int, default=160)
    ap.add_argument("--reuse", action="store_true", help="rebuild sprites from existing assets/faces/*.jpg")
    a = ap.parse_args()
    if not a.reuse and not (a.images and a.yunet) and not (a.scroll and a.yunet and a.edsr):
        ap.error("pass --images and --yunet, or --scroll, --yunet and --edsr, or --reuse")
    proj = pathlib.Path(a.project).expanduser().resolve()
    (proj / "assets" / "faces").mkdir(parents=True, exist_ok=True)
    (proj / "assets" / "framed").mkdir(parents=True, exist_ok=True)
    (proj / "assets" / "img").mkdir(parents=True, exist_ok=True)
    if a.images:
        for d in ("faces", "framed"):
            for old in (proj / "assets" / d).glob("f*.jpg"):
                old.unlink()
        spec, aligned, framed = from_images(a, proj)
        finish(a, proj, spec, aligned, framed)
        return
    if not a.reuse:
        fr = frames(a.scroll)
        det = cv2.FaceDetectorYN.create(a.yunet, "", (T * 4, T * 4), 0.6, 0.3, 5000)
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(a.edsr)
        sr.setModel("edsr", 4)

    def tile(i, c, top):
        return fr[i, top:top + T, COLS[c]:COLS[c] + T].copy()

    if a.candidates:
        found = []
        for i, c, top in json.loads(pathlib.Path(a.candidates).read_text()):
            t = tile(i, c, top)
            if t.shape[:2] != (T, T):
                continue
            _, faces = det.detect(cv2.resize(t, (T * 4, T * 4), interpolation=cv2.INTER_LANCZOS4))
            if faces is None:
                continue
            f = max(faces, key=lambda f: f[14])
            eyes = sorted([(f[4] / 4, f[5] / 4), (f[6] / 4, f[7] / 4)])
            ed = float(np.hypot(eyes[1][0] - eyes[0][0], eyes[1][1] - eyes[0][1]))
            ang = float(np.degrees(np.arctan2(eyes[1][1] - eyes[0][1], eyes[1][0] - eyes[0][0])))
            if f[14] > 0.85 and abs(ang) < 10 and ed >= 15:
                found.append({"frame": int(i), "col": int(c), "top": int(top), "score": round(float(f[14]), 3),
                              "eyes": [[round(float(x), 2), round(float(y), 2)] for x, y in eyes]})
        found.sort(key=lambda r: -(r["score"] * np.hypot(r["eyes"][1][0] - r["eyes"][0][0], r["eyes"][1][1] - r["eyes"][0][1])))
        chosen = sorted(found[:a.count], key=lambda r: (r["frame"], r["col"]))
        (HERE / "faces.json").write_text(json.dumps({"out": OUT, "eye_gap": E, "eye_y": EY, "faces": chosen}, indent=0))
    spec = json.loads((HERE / "faces.json").read_text())
    faces = spec["faces"]
    if spec.get("source") == "images" and a.reuse:
        n = len(faces)
        finish(a, proj, spec, [cv2.imread(str(proj / "assets" / "faces" / f"f{k:03d}.jpg")) for k in range(n)],
               [cv2.imread(str(proj / "assets" / "framed" / f"f{k:03d}.jpg")) for k in range(n)])
        return

    aligned, framed = [], []
    for k, r in enumerate(faces):
        if a.reuse:
            aligned.append(cv2.imread(str(proj / "assets" / "faces" / f"f{k:03d}.jpg")))
            framed.append(cv2.imread(str(proj / "assets" / "framed" / f"f{k:03d}.jpg")))
            continue
        t = tile(r["frame"], r["col"], r["top"])
        r["block"] = blockiness(fr[r["frame"]], r)
        big = sr.upsample(t)
        src = np.array([[x * 4, y * 4] for x, y in r["eyes"]], np.float32)
        out = []
        for size, gap, ey, border in ((OUT, E, EY, cv2.BORDER_REPLICATE), (FO, FE, FEY, cv2.BORDER_CONSTANT)):
            dst = np.array([[size / 2 - gap / 2, ey], [size / 2 + gap / 2, ey]], np.float32)
            M, _ = cv2.estimateAffinePartial2D(src, dst)
            img = cv2.warpAffine(big, M, (size, size), flags=cv2.INTER_CUBIC, borderMode=border, borderValue=NAVY_BGR)
            out.append(cv2.addWeighted(img, 1.35, cv2.GaussianBlur(img, (0, 0), 2.0), -0.35, 0))  # gentle unsharp
        cv2.imwrite(str(proj / "assets" / "faces" / f"f{k:03d}.jpg"), out[0], [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str(proj / "assets" / "framed" / f"f{k:03d}.jpg"), out[1], [cv2.IMWRITE_JPEG_QUALITY, 90])
        aligned.append(out[0])
        framed.append(out[1])
        print(f"face {k + 1}/{len(faces)}", flush=True)

    finish(a, proj, spec, aligned, framed)


def finish(a, proj, spec, aligned, framed):
    """rank, dedupe, pick the hero faces, write faces.json and every sprite"""
    faces = spec["faces"]
    # rank: sharpness (Laplacian variance of the face, scaled by source eye distance) and
    # drop repeats (the feed shows some learners twice, and the recording scrolls back)
    sharp, small = [], []
    for img in aligned:
        g = cv2.cvtColor(img[70:330, 90:310], cv2.COLOR_BGR2GRAY)
        sharp.append(float(cv2.Laplacian(cv2.GaussianBlur(g, (0, 0), 1.0), cv2.CV_64F).var()))
        s = cv2.resize(cv2.cvtColor(img[100:300, 120:280], cv2.COLOR_BGR2GRAY), (24, 30), interpolation=cv2.INTER_AREA).astype(float)
        small.append((s - s.mean()) / (s.std() + 1e-6))
    ed = [float(np.hypot(r["eyes"][1][0] - r["eyes"][0][0], r["eyes"][1][1] - r["eyes"][0][1])) for r in faces]
    order = []
    for k in sorted(range(len(aligned)), key=lambda k: -sharp[k] * ed[k] ** 0.5):
        if sharp[k] >= 3.0 and all((small[k] * small[j]).mean() < 0.82 for j in order):
            order.append(k)
    spec["order"] = order
    if spec.get("source") == "images":
        spec["big"] = list(order)            # full-resolution posts: every distinct face is clean enough
        names = [r["file"] for r in faces]
        pick = lambda nm, default: names.index(nm) if nm and nm in names else default
        spec["hold"] = pick(getattr(a, "pick_hold", None), order[0])
        spec["hero"] = pick(getattr(a, "pick_hero", None), order[1] if order[1] != spec["hold"] else order[2])
    else:
        # big: the distinct faces with the cleanest source pixels (least 8x8 compression blocking), for full-size windows
        spec["big"] = sorted((k for k in order if faces[k].get("block", 9) < 1.25), key=lambda k: faces[k]["block"])
    (HERE / "faces.json").write_text(json.dumps(spec, indent=0))

    n = len(aligned)
    cell, cols = OUT, 10
    rows = (n + cols - 1) // cols
    sheet = np.zeros((rows * cell, cols * cell, 3), np.uint8)
    for k, img in enumerate(aligned):
        sheet[(k // cols) * cell:(k // cols + 1) * cell, (k % cols) * cell:(k % cols + 1) * cell] = img
    cv2.imwrite(str(proj / "assets" / "img" / "faces_sheet.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    fc = 300
    fsheet = np.zeros((rows * fc, cols * fc, 3), np.uint8)
    for k, img in enumerate(framed):
        fsheet[(k // cols) * fc:(k // cols + 1) * fc, (k % cols) * fc:(k % cols + 1) * fc] = cv2.resize(img, (fc, fc), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(proj / "assets" / "img" / "framed_sheet.jpg"), fsheet, [cv2.IMWRITE_JPEG_QUALITY, 90])

    # tight crops: a square centred between the eyes and the mouth
    c0, c1 = int(OUT / 2 - 1.25 * E), int(OUT / 2 + 1.25 * E)
    r0 = int(EY - 0.95 * E)
    tight = [img[r0:r0 + (c1 - c0), c0:c1] for img in aligned]
    cc, ccols = 128, 20
    crows = (n + ccols - 1) // ccols
    cs = np.zeros((crows * cc, ccols * cc, 3), np.uint8)
    for k, t in enumerate(tight):
        cs[(k // ccols) * cc:(k // ccols + 1) * cc, (k % ccols) * cc:(k % ccols + 1) * cc] = cv2.resize(t, (cc, cc), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(proj / "assets" / "img" / "face_cells.jpg"), cs, [cv2.IMWRITE_JPEG_QUALITY, 90])
    mc, mcols, mrows = 48, 24, 14
    mos = np.zeros((mrows * mc, mcols * mc, 3), np.uint8)
    rng = np.random.default_rng(14)
    pick = [order[i % len(order)] for i in rng.permutation(mrows * mcols)]
    for k in range(mrows * mcols):
        mos[(k // mcols) * mc:(k // mcols + 1) * mc, (k % mcols) * mc:(k % mcols + 1) * mc] = cv2.resize(tight[pick[k]], (mc, mc), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(proj / "assets" / "img" / "face_mosaic.jpg"), mos, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"aligned {n} faces, {len(order)} distinct and sharp; sprites written")


if __name__ == "__main__":
    main()
