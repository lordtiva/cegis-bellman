"""
Two-Layer Outward-Rounded Interval Arithmetic, Policy Mappers & Audit Kernels:
  1. 50-digit Decimal `Interval` (ROUND_FLOOR / ROUND_CEILING, libm-free ln() via
     MR Lemma 11) for all analytical proofs, 1D B&B audits, derivatives, tails,
     and institutional policy-box mappings (tau_p, tau_u, N_f, g) -> (A_tilde, q_tilde).
  2. Numba-compiled IEEE-754 outward-rounded interval arithmetic (`np.nextafter`)
     for Python-fallback 3D leaf-box auditing when the native Rust library is absent.
"""

from __future__ import annotations

from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
import math
from typing import Dict, Tuple
import numpy as np
from numba import njit


# ---------------------------------------------------------------------------
# Canonical MVS / Institutional Base Constants
# ---------------------------------------------------------------------------
CANONICAL_A = (0.749, 0.751)
CANONICAL_BETA = (0.9699, 0.9701)
CANONICAL_Q = (0.9199, 0.9201)
CANONICAL_ETA = (0.6999, 0.7001)
CANONICAL_BM = 0.10
CANONICAL_HM = 0.28

Q_POINT = 0.92
BETA_POINT = 0.97
ETA_POINT = 0.70
THETA_POINT = 1.5


