# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/jungle_opus55/scripts/sdf_mesh.py (imported 2026-10-25)
# Changed: header only (pure numpy)
"""Implicit one-surface wood for the canopy master (opus_batch03).  Pure numpy.

Field: every skeleton branch is a tapered capsule chain (roots flattened by zscale); a branch's subtree is
smooth-unioned into its parent with the branch's fillet k (polynomial smooth minimum, I. Quilez,
https://iquilezles.org/articles/smin/), continuation joins (column ports) use a plain min.  So the trunk
flares into roots/co-stem/limbs and every limb flares into its branches and twigs as ONE surface.
Polygonisation: sparse naive surface nets (dual contouring with averaged edge crossings, one Newton step onto
the zero set) on a global lattice whose pitch divides 2 m exactly, so translated duplicate columns produce
bit-identical meshes.  Quads are oriented outward (inside -> outside along each sign-changing edge)."""
import math
from collections import defaultdict

import numpy as np

BIG = 1e3
Z_CLIP = -0.45


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


class Field:
    def __init__(self, design):
        self.names = list(design.order)
        self.idx = {n: i for i, n in enumerate(self.names)}
        self.br = [design.B[n] for n in self.names]
        self.parent = [self.idx[b.parent] if b.parent else -1 for b in self.br]
        self.children = [[self.idx[c] for c in b.children if c in self.idx] for b in self.br]
        self.k = np.array([0.0 if b.cont else b.k for b in self.br])
        self.A = [b.P[:-1] for b in self.br]
        self.Bp = [b.P[1:] for b in self.br]
        self.RA = [b.R[:-1] for b in self.br]
        self.RB = [b.R[1:] for b in self.br]
        self.zs = [b.zscale for b in self.br]
        lo, hi = [], []
        for b in self.br:
            m = float(b.R.max()) * max(1.0, b.zscale) + 0.02
            lo.append(b.P.min(0) - m)
            hi.append(b.P.max(0) + m)
        self.lo, self.hi = np.array(lo), np.array(hi)
        self.kmax = float(self.k.max())
        # ancestors
        self.anc = []
        for i in range(len(self.br)):
            a, p = [], self.parent[i]
            while p >= 0:
                a.append(p)
                p = self.parent[p]
            self.anc.append(a)

    def cand(self, lo, hi, margin):
        m = (self.hi + margin >= lo).all(1) & (self.lo - margin <= hi).all(1)
        return np.nonzero(m)[0]

    def dist_branch(self, P, bi):
        A, B, RA, RB = self.A[bi], self.Bp[bi], self.RA[bi], self.RB[bi]
        d = B - A
        dd = np.maximum((d * d).sum(1), 1e-14)
        AP = P[:, None, :] - A[None]
        t = np.clip((AP * d[None]).sum(2) / dd[None], 0, 1)
        q = AP - t[..., None] * d[None]
        if self.zs[bi] != 1.0:
            q[..., 2] *= self.zs[bi]
        dist = np.sqrt((q * q).sum(2)) - (RA[None] + t * (RB - RA)[None])
        j = dist.argmin(1)
        return dist[np.arange(len(P)), j], j, t[np.arange(len(P)), j]

    def eval(self, P, cand, want_label=False):
        cs = set(int(c) for c in cand)
        need = set(cs)
        for c in cs:
            need.update(self.anc[c])
        G = {}
        lab_b = np.full(len(P), -1)
        lab_s = np.zeros(len(P), int)
        best = np.full(len(P), BIG)
        for bi in sorted(need, reverse=True):          # children have larger indices than parents
            if bi in cs:
                dist, seg, _ = self.dist_branch(P, bi)
                if want_label:
                    m = dist < best
                    best[m] = dist[m]
                    lab_b[m] = bi
                    lab_s[m] = seg[m]
            else:
                dist = np.full(len(P), BIG)
            g = dist
            for ch in self.children[bi]:
                if ch in G:
                    g = smin(g, G.pop(ch), self.k[ch])
            G[bi] = g
        roots = [bi for bi in G]
        F = G[roots[0]]
        for r in roots[1:]:
            F = np.minimum(F, G[r])
        F = np.maximum(F, Z_CLIP - P[:, 2])             # flat underground bottom (below the walking plane)
        if want_label:
            return F, lab_b, lab_s
        return F


