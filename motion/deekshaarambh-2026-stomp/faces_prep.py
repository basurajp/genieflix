#!/usr/bin/env python3
"""Turn the learners' original posts into the stomp piece's photos and its one steady post frame.

NOT stdlib: needs opencv-contrib-python-headless and numpy in a venv, plus the
YuNet face-landmark model (face_detection_yunet_2023mar.onnx, opencv_zoo). This
is the only script in the repo with those needs. It runs once per set of posts,
and the rest of the stomp piece reads its outputs.

Usage:
  python faces_prep.py --project <dir> --images <folder of the posts> \
      --yunet face_detection_yunet_2023mar.onnx [--pick-hold <file>] [--pick-hero <file>]
  python faces_prep.py --project <dir> --reuse      # rebuild the sprites from assets/faces and assets/framed

Every post is the same Deekshaarambh frame with the learner's photo in its
window. The frame is rebuilt from the posts themselves: the per-pixel median of
every post 1254 px or larger is the frame wherever the posts agree, and the
window is where they disagree (the sparks, the scroll and the paper plane that
overlap the window stay part of the frame). Each learner's photo is then cut
from their own post's window only, scaled and moved so the eyes land on one
point with one spacing as nearly as the photo allows: the window is always
filled, and no photo pixel is shown larger than 1.25 screen pixels. A file that
is a plain photo (no frame) is cropped the same way from the whole image.

Writes:
  motion/deekshaarambh-2026-stomp/faces.json  file names, sizes, eye landmarks, where the eyes land in the
                                               post, "order" (distinct faces, sharpest first), "hold", "hero",
                                               and "post_frame" (the window and the eye target). Numbers only.
  <project>/assets/img/frame.png           the frame, 1000x1000, the window transparent
  <project>/assets/inner/fNNN.jpg          the photo layer, cut to the window's bounding box
  <project>/assets/framed/fNNN.jpg         the whole post rebuilt (frame over that photo), 1000x1000
  <project>/assets/faces/fNNN.jpg          400x400 tight face, eyes at (145,170) and (255,170)
  <project>/assets/img/framed_sheet.jpg    the rebuilt posts as a 10-column sprite of 300 px cells
  <project>/assets/img/faces_sheet.jpg     the tight faces as a 10-column sprite of 400 px cells
  <project>/assets/img/face_cells.jpg      tight 128 px face crops, 20-column sprite (number, map tiles)
  <project>/assets/img/face_mosaic.jpg     1152x672 mosaic of tight face crops (fills type)
"""
import argparse
import json
import math
import pathlib

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
OUT, E, EY = 400, 110, 170            # tight faces: canvas, eye gap, eye line
FO = 1000                             # the post canvas
FRAME_MIN = 1254                      # posts at least this big build the frame
DISAGREE = 40                         # a post disagrees with the median where a channel is off by more than this
DISPLAY = 0.86                        # the windows show the 1000 px post at 860 px
MAX_UP = 1.25                         # most screen pixels per photo pixel
PLAIN_DIFF = 20.0                     # mean difference from the frame above which a file is a plain photo


def detect(det, img):
    """the main person's eyes (left, right) in image pixels, with the detector score and the tilt"""
    h, w = img.shape[:2]
    sc = min(1.0, 900 / max(w, h))
    small = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc < 1.0 else img
    det.setInputSize((small.shape[1], small.shape[0]))
    _, found = det.detect(small)
    if found is None:
        return None
    f = max(found, key=lambda f: f[2] * f[3] * f[14])          # the main person: biggest confident face
    eyes = sorted([(f[4] / sc, f[5] / sc), (f[6] / sc, f[7] / sc)])
    ang = float(np.degrees(np.arctan2(eyes[1][1] - eyes[0][1], eyes[1][0] - eyes[0][0])))
    return eyes, float(f[14]), ang


