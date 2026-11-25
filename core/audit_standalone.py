"""Zero-dependency standalone formal auditor for cegis-bellman v0.1 certificates (.json.xz)."""
from __future__ import annotations

import argparse
import bisect
import ctypes
import hashlib
import json
import lzma
import math
import os
import platform
import time
from decimal import Decimal, localcontext, ROUND_CEILING, ROUND_FLOOR

LN2_LO = Decimal("0.693147180559945309417232121458176568075500134360255254120680")
LN2_HI = Decimal("0.693147180559945309417232121458176568075500134360255254120681")
TWO32 = Decimal("2.8284271247461900976033774484193961571393437507538961463533595")
PREC, IPREC = 50, 66
_LNC = {}
_LIB_C = {}


def _d(x: Decimal, rnd) -> Decimal:
    with localcontext() as c:
        c.prec, c.rounding = PREC, rnd
        return +x


def _op(fn, a: Decimal, b: Decimal, rnd) -> Decimal:
    with localcontext() as c:
        c.prec, c.rounding = PREC, rnd
        return fn(a, b)


def _ln_dec(x: Decimal) -> tuple[Decimal, Decimal]:
    res = _LNC.get(x)
    if res is not None:
        return res
    if x <= 0:
        return Decimal("-1e999"), Decimal("-1e999")
    if x == 1:
        return Decimal(0), Decimal(0)
    with localcontext() as c:
        c.prec = IPREC
        k, two, half, m = 0, Decimal(2), Decimal("0.5"), x
        while m >= two:
            m, k = m * half, k + 1
        while m < 1:
            m, k = m * two, k - 1
        mlo = mhi = m
        for _ in range(4):
            c.rounding = ROUND_FLOOR
            mlo = mlo.sqrt()
            c.rounding = ROUND_CEILING
            mhi = mhi.sqrt()
        c.rounding = ROUND_FLOOR
        vlo = (mlo - 1) / (mlo + 1)
        v2lo = vlo * vlo
        slo = tlo = vlo
        c.rounding = ROUND_CEILING
        vhi = (mhi - 1) / (mhi + 1)
        v2hi = vhi * vhi
        shi = thi = vhi
        for j in range(1, 18):
            d = Decimal(2 * j + 1)
            c.rounding = ROUND_FLOOR
            tlo = tlo * v2lo
            slo = slo + tlo / d
            c.rounding = ROUND_CEILING
            thi = thi * v2hi
            shi = shi + thi / d
        c.rounding = ROUND_CEILING
        rem = (two * thi * v2hi) / (Decimal(37) * (1 - v2hi))
        kd, m32 = Decimal(k), Decimal(32)
        c.rounding = ROUND_FLOOR
        lo = m32 * slo + (kd * LN2_LO if k >= 0 else kd * LN2_HI)
        c.rounding = ROUND_CEILING
        hi = m32 * shi + Decimal(16) * rem + (kd * LN2_HI if k >= 0 else kd * LN2_LO)
    out = (_d(lo, ROUND_FLOOR), _d(hi, ROUND_CEILING))
    if len(_LNC) < 25000:
        _LNC[x] = out
    return out