def surface_nets(design, h=1.0 / 64, hz=None, x0=-3.75, x1=3.75, z0=None, z1=7.7, block=16, log=print):
    LEVEL = math.sqrt(6.0)
    hz = hz or LEVEL / 157
    z0 = z0 if z0 is not None else -40 * hz
    f = Field(design)
    nx = int(round((x1 - x0) / h))
    nz = int(math.ceil((z1 - z0) / hz))
    nbx = nx // block + 1
    nbz = nz // block + 1
    NX = nbx * block + 1
    NZ = nbz * block + 1
    origin = np.array([x0, x0, z0])
    step = np.array([h, h, hz])
    half_diag = 0.5 * math.sqrt((block * h) ** 2 * 2 + (block * hz) ** 2)
    margin = f.kmax + 3 * h
    keys_all, verts_all, labb_all, labs_all = [], [], [], []
    quads_all = []
    nact = 0
    ii = np.arange(block + 1)
    gi, gj, gk = np.meshgrid(ii, ii, ii, indexing="ij")
    for bk in range(nbz):
        for bj in range(nbx):
            for bi in range(nbx):
                lo = origin + np.array([bi, bj, bk]) * block * step
                hi = lo + block * step
                cand = f.cand(lo, hi, margin)
                if len(cand) == 0:
                    continue
                cen = (lo + hi) / 2
                Fc = f.eval(cen[None], cand)[0]
                if abs(Fc) > half_diag + 3 * h:
                    continue
                Pg = lo + np.stack([gi, gj, gk], -1).reshape(-1, 3) * step
                F = f.eval(Pg, cand).reshape(block + 1, block + 1, block + 1)
                ins = F < 0
                if ins.all() or not ins.any():
                    continue
                nact += 1
                # cubes with sign change
                c0 = ins[:-1, :-1, :-1]
                anyin = np.zeros_like(c0)
                allin = np.ones_like(c0)
                for dx in (0, 1):
                    for dy in (0, 1):
                        for dz in (0, 1):
                            s = ins[dx:block + dx, dy:block + dy, dz:block + dz]
                            anyin |= s
                            allin &= s
                surf = anyin & ~allin
                ci = np.argwhere(surf)
                if len(ci):
                    acc = np.zeros((len(ci), 3))
                    cnt = np.zeros(len(ci))
                    for ax in range(3):
                        o1, o2 = [a for a in range(3) if a != ax]
                        for u in (0, 1):
                            for v in (0, 1):
                                a = ci.copy()
                                a[:, o1] += u
                                a[:, o2] += v
                                b = a.copy()
                                b[:, ax] += 1
                                Fa = F[a[:, 0], a[:, 1], a[:, 2]]
                                Fb = F[b[:, 0], b[:, 1], b[:, 2]]
                                m = (Fa < 0) != (Fb < 0)
                                t = Fa / np.where(m, Fa - Fb, 1.0)
                                p = a + (b - a) * t[:, None]
                                acc[m] += p[m]
                                cnt[m] += 1
                    vloc = acc / cnt[:, None]
                    V = lo + vloc * step
                    # one Newton step onto F = 0
                    e = 0.25 * h
                    Fv = f.eval(V, cand)
                    g = np.zeros_like(V)
                    for ax in range(3):
                        dv = np.zeros(3)
                        dv[ax] = e
                        g[:, ax] = (f.eval(V + dv, cand) - f.eval(V - dv, cand)) / (2 * e)
                    gn = (g * g).sum(1)
                    stepv = (Fv / np.maximum(gn, 1e-9))[:, None] * g
                    lim = 0.5 * h
                    sl = np.linalg.norm(stepv, axis=1)
                    stepv *= np.minimum(1.0, lim / np.maximum(sl, 1e-12))[:, None]
                    V = V - stepv
                    _, lb, ls = f.eval(V, cand, want_label=True)
                    gc = ci + np.array([bi, bj, bk]) * block
                    keys_all.append(gc[:, 0] + NX * (gc[:, 1] + NX * gc[:, 2]))
                    verts_all.append(V)
                    labb_all.append(lb)
                    labs_all.append(ls)
                # sign-changing edges with lower endpoint inside the block's own range
                for ax in range(3):
                    sl0 = [slice(0, block)] * 3
                    sl1 = [slice(0, block)] * 3
                    sl1[ax] = slice(1, block + 1)
                    a_in = ins[tuple(sl0)]
                    b_in = ins[tuple(sl1)]
                    m = a_in != b_in
                    if not m.any():
                        continue
                    e = np.argwhere(m)
                    outward_pos = a_in[m]                   # inside at lower endpoint -> normal along +ax
                    g = e + np.array([bi, bj, bk]) * block
                    o1, o2 = [(1, 2), (2, 0), (0, 1)][ax]
                    def ck(d1, d2):
                        c = g.copy()
                        c[:, o1] += d1
                        c[:, o2] += d2
                        return c[:, 0] + NX * (c[:, 1] + NX * c[:, 2])
                    q = np.stack([ck(-1, -1), ck(0, -1), ck(0, 0), ck(-1, 0)], 1)
                    q[~outward_pos] = q[~outward_pos][:, ::-1]
                    quads_all.append(q)
    keys = np.concatenate(keys_all)
    V = np.concatenate(verts_all)
    LB = np.concatenate(labb_all)
    LS = np.concatenate(labs_all)
    order = np.argsort(keys)
    keys, V, LB, LS = keys[order], V[order], LB[order], LS[order]
    assert (np.diff(keys) > 0).all(), "duplicate cube keys"
    Q = np.concatenate(quads_all)
    pos = np.searchsorted(keys, Q)
    pos = np.clip(pos, 0, len(keys) - 1)
    ok = (keys[pos] == Q).all(1)
    log(f"surface nets: active blocks {nact}, verts {len(V)}, quads {len(Q)}, missing-quad {int((~ok).sum())}")
    pos = pos[ok]
    # triangulate along the shorter diagonal
    a, b, c, d = pos[:, 0], pos[:, 1], pos[:, 2], pos[:, 3]
    d1 = np.linalg.norm(V[a] - V[c], axis=1)
    d2 = np.linalg.norm(V[b] - V[d], axis=1)
    use1 = d1 <= d2
    T = np.concatenate([np.stack([a, b, c], 1)[use1], np.stack([a, c, d], 1)[use1],
                        np.stack([b, c, d], 1)[~use1], np.stack([b, d, a], 1)[~use1]])
    return {"V": V, "T": T, "label_branch": LB, "label_seg": LS, "names": f.names, "h": h, "hz": hz,
            "origin": origin, "field": f}


