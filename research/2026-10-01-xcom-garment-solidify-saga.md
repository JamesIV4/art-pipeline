# XCOM 2026-09-30 .. 10-01: the unit garment / solidify saga and the delete-group fix

## Sequence

- v01-v03 (units_rebuild_max): disconnected primitive cloth tubes, then cloth
  material assigned to the fitted body. User: flexible clothing must use a real
  garment workflow. Also stretched neck / small head from fitting a legacy outfit.
- Research (MPFB Creating Clothes, MakeClothes, Blender Studio sculpted garments
  and clothing shapes, Cloth Filter): extract helper garment, own cut/ease/hems,
  restrained folds, panel UVs, bounded weights, test bends before propagating.
- v04: separate garment eased 9-12 mm over the full body, 3 mm Solidify wall.
- v05: neck/wrist closures rebuilt as explicit triangle fans with protected
  perimeters before masked decimation (exposed skin 15,060 -> 6,600 tris, closed,
  zero non-manifold). But the 3 mm wall reached Z 2.61 m vs outer max 2.00 m.
- v06: cause localised to underarm vertices (edges 16-73 mm, adjacent normals to
  175.7 deg): even-offset compensation amplified 3 mm to ~1.84 m. Ordinary
  offset held 2.99994-3.00005 mm. Remaining: 9-21 reversed pairs, 10-21 body
  intersections, 166-232 self-intersection pairs; positive clearance 0.673 mm
  did not override them.
- v07: bounded local fairing of the stored crossing neighbourhood (172 verts):
  outer crossings 41 -> 0, reversed pairs 21 -> 0; 1.8995 mm local clearance
  cleared 38 body intersections. Still 16 underarm self-intersections; topology
  fix stopped at degree-4 seam vertices.
- v08-v11: more connected-seam patches; still fighting contacts in arm/hip poses.
- 2026-10-01, units_opus55 (new lane): MakeClothes delete-group convention. Suit
  copied from body faces, Taubin-smoothed, offset 5.5 mm, keeps body weights;
  hidden body faces deleted (22 mm overlap at openings). Hems turned in 3.5 mm,
  seams as iso-contour loops pressed 1.1 mm. Armour as iso-contour plates with
  ordinary-offset walls. Solved in one pilot; remaining risk only garment self-
  contact in deep creases, measured per pose.

## Lessons kept

- Diagnose before repairing; the first hypothesis (collar topology) was wrong.
- Solidify: ordinary offset by default; clamps chosen from the mesh; never move
  the body or inflate globally.
- Paired-shell, intersection and clearance gates on final geometry; sample
  clearance is not a pass.
- Prefer construction that removes the failure class (nothing under the cloth)
  over ever-finer repair of a fragile construction.
- Budget: XCOM_1 male v01 ~26.1k (hands dominate exposed body) vs 24k ceiling.

## Sources

XCOM `art/review/units-garment-workflow-guide.md`, `units-solidify-spike-guide.md`,
`art/team/units_rebuild_max/research.md` (V04-V08), `repair_plan_v11.md`,
`art/team/units_opus55/research.md`, `HUMANOID_UNITS_WORKFLOW.md`.