def align_face(img, eyes):
    """the 400 px tight face, eyes level at (145,170) and (255,170). Large sources are first reduced
    (area filter) so the warp never shrinks by more than 20%."""
    ed = float(np.hypot(eyes[1][0] - eyes[0][0], eyes[1][1] - eyes[0][1]))
    pre = min(1.0, 1.25 * E / ed)
    src_img = cv2.resize(img, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA) if pre < 1.0 else img
    src = np.array([[x * pre, y * pre] for x, y in eyes], np.float32)
    dst = np.array([[OUT / 2 - E / 2, EY], [OUT / 2 + E / 2, EY]], np.float32)
    M, _ = cv2.estimateAffinePartial2D(src, dst)
    w = cv2.warpAffine(src_img, M, (OUT, OUT), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(w, 1.15, cv2.GaussianBlur(w, (0, 0), 1.2), -0.15, 0)


def build_frame(stack):
    """median of the posts -> (frame RGBA, window mask, window box [x0, y0, x1, y1], corner radius)"""
    med = np.empty((FO, FO, 3), np.uint8)
    frac = np.empty((FO, FO), np.float32)
    for r0 in range(0, FO, 100):
        part = np.stack([s[r0:r0 + 100] for s in stack])
        m = np.round(np.median(part, axis=0))
        med[r0:r0 + 100] = m.astype(np.uint8)
        frac[r0:r0 + 100] = (np.abs(part.astype(np.int16) - m.astype(np.int16)[None]).max(axis=3) > DISAGREE).mean(axis=0)
    win = cv2.morphologyEx((frac > 0.12).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    _, lab, st, _ = cv2.connectedComponentsWithStats(win)
    win = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    ff = win.copy()
    cv2.floodFill(ff, np.zeros((FO + 2, FO + 2), np.uint8), (0, 0), 1)
    win |= 1 - ff                                                  # photo areas that happened to agree
    ys, xs = np.nonzero(win)
    box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    # the corners' missing area gives the radius (overlapping artwork only makes it larger, which is safe)
    r = math.ceil(math.sqrt(max(0, (box[2] - box[0]) * (box[3] - box[1]) - int(win.sum())) / (4 - math.pi)))
    alpha = 255.0 - cv2.GaussianBlur(win.astype(np.float32) * 255.0, (0, 0), 0.8)
    return np.dstack([med, np.clip(alpha, 0, 255).astype(np.uint8)]), win, box, r


def place(eyes, U, T, target, gap):
    """scale s and offset (tx, ty), canvas = s * source + t, putting the eyes on target with the given gap
    as nearly as the photo allows: T (canvas) stays inside the usable source rect U, and no photo pixel
    is shown larger than MAX_UP screen pixels"""
    (ax, ay), (bx, by) = eyes
    g, mx, my = math.hypot(bx - ax, by - ay), (ax + bx) / 2, (ay + by) / 2
    cover = max((T[2] - T[0]) / (U[2] - U[0]), (T[3] - T[1]) / (U[3] - U[1]))
    s = max(cover, min(gap / g, MAX_UP / DISPLAY))
    tx = min(max(target[0] - s * mx, T[2] - s * U[2]), T[0] - s * U[0])
    ty = min(max(target[1] - s * my, T[3] - s * U[3]), T[1] - s * U[1])
    return s, tx, ty


def render_photo(img, s, tx, ty):
    pre = min(1.0, 1.25 * s)
    src = cv2.resize(img, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA) if pre < 1.0 else img
    kx, ky = src.shape[1] / img.shape[1], src.shape[0] / img.shape[0]
    M = np.float32([[s / kx, 0, tx], [0, s / ky, ty]])
    w = cv2.warpAffine(src, M, (FO, FO), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(w, 1.15, cv2.GaussianBlur(w, (0, 0), 1.2), -0.15, 0)


def from_images(a, proj):
    files = sorted(p for p in pathlib.Path(a.images).expanduser().iterdir()
                   if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    det = cv2.FaceDetectorYN.create(a.yunet, "", (320, 320), 0.6, 0.3, 5000)
    faces, aligned, stack, small_posts = [], [], [], []
    for p in files:                       # pass 1: faces, and the big posts for the frame
        img = cv2.imread(str(p))
        if img is None:
            print(f"skip {p.name}: unreadable")
            continue
        h, w = img.shape[:2]
        d = detect(det, img)
        if d is None:
            print(f"skip {p.name}: no face")
            continue
        eyes, score, ang = d
        ed = float(np.hypot(eyes[1][0] - eyes[0][0], eyes[1][1] - eyes[0][1]))
        if score < 0.8 or abs(ang) > 25 or ed < 40:
            print(f"skip {p.name}: score {score:.2f}, tilt {ang:.0f} deg, eye gap {ed:.0f}px")
            continue
        faces.append({"file": p.name, "size": [w, h], "score": round(score, 3),
                      "eyes": [[round(float(x), 1), round(float(y), 1)] for x, y in eyes]})
        aligned.append(align_face(img, eyes))
        if w == h:
            (stack if w >= FRAME_MIN else small_posts).append(cv2.resize(img, (FO, FO), interpolation=cv2.INTER_AREA))
    if len(stack) < 12:
        stack += small_posts
    small_posts.clear()
    frame, win, box, r = build_frame(stack)
    stack.clear()
    cv2.imwrite(str(proj / "assets" / "img" / "frame.png"), frame)
    outside = cv2.dilate(win, np.ones((15, 15), np.uint8)) == 0
    fr_rgb, fr_a = frame[..., :3].astype(np.float32), frame[..., 3:].astype(np.float32) / 255.0

    def native(rec):                     # a framed post's eyes in canvas pixels, as posted
        n = FO / rec["size"][0]
        (ax, ay), (bx, by) = rec["eyes"]
        return (ax + bx) / 2 * n, (ay + by) / 2 * n, math.hypot(bx - ax, by - ay) * n

    # pass 2: classify each file against the frame, then cut its photo into the window
    framed, posts = [], []
    for k, rec in enumerate(faces):
        img = cv2.imread(str(pathlib.Path(a.images).expanduser() / rec["file"]))
        w, h = rec["size"]
        if w == h:
            c = cv2.resize(img, (FO, FO), interpolation=cv2.INTER_AREA).astype(np.float32)
            diff = float(np.abs(c - fr_rgb).mean(axis=2)[outside].mean())
        else:
            diff = 99.0
        rec["plain"] = diff > PLAIN_DIFF
        posts.append(img if rec["plain"] else None)
    nat = [native(rec) for rec in faces if not rec["plain"]]
    target = ((box[0] + box[2]) / 2, float(np.median([v[1] for v in nat])) if nat else box[1] + 0.32 * (box[3] - box[1]))
    gap = float(np.percentile([v[2] for v in nat], 70)) if nat else 0.17 * (box[2] - box[0])
    inner_t = (box[0] + r - 3, box[1] + r - 3, box[2] - r + 3, box[3] - r + 3)
    whole_t = (box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2)
    for k, rec in enumerate(faces):
        img = posts[k] if posts[k] is not None else cv2.imread(str(pathlib.Path(a.images).expanduser() / rec["file"]))
        w, h = rec["size"]
        if rec["plain"]:
            U, T = (0, 0, w, h), whole_t
        else:
            n = FO / w
            U, T = ((box[0] + r) / n, (box[1] + r) / n, (box[2] - r) / n, (box[3] - r) / n), inner_t
        s, tx, ty = place(rec["eyes"], U, T, target, gap)
        photo = render_photo(img, s, tx, ty)
        post = (photo.astype(np.float32) * (1 - fr_a) + fr_rgb * fr_a).astype(np.uint8)
        (ax, ay), (bx, by) = rec["eyes"]
        rec["post"] = [round(s * (ax + bx) / 2 + tx, 1), round(s * (ay + by) / 2 + ty, 1), round(s * math.hypot(bx - ax, by - ay), 1)]
        cv2.imwrite(str(proj / "assets" / "inner" / f"f{k:03d}.jpg"), photo[box[1]:box[3], box[0]:box[2]], [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str(proj / "assets" / "framed" / f"f{k:03d}.jpg"), post, [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str(proj / "assets" / "faces" / f"f{k:03d}.jpg"), aligned[k], [cv2.IMWRITE_JPEG_QUALITY, 93])
        framed.append(post)
        posts[k] = None
    print(f"{len(faces)} of {len(files)} files aligned ({sum(r_['plain'] for r_ in faces)} plain photos); "
          f"window {box}, corner radius {r}, eyes to ({target[0]:.0f}, {target[1]:.0f}) gap {gap:.0f}")
    spec = {"source": "images", "out": OUT, "eye_gap": E, "eye_y": EY,
            "post_frame": {"canvas": FO, "window": box, "radius": r, "eye": [round(target[0], 1), round(target[1], 1)], "gap": round(gap, 1)},
            "faces": faces}
    return spec, aligned, framed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    ap.add_argument("--images", help="a folder of the learners' original posts")
    ap.add_argument("--yunet")
    ap.add_argument("--pick-hold", help="file name of the post held on 'each one.' (default: the sharpest)")
    ap.add_argument("--pick-hero", help="file name of the post the number grows from (default: the second sharpest)")
    ap.add_argument("--reuse", action="store_true", help="rebuild the sprites from assets/faces and assets/framed")
    a = ap.parse_args()
    if not a.reuse and not (a.images and a.yunet):
        ap.error("pass --images and --yunet, or --reuse")
    proj = pathlib.Path(a.project).expanduser().resolve()
    for d in ("faces", "framed", "inner", "img"):
        (proj / "assets" / d).mkdir(parents=True, exist_ok=True)
    if a.reuse:
        spec = json.loads((HERE / "faces.json").read_text(encoding="utf-8-sig"))
        n = len(spec["faces"])
        finish(a, proj, spec, [cv2.imread(str(proj / "assets" / "faces" / f"f{k:03d}.jpg")) for k in range(n)],
               [cv2.imread(str(proj / "assets" / "framed" / f"f{k:03d}.jpg")) for k in range(n)])
        return
    for d in ("faces", "framed", "inner"):
        for old in (proj / "assets" / d).glob("f*.jpg"):
            old.unlink()
    spec, aligned, framed = from_images(a, proj)
    finish(a, proj, spec, aligned, framed)


def finish(a, proj, spec, aligned, framed):
    """rank, dedupe, pick the hero faces, write faces.json and every sprite"""
    faces = spec["faces"]
    # rank: sharpness (Laplacian variance of the face, scaled by source eye distance), and drop
    # repeats (some learners posted twice)
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
    # big: the faces for the eye-locked windows, the ones whose eyes landed closest to the target first
    # (a photo cut only from its own window cannot always reach it), sharpest first within each group
    pf = spec["post_frame"]

    def lock_err(k):
        mx, my, g = faces[k]["post"]
        return math.hypot(mx - pf["eye"][0], my - pf["eye"][1]) / pf["gap"] + abs(math.log(g / pf["gap"]))
    spec["big"] = [k for k in order if lock_err(k) <= 0.5] + [k for k in order if lock_err(k) > 0.5]
    names = [r["file"] for r in faces]
    pick = lambda nm, default: names.index(nm) if nm and nm in names else default
    spec["hold"] = pick(a.pick_hold, order[0])
    spec["hero"] = pick(a.pick_hero, order[1] if order[1] != spec["hold"] else order[2])
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
    # compose.py shifts whole tile lattices across this sprite on the beat, so every cell must hold a
    # distinct sharp face: cells outside "order" (repeats, soft faces, the empty tail) borrow one from it
    keep = set(order)
    spare = iter(order[(len(order) // 2 + j) % len(order)] for j in range(crows * ccols))
    for k in range(crows * ccols):
        src = tight[k] if k in keep else tight[next(spare)]
        cs[(k // ccols) * cc:(k // ccols + 1) * cc, (k % ccols) * cc:(k % ccols + 1) * cc] = cv2.resize(src, (cc, cc), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(proj / "assets" / "img" / "face_cells.jpg"), cs, [cv2.IMWRITE_JPEG_QUALITY, 90])
    mc, mcols, mrows = 48, 24, 14
    mos = np.zeros((mrows * mc, mcols * mc, 3), np.uint8)
    rng = np.random.default_rng(14)
    pick_m = [order[i % len(order)] for i in rng.permutation(mrows * mcols)]
    for k in range(mrows * mcols):
        mos[(k // mcols) * mc:(k // mcols + 1) * mc, (k % mcols) * mc:(k % mcols + 1) * mc] = cv2.resize(tight[pick_m[k]], (mc, mc), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(proj / "assets" / "img" / "face_mosaic.jpg"), mos, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"aligned {n} faces, {len(order)} distinct and sharp; sprites written")


if __name__ == "__main__":
    main()