def _edge_counts(T):
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
    k = e[:, 0].astype(np.int64) * (int(T.max()) + 2) + e[:, 1]
    u, inv, c = np.unique(k, return_inverse=True, return_counts=True)
    return e, c[inv].reshape(3, -1).T          # per triangle, per edge (01, 12, 20) use count


def bowtie_vertices(T, nV):
    """vertices whose incident triangles form more than one edge-connected fan."""
    inc = [[] for _ in range(nV)]
    for ti, t in enumerate(T):
        for v in t:
            inc[v].append(ti)
    bad = []
    for v in range(nV):
        ts = inc[v]
        if len(ts) < 2:
            continue
        # neighbours of v per triangle: the two other vertices; fans connect through shared other-vertices
        parent = {}

        def find(x):
            while parent.get(x, x) != x:
                x = parent[x]
            return x
        for ti in ts:
            a, b = [w for w in T[ti] if w != v]
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        roots = {find(w) for ti in ts for w in T[ti] if w != v}
        if len(roots) > 1:
            bad.append(v)
    return bad


def repair_nonmanifold(V, T, labels, rounds=4, log=print):
    """surface nets makes a non-manifold edge where a lattice face is ambiguous (checkerboard signs, thin twig
    grazing the face).  Remove the triangles around such edges/bowtie vertices and close each hole with a fan
    (boundary direction reversed, so the result stays consistently outward).  Sub-centimetre, local."""
    V = V.copy()
    labels = labels.copy()
    pre_holes = None
    for r in range(rounds):
        e, cnt = _edge_counts(T)
        et = e.reshape(3, -1, 2).transpose(1, 0, 2)               # (m, 3, 2) per-triangle edges
        badv = set(np.unique(et[cnt != 2].ravel()).tolist()) if (cnt != 2).any() else set()
        if pre_holes is None:
            pre_holes = int((cnt == 1).sum())
        badv |= set(bowtie_vertices(T, len(V)))
        if not badv:
            log(f"repair: manifold after {r} rounds")
            return V, T, labels
        # grow the removal region until its boundary is a set of simple loops
        for grow in range(6):
            rm = np.isin(T, list(badv)).any(1)
            keepT = T[~rm]
            e2 = np.concatenate([keepT[:, [0, 1]], keepT[:, [1, 2]], keepT[:, [2, 0]]])
            und = np.sort(e2, 1)
            k = und[:, 0].astype(np.int64) * (len(V) + 1) + und[:, 1]
            u, inv, c = np.unique(k, return_inverse=True, return_counts=True)
            bnd = e2[c[inv] == 1]
            outd = defaultdict(list)
            ind = defaultdict(int)
            for a, b in bnd:
                outd[int(a)].append(int(b))
                ind[int(b)] += 1
            pinch = {v for v in set(outd) | set(ind) if len(outd.get(v, [])) != 1 or ind.get(v, 0) != 1}
            if not pinch:
                break
            badv |= pinch
        nxt = {a: bs[0] for a, bs in outd.items()}
        newV, newL, newT = [], [], []
        seen = set()
        for a in list(nxt):
            if a in seen:
                continue
            lp, cur = [a], nxt[a]
            seen.add(a)
            while cur != a and cur not in seen:
                lp.append(cur)
                seen.add(cur)
                cur = nxt[cur]
            ci = len(V) + len(newV)
            newV.append(V[lp].mean(0))
            newL.append(labels[lp[0]])
            for i in range(len(lp)):
                newT.append((ci, lp[(i + 1) % len(lp)], lp[i]))
        if newV:
            V = np.vstack([V, np.array(newV)])
            labels = np.concatenate([labels, np.array(newL)])
        T = np.vstack([keepT, np.array(newT, dtype=T.dtype)]) if newT else keepT
        log(f"repair round {r}: removed {int(rm.sum())} tris around {len(badv)} verts, filled {len(newV)} holes")
    e, cnt = _edge_counts(T)
    log(f"repair: after {rounds} rounds edge use {dict(zip(*np.unique(cnt, return_counts=True)))}")
    return V, T, labels