# ---------------------------------------------------------------------------
# Standard float64 Model Primitives (used only in float64 B&B pruning / VFI)
# ---------------------------------------------------------------------------
def F_A(A: float, K, L):
    """CES production with theta = 3/2, rho = -1, w = 1/2: A * (2KL/(K+L))^(3/2)."""
    L_arr = np.asarray(L, dtype=np.float64) if not np.isscalar(L) else L
    if np.isscalar(L):
        if L <= 0.0:
            return 0.0 * np.asarray(K, dtype=np.float64) if not np.isscalar(K) else 0.0
        return A * ((2.0 * K * L) / (K + L)) ** 1.5
    safe_L = np.maximum(L_arr, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(safe_L > 0.0, (2.0 * K * safe_L) / np.maximum(K + safe_L, 1e-300), 0.0)
    return np.where(safe_L > 0.0, A * (ratio ** 1.5), 0.0)


def dF_dK(A: float, K, L):
    if np.isscalar(L) and L <= 0.0:
        return 0.0 * np.asarray(K, dtype=np.float64) if not np.isscalar(K) else 0.0
    return 1.5 * A * (2.0 ** 1.5) * (K ** 0.5) * (L ** 2.5) * ((K + L) ** (-2.5))


def dF_dL(A: float, K, L):
    if np.isscalar(L) and L <= 0.0:
        return 0.0 * np.asarray(K, dtype=np.float64) if not np.isscalar(K) else 0.0
    return 1.5 * A * (2.0 ** 1.5) * (K ** 2.5) * (L ** 0.5) * ((K + L) ** (-2.5))


def box_worst_u(c, L, e_lo: float = CANONICAL_ETA[0], e_hi: float = CANONICAL_ETA[1]):
    lc = np.log(c)
    ll = np.log(1.0 - L)
    u1 = e_lo * lc + (1.0 - e_lo) * ll
    u2 = e_hi * lc + (1.0 - e_hi) * ll
    return np.minimum(u1, u2)


def E_plus_exact(
    A_hi: float,
    q_hi: float,
    K: float,
    a: float,
    l0: float,
    e_lo: float = CANONICAL_ETA[0],
    e_hi: float = CANONICAL_ETA[1],
    h_m: float = CANONICAL_HM,
    ak_mode: bool = False,
) -> float:
    """Exact tangent adverse-exit envelope max_{eta in [e_lo, e_hi]} E^+(K, a; l0)."""
    if not ak_mode or K <= h_m:
        t = float(dF_dL(A_hi, K, l0))
        S = q_hi * K + float(F_A(A_hi, K, l0)) + (1.0 - l0) * t
    else:
        t = (K / h_m) * float(dF_dL(A_hi, h_m, l0))
        S = q_hi * K + (K / h_m) * float(F_A(A_hi, h_m, l0)) + (1.0 - l0) * t
    c_sup = S - a
    vals = []
    for eta in (e_lo, e_hi):
        om_L = min(1.0, (1.0 - eta) * c_sup / t)
        c_opt = c_sup - t * om_L
        vals.append(eta * math.log(c_opt) + (1.0 - eta) * math.log(om_L))
    return max(vals)


# ---------------------------------------------------------------------------
# Layer 1: 50-digit Outward-Rounded Decimal Interval Arithmetic (zero libm)
# ---------------------------------------------------------------------------
class Interval:
    """Outward-rounded closed interval [lo, hi] using 50-digit Decimal arithmetic."""

    PREC = 50

    def __init__(self, lo, hi=None):
        if isinstance(lo, Interval) and hi is None:
            self.lo, self.hi = lo.lo, lo.hi
            return
        if hi is None:
            hi = lo
        self.lo = self._to_dec(lo, ROUND_FLOOR)
        self.hi = self._to_dec(hi, ROUND_CEILING)
        assert self.lo <= self.hi, f"Invalid interval [{self.lo}, {self.hi}]"

    @classmethod
    def _to_dec(cls, x, rounding):
        with localcontext() as ctx:
            ctx.prec = cls.PREC
            ctx.rounding = rounding
            if isinstance(x, Decimal):
                return +x
            if isinstance(x, int):
                return Decimal(x)
            if isinstance(x, str):
                return +Decimal(x)
            return +Decimal.from_float(float(x))

    @classmethod
    def _raw(cls, lo: Decimal, hi: Decimal) -> "Interval":
        obj = cls.__new__(cls)
        obj.lo = lo
        obj.hi = hi
        return obj

    def __repr__(self) -> str:
        return f"Interval({self.lo}, {self.hi})"

    def __add__(self, other):
        o = other if isinstance(other, Interval) else Interval(other)
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo = self.lo + o.lo
            ctx.rounding = ROUND_CEILING
            hi = self.hi + o.hi
        return Interval._raw(lo, hi)

    def __radd__(self, other):
        return self.__add__(other)

    def __neg__(self):
        return Interval._raw(-self.hi, -self.lo)

    def __sub__(self, other):
        o = other if isinstance(other, Interval) else Interval(other)
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo = self.lo - o.hi
            ctx.rounding = ROUND_CEILING
            hi = self.hi - o.lo
        return Interval._raw(lo, hi)

    def __rsub__(self, other):
        o = other if isinstance(other, Interval) else Interval(other)
        return o.__sub__(self)

    def __mul__(self, other):
        o = other if isinstance(other, Interval) else Interval(other)
        pairs = [(self.lo, o.lo), (self.lo, o.hi), (self.hi, o.lo), (self.hi, o.hi)]
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo = min(a * b for a, b in pairs)
            ctx.rounding = ROUND_CEILING
            hi = max(a * b for a, b in pairs)
        return Interval._raw(lo, hi)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        o = other if isinstance(other, Interval) else Interval(other)
        if o.lo <= 0 <= o.hi:
            raise ZeroDivisionError("Interval divisor spans zero")
        pairs = [(self.lo, o.lo), (self.lo, o.hi), (self.hi, o.lo), (self.hi, o.hi)]
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo = min(a / b for a, b in pairs)
            ctx.rounding = ROUND_CEILING
            hi = max(a / b for a, b in pairs)
        return Interval._raw(lo, hi)

    def __rtruediv__(self, other):
        o = other if isinstance(other, Interval) else Interval(other)
        return o.__truediv__(self)

    def sqrt(self) -> "Interval":
        assert self.lo >= 0
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo = self.lo.sqrt()
            ctx.rounding = ROUND_CEILING
            hi = self.hi.sqrt()
        return Interval._raw(lo, hi)

    def ln(self) -> "Interval":
        assert self.lo > 0
        lo = self._ln_pt(self.lo, is_hi=False)
        hi = self._ln_pt(self.hi, is_hi=True)
        return Interval._raw(lo, hi)

    def exp(self) -> "Interval":
        """Outward-rounded exponential via Decimal.exp() in high precision."""
        with localcontext() as ctx:
            ctx.prec = self.PREC + 10
            ctx.rounding = ROUND_FLOOR
            lo = self.lo.exp()
            ctx.rounding = ROUND_CEILING
            hi = self.hi.exp()
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo_r = +lo
            ctx.rounding = ROUND_CEILING
            hi_r = +hi
        return Interval._raw(lo_r, hi_r)

    def pow_rat(self, num: int, den: int) -> "Interval":
        """Outward-rounded rational power x^(num/den) for x > 0 and den > 0."""
        assert den > 0
        if num == 0:
            return Interval("1")
        if den == 1 and num >= 0:
            return self.pow_int(num)
        if den == 2:
            return self.pow_half_int(num)
        # x^(num/den) = exp((num/den) * ln(x))
        assert self.lo > 0
        r = Interval(num) / Interval(den)
        return (r * self.ln()).exp()

    @classmethod
    def _ln_lemma11_series(cls, m_lo: Decimal, m_hi: Decimal, n_terms: int = 55) -> Tuple[Decimal, Decimal]:
        """MR Lemma 11 (Eq. F.5) rational enclosure of log(m) for 1 <= m_lo <= m_hi <= 2."""
        with localcontext() as ctx:
            ctx.prec = cls.PREC + 12
            one = Decimal(1)
            two = Decimal(2)
            ctx.rounding = ROUND_FLOOR
            v_lo = (m_lo - one) / (m_lo + one)
            v2_lo = v_lo * v_lo
            term_lo = v_lo
            s_lo = v_lo
            for j in range(1, n_terms):
                term_lo = term_lo * v2_lo
                s_lo = s_lo + term_lo / Decimal(2 * j + 1)
            if v_lo >= Decimal(0):
                out_lo = two * s_lo
            else:
                ctx.rounding = ROUND_CEILING
                av_lo = -v_lo
                av2_lo = av_lo * av_lo
                av_tail = av_lo ** (2 * n_terms + 1)
                ctx.rounding = ROUND_FLOOR
                den_lo = Decimal(2 * n_terms + 1) * (one - av2_lo)
                ctx.rounding = ROUND_CEILING
                rem_lo = (two * av_tail) / den_lo
                ctx.rounding = ROUND_FLOOR
                out_lo = two * s_lo - rem_lo

            ctx.rounding = ROUND_CEILING
            v_hi = (m_hi - one) / (m_hi + one)
            v2_hi = v_hi * v_hi
            term_hi = v_hi
            s_hi = v_hi
            for j in range(1, n_terms):
                term_hi = term_hi * v2_hi
                s_hi = s_hi + term_hi / Decimal(2 * j + 1)
            v_tail = term_hi * v2_hi
            ctx.rounding = ROUND_FLOOR
            one_m_v2 = one - v2_hi
            ctx.rounding = ROUND_CEILING
            rem = (two * v_tail) / (Decimal(2 * n_terms + 1) * one_m_v2)
            out_hi = two * s_hi + rem
        return out_lo, out_hi

    @classmethod
    def _get_ln2_bounds(cls) -> Tuple[Decimal, Decimal]:
        bounds = getattr(cls, "_LN2_BOUNDS", None)
        if bounds is None:
            bounds = cls._ln_lemma11_series(Decimal(2), Decimal(2), n_terms=60)
            cls._LN2_BOUNDS = bounds
        return bounds

    @classmethod
    def _ln_pt(cls, x: Decimal, is_hi: bool) -> Decimal:
        if x == Decimal(1):
            return Decimal(0)
        with localcontext() as ctx:
            ctx.prec = cls.PREC + 12
            two = Decimal(2)
            if x >= Decimal(1):
                k = max(0, int(x).bit_length() - 1)
                pow2 = two ** k
                ctx.rounding = ROUND_FLOOR
                m_lo = x / pow2
                ctx.rounding = ROUND_CEILING
                m_hi = x / pow2
                while m_lo >= two:
                    k += 1
                    pow2 *= two
                    ctx.rounding = ROUND_FLOOR
                    m_lo = x / pow2
                    ctx.rounding = ROUND_CEILING
                    m_hi = x / pow2
                while m_hi < Decimal(1):
                    k -= 1
                    pow2 //= two
                    ctx.rounding = ROUND_FLOOR
                    m_lo = x / pow2
                    ctx.rounding = ROUND_CEILING
                    m_hi = x / pow2
            else:
                ctx.rounding = ROUND_CEILING
                inv_x = Decimal(1) / x
                k = -int(inv_x).bit_length()
                pow2 = two ** (-k)
                ctx.rounding = ROUND_FLOOR
                m_lo = x * pow2
                ctx.rounding = ROUND_CEILING
                m_hi = x * pow2
                while m_hi < Decimal(1):
                    k -= 1
                    pow2 *= two
                    ctx.rounding = ROUND_FLOOR
                    m_lo = x * pow2
                    ctx.rounding = ROUND_CEILING
                    m_hi = x * pow2
                while m_lo >= two:
                    k += 1
                    pow2 //= two
                    ctx.rounding = ROUND_FLOOR
                    m_lo = x * pow2
                    ctx.rounding = ROUND_CEILING
                    m_hi = x * pow2

            ln_m_lo, ln_m_hi = cls._ln_lemma11_series(m_lo, m_hi, n_terms=55)
            ln2_lo, ln2_hi = cls._get_ln2_bounds()
            kd = Decimal(k)
            if is_hi:
                ctx.rounding = ROUND_CEILING
                k_term = kd * (ln2_hi if k >= 0 else ln2_lo)
                val = k_term + ln_m_hi
            else:
                ctx.rounding = ROUND_FLOOR
                k_term = kd * (ln2_lo if k >= 0 else ln2_hi)
                val = k_term + ln_m_lo
        with localcontext() as ctx:
            ctx.prec = cls.PREC
            ctx.rounding = ROUND_CEILING if is_hi else ROUND_FLOOR
            return +val

    def pow_int(self, n: int) -> "Interval":
        assert isinstance(n, int) and n >= 0
        if n == 0:
            return Interval("1")
        if n == 1:
            return self
        if n % 2 == 0 and self.lo <= 0 <= self.hi:
            with localcontext() as ctx:
                ctx.prec = self.PREC
                ctx.rounding = ROUND_CEILING
                return Interval._raw(Decimal(0), max(abs(self.lo), abs(self.hi)) ** n)
        if n % 2 == 0 and self.hi < 0:
            with localcontext() as ctx:
                ctx.prec = self.PREC
                ctx.rounding = ROUND_FLOOR
                lo = self.hi ** n
                ctx.rounding = ROUND_CEILING
                hi = self.lo ** n
            return Interval._raw(lo, hi)
        with localcontext() as ctx:
            ctx.prec = self.PREC
            ctx.rounding = ROUND_FLOOR
            lo = self.lo ** n
            ctx.rounding = ROUND_CEILING
            hi = self.hi ** n
        return Interval._raw(min(lo, hi), max(lo, hi))

    def pow_half_int(self, num_halves: int) -> "Interval":
        if num_halves == 0:
            return Interval("1")
        k = abs(num_halves)
        p = self.pow_int(k // 2) if k % 2 == 0 else self.pow_int(k).sqrt()
        return p if num_halves > 0 else Interval("1") / p

    def abs(self) -> "Interval":
        if self.lo >= 0:
            return self
        if self.hi <= 0:
            return -self
        return Interval._raw(Decimal(0), max(-self.lo, self.hi))

    def max_abs(self) -> Decimal:
        return max(abs(self.lo), abs(self.hi))

    def hull(self, other) -> "Interval":
        o = other if isinstance(other, Interval) else Interval(other)
        return Interval._raw(min(self.lo, o.lo), max(self.hi, o.hi))

    def to_float_bounds(self) -> Tuple[float, float]:
        lo_f = float(self.lo)
        if Decimal.from_float(lo_f) > self.lo:
            lo_f = math.nextafter(lo_f, -math.inf)
        hi_f = float(self.hi)
        if Decimal.from_float(hi_f) < self.hi:
            hi_f = math.nextafter(hi_f, math.inf)
        return lo_f, hi_f


# ---------------------------------------------------------------------------
# Institutional Policy-to-Model Conservative Interval Mappers
# ---------------------------------------------------------------------------
def iv_effective_A(
    A0: float,
    alpha_num: int,
    alpha_den: int,
    tau_p_iv: Interval,
    tau_u_iv: Interval,
    nf_iv: Interval = Interval("1"),
    g_iv: Interval = Interval("0"),
    theta_num: int = 3,
    theta_den: int = 2,
) -> Interval:
    """
    Outward-rounded enclosure of:
      A_tilde(tau_p, tau_u, N_f, g) = A0 * tau_p^alpha * (1 - tau_p - tau_u) * N_f^{-(theta-1)} / (1 + g).
    Evaluates the concave/unimodal factor tau_p^alpha * (1 - tau_p - tau_u) tightly by
    splitting at the interior maximizer tau_p^* = gamma * (1 - tau_u), where gamma = alpha / (1 + alpha).
    """
    assert tau_p_iv.lo > 0 and nf_iv.lo >= 1 and (Interval("1") + g_iv).lo > 0
    one = Interval("1")
    iv_A0 = Interval(str(A0))
    # Exact gamma = alpha / (1 + alpha)
    iv_gamma = Interval(alpha_num) / Interval(alpha_num + alpha_den)

    def _f_tau_pt(tp_iv: Interval, tu_pt: Interval) -> Interval:
        net = one - tp_iv - tu_pt
        assert net.lo > 0, f"Infeasible tax/waste box: 1 - tau_p - tau_u <= 0 ({net})"
        return tp_iv.pow_rat(alpha_num, alpha_den) * net

    # Monotone decreasing in tau_u: max at tau_u.lo, min at tau_u.hi
    tu_lo_iv = Interval._raw(tau_u_iv.lo, tau_u_iv.lo)
    tu_hi_iv = Interval._raw(tau_u_iv.hi, tau_u_iv.hi)
    tp_lo_iv = Interval._raw(tau_p_iv.lo, tau_p_iv.lo)
    tp_hi_iv = Interval._raw(tau_p_iv.hi, tau_p_iv.hi)

    # Lower bound over tau_p in [tp_lo, tp_hi] at worst tau_u = tu_hi (quasiconcave -> min at endpoints)
    f_min_lo = _f_tau_pt(tp_lo_iv, tu_hi_iv)
    f_min_hi = _f_tau_pt(tp_hi_iv, tu_hi_iv)
    f_lo = min(f_min_lo.lo, f_min_hi.lo)

    # Upper bound over tau_p in [tp_lo, tp_hi] at best tau_u = tu_lo (peak at tau_p^* = gamma * (1 - tu_lo))
    tp_star = iv_gamma * (one - tu_lo_iv)
    f_max_candidates = [_f_tau_pt(tp_lo_iv, tu_lo_iv).hi, _f_tau_pt(tp_hi_iv, tu_lo_iv).hi]
    if tp_star.hi >= tau_p_iv.lo and tp_star.lo <= tau_p_iv.hi:
        tp_star_clip = Interval._raw(max(tp_star.lo, tau_p_iv.lo), min(tp_star.hi, tau_p_iv.hi))
        f_max_candidates.append(_f_tau_pt(tp_star_clip, tu_lo_iv).hi)
    f_hi = max(f_max_candidates)
    f_iv = Interval._raw(f_lo, f_hi)

    # N_f^-(theta - 1) and 1 / (1 + g)
    exp_num = theta_num - theta_den
    nf_factor = Interval("1") / nf_iv.pow_rat(exp_num, theta_den) if exp_num != 0 else Interval("1")
    return iv_A0 * f_iv * nf_factor / (one + g_iv)


def iv_effective_q(q_iv: Interval, g_iv: Interval) -> Interval:
    """Outward-rounded enclosure of q_tilde = q / (1 + g)."""
    one = Interval("1")
    assert (one + g_iv).lo > 0
    return q_iv / (one + g_iv)


# ---------------------------------------------------------------------------
# CES Interval Evaluators
# ---------------------------------------------------------------------------
def iv_F_A(A: Interval, K: Interval, L: Interval) -> Interval:
    if L.hi <= 0:
        return Interval("0")
    A_lo = Interval._raw(A.lo, A.lo)
    A_hi = Interval._raw(A.hi, A.hi)
    K_lo = Interval._raw(K.lo, K.lo)
    K_hi = Interval._raw(K.hi, K.hi)
    L_lo = Interval._raw(L.lo, L.lo)
    L_hi = Interval._raw(L.hi, L.hi)

    def _pt(ap: Interval, kp: Interval, lp: Interval) -> Interval:
        if lp.hi <= 0:
            return Interval("0")
        return ap * (Interval("2") * kp * lp / (kp + lp)).pow_half_int(3)

    return Interval._raw(_pt(A_lo, K_lo, L_lo).lo, _pt(A_hi, K_hi, L_hi).hi)


def iv_prod_Y(A_iv: Interval, K_iv: Interval, L_iv: Interval, h_m: float = CANONICAL_HM, ak_mode: bool = False) -> Interval:
    if not ak_mode:
        return iv_F_A(A_iv, K_iv, L_iv)
    h_iv = Interval(str(h_m))
    A_lo = Interval._raw(A_iv.lo, A_iv.lo)
    A_hi = Interval._raw(A_iv.hi, A_iv.hi)
    K_lo = Interval._raw(K_iv.lo, K_iv.lo)
    K_hi = Interval._raw(K_iv.hi, K_iv.hi)
    L_lo = Interval._raw(L_iv.lo, L_iv.lo)
    L_hi = Interval._raw(L_iv.hi, L_iv.hi)

    def _pt(ap: Interval, kp: Interval, lp: Interval) -> Interval:
        if kp.hi <= h_iv.lo:
            return iv_F_A(ap, kp, lp)
        return (kp / h_iv) * iv_F_A(ap, h_iv, lp)

    return Interval._raw(_pt(A_lo, K_lo, L_lo).lo, _pt(A_hi, K_hi, L_hi).hi)


def iv_dF_dK(A_iv: Interval, K_iv: Interval, L_iv: Interval) -> Interval:
    two_3_2 = Interval("2").pow_half_int(3)
    c15 = Interval("1.5") * A_iv * two_3_2

    def _at_k(k_pt: Interval, l_pt: Interval) -> Interval:
        if l_pt.hi <= 0:
            return Interval("0")
        return c15 * k_pt.pow_half_int(1) * l_pt.pow_half_int(5) * (k_pt + l_pt).pow_half_int(-5)

    L_lo = Interval._raw(L_iv.lo, L_iv.lo)
    L_hi = Interval._raw(L_iv.hi, L_iv.hi)
    K_lo = Interval._raw(K_iv.lo, K_iv.lo)
    K_hi = Interval._raw(K_iv.hi, K_iv.hi)

    lo = min(_at_k(K_lo, L_lo).lo, _at_k(K_hi, L_lo).lo)
    hi = max(_at_k(K_lo, L_hi).hi, _at_k(K_hi, L_hi).hi)
    kp_iv = L_hi / Interval("4")
    if kp_iv.hi >= K_iv.lo and kp_iv.lo <= K_iv.hi:
        kp_clipped = Interval._raw(max(kp_iv.lo, K_iv.lo), min(kp_iv.hi, K_iv.hi))
        hi = max(hi, _at_k(kp_clipped, L_hi).hi)
    return Interval._raw(lo, hi)


def iv_dF_dL(A_iv: Interval, K_iv: Interval, L_iv: Interval) -> Interval:
    two_3_2 = Interval("2").pow_half_int(3)
    c15 = Interval("1.5") * A_iv * two_3_2

    def _at_kl(k_pt: Interval, l_pt: Interval) -> Interval:
        if l_pt.hi <= 0:
            return Interval("0")
        return c15 * k_pt.pow_half_int(5) * l_pt.pow_half_int(1) * (k_pt + l_pt).pow_half_int(-5)

    L_lo = Interval._raw(L_iv.lo, L_iv.lo)
    L_hi = Interval._raw(L_iv.hi, L_iv.hi)
    K_lo = Interval._raw(K_iv.lo, K_iv.lo)
    K_hi = Interval._raw(K_iv.hi, K_iv.hi)

    lo = min(_at_kl(K_lo, L_lo).lo, _at_kl(K_lo, L_hi).lo)
    hi = max(_at_kl(K_hi, L_lo).hi, _at_kl(K_hi, L_hi).hi)
    lp_iv = K_hi / Interval("4")
    if lp_iv.hi >= L_iv.lo and lp_iv.lo <= L_iv.hi:
        lp_clipped = Interval._raw(max(lp_iv.lo, L_iv.lo), min(lp_iv.hi, L_iv.hi))
        hi = max(hi, _at_kl(K_hi, lp_clipped).hi)
    return Interval._raw(lo, hi)


def iv_prod_dY_dK(A_iv: Interval, K_iv: Interval, L_iv: Interval, h_m: float = CANONICAL_HM, ak_mode: bool = False) -> Interval:
    if not ak_mode:
        return iv_dF_dK(A_iv, K_iv, L_iv)
    h_iv = Interval(str(h_m))
    if K_iv.hi <= h_iv.lo:
        return iv_dF_dK(A_iv, K_iv, L_iv)
    ak_iv = iv_F_A(A_iv, h_iv, L_iv) / h_iv
    if K_iv.lo >= h_iv.hi:
        return ak_iv
    return iv_dF_dK(A_iv, K_iv, L_iv).hull(ak_iv)


def iv_prod_dY_dL(A_iv: Interval, K_iv: Interval, L_iv: Interval, h_m: float = CANONICAL_HM, ak_mode: bool = False) -> Interval:
    if not ak_mode:
        return iv_dF_dL(A_iv, K_iv, L_iv)
    h_iv = Interval(str(h_m))
    if K_iv.hi <= h_iv.lo:
        return iv_dF_dL(A_iv, K_iv, L_iv)
    ak_iv = (K_iv / h_iv) * iv_dF_dL(A_iv, h_iv, L_iv)
    if K_iv.lo >= h_iv.hi:
        return ak_iv
    return iv_dF_dL(A_iv, K_iv, L_iv).hull(ak_iv)


def iv_box_worst_u(c: Interval, L: Interval, e_lo: Interval, e_hi: Interval) -> Interval:
    one = Interval("1")
    lc = c.ln()
    ll = (one - L).ln()
    u1 = e_lo * lc + (one - e_lo) * ll
    u2 = e_hi * lc + (one - e_hi) * ll
    return Interval._raw(min(u1.lo, u2.lo), min(u1.hi, u2.hi))


def iv_E_plus_exact(
    A_hi: Interval,
    q_hi: Interval,
    K: Interval,
    a: Interval,
    l0: Interval,
    e_lo: Interval,
    e_hi: Interval,
    h_m: float = CANONICAL_HM,
    ak_mode: bool = False,
) -> Interval:
    one = Interval("1")
    h_iv = Interval(str(h_m))
    two_3_2 = Interval("2").pow_half_int(3)
    if not ak_mode or K.hi <= h_iv.lo:
        t = Interval("1.5") * A_hi * two_3_2 * K.pow_half_int(5) * l0.pow_half_int(1) * (K + l0).pow_half_int(-5)
        S = q_hi * K + iv_F_A(A_hi, K, l0) + (one - l0) * t
    elif K.lo >= h_iv.hi:
        t_h = Interval("1.5") * A_hi * two_3_2 * h_iv.pow_half_int(5) * l0.pow_half_int(1) * (h_iv + l0).pow_half_int(-5)
        F_h = iv_F_A(A_hi, h_iv, l0)
        t = (K / h_iv) * t_h
        S = q_hi * K + (K / h_iv) * F_h + (one - l0) * t
    else:
        raise ValueError("K interval crosses h_m in AK mode")
    c_sup = S - a
    vals = []
    for eta in (e_lo, e_hi):
        om_raw = (one - eta) * c_sup / t
        om_L = Interval._raw(min(om_raw.lo, Decimal(1)), min(om_raw.hi, Decimal(1)))
        c_opt = c_sup - t * om_L
        vals.append(eta * c_opt.ln() + (one - eta) * om_L.ln())
    return Interval._raw(max(v.lo for v in vals), max(v.hi for v in vals))


def iv_dE_plus_dK(
    A_hi: Interval,
    q_hi: Interval,
    K: Interval,
    a: Interval,
    l0: Interval,
    e_lo: Interval,
    e_hi: Interval,
    h_m: float = CANONICAL_HM,
    ak_mode: bool = False,
) -> Interval:
    one = Interval("1")
    h_iv = Interval(str(h_m))
    two_3_2 = Interval("2").pow_half_int(3)
    if not ak_mode or K.hi <= h_iv.lo:
        K_lo = Interval._raw(K.lo, K.lo)
        K_hi = Interval._raw(K.hi, K.hi)
        t_at_lo = Interval("1.5") * A_hi * two_3_2 * K_lo.pow_half_int(5) * l0.pow_half_int(1) * (K_lo + l0).pow_half_int(-5)
        t_at_hi = Interval("1.5") * A_hi * two_3_2 * K_hi.pow_half_int(5) * l0.pow_half_int(1) * (K_hi + l0).pow_half_int(-5)
        t_iv = Interval._raw(t_at_lo.lo, t_at_hi.hi)
        S_at_lo = q_hi * K_lo + iv_F_A(A_hi, K_lo, l0) + (one - l0) * t_at_lo
        S_at_hi = q_hi * K_hi + iv_F_A(A_hi, K_hi, l0) + (one - l0) * t_at_hi
        c_sup_iv = Interval._raw((S_at_lo - a).lo, (S_at_hi - a).hi)

        def _t_prime(k_pt: Interval) -> Interval:
            t_k = Interval("1.5") * A_hi * two_3_2 * k_pt.pow_half_int(5) * l0.pow_half_int(1) * (k_pt + l0).pow_half_int(-5)
            return t_k * (Interval("2.5") * l0) / (k_pt * (k_pt + l0))

        tp_lo = min(_t_prime(K_lo).lo, _t_prime(K_hi).lo)
        tp_hi = max(_t_prime(K_lo).hi, _t_prime(K_hi).hi)
        kp_tp = Decimal("0.75") * l0.lo
        if K.lo <= kp_tp <= K.hi:
            tp_hi = max(tp_hi, _t_prime(Interval._raw(kp_tp, kp_tp)).hi)
        tp_iv = Interval._raw(tp_lo, tp_hi)
        Sp_iv = q_hi + iv_dF_dK(A_hi, K, l0) + (one - l0) * tp_iv

        om_max_iv = (one - e_lo) * c_sup_iv / t_iv
        if om_max_iv.hi < Decimal("1"):
            t_log_d = (Interval("2.5") * l0) / (K * (K + l0))
            d1 = Sp_iv / c_sup_iv - (one - e_lo) * t_log_d
            d2 = Sp_iv / c_sup_iv - (one - e_hi) * t_log_d
            return d1.hull(d2)

        d_vals = []
        for eta_pt in (e_lo, e_hi):
            om_raw = (one - eta_pt) * c_sup_iv / t_iv
            om_clamped = Interval._raw(min(max(om_raw.lo, Decimal(0)), Decimal(1)),
                                       min(max(om_raw.hi, Decimal(0)), Decimal(1)))
            c_opt_use = (
                eta_pt * c_sup_iv if om_raw.hi <= Decimal(1)
                else (c_sup_iv - t_iv if om_raw.lo >= Decimal(1)
                      else (eta_pt * c_sup_iv).hull(c_sup_iv - t_iv))
            )
            d_vals.append(eta_pt * (Sp_iv - tp_iv * om_clamped) / c_opt_use)
        return d_vals[0].hull(d_vals[1])

    elif K.lo >= h_iv.hi:
        t_h = Interval("1.5") * A_hi * two_3_2 * h_iv.pow_half_int(5) * l0.pow_half_int(1) * (h_iv + l0).pow_half_int(-5)
        F_h = iv_F_A(A_hi, h_iv, l0)
        R_tan = q_hi + F_h / h_iv + (one - l0) * (t_h / h_iv)
        t_over_K = t_h / h_iv
        t_iv = K * t_over_K
        c_sup_iv = K * R_tan - a
        om_max_iv = (one - e_lo) * c_sup_iv / t_iv
        if om_max_iv.hi < Decimal("1"):
            d1 = R_tan / c_sup_iv - (one - e_lo) / K
            d2 = R_tan / c_sup_iv - (one - e_hi) / K
            return d1.hull(d2)
        d_vals = []
        for eta_pt in (e_lo, e_hi):
            om_raw = (one - eta_pt) * c_sup_iv / t_iv
            om_clamped = Interval._raw(min(max(om_raw.lo, Decimal(0)), Decimal(1)),
                                       min(max(om_raw.hi, Decimal(0)), Decimal(1)))
            c_opt = c_sup_iv - t_iv * om_clamped
            d_vals.append(eta_pt * (R_tan - t_over_K * om_clamped) / c_opt)
        return d_vals[0].hull(d_vals[1])
    raise ValueError("K interval crosses h_m in AK mode")


# ---------------------------------------------------------------------------
# Layer 2: Numba IEEE-754 Outward-Rounded Fallback Leaf Audits
# ---------------------------------------------------------------------------
@njit(cache=True)
def _dn(x: float, n_ulp: int = 1) -> float:
    for _ in range(n_ulp):
        x = np.nextafter(x, -np.inf)
    return x


@njit(cache=True)
def _up(x: float, n_ulp: int = 1) -> float:
    for _ in range(n_ulp):
        x = np.nextafter(x, np.inf)
    return x


@njit(cache=True)
def _iv_add(a0: float, a1: float, b0: float, b1: float) -> Tuple[float, float]:
    return _dn(a0 + b0), _up(a1 + b1)


@njit(cache=True)
def _iv_sub(a0: float, a1: float, b0: float, b1: float) -> Tuple[float, float]:
    return _dn(a0 - b1), _up(a1 - b0)


@njit(cache=True)
def _iv_mul(a0: float, a1: float, b0: float, b1: float) -> Tuple[float, float]:
    p1, p2, p3, p4 = a0 * b0, a0 * b1, a1 * b0, a1 * b1
    return _dn(min(min(p1, p2), min(p3, p4))), _up(max(max(p1, p2), max(p3, p4)))


@njit(cache=True)
def _iv_div(a0: float, a1: float, b0: float, b1: float) -> Tuple[float, float]:
    p1, p2, p3, p4 = a0 / b0, a0 / b1, a1 / b0, a1 / b1
    return _dn(min(min(p1, p2), min(p3, p4))), _up(max(max(p1, p2), max(p3, p4)))


@njit(cache=True)
def _iv_ln_pt(x: float) -> Tuple[float, float]:
    if x <= 0.0:
        return -np.inf, -np.inf
    return _dn(math.log(x), 2), _up(math.log(x), 2)
