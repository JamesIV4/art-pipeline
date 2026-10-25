# XCOM 2026-10-02 .. 10-16: "lettuce" foliage rebuild and waxy leaf response

## 2026-10-02: lettuce folds

User: tree leaf clumps and grass "look like lettuce folds". Root diagnosed six
causes (few large leaf sheets curled into lobes; leaf clusters as smooth shells;
gap-free textures mipping to blocks; flat per-card normals + sheen; even ball
clumps; grass ribbons) and wrote the mandatory foliage guide from Polycount
threads, GPU Gems ch. 7 and lush-tree workflows: many small alpha spray cards on
twigs, atlas with gaps, crown volume normals transferred from a proxy, grass as
crossed blade-clump cards with up normals. Approved wood skeletons, trunks,
joins and ground bases were kept; only foliage was rebuilt as new versions. Palm
fronds (rachis + separate leaflets) were already correct.

Supporting finding (canopy tree batch): sprite crown greens are dark and
saturated (median sRGB 8,52,0, highlights 20,108,52); first Godot review showed
leaves lighter and yellower; per-card vertex colour (top ~1.0, bulk ~0.5,
undersides ~0.36-0.42) brought them in. Leaf roughness was then raised to
0.68-0.80 to stop gray sky glints.

## 2026-10-04: living plants must look waxy

User: living plants must read living and waxy (smooth cuticle, crisp highlights,
slight translucency), not subdued matte. The gray-olive veil came from uniform
roughness ~0.76 under Godot's default specular, so the 10-02 roughness raise was
the wrong fix.

## 2026-10-16: approved recipe (variant A)

ORM roughness centred ~0.42 (keep the texture's spread, 0.28-0.58), leaf normal
scale 1.0, runtime dielectric specular 0.25 on living-plant materials. Converted
in one pass by `make_waxy_foliage.py` (waxy ORM copies, originals and shared
folders untouched, seals refreshed, runtime manifest `plant_wax.json`).
Per-class centres: conifer needles 0.48, grass blades 0.52, petals 0.50, cactus
0.40. Exception discovered in the farm capture: clipped flat-topped hedges turned
waxy roughness into long pale glare bars; hedges keep authored roughness and only
get the low specular. Dead wood, bark, dry grass, straw, litter stay matte.

## Rejected

- Retinting foliage to counter the gray veil (fix specular instead).
- Library/free trees (asset-server eval 2026-10-06): far over budget or alpha-
  card trees that collapse when decimated.

## Sources

XCOM `art/team/VEGETATION_FOLIAGE_GUIDE.md`, `art/team/ORCHESTRATION_OPUS55.md`
("Plant light response"), `art/tools/make_waxy_foliage.py`,
`art/team/vegetation_anatomy_max/opus_batch03/research.md`,
`art/review/opus_revision_queue.md` (foliage rows).