def gradient(f, P, cand=None, e=0.003):
    """normalised field gradient at points P (for shading normals)."""
    if cand is None:
        lo, hi = P.min(0), P.max(0)
        cand = f.cand(lo, hi, f.kmax + 0.05)
    g = np.zeros_like(P)
    for ax in range(3):
        dv = np.zeros(3)
        dv[ax] = e
        g[:, ax] = f.eval(P + dv, cand) - f.eval(P - dv, cand)
    return g / np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]


def label_points(f, P, cell=0.25):
    """nearest skeleton branch / segment (and its unsmoothed capsule distance) for arbitrary points,
    processed in spatially coherent buckets."""
    LB = np.full(len(P), -1)
    LS = np.zeros(len(P), int)
    DB = np.full(len(P), BIG)
    key = np.floor(P / cell).astype(np.int64)
    k1 = key[:, 0] * 1000003 + key[:, 1] * 1009 + key[:, 2]
    order = np.argsort(k1, kind="stable")
    ks = k1[order]
    starts = np.concatenate([[0], np.nonzero(np.diff(ks))[0] + 1, [len(ks)]])
    for a, b in zip(starts[:-1], starts[1:]):
        ids = order[a:b]
        Q = P[ids]
        cand = f.cand(Q.min(0), Q.max(0), 0.12)
        best = np.full(len(Q), BIG)
        lb = np.full(len(Q), -1)
        ls = np.zeros(len(Q), int)
        for bi in cand:
            dist, seg, _ = f.dist_branch(Q, bi)
            m = dist < best
            best[m] = dist[m]
            lb[m] = bi
            ls[m] = seg[m]
        LB[ids], LS[ids], DB[ids] = lb, ls, best
    return LB, LS, DB
