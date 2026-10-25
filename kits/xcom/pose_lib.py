# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/units_opus55/pose_lib.py (imported 2026-10-25)
# Changed: header only
"""World-space posing helpers for the MPFB game_engine rig (Blender side).

All directions are in Blender world space: +Y = model front (facing 0 = north),
anatomical left = -X, Z up. Bones are rotated about their head (FK); children follow.
`aim_to` uses the minimal rotation from the bone's current head->child-head vector, so
twist is inherited from the rest A-pose unless set explicitly.
"""
import math
import bpy
from mathutils import Matrix, Vector, Quaternion


def upd():
    bpy.context.view_layer.update()


def rad(d):
    return math.radians(d)


class Poser:
    def __init__(self, rig):
        self.rig = rig
        self.mw = rig.matrix_world.copy()
        self.mwi = self.mw.inverted()
        self.pb = rig.pose.bones
        self.rest_world = {b.name: (self.mw @ b.matrix_local) for b in rig.data.bones}

    # ---------------------------------------------------------------- queries
    def head(self, name):
        return self.mw @ self.pb[name].head

    def tail(self, name):
        return self.mw @ self.pb[name].tail

    def child_head(self, name):
        kids = [c for c in self.rig.data.bones[name].children]
        if not kids:
            return self.tail(name)
        # prefer the connected / closest child (calf for thigh, foot for calf, ball for foot)
        h = self.head(name)
        t = self.tail(name)
        k = min(kids, key=lambda c: (self.head(c.name) - t).length)
        return self.head(k.name)

    def world_matrix(self, name):
        return self.mw @ self.pb[name].matrix

    # ---------------------------------------------------------------- edits
    def reset(self):
        for p in self.pb:
            p.rotation_mode = 'QUATERNION'
            p.rotation_quaternion = (1, 0, 0, 0)
            p.location = (0, 0, 0)
            p.scale = (1, 1, 1)
        upd()

    def rot_world(self, name, R, pivot=None):
        """Rotate bone `name` by world 3x3 R about `pivot` (default: its head)."""
        p = self.pb[name]
        h = Vector(pivot) if pivot is not None else self.head(name)
        M = Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h)
        p.matrix = self.mwi @ M @ self.mw @ p.matrix
        upd()

    def rot_axis(self, name, axis, deg, pivot=None):
        self.rot_world(name, Matrix.Rotation(rad(deg), 3, Vector(axis).normalized()), pivot)

    def translate(self, name, d):
        p = self.pb[name]
        M = Matrix.Translation(Vector(d))
        p.matrix = self.mwi @ M @ self.mw @ p.matrix
        upd()

    def aim_to(self, name, direction, twist=0.0, ref=None):
        """Point the bone's head->ref vector (default head->child head) along `direction`."""
        h = self.head(name)
        r = (ref() if callable(ref) else self.child_head(name)) - h
        d = Vector(direction).normalized()
        q = r.normalized().rotation_difference(d)
        R = q.to_matrix()
        if twist:
            R = Matrix.Rotation(rad(twist), 3, d) @ R
        self.rot_world(name, R)

    def aim_point(self, name, point, twist=0.0):
        self.aim_to(name, Vector(point) - self.head(name), twist)

    def set_world_rot(self, name, R3):
        """Give bone `name` the world rotation R3 (keeps its head where it is)."""
        p = self.pb[name]
        h = self.head(name)
        M = Matrix.Translation(h) @ R3.to_4x4()
        p.matrix = self.mwi @ M
        upd()

    def rest_rot(self, name):
        return self.rest_world[name].to_3x3().normalized()

    # ---------------------------------------------------------------- limbs
    def arm(self, side, upper, fore, hand=None, twist_upper=0.0, twist_fore=0.0):
        """Directions given for the LEFT side as (out_deg, fwd_deg) from straight down;
        mirrored for the right. out = abduction away from the body, fwd = toward +Y."""
        sx = -1.0 if side == 'l' else 1.0

        def vec(od):
            o, f = od
            # spherical: polar angle from -Z; azimuth split into out (x) and fwd (y)
            return Vector((sx * math.tan(rad(o)), math.tan(rad(f)), -1.0)).normalized()
        self.aim_to(f'upperarm_{side}', vec(upper), twist_upper * (1 if side == 'l' else -1))
        self.aim_to(f'lowerarm_{side}', vec(fore), twist_fore * (1 if side == 'l' else -1))
        if hand is not None:
            self.aim_to(f'hand_{side}', vec(hand), ref=lambda s=side: self._hand_ref(s))

    def arm_dir(self, side, upper_dir, fore_dir, hand_dir=None, twist_fore=0.0):
        """Absolute world directions (already sided)."""
        self.aim_to(f'upperarm_{side}', upper_dir)
        self.aim_to(f'lowerarm_{side}', fore_dir, twist_fore)
        if hand_dir is not None:
            self.aim_to(f'hand_{side}', hand_dir, ref=lambda s=side: self._hand_ref(s))

    def _hand_ref(self, side):
        return self.head(f'middle_01_{side}')

    def leg_ik(self, side, ankle, pole=(0, 1, 0)):
        """Analytic two-bone IK: thigh head fixed, ankle (foot head) to `ankle`, knee toward pole."""
        th, ca, ft = f'thigh_{side}', f'calf_{side}', f'foot_{side}'
        H = self.head(th)
        K0 = self.head(ca)
        A0 = self.head(ft)
        L1 = (K0 - H).length
        L2 = (A0 - K0).length
        T = Vector(ankle)
        d = T - H
        dist = min(d.length, (L1 + L2) * 0.9995)
        dvec = d.normalized()
        a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
        h = math.sqrt(max(L1 * L1 - a * a, 0.0))
        pv = Vector(pole)
        pp = (pv - dvec * pv.dot(dvec)).normalized()
        K = H + dvec * a + pp * h
        self.aim_to(th, K - H, ref=lambda: self.head(ca))
        self.aim_to(ca, (H + dvec * dist) - self.head(ca), ref=lambda: self.head(ft))
        return (d.length - dist)          # >0: target was out of reach

    def foot_world(self, side, pitch_deg=0.0, yaw_deg=0.0, toe_pitch_deg=None):
        """Foot world rotation = rest rotation pitched about world X (toe down = negative)
        and yawed about Z; ball (toes) keeps rest world rotation pitched by toe_pitch."""
        R = Matrix.Rotation(rad(yaw_deg), 3, 'Z') @ Matrix.Rotation(rad(pitch_deg), 3, 'X')
        self.set_world_rot(f'foot_{side}', R @ self.rest_rot(f'foot_{side}'))
        tp = 0.0 if toe_pitch_deg is None else toe_pitch_deg
        R2 = Matrix.Rotation(rad(yaw_deg), 3, 'Z') @ Matrix.Rotation(rad(tp), 3, 'X')
        self.set_world_rot(f'ball_{side}', R2 @ self.rest_rot(f'ball_{side}'))

    def key_all(self, frame, bones=None):
        for p in self.pb:
            if bones and p.name not in bones:
                continue
            p.keyframe_insert('rotation_quaternion', frame=frame)
            p.keyframe_insert('location', frame=frame)