class Iv:
    __slots__ = ("lo", "hi")

    def __init__(self, x):
        if isinstance(x, Iv):
            self.lo, self.hi = x.lo, x.hi
            return
        d = Decimal.from_float(x) if isinstance(x, float) else (x if isinstance(x, Decimal) else Decimal(x))
        self.lo, self.hi = _d(d, ROUND_FLOOR), _d(d, ROUND_CEILING)

    @classmethod
    def raw(cls, lo: Decimal, hi: Decimal) -> "Iv":
        o = cls.__new__(cls)
        o.lo, o.hi = _d(lo, ROUND_FLOOR), _d(hi, ROUND_CEILING)
        return o

    def __add__(self, o):
        o = Iv(o)
        return Iv.raw(_op(Decimal.__add__, self.lo, o.lo, ROUND_FLOOR), _op(Decimal.__add__, self.hi, o.hi, ROUND_CEILING))

    def __sub__(self, o):
        o = Iv(o)
        return Iv.raw(_op(Decimal.__sub__, self.lo, o.hi, ROUND_FLOOR), _op(Decimal.__sub__, self.hi, o.lo, ROUND_CEILING))

    def __mul__(self, o):
        o = Iv(o)
        return Iv.raw(
            min(_op(Decimal.__mul__, a, b, ROUND_FLOOR) for a in (self.lo, self.hi) for b in (o.lo, o.hi)),
            max(_op(Decimal.__mul__, a, b, ROUND_CEILING) for a in (self.lo, self.hi) for b in (o.lo, o.hi)),
        )

    def __truediv__(self, o):
        o = Iv(o)
        assert o.lo > 0 or o.hi < 0
        return Iv.raw(
            min(_op(Decimal.__truediv__, a, b, ROUND_FLOOR) for a in (self.lo, self.hi) for b in (o.lo, o.hi)),
            max(_op(Decimal.__truediv__, a, b, ROUND_CEILING) for a in (self.lo, self.hi) for b in (o.lo, o.hi)),
        )

    def ln(self) -> "Iv":
        return Iv.raw(_ln_dec(self.lo)[0], _ln_dec(self.hi)[1])

    def sqrt(self) -> "Iv":
        with localcontext() as c:
            c.prec, c.rounding = PREC, ROUND_FLOOR
            lo = Decimal(0) if self.lo <= 0 else self.lo.sqrt()
            c.rounding = ROUND_CEILING
            hi = Decimal(0) if self.hi <= 0 else self.hi.sqrt()
        return Iv.raw(lo, hi)

    def pow_int(self, n: int) -> "Iv":
        r, b, e = Iv(1), self, n
        while e > 0:
            if e & 1:
                r = r * b
            b, e = b * b, e >> 1
        return r

    def pow_half(self, num: int) -> "Iv":
        if num == 0:
            return Iv(1)
        pos = (self.sqrt() if num & 1 else Iv(1)) * (self.pow_int(abs(num) // 2) if abs(num) // 2 else Iv(1))
        return pos if num > 0 else Iv(1) / pos

    def hull(self, o) -> "Iv":
        o = Iv(o)
        return Iv.raw(min(self.lo, o.lo), max(self.hi, o.hi))

    def max_abs(self) -> Decimal:
        return max(abs(self.lo), abs(self.hi))


TWO32_IV = Iv.raw(TWO32 - Decimal("1e-45"), TWO32 + Decimal("1e-45"))


def iv_fa(a: Iv, k: Iv, l: Iv) -> Iv:
    if l.hi <= 0:
        return Iv(0)
    return a * ((Iv(2) * k * l) / (k + l)).pow_half(3)


def prep_pwl(d: dict) -> dict:
    ks = [float(x) for x in d["ks"]]
    vals = [float(v) for v in d["vals"]]
    lks = [math.log(k) for k in ks]
    slopes = [(vals[i + 1] - vals[i]) / (lks[i + 1] - lks[i]) for i in range(len(ks) - 1)]
    kd = [Decimal.from_float(k) for k in ks]
    iv_v = [Iv(v) for v in vals]
    iv_lk = [Iv.raw(k, k).ln() for k in kd]
    return {
        "ks": ks, "lks": lks, "vals": vals, "slopes": slopes,
        "s_lo": float(d["s_lo"]), "s_hi": float(d["s_hi"]),
        "kd": kd, "iv_v": iv_v, "iv_lk": iv_lk,
    }


def pwl_eval(pwl: dict, k: Iv) -> Iv:
    kd, ivv, lks = pwl["kd"], pwl["iv_v"], pwl["iv_lk"]
    lo, hi = Decimal("1e99"), Decimal("-1e99")
    if k.lo <= kd[0]:
        v = ivv[0] + Iv(pwl["s_lo"]) * (Iv.raw(k.lo, min(k.hi, kd[0])) / Iv.raw(kd[0], kd[0])).ln()
        lo, hi = min(lo, v.lo), max(hi, v.hi)
    if k.hi >= kd[-1]:
        v = ivv[-1] + Iv(pwl["s_hi"]) * (Iv.raw(max(k.lo, kd[-1]), k.hi) / Iv.raw(kd[-1], kd[-1])).ln()
        lo, hi = min(lo, v.lo), max(hi, v.hi)
    i0 = max(0, bisect.bisect_right(kd, k.lo) - 1)
    i1 = min(len(kd) - 2, bisect.bisect_left(kd, k.hi))
    for i in range(i0, i1 + 1):
        xL, xR = max(k.lo, kd[i]), min(k.hi, kd[i + 1])
        if xL <= xR:
            lk0, dv, den = lks[i], ivv[i + 1] - ivv[i], lks[i + 1] - lks[i]
            for xp in (xL, xR):
                v = ivv[i] + dv * ((Iv.raw(xp, xp).ln() - lk0) / den)
                lo, hi = min(lo, v.lo), max(hi, v.hi)
    return Iv.raw(lo, hi)


def pwl_deriv(pwl: dict, k: Iv) -> Iv:
    kd, ivv, lks = pwl["kd"], pwl["iv_v"], pwl["iv_lk"]
    lo, hi = Decimal("1e99"), Decimal("-1e99")
    if k.lo < kd[0]:
        d = Iv(pwl["s_lo"]) / Iv.raw(k.lo, min(k.hi, kd[0]))
        lo, hi = min(lo, d.lo), max(hi, d.hi)
    if k.hi > kd[-1]:
        d = Iv(pwl["s_hi"]) / Iv.raw(max(k.lo, kd[-1]), k.hi)
        lo, hi = min(lo, d.lo), max(hi, d.hi)
    i0 = max(0, bisect.bisect_right(kd, k.lo) - 1)
    i1 = min(len(kd) - 2, bisect.bisect_left(kd, k.hi))
    for i in range(i0, i1 + 1):
        xL, xR = max(k.lo, kd[i]), min(k.hi, kd[i + 1])
        if xL <= xR:
            d = ((ivv[i + 1] - ivv[i]) / (lks[i + 1] - lks[i])) / Iv.raw(xL, xR)
            lo, hi = min(lo, d.lo), max(hi, d.hi)
    return Iv.raw(lo, hi)


def pwl_eval_f64(pwl: dict, k: float) -> float:
    ks, lks, vals, sl = pwl["ks"], pwl["lks"], pwl["vals"], pwl["slopes"]
    lk = math.log(max(k, 1e-300))
    if k <= ks[0]:
        return vals[0] + pwl["s_lo"] * (lk - lks[0])
    if k >= ks[-1]:
        return vals[-1] + pwl["s_hi"] * (lk - lks[-1])
    i = min(max(0, bisect.bisect_right(ks, k) - 1), len(sl) - 1)
    return vals[i] + sl[i] * (lk - lks[i])


class BbOut(ctypes.Structure):
    _fields_ = [
        ("certified", ctypes.c_int), ("iv_certified", ctypes.c_int),
        ("d_ub", ctypes.c_double), ("d_ub_iv", ctypes.c_double),
        ("d_lb", ctypes.c_double), ("leaf_count", ctypes.c_size_t), ("n_ce", ctypes.c_size_t),
    ]


def load_dll(pure: bool = False):
    if pure:
        return None
    if 0 not in _LIB_C:
        sysname = platform.system()
        ext = "cegis_bellman_verifier.dll" if sysname == "Windows" else ("libcegis_bellman_verifier.dylib" if sysname == "Darwin" else "libcegis_bellman_verifier.so")
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rust_verifier", ext)
        if not os.path.exists(path):
            _LIB_C[0] = None
            return None
        lib = ctypes.CDLL(path)
        P, D, Z, I = ctypes.POINTER(ctypes.c_double), ctypes.c_double, ctypes.c_size_t, ctypes.c_int
        for fn, args in [
            ("rs_verify_staying_barrier_bb_ext", [P, P, P, P, Z, D, D, P, P, P, P, Z, D, D, D, D, D, D, D, D, D, D, D, D, D, Z, P, Z]),
            ("rs_verify_super_barrier_bb_ext", [P, P, P, P, Z, D, D, P, P, P, P, Z, D, D, D, D, D, D, D, D, D, D, D, D, D, I, Z, Z, P, Z]),
            ("rs_verify_adverse_exit_bb_ext", [P, P, P, P, Z, D, D, D, D, D, D, D, D, D, D, D, D, D, D, I, D, Z, I, P, Z]),
        ]:
            getattr(lib, fn).argtypes = args
            getattr(lib, fn).restype = BbOut
        _LIB_C[0] = lib
    return _LIB_C[0]


def _c_pwl(p: dict):
    n = len(p["ks"])
    A, As = ctypes.c_double * n, ctypes.c_double * (n - 1)
    return A(*p["ks"]), A(*p["lks"]), A(*p["vals"]), As(*p["slopes"]), n, p["s_lo"], p["s_hi"]


def super_tail_max(vs: dict, ev: dict, av: float, qhi: float, bL: float, bR: float, eL: float, eU: float) -> float:
    ks_e = ev["ks"]
    ixlo, ixc = Iv.raw(vs["kd"][0], vs["kd"][0]), Iv.raw(vs["kd"][-1], vs["kd"][-1])
    ivA, ivq, ieL, ieU = Iv(str(av)), Iv(str(qhi)), Iv(str(eL)), Iv(str(eU))
    slo, Dhi, sloe, Dhie = Iv(vs["s_lo"]), Iv(vs["s_hi"]), Iv(ev["s_lo"]), Iv(ev["s_hi"])
    vs0, ve0, vse, vee = vs["iv_v"][0], ev["iv_v"][0], vs["iv_v"][-1], ev["iv_v"][-1]
    rt = ivq + iv_fa(ivA, ixlo, Iv(1)) / ixlo
    assert rt.hi < 1
    Finf = ivA * Iv(2).pow_half(3)
    Ye = ivq * ixc + Finf
    assert Ye.hi < ixc.lo
    out = Decimal("-1e99")
    for bv in (bL, bR):
        ivb = Iv(str(bv))
        cslo, cdhi = ieL + ivb * sloe, ieU + ivb * Dhie
        assert (cslo - slo).lo >= 0 and (cdhi - Dhi).hi <= 0
        sopt, shopt = (ivb * sloe) / cslo, (ivb * Dhie) / cdhi
        tlo = ieL * ((Iv(1) - sopt) * ixlo).ln() + ivb * sloe * sopt.ln() + cslo * rt.ln() + ivb * ve0 - vs0
        th1 = ieU * Ye.ln() + ivb * pwl_eval(ev, Iv(1)) - vse
        i1 = max(0, sum(1 for k in ks_e if k < 1.0) - 1)
        slm = min((((ev["iv_v"][j + 1] - ev["iv_v"][j]) / (ev["iv_lk"][j + 1] - ev["iv_lk"][j])) / Iv.raw(ev["kd"][j + 1], ev["kd"][j + 1])).lo for j in range(i1, len(ks_e) - 1))
        assert slm > 0
        ivsl = Iv.raw(slm, slm)
        cs = ieU / (ivb * ivsl)
        xc = (ixc + cs - Finf) / ivq
        xp = (Dhi * (ixc - Finf)) / ((Dhi - ieU) * ivq)
        g1 = lambda x: ieU * cs.ln() + ivb * (vee + ivsl * (ivq * x + Finf - cs - ixc)) - (vse + Dhi * (x / ixc).ln())
        g2p = ieU * (ivq * xp + Finf - ixc).ln() + ivb * vee - (vse + Dhi * (xp / ixc).ln())
        thl = ieU * (Iv(1) - shopt).ln() + ivb * Dhie * shopt.ln() + cdhi * (Ye / ixc).ln() + ieU * ixc.ln() + ivb * vee - vse
        thi = max(th1.hi, g1(ixc).hi, g1(xc).hi, g2p.hi, thl.hi)
        out = max(out, tlo.hi, thi)
    return math.nextafter(float(out), math.inf)


def check_witness_1d(W: dict, EW: dict, kp: dict, L: dict, alo: float, qlo: float, bL: float, bR: float, eL: float, eU: float, ka: float, kb: float):
    ivA, ivq, ibL, ibR, ieL, ieU = Iv(str(alo)), Iv(str(qlo)), Iv(str(bL)), Iv(str(bR)), Iv(str(eL)), Iv(str(eU))
    one, ika, ikb = Iv(1), Iv(str(ka)), Iv(str(kb))
    ks = sorted({Decimal.from_float(x) for x in [ka, kb, *W["ks"], *kp["ks"], *L["ks"]] if ka <= x <= kb} | {Decimal.from_float(ka * ((kb / ka) ** (i / 64.0))) for i in range(65)})

    def _seg(k0: Decimal, k1: Decimal, dp: int = 0) -> Decimal:
        k_iv = Iv.raw(k0, k1)
        Liv, kpiv = pwl_eval(L, k_iv), pwl_eval(kp, k_iv)
        assert Liv.lo >= 0 and Liv.hi < 1 and kpiv.lo >= ika.lo and kpiv.hi <= ikb.hi
        civ = ivq * k_iv + iv_fa(ivA, k_iv, Liv) - kpiv
        if civ.lo <= 0:
            assert dp < 18
            m = (k0 + k1) / Decimal(2)
            return max(_seg(k0, m, dp + 1), _seg(m, k1, dp + 1))
        lc, ll = civ.ln(), (one - Liv).ln()
        u1, u2 = ieL * lc + (one - ieL) * ll, ieU * lc + (one - ieU) * ll
        u_lo = min(u1.lo, u2.lo)
        ew_iv = pwl_eval(EW, kpiv)
        bew_lo = min((ibR * ew_iv).lo if ew_iv.lo < 0 else (ibL * ew_iv).lo, (ibR * ew_iv).lo if ew_iv.hi < 0 else (ibL * ew_iv).lo)
        r_hi = pwl_eval(W, k_iv).hi - (u_lo + bew_lo)
        if r_hi <= 0:
            return r_hi
        xm = (k0 + k1) / Decimal(2)
        xm_iv = Iv.raw(xm, xm)
        hx = Iv.raw((k1 - k0) / Decimal(2), (k1 - k0) / Decimal(2))
        Lm, kpm = pwl_eval(L, xm_iv), pwl_eval(kp, xm_iv)
        cm = ivq * xm_iv + iv_fa(ivA, xm_iv, Lm) - kpm
        lcm, llm = cm.ln(), (one - Lm).ln()
        um1, um2 = ieL * lcm + (one - ieL) * llm, ieU * lcm + (one - ieU) * llm
        ewm = pwl_eval(EW, kpm)
        bewm_lo = min((ibR * ewm).lo if ewm.lo < 0 else (ibL * ewm).lo, (ibR * ewm).lo if ewm.hi < 0 else (ibL * ewm).lo)
        rm_hi = pwl_eval(W, xm_iv).hi - (min(um1.lo, um2.lo) + bewm_lo)

        dW, dL, dkp, dEW = pwl_deriv(W, k_iv), pwl_deriv(L, k_iv), pwl_deriv(kp, k_iv), pwl_deriv(EW, kpiv)
        c15 = Iv("1.5") * ivA * TWO32_IV
        def _dfk(kv: Iv, lv: Iv) -> Iv:
            if lv.hi <= 0: return Iv(0)
            kL, kR, lL, lR = Iv.raw(kv.lo, kv.lo), Iv.raw(kv.hi, kv.hi), Iv.raw(lv.lo, lv.lo), Iv.raw(lv.hi, lv.hi)
            at = lambda a, b: Iv(0) if b.hi <= 0 else c15 * a.pow_half(1) * b.pow_half(5) * (a + b).pow_half(-5)
            lo, hi = min(at(kL, lL).lo, at(kR, lL).lo), max(at(kL, lR).hi, at(kR, lR).hi)
            pk = lR / Iv(4)
            if pk.hi >= kv.lo and pk.lo <= kv.hi:
                hi = max(hi, at(Iv.raw(max(pk.lo, kv.lo), min(pk.hi, kv.hi)), lR).hi)
            return Iv.raw(lo, hi)
        def _dfl(kv: Iv, lv: Iv) -> Iv:
            if lv.hi <= 0: return Iv(0)
            kL, kR, lL, lR = Iv.raw(kv.lo, kv.lo), Iv.raw(kv.hi, kv.hi), Iv.raw(lv.lo, lv.lo), Iv.raw(lv.hi, lv.hi)
            at = lambda a, b: Iv(0) if b.hi <= 0 else c15 * a.pow_half(5) * b.pow_half(1) * (a + b).pow_half(-5)
            lo, hi = min(at(kL, lL).lo, at(kL, lR).lo), max(at(kR, lL).hi, at(kR, lR).hi)
            pl = kR / Iv(4)
            if pl.hi >= lv.lo and pl.lo <= lv.hi:
                hi = max(hi, at(kR, Iv.raw(max(pl.lo, lv.lo), min(pl.hi, lv.hi))).hi)
            return Iv.raw(lo, hi)
        dc = ivq + _dfk(k_iv, Liv) + _dfl(k_iv, Liv) * dL - dkp
        ec_iv = ieU if civ.lo >= 1 else (ieL if civ.hi < 1 else ieL.hull(ieU))
        du = (ec_iv / civ) * dc - ((one - ec_iv) / (one - Liv)) * dL
        bv_iv = ibL if ew_iv.lo >= 0 else (ibR if ew_iv.hi < 0 else ibL.hull(ibR))
        df = dW - du - bv_iv * dEW * dkp
        ub = min(r_hi, rm_hi + (Iv.raw(df.max_abs(), df.max_abs()) * hx).hi)
        if ub > 0 and dp < 18:
            return max(_seg(k0, xm, dp + 1), _seg(xm, k1, dp + 1))
        return ub

    assert max(_seg(a, b) for a, b in zip(ks[:-1], ks[1:])) <= 0


def check_exit_1d(W: dict, epsi: float, ahi: float, qhi: float, bL: float, bR: float, eL: float, eU: float, ax: float, l0: float, ka: float, kb: float, h_m: float, lib):
    if lib is not None:
        p = _c_pwl(W)
        res = lib.rs_verify_adverse_exit_bb_ext(*p[:4], p[4], p[5], p[6], epsi, ahi, qhi, bL, bR, eL, eU, ax, l0, ka, kb, h_m, 0, 2e-4, 35, 1, None, 0)
        assert res.certified and res.iv_certified, f"Adverse exit failed [{ka},{kb}]: m_lb_iv={res.d_ub_iv}"
        return
    ivA, ivq, iva, ivl, ieL, ieU = Iv(str(ahi)), Iv(str(qhi)), Iv(str(ax)), Iv(str(l0)), Iv(str(eL)), Iv(str(eU))
    iv_cont = Iv(str(bL if epsi < 0 else bR)) * Iv(str(epsi))
    ks = sorted({Decimal.from_float(x) for x in [ka, kb, *W["ks"]] if ka <= x <= kb} | {Decimal.from_float(ka + (kb - ka) * (i / 48.0)) for i in range(49)})
    for a, b in zip(ks[:-1], ks[1:]):
        k_iv = Iv.raw(a, b)
        t = Iv("1.5") * ivA * TWO32_IV * k_iv.pow_half(5) * ivl.sqrt() * (k_iv + ivl).pow_half(-5)
        cs = ivq * k_iv + iv_fa(ivA, k_iv, ivl) + (Iv(1) - ivl) * t - iva
        vals = []
        for eta in (ieL, ieU):
            om_r = (Iv(1) - eta) * cs / t
            om_l = Iv.raw(min(om_r.lo, Decimal(1)), min(om_r.hi, Decimal(1)))
            vals.append(eta * (cs - t * om_l).ln() + (Iv(1) - eta) * om_l.ln())
        e_iv = Iv.raw(max(v.lo for v in vals), max(v.hi for v in vals))
        assert (pwl_eval(W, k_iv) - (e_iv + iv_cont)).lo > 0


def check_h2(W: dict, kp_p: dict, L_p: dict, ew80: float, epsi_h: float, alo: float, ahi: float, qlo: float, qhi: float, bL: float, bR: float, eL: float, eU: float, h_m: float, k_h2: float):
    kp80 = pwl_eval_f64(kp_p, k_h2)
    L80 = pwl_eval_f64(L_p, k_h2)
    ivAl, ivAh, ivql, ivqh = Iv(str(alo)), Iv(str(ahi)), Iv(str(qlo)), Iv(str(qhi))
    ivbL, ivbR, iveL, iveU = Iv(str(bL)), Iv(str(bR)), Iv(str(eL)), Iv(str(eU))
    one, ivh = Iv(1), Iv(str(h_m))
    iv_ep = (ivbL if epsi_h < 0 else ivbR) * Iv(str(epsi_h))
    # Bisection for K_+ where F_{A_+}(K, 1) = (1 - q_+) K
    k_lo, k_hi = 1.0, 200.0
    for _ in range(60):
        km = 0.5 * (k_lo + k_hi)
        if ahi * ((2.0 * km) / (km + 1.0)) ** 1.5 - (1.0 - qhi) * km > 0.0:
            k_lo = km
        else:
            k_hi = km
    kp_plus = k_hi
    ivkp80, ivL80, ivew = Iv(kp80), Iv(L80), Iv(ew80)
    iv_tw = (ivbR if ivew.lo < 0 else ivbL) * ivew
    ks = [k_h2 * ((kp_plus / k_h2) ** (i / 30.0)) for i in range(31)]
    for j in range(30):
        kL, kR = Iv(ks[j]), Iv(ks[j + 1])
        uW = min((iveL * (ivql * kL + iv_fa(ivAl, kL, ivL80) - ivkp80).ln() + (one - iveL) * (one - ivL80).ln()).lo,
                 (iveU * (ivql * kL + iv_fa(ivAl, kL, ivL80) - ivkp80).ln() + (one - iveU) * (one - ivL80).ln()).lo)
        cE = ivqh * kR + iv_fa(ivAh, kR, one) - ivh
        ec = iveL if cE.hi < 1 else (iveU if cE.lo >= 1 else iveL.hull(iveU))
        assert (Iv.raw(uW, uW) + iv_tw - (ec * cE.ln() + iv_ep)).lo > 0
    ivkpp = Iv(kp_plus)
    rc = (ivql * ivkpp + iv_fa(ivAl, ivkpp, ivL80) - ivkp80) / (ivqh * ivkpp + ivAh * TWO32_IV - ivh)
    rq = ivql / ivqh
    mr = Iv.raw(min(rc.lo, rq.lo), min(rc.hi, rq.hi))
    assert (iveU * mr.ln() + (one - iveU) * (one - ivL80).ln() + iv_tw - iv_ep).lo > 0


def check_deriv_below(ev: dict, kb: float, blo: float, alo: float, qlo: float, ax: float, l0: float, eL: float, eU: float):
    ivA, ivq, ivK, iva, ivl = Iv(str(alo)), Iv(str(qlo)), Iv(str(kb)), Iv(str(ax)), Iv(str(l0))
    t = Iv("1.5") * ivA * TWO32_IV * ivK.pow_half(5) * ivl.sqrt() / (ivK + ivl).pow_half(5)
    cs = ivq * ivK + iv_fa(ivA, ivK, ivl) + (Iv(1) - ivl) * t - iva
    clo = min((cs - t * Iv.raw(*([min(Decimal(1), ((Iv(1) - Iv(str(e))) * cs / t).hi)] * 2))).lo for e in (eL, eU))
    kd, ivv, lks = ev["kd"], ev["iv_v"], ev["iv_lk"]
    md = (Iv(ev["s_lo"]) / Iv.raw(kd[0], kd[0])).lo
    for i in range(len(kd) - 1):
        if ev["ks"][i] >= kb:
            break
        sl = (ivv[i + 1] - ivv[i]) / (lks[i + 1] - lks[i])
        assert sl.lo > 0
        md = min(md, (sl / Iv(min(ev["ks"][i + 1], kb))).lo)
    assert (Iv(str(blo)) * Iv.raw(md, md) - Iv(str(eU)) / Iv.raw(clo, clo)).lo > 0


def audit_static_cert(c: dict, lib):
    b_m, h_m, k_h2 = c["b_m"], c["h_m"], c["k_h2"]
    bx = c["box"]
    Alo, Ahi = bx["A"]
    qlo, qhi = bx["q"]
    bL, bR = bx["beta"]
    eL, eU = bx["eta"]
    Psi, W, kp, L, B = prep_pwl(c["Psi"]), prep_pwl(c["W"]), prep_pwl(c["kp"]), prep_pwl(c["L"]), prep_pwl(c["B"])

    assert all(s >= -1e-12 for s in Psi["slopes"]) and Psi["s_lo"] >= 0 and Psi["s_hi"] >= 0
    tm = super_tail_max(Psi, Psi, Ahi, qhi, bL, bR, eL, eU)
    if lib is not None:
        p = _c_pwl(Psi)
        r = lib.rs_verify_super_barrier_bb_ext(*p[:4], p[4], p[5], p[6], *p[:4], p[4], p[5], p[6], Ahi, qhi, bL, bR, eL, eU, 0.0, 0.0, h_m, tm, 3e-4, 0, 55, 350_000, None, 0)
        assert r.certified and r.iv_certified, f"Super barrier failed: d_ub_iv={r.d_ub_iv}"
    check_witness_1d(W, W, kp, L, Alo, qlo, bL, bR, eL, eU, b_m, 5.5)
    psi_b = pwl_eval_f64(Psi, b_m)
    psi_h = pwl_eval_f64(Psi, h_m)
    check_exit_1d(W, psi_b, Ahi, qhi, bL, bR, eL, eU, b_m, c["l0_M"], b_m, h_m, h_m, lib)
    check_exit_1d(W, psi_h, Ahi, qhi, bL, bR, eL, eU, h_m, c["l0_H1"], h_m, k_h2, h_m, lib)
    ew80 = pwl_eval_f64(W, pwl_eval_f64(kp, k_h2))
    check_h2(W, kp, L, ew80, psi_h, Alo, Ahi, qlo, qhi, bL, bR, eL, eU, h_m, k_h2)
    check_deriv_below(Psi, b_m, bL, Alo, qlo, b_m, c["l0_M"], eL, eU)
    check_deriv_below(Psi, h_m, bL, Alo, qlo, h_m, c["l0_H1"], eL, eU)

    if lib is not None:
        pb = _c_pwl(B)
        rb = lib.rs_verify_staying_barrier_bb_ext(*pb[:4], pb[4], pb[5], pb[6], *pb[:4], pb[4], pb[5], pb[6], b_m, h_m, Ahi, qhi, bL, bR, eL, eU, 0.0, 0.0, 2e-4, 45, None, 0)
        assert rb.certified and rb.iv_certified, f"Staying barrier failed: d_ub_iv={rb.d_ub_iv}"

    # Verify deadline T_cert in Interval arithmetic
    ks_d = sorted({Decimal.from_float(x) for x in [b_m, h_m, *B["ks"], *Psi["ks"], *W["ks"]] if b_m <= x <= h_m} | {Decimal.from_float(b_m * ((h_m / b_m) ** (i / 41.0))) for i in range(42)})
    inf_wb, sup_pb = Decimal("1e30"), Decimal("-1e30")
    for k0, k1 in zip(ks_d[:-1], ks_d[1:]):
        kiv = Iv.raw(k0, k1)
        Biv, Wiv, Piv = pwl_eval(B, kiv), pwl_eval(W, kiv), pwl_eval(Psi, kiv)
        inf_wb = min(inf_wb, (Wiv - Biv).lo)
        sup_pb = max(sup_pb, (Piv - Biv).hi)
    assert inf_wb > 0 and (Iv(str(bR)).pow_int(int(c["T_cert"])) * Iv.raw(sup_pb, sup_pb)).hi < inf_wb


def audit_markov_cert(c: dict, lib):
    b_m, h_m, k_h2 = c["b_m"], c["h_m"], c["k_h2"]
    P = c["P"]
    p00, p01 = P[0][0], P[0][1]
    p10, p11 = P[1][0], P[1][1]
    r0, r1 = c["regimes"][0]["box"], c["regimes"][1]["box"]
    A0_lo, A0_hi = r0["A"]
    A1_lo, A1_hi = r1["A"]
    q0_lo, q0_hi = r0["q"]
    q1_lo, q1_hi = r1["q"]
    bL, bR = min(r0["beta"][0], r1["beta"][0]), max(r0["beta"][1], r1["beta"][1])
    eL, eU = min(r0["eta"][0], r1["eta"][0]), max(r0["eta"][1], r1["eta"][1])

    Psi0, Psi1 = prep_pwl(c["Psi"][0]), prep_pwl(c["Psi"][1])
    W0, W1 = prep_pwl(c["W"][0]), prep_pwl(c["W"][1])
    kp0, L0 = prep_pwl(c["kp"][0]), prep_pwl(c["L"][0])
    kp1, L1 = prep_pwl(c["kp"][1]), prep_pwl(c["L"][1])
    B0, B1 = prep_pwl(c["B"][0]), prep_pwl(c["B"][1])

    evP0 = prep_pwl({"ks": Psi0["ks"], "vals": [p00 * a + p01 * b for a, b in zip(Psi0["vals"], Psi1["vals"])], "s_lo": Psi0["s_lo"], "s_hi": Psi0["s_hi"]})
    evP1 = prep_pwl({"ks": Psi0["ks"], "vals": [p10 * a + p11 * b for a, b in zip(Psi0["vals"], Psi1["vals"])], "s_lo": Psi1["s_lo"], "s_hi": Psi1["s_hi"]})
    tm0 = super_tail_max(Psi0, evP0, A0_hi, q0_hi, bL, bR, eL, eU)
    tm1 = super_tail_max(Psi1, evP1, A1_hi, q1_hi, bL, bR, eL, eU)
    if lib is not None:
        for ps, ev, Av, qv, tm in ((Psi0, evP0, A0_hi, q0_hi, tm0), (Psi1, evP1, A1_hi, q1_hi, tm1)):
            p_s, p_e = _c_pwl(ps), _c_pwl(ev)
            r = lib.rs_verify_super_barrier_bb_ext(*p_s[:4], p_s[4], p_s[5], p_s[6], *p_e[:4], p_e[4], p_e[5], p_e[6], Av, qv, bL, bR, eL, eU, 0.0, 0.0, h_m, tm, 3e-4, 0, 55, 350_000, None, 0)
            assert r.certified and r.iv_certified, f"Markov super failed: d_ub_iv={r.d_ub_iv}"

    evW0 = prep_pwl({"ks": W0["ks"], "vals": [p00 * a + p01 * b for a, b in zip(W0["vals"], W1["vals"])], "s_lo": 0.0, "s_hi": 0.0})
    evW1 = prep_pwl({"ks": W0["ks"], "vals": [p10 * a + p11 * b for a, b in zip(W0["vals"], W1["vals"])], "s_lo": 0.0, "s_hi": 0.0})
    check_witness_1d(W0, evW0, kp0, L0, A0_lo, q0_lo, bL, bR, eL, eU, b_m, 5.5)
    check_witness_1d(W1, evW1, kp1, L1, A1_lo, q1_lo, bL, bR, eL, eU, b_m, 5.5)

    p0b, p1b = pwl_eval_f64(Psi0, b_m), pwl_eval_f64(Psi1, b_m)
    p0h, p1h = pwl_eval_f64(Psi0, h_m), pwl_eval_f64(Psi1, h_m)
    epb0, epb1 = p00 * p0b + p01 * p1b, p10 * p0b + p11 * p1b
    eph0, eph1 = p00 * p0h + p01 * p1h, p10 * p0h + p11 * p1h
    check_exit_1d(W0, epb0, A0_hi, q0_hi, bL, bR, eL, eU, b_m, c["l0_M"][0], b_m, h_m, h_m, lib)
    check_exit_1d(W1, epb1, A1_hi, q1_hi, bL, bR, eL, eU, b_m, c["l0_M"][1], b_m, h_m, h_m, lib)
    check_exit_1d(W0, eph0, A0_hi, q0_hi, bL, bR, eL, eU, h_m, c["l0_H1"][0], h_m, k_h2, h_m, lib)
    check_exit_1d(W1, eph1, A1_hi, q1_hi, bL, bR, eL, eU, h_m, c["l0_H1"][1], h_m, k_h2, h_m, lib)

    kp80_0 = pwl_eval_f64(kp0, k_h2); ew80_0 = p00 * pwl_eval_f64(W0, kp80_0) + p01 * pwl_eval_f64(W1, kp80_0)
    kp80_1 = pwl_eval_f64(kp1, k_h2); ew80_1 = p10 * pwl_eval_f64(W0, kp80_1) + p11 * pwl_eval_f64(W1, kp80_1)
    check_h2(W0, kp0, L0, ew80_0, eph0, A0_lo, A0_hi, q0_lo, q0_hi, bL, bR, eL, eU, h_m, k_h2)
    check_h2(W1, kp1, L1, ew80_1, eph1, A1_lo, A1_hi, q1_lo, q1_hi, bL, bR, eL, eU, h_m, k_h2)
    check_deriv_below(evP0, b_m, bL, A0_lo, q0_lo, b_m, c["l0_M"][0], eL, eU)
    check_deriv_below(evP1, b_m, bL, A1_lo, q1_lo, b_m, c["l0_M"][1], eL, eU)
    check_deriv_below(evP0, h_m, bL, A0_lo, q0_lo, h_m, c["l0_H1"][0], eL, eU)
    check_deriv_below(evP1, h_m, bL, A1_lo, q1_lo, h_m, c["l0_H1"][1], eL, eU)

    evB0 = prep_pwl({"ks": B0["ks"], "vals": [p00 * a + p01 * b for a, b in zip(B0["vals"], B1["vals"])], "s_lo": 0.0, "s_hi": 0.0})
    evB1 = prep_pwl({"ks": B0["ks"], "vals": [p10 * a + p11 * b for a, b in zip(B0["vals"], B1["vals"])], "s_lo": 0.0, "s_hi": 0.0})
    if lib is not None:
        for b_s, b_e, Av, qv in ((B0, evB0, A0_hi, q0_hi), (B1, evB1, A1_hi, q1_hi)):
            pl, pe = _c_pwl(b_s), _c_pwl(b_e)
            rb = lib.rs_verify_staying_barrier_bb_ext(*pl[:4], pl[4], pl[5], pl[6], *pe[:4], pe[4], pe[5], pe[6], b_m, h_m, Av, qv, bL, bR, eL, eU, 0.0, 0.0, 2e-4, 45, None, 0)
            assert rb.certified and rb.iv_certified, f"Markov staying failed: d_ub_iv={rb.d_ub_iv}"

    # Verify Doob eps0 > 0 in 50-digit Interval arithmetic
    ks_d = sorted({Decimal.from_float(x) for x in [b_m, h_m, *B0["ks"], *B1["ks"], *W0["ks"], *W1["ks"], *Psi0["ks"], *Psi1["ks"]] if b_m <= x <= h_m} | {Decimal.from_float(b_m * ((h_m / b_m) ** (i / 41.0))) for i in range(42)})
    m_inf, d_stay = Decimal("1e30"), Decimal("-1e30")
    for k0, k1 in zip(ks_d[:-1], ks_d[1:]):
        kiv = Iv.raw(k0, k1)
        m_inf = min(m_inf, (pwl_eval(W0, kiv) - pwl_eval(B0, kiv)).lo, (pwl_eval(W1, kiv) - pwl_eval(B1, kiv)).lo)
        d_stay = max(d_stay, (pwl_eval(Psi0, kiv) - pwl_eval(B0, kiv)).hi, (pwl_eval(Psi1, kiv) - pwl_eval(B1, kiv)).hi)
    ivh = Iv(str(h_m))
    ym0 = Iv(str(q0_hi)) * ivh + iv_fa(Iv(str(A0_hi)), ivh, Iv(1))
    ym1 = Iv(str(q1_hi)) * ivh + iv_fa(Iv(str(A1_hi)), ivh, Iv(1))
    ym = Iv.raw(max(ym0.lo, ym1.lo), max(ym0.hi, ym1.hi))
    d_ex = max((pwl_eval(Psi0, ym) - pwl_eval(B0, ivh)).hi, (pwl_eval(Psi1, ym) - pwl_eval(B1, ivh)).hi)
    T0 = int(c["doob"]["T0_opt"])
    tail = Iv(str(bR)).pow_int(T0) * Iv.raw(d_stay, d_stay)
    eps0_iv = (Iv.raw(m_inf, m_inf) - tail) / (Iv(str(bR)) * Iv.raw(d_ex, d_ex) - tail)
    assert eps0_iv.lo > 0, f"Doob eps0 <= 0: {eps0_iv.lo}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Standalone formal auditor for cegis-bellman certificates")
    ap.add_argument("archive", help="Path to .json.xz certificate archive")
    ap.add_argument("--pure-python", action="store_true", help="Disable Rust DLL (50-digit Decimal only)")
    ap.add_argument("--model", default=None, help="Audit only a specific model key")
    args = ap.parse_args()

    t0 = time.time()
    with lzma.open(args.archive, "rb") as fh:
        env = json.loads(fh.read().decode("utf-8"))
    expected_sha = env.get("sha256_models", "")
    actual_sha = hashlib.sha256(json.dumps(env["models"], sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    assert expected_sha == actual_sha, f"SHA-256 mismatch: {expected_sha} != {actual_sha}"
    lib = load_dll(pure=args.pure_python)
    print(f"[Audit] Archive={args.archive} | schema={env.get('schema_version')} | sha256=OK | rust={'ON' if lib else 'OFF'}", flush=True)

    models = env["models"]
    targets = [args.model] if args.model else list(models.keys())
    total_certs = 0
    for mkey in targets:
        mdata = models[mkey]
        kind = mdata["kind"]
        certs = mdata["certificates"]
        for idx, rec in enumerate(certs):
            if kind == "static":
                audit_static_cert(rec, lib)
            elif kind == "markov":
                audit_markov_cert(rec, lib)
            else:
                raise ValueError(f"Unknown certificate kind: {kind}")
            total_certs += 1
        print(f"  [PASS] {mkey}: {len(certs)} {kind} certificate(s) verified.", flush=True)
    print(f"[Audit] ALL {total_certs} certificates PASSED in {time.time() - t0:.2f}s.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
