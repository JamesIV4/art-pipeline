# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/guns_v2/lib/iou.py (imported 2026-10-25)
# Changed: header only
"""Silhouette IoU of a model render against its BIGOBS sprite (system Python + numpy + Pillow).

python iou.py <silhouette.png (alpha, rendered by gv2_lib.silhouette_render at S px per sprite px)> <sprite_big1.png>
              <out overlay.png> [--json out.json]
IoU_fine: at render resolution (sprite mask upscaled nearest). IoU_px: at sprite resolution, a sprite pixel counts as model
when the render covers >= 50 % of it. Overlay: the enlarged sprite with model-only pixels tinted cyan, sprite-only pixels
tinted magenta and the model outline in yellow.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def iou(a, b):
    i = np.logical_and(a, b).sum()
    u = np.logical_or(a, b).sum()
    return float(i) / float(u) if u else 0.0


def main():
    sil, spr, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    jpath = Path(sys.argv[sys.argv.index("--json") + 1]) if "--json" in sys.argv else None
    excl = []
    if "--exclude" in sys.argv:          # sprite-px boxes x0,y0,x1,y1;... left out of a second IoU (the user-modernised grip)
        excl = [tuple(float(v) for v in b.split(",")) for b in sys.argv[sys.argv.index("--exclude") + 1].split(";") if b]
    S_img = Image.open(sil).convert("RGBA")
    P_img = Image.open(spr).convert("RGBA")
    S = S_img.width // P_img.width
    SY = S_img.height // P_img.height          # display aspect: 10 x 12 render px per sprite px
    m = np.asarray(S_img)[..., 3] > 127
    p = np.asarray(P_img)[..., 3] > 0
    pu = np.kron(p, np.ones((SY, S), bool))
    fine = iou(m, pu)
    cov = m.reshape(P_img.height, SY, P_img.width, S).mean(axis=(1, 3))
    mp = cov >= 0.5
    px = iou(mp, p)
    excl_iou = None
    if excl:
        keep = np.ones_like(m)
        for x0, y0, x1, y1 in excl:
            keep[int(round(y0 * SY)):int(round(y1 * SY)), int(round(x0 * S)):int(round(x1 * S))] = False
        excl_iou = iou(m & keep, pu & keep)
    # overlay
    base = np.asarray(P_img.resize((P_img.width * S, P_img.height * SY), Image.NEAREST).convert("RGBA")).astype(np.float32)
    bg = np.zeros_like(base)
    bg[...] = (34, 44, 54, 255)
    a = base[..., 3:4] / 255.0
    rgb = base[..., :3] * a + bg[..., :3] * (1 - a)
    only_m = m & ~pu
    only_p = pu & ~m
    rgb[only_m] = rgb[only_m] * 0.35 + np.array([0, 230, 255]) * 0.65
    rgb[only_p] = rgb[only_p] * 0.35 + np.array([255, 40, 200]) * 0.65
    im = Image.fromarray(rgb.clip(0, 255).astype(np.uint8), "RGB")
    edge = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)
    e = np.asarray(edge) > 0
    arr = np.asarray(im).copy()
    arr[e] = (255, 230, 60)
    im = Image.fromarray(arr)
    d = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in excl:        # the excluded (modernised grip) zone, dashed white
        bx = [int(round(x0 * S)), int(round(y0 * SY)), int(round(x1 * S)) - 1, int(round(y1 * SY)) - 1]
        for k in range(bx[0], bx[2], 8):
            d.line([(k, bx[1]), (min(k + 4, bx[2]), bx[1])], fill=(255, 255, 255))
            d.line([(k, bx[3]), (min(k + 4, bx[2]), bx[3])], fill=(255, 255, 255))
        for k in range(bx[1], bx[3], 8):
            d.line([(bx[0], k), (bx[0], min(k + 4, bx[3]))], fill=(255, 255, 255))
            d.line([(bx[2], k), (bx[2], min(k + 4, bx[3]))], fill=(255, 255, 255))
    d.text((4, 4), f"IoU {fine:.3f} (fine)  {px:.3f} (sprite px)" + (f"  {excl_iou:.3f} excl. grip zone" if excl else ""),
           fill=(255, 255, 255))
    d.text((4, 16), "cyan: model only  magenta: sprite only  yellow: model outline" + ("  dashed: grip zone" if excl else ""),
           fill=(220, 220, 220))
    if not out.exists():
        im.save(out)
    res = {"iou_fine": round(fine, 4), "iou_sprite_px": round(px, 4), "render_px_per_sprite_px": [S, SY],
           "pixel_aspect": "sprite pixels shown 1:%.2f (320x200 at 4:3)" % (SY / S),
           "model_px": int(m.sum()), "sprite_px_upscaled": int(pu.sum()), "overlay": str(out)}
    if excl:
        res["iou_fine_excluding_grip_zone"] = round(excl_iou, 4)
        res["grip_zone_px"] = [list(b) for b in excl]
    print("IOU", json.dumps(res))
    if jpath and not jpath.exists():
        jpath.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
