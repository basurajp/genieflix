#!/usr/bin/env python3
"""Cut, super-resolve and eye-align student faces from the scroll recording.

NOT stdlib: needs opencv-contrib-python-headless and numpy in a venv, plus two
model files (YuNet face landmarks, EDSR x4 super-resolution). This is the only
script in the repo with those needs. It runs once per source recording, and
the rest of the stomp piece reads its outputs.

Usage:
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

With --candidates omitted it reuses faces.json (frame/col/top) and only re-renders pixels.
With --reuse it also skips super-resolution and rebuilds the sprites from assets/faces/.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    ap.add_argument("--scroll")
    ap.add_argument("--yunet")
    ap.add_argument("--edsr")
    ap.add_argument("--candidates")
    ap.add_argument("--count", type=int, default=160)
    ap.add_argument("--reuse", action="store_true", help="rebuild sprites from existing assets/faces/*.jpg")
    a = ap.parse_args()
    if not a.reuse and not (a.scroll and a.yunet and a.edsr):
        ap.error("--scroll, --yunet and --edsr are required unless --reuse")
    proj = pathlib.Path(a.project).expanduser().resolve()
    (proj / "assets" / "faces").mkdir(parents=True, exist_ok=True)
    (proj / "assets" / "framed").mkdir(parents=True, exist_ok=True)
    (proj / "assets" / "img").mkdir(parents=True, exist_ok=True)
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
