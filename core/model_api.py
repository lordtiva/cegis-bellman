"""
Abstract 1D Economy Interfaces (`ParamBox`, `Economy1D`, `MarkovEconomy1D`)
and Continuous VFI + Analytical Threshold Solvers.

Decouples economic models (Barro-CES, Political Markov, Stochastic Red Queen,
MVS canonical) from the CEGIS-LP synthesis and Rust/Interval verification engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable, Dict, Optional, Sequence, Tuple
import numpy as np
from scipy.optimize import brentq

from core.interval_arith import (
    CANONICAL_BETA,
    CANONICAL_BM,
    CANONICAL_ETA,
    CANONICAL_HM,
    CANONICAL_Q,
    F_A,
    dF_dK,
    dF_dL,
    Interval,
    iv_effective_A,
    iv_effective_q,
)


@dataclass(frozen=True)
class ParamBox:
    """Outward-rounded parameter box in reduced 1D Bellman coordinates (A, q, beta, eta)."""
    A_lo: float
    A_hi: float
    q_lo: float
    q_hi: float
    b_lo: float = CANONICAL_BETA[0]
    b_hi: float = CANONICAL_BETA[1]
    e_lo: float = CANONICAL_ETA[0]
    e_hi: float = CANONICAL_ETA[1]
    label: str = "box"

    @property
    def A_mid(self) -> float:
        return 0.5 * (self.A_lo + self.A_hi)

    @property
    def q_mid(self) -> float:
        return 0.5 * (self.q_lo + self.q_hi)

    @property
    def b_mid(self) -> float:
        return 0.5 * (self.b_lo + self.b_hi)

    @property
    def e_mid(self) -> float:
        return 0.5 * (self.e_lo + self.e_hi)

    def to_dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "A": [self.A_lo, self.A_hi],
            "q": [self.q_lo, self.q_hi],
            "beta": [self.b_lo, self.b_hi],
            "eta": [self.e_lo, self.e_hi],
        }


@dataclass(frozen=True)
class RegimeSpec:
    """Single regime specification in a finite-state Markov 1D economy."""
    name: str
    box: ParamBox
    g: float = 0.0


def build_policy_param_box(
    A0: float,
    alpha_num: int,
    alpha_den: int,
    tau_p: Tuple[float, float],
    tau_u: Tuple[float, float],
    nf: Tuple[float, float] = (1.0, 1.0),
    g: Tuple[float, float] = (0.0, 0.0),
    q_rng: Tuple[float, float] = CANONICAL_Q,
    b_rng: Tuple[float, float] = CANONICAL_BETA,
    e_rng: Tuple[float, float] = CANONICAL_ETA,
    label: str = "policy_box",
) -> ParamBox:
    """Conservatively map an institutional policy box into a reduced 1D `ParamBox` via 50-digit Intervals."""
    A_iv = iv_effective_A(
        A0=A0,
        alpha_num=alpha_num,
        alpha_den=alpha_den,
        tau_p_iv=Interval(str(tau_p[0]), str(tau_p[1])),
        tau_u_iv=Interval(str(tau_u[0]), str(tau_u[1])),
        nf_iv=Interval(str(nf[0]), str(nf[1])),
        g_iv=Interval(str(g[0]), str(g[1])),
    )
    q_iv = iv_effective_q(
        q_iv=Interval(str(q_rng[0]), str(q_rng[1])),
        g_iv=Interval(str(g[0]), str(g[1])),
    )
    A_lo, A_hi = A_iv.to_float_bounds()
    q_lo, q_hi = q_iv.to_float_bounds()
    return ParamBox(
        A_lo=A_lo, A_hi=A_hi,
        q_lo=q_lo, q_hi=q_hi,
        b_lo=float(b_rng[0]), b_hi=float(b_rng[1]),
        e_lo=float(e_rng[0]), e_hi=float(e_rng[1]),
        label=label,
    )


def _golden_L_vec(
    Av: float, qv: float, eL: float, eU: float, x_arr: np.ndarray, y_arr: np.ndarray,
    is_upper: bool,
) -> Tuple[np.ndarray, np.ndarray]:
    lo = np.full_like(x_arr, 1e-8, dtype=np.float64)
    hi = np.full_like(x_arr, 1.0 - 1e-9, dtype=np.float64)
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0

    def _obj(Lv):
        c = qv * x_arr + F_A(Av, x_arr, Lv) - y_arr
        lc = np.log(np.maximum(c, 1e-300))
        ll = np.log(1.0 - Lv)
        u1 = eL * lc + (1.0 - eL) * ll
        u2 = eU * lc + (1.0 - eU) * ll
        uv = np.maximum(u1, u2) if is_upper else np.minimum(u1, u2)
        return np.where(c > 1e-15, uv, -1e9 + c)

    u0 = _obj(np.zeros_like(lo))
    x1 = hi - inv_phi * (hi - lo)
    x2 = lo + inv_phi * (hi - lo)
    f1, f2 = _obj(x1), _obj(x2)
    for _ in range(28):
        mr = f1 < f2
        lo = np.where(mr, x1, lo)
        hi = np.where(mr, hi, x2)
        x1n = np.where(mr, x2, hi - inv_phi * (hi - lo))
        x2n = np.where(mr, lo + inv_phi * (hi - lo), x1)
        f1n = np.where(mr, f2, _obj(x1n))
        f2n = np.where(mr, _obj(x2n), f1)
        x1, x2, f1, f2 = x1n, x2n, f1n, f2n
    Lb = 0.5 * (lo + hi)
    ub = _obj(Lb)
    use0 = u0 > ub
    return np.where(use0, 0.0, Lb), np.where(use0, u0, ub)


def solve_teacher_vfi(
    Av: float,
    qv: float,
    bv: float,
    eL: float,
    eU: float,
    is_upper: bool,
    k_grid: np.ndarray,
    p_ruin: float = 0.0,
    v_ruin: float = 0.0,
    h_safe: float = CANONICAL_HM,
    max_iter: int = 140,
    n_L: int = 34,
    n_s: int = 34,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Continuous VFI solver (log-linear interpolation + golden-section continuous refinement)."""
    lk_g = np.log(k_grid)
    b_lo_eff = bv * (1.0 - p_ruin)
    s_lo = eL / (1.0 - b_lo_eff)
    D_hi = 2.5
    Ls = np.unique(np.concatenate([
        [0.0],
        np.geomspace(1e-6, 1e-3, 6, endpoint=False),
        np.geomspace(1e-3, 0.1, 8, endpoint=False),
        np.linspace(0.1, 0.997, max(12, n_L - 14)),
    ]))
    ss = np.unique(np.concatenate([
        np.linspace(0.15, 0.90, 22, endpoint=False),
        1.0 - np.geomspace(2e-5, 0.10, 18),
    ]))

    Y_mat = qv * k_grid[:, None] + F_A(Av, k_grid[:, None], Ls[None, :])
    V_cake0 = (eL / (1.0 - bv)) * (math.log(max((1.0 - bv) * qv, 1e-12)) + (bv / (1.0 - bv)) * math.log(max(bv * qv, 1e-12)))
    V = np.where(k_grid > 0.0014, -35.0, V_cake0 + s_lo * lk_g) if Av >= 0.25 else (V_cake0 + s_lo * lk_g)

    def _interp(kp_arr, Va):
        lk = np.log(np.maximum(kp_arr, 1e-300))
        r = np.interp(np.clip(lk, lk_g[0], lk_g[-1]), lk_g, Va)
        r = np.where(kp_arr < k_grid[0], Va[0] + s_lo * (lk - lk_g[0]), r)
        return np.where(kp_arr > k_grid[-1], Va[-1] + D_hi * (lk - lk_g[-1]), r)

    c_3 = np.maximum(Y_mat[:, :, None] * (1.0 - ss[None, None, :]), 1e-30)
    y_3 = Y_mat[:, :, None] * ss[None, None, :]
    ec_3 = np.where(c_3 < 1.0, eL, eU)
    ua = ec_3 * np.log(c_3) + (1.0 - eL) * np.log(1.0 - Ls[None, :, None])
    ub = ec_3 * np.log(c_3) + (1.0 - eU) * np.log(1.0 - Ls[None, :, None])
    u_3 = np.maximum(ua, ub) if is_upper else np.minimum(ua, ub)
    if not is_upper:
        u_3 = np.where(y_3 <= k_grid[-1] * 0.995, u_3, -1e9)

    ruin_mask_3 = (k_grid < h_safe)[:, None, None] if p_ruin > 0.0 else None
    ruin_mask_1 = (k_grid < h_safe) if p_ruin > 0.0 else None
    omp_r = 1.0 - p_ruin
    pv_r = p_ruin * v_ruin

    inv_phi_t = (math.sqrt(5.0) - 1.0) / 2.0
    Y_max_row = Y_mat[:, -1]
    pol_kp = np.zeros_like(k_grid)
    pol_L = np.zeros_like(k_grid)
    for it_v in range(max_iter):
        ev_3 = _interp(y_3, V)
        if ruin_mask_3 is not None:
            ev_3 = np.where(ruin_mask_3, omp_r * ev_3 + pv_r, ev_3)
        tot = u_3 + bv * ev_3
        flat_tot = tot.reshape(len(k_grid), -1)
        idx = np.argmax(flat_tot, axis=1)
        iL = idx // len(ss)
        iS = idx % len(ss)
        Vn = flat_tot[np.arange(len(k_grid)), idx]
        pol_kp = y_3[np.arange(len(k_grid)), iL, iS]
        pol_L = Ls[iL]
        u_pol = u_3[np.arange(len(k_grid)), iL, iS]
        if not is_upper and it_v >= 12 and it_v % 4 == 0:
            kp_hi_cap = np.minimum(Y_max_row * (1.0 - 1e-7), k_grid[-1] * 0.995)
            lo_k = np.maximum(k_grid[0], 0.92 * pol_kp)
            hi_k = np.maximum(lo_k * (1.0 + 1e-9), np.minimum(kp_hi_cap, 1.08 * pol_kp))
            x1 = hi_k - inv_phi_t * (hi_k - lo_k)
            x2 = lo_k + inv_phi_t * (hi_k - lo_k)
            _, u1 = _golden_L_vec(Av, qv, eL, eU, k_grid, x1, is_upper=False)
            _, u2 = _golden_L_vec(Av, qv, eL, eU, k_grid, x2, is_upper=False)
            ev1 = _interp(x1, V); ev2 = _interp(x2, V)
            if ruin_mask_1 is not None:
                ev1 = np.where(ruin_mask_1, omp_r * ev1 + pv_r, ev1)
                ev2 = np.where(ruin_mask_1, omp_r * ev2 + pv_r, ev2)
            f1 = u1 + bv * ev1
            f2 = u2 + bv * ev2
            for _ in range(10):
                mr = f1 < f2
                lo_k = np.where(mr, x1, lo_k)
                hi_k = np.where(mr, hi_k, x2)
                x1n = np.where(mr, x2, hi_k - inv_phi_t * (hi_k - lo_k))
                x2n = np.where(mr, lo_k + inv_phi_t * (hi_k - lo_k), x1)
                _, u1n = _golden_L_vec(Av, qv, eL, eU, k_grid, x1n, is_upper=False)
                _, u2n = _golden_L_vec(Av, qv, eL, eU, k_grid, x2n, is_upper=False)
                ev1n = _interp(x1n, V); ev2n = _interp(x2n, V)
                if ruin_mask_1 is not None:
                    ev1n = np.where(ruin_mask_1, omp_r * ev1n + pv_r, ev1n)
                    ev2n = np.where(ruin_mask_1, omp_r * ev2n + pv_r, ev2n)
                f1n = np.where(mr, f2, u1n + bv * ev1n)
                f2n = np.where(mr, u2n + bv * ev2n, f1)
                x1, x2, f1, f2 = x1n, x2n, f1n, f2n
            kp_ref = np.where(f1 > f2, x1, x2)
            L_ref, u_ref = _golden_L_vec(Av, qv, eL, eU, k_grid, kp_ref, is_upper=False)
            evr = _interp(kp_ref, V)
            if ruin_mask_1 is not None:
                evr = np.where(ruin_mask_1, omp_r * evr + pv_r, evr)
            use_ref = (u_ref + bv * evr) > Vn
            pol_kp = np.where(use_ref, kp_ref, pol_kp)
            pol_L = np.where(use_ref, L_ref, pol_L)
            u_pol = np.where(use_ref, u_ref, u_pol)
            Vn = np.where(use_ref, u_ref + bv * evr, Vn)
        for _ in range(25):
            ev_p = _interp(pol_kp, Vn)
            if ruin_mask_1 is not None:
                ev_p = np.where(ruin_mask_1, omp_r * ev_p + pv_r, ev_p)
            Vn = u_pol + bv * ev_p
        if np.max(np.abs(Vn - V)) < 1e-6 and it_v >= 20 and (is_upper or it_v % 4 == 0):
            V = Vn
            break
        V = Vn
    return V, pol_kp, pol_L


def solve_markov_teacher_vfi(
    P_low: np.ndarray,
    A0: float,
    A1: float,
    q0: float,
    q1: float,
    bv: float,
    eL: float,
    eU: float,
    is_upper: bool,
    k_grid: np.ndarray,
    P_high: Optional[np.ndarray] = None,
    h_switch: float = CANONICAL_HM,
    max_iter: int = 180,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Coupled 2-regime VFI solver supporting regime-dependent (A_w, q_w) AND optional
    state-dependent transition matrix switching from P_low (K < h_switch) to P_high (K >= h_switch).
    """
    P_lo = np.asarray(P_low, dtype=np.float64)
    P_hi = P_lo if P_high is None else np.asarray(P_high, dtype=np.float64)
    assert P_lo.shape == (2, 2) and P_hi.shape == (2, 2)

    lk_g = np.log(k_grid)
    s_lo = eL / (1.0 - bv)
    D_hi = 2.5
    Ls = np.unique(np.concatenate([
        [0.0],
        np.geomspace(1e-6, 1e-3, 8, endpoint=False),
        np.geomspace(1e-3, 0.1, 10, endpoint=False),
        np.linspace(0.1, 0.997, 32),
    ]))
    ss = np.unique(np.concatenate([
        np.linspace(0.15, 0.90, 22, endpoint=False),
        1.0 - np.geomspace(2e-5, 0.10, 22),
    ]))

    def _u_grid(Av: float, qv: float):
        Y = qv * k_grid[:, None] + F_A(Av, k_grid[:, None], Ls[None, :])
        c = np.maximum(Y[:, :, None] * (1.0 - ss[None, None, :]), 1e-30)
        y = Y[:, :, None] * ss[None, None, :]
        ec = np.where(c < 1.0, eL, eU)
        ua = ec * np.log(c) + (1.0 - eL) * np.log(1.0 - Ls[None, :, None])
        ub = ec * np.log(c) + (1.0 - eU) * np.log(1.0 - Ls[None, :, None])
        u = np.maximum(ua, ub) if is_upper else np.minimum(ua, ub)
        if not is_upper:
            u = np.where(y <= k_grid[-1] * 0.995, u, -1e9)
        return y, u

    y0, u0 = _u_grid(A0, q0)
    y1, u1 = _u_grid(A1, q1)
    V_cake0 = (eL / (1.0 - bv)) * (math.log(max((1.0 - bv) * q0, 1e-12)) + (bv / (1.0 - bv)) * math.log(max(bv * q0, 1e-12)))
    V0 = np.where(k_grid > 0.0014, -35.0, V_cake0 + s_lo * lk_g)
    V1 = V0.copy() - 2.0

    def _interp(kp_arr, Va):
        lk = np.log(np.maximum(kp_arr, 1e-300))
        r = np.interp(np.clip(lk, lk_g[0], lk_g[-1]), lk_g, Va)
        r = np.where(kp_arr < k_grid[0], Va[0] + s_lo * (lk - lk_g[0]), r)
        return np.where(kp_arr > k_grid[-1], Va[-1] + D_hi * (lk - lk_g[-1]), r)

    inv_phi_m = (math.sqrt(5.0) - 1.0) / 2.0
    ym_0 = y0[:, -1, -1]
    ym_1 = y1[:, -1, -1]
    low_mask = k_grid < h_switch
    p00 = np.where(low_mask, P_lo[0, 0], P_hi[0, 0])
    p01 = np.where(low_mask, P_lo[0, 1], P_hi[0, 1])
    p10 = np.where(low_mask, P_lo[1, 0], P_hi[1, 0])
    p11 = np.where(low_mask, P_lo[1, 1], P_hi[1, 1])

    kp0 = kp1 = L0 = L1 = np.zeros_like(k_grid)
    for it_m in range(max_iter):
        EV0_grid = p00 * V0 + p01 * V1
        EV1_grid = p10 * V0 + p11 * V1
        tot0 = (u0 + bv * _interp(y0, EV0_grid)).reshape(len(k_grid), -1)
        tot1 = (u1 + bv * _interp(y1, EV1_grid)).reshape(len(k_grid), -1)
        i0 = np.argmax(tot0, axis=1)
        i1 = np.argmax(tot1, axis=1)
        iL0, iS0 = i0 // len(ss), i0 % len(ss)
        iL1, iS1 = i1 // len(ss), i1 % len(ss)
        V0n = tot0[np.arange(len(k_grid)), i0]
        V1n = tot1[np.arange(len(k_grid)), i1]
        kp0, L0 = y0[np.arange(len(k_grid)), iL0, iS0], Ls[iL0]
        kp1, L1 = y1[np.arange(len(k_grid)), iL1, iS1], Ls[iL1]
        u0p, u1p = u0[np.arange(len(k_grid)), iL0, iS0], u1[np.arange(len(k_grid)), iL1, iS1]

        if not is_upper and it_m >= 20 and it_m % 4 == 0:
            def _ref_st(Av_s, qv_s, ym_s, kp_s, EV_s, L_cur, u_cur, V_cur):
                lo_k = np.maximum(k_grid[0], 0.92 * kp_s)
                hi_k = np.maximum(lo_k * (1.0 + 1e-9), np.minimum(np.minimum(ym_s * (1.0 - 1e-7), k_grid[-1] * 0.995), 1.08 * kp_s))
                x1 = hi_k - inv_phi_m * (hi_k - lo_k)
                x2 = lo_k + inv_phi_m * (hi_k - lo_k)
                _, ua_1 = _golden_L_vec(Av_s, qv_s, eL, eU, k_grid, x1, is_upper=False)
                _, ua_2 = _golden_L_vec(Av_s, qv_s, eL, eU, k_grid, x2, is_upper=False)
                f1, f2 = ua_1 + bv * _interp(x1, EV_s), ua_2 + bv * _interp(x2, EV_s)
                for _ in range(10):
                    mr = f1 < f2
                    lo_k = np.where(mr, x1, lo_k)
                    hi_k = np.where(mr, hi_k, x2)
                    x1n = np.where(mr, x2, hi_k - inv_phi_m * (hi_k - lo_k))
                    x2n = np.where(mr, lo_k + inv_phi_m * (hi_k - lo_k), x1)
                    _, ua1n = _golden_L_vec(Av_s, qv_s, eL, eU, k_grid, x1n, is_upper=False)
                    _, ua2n = _golden_L_vec(Av_s, qv_s, eL, eU, k_grid, x2n, is_upper=False)
                    f1n = np.where(mr, f2, ua1n + bv * _interp(x1n, EV_s))
                    f2n = np.where(mr, ua2n + bv * _interp(x2n, EV_s), f1)
                    x1, x2, f1, f2 = x1n, x2n, f1n, f2n
                kp_r = np.where(f1 > f2, x1, x2)
                L_r, u_r = _golden_L_vec(Av_s, qv_s, eL, eU, k_grid, kp_r, is_upper=False)
                V_r = u_r + bv * _interp(kp_r, EV_s)
                use_r = V_r > V_cur
                return np.where(use_r, kp_r, kp_s), np.where(use_r, L_r, L_cur), np.where(use_r, u_r, u_cur), np.where(use_r, V_r, V_cur)

            kp0, L0, u0p, V0n = _ref_st(A0, q0, ym_0, kp0, EV0_grid, L0, u0p, V0n)
            kp1, L1, u1p, V1n = _ref_st(A1, q1, ym_1, kp1, EV1_grid, L1, u1p, V1n)

        for _ in range(25):
            EV0n = p00 * V0n + p01 * V1n
            EV1n = p10 * V0n + p11 * V1n
            V0n = u0p + bv * _interp(kp0, EV0n)
            V1n = u1p + bv * _interp(kp1, EV1n)
        if max(np.max(np.abs(V0n - V0)), np.max(np.abs(V1n - V1))) < 1e-6 and it_m >= 20:
            V0, V1 = V0n, V1n
            break
        V0, V1 = V0n, V1n
    return V0, V1, kp0, L0, kp1, L1


@dataclass
class Economy1D:
    """Deterministic 1D CES increasing-returns economy with analytical threshold & VFI helpers."""
    A: float
    q: float = 0.92
    beta: float = 0.97
    eta: float = 0.70
    b_m: float = CANONICAL_BM
    h_m: float = CANONICAL_HM

    @staticmethod
    def a_rep(q: float = 0.92) -> float:
        """Exact physical reproduction threshold A_rep = (1 - q) / (4*sqrt(6)/9)."""
        return (1.0 - q) / (4.0 * math.sqrt(6.0) / 9.0)

    def solve_vfi(self, k_grid: Optional[np.ndarray] = None) -> Dict[str, object]:
        if k_grid is None:
            k_grid = np.unique(np.concatenate([
                np.geomspace(1e-4, 0.004, 80, endpoint=False),
                np.geomspace(0.004, 0.05, 80, endpoint=False),
                np.geomspace(0.05, 0.40, 80, endpoint=False),
                np.geomspace(0.40, 60.0, 90),
            ]))
        V, kp, L = solve_teacher_vfi(self.A, self.q, self.beta, self.eta, self.eta, False, k_grid)
        S = self.estimate_skiba(k_grid, kp)
        return {"k_grid": k_grid, "V": V, "kp": kp, "L": L, "skiba": S}

    @staticmethod
    def estimate_skiba(k_grid: np.ndarray, kp: np.ndarray, k_min_search: float = 2e-4) -> Optional[float]:
        """Locate the Skiba separatrix where kp(K) jumps from contracting (kp < K) to expanding (kp > K)."""
        mask = k_grid >= k_min_search
        ks = k_grid[mask]
        kps = kp[mask]
        diff = kps - ks
        # Look for sign flip from negative to positive in [k_min_search, 1.0]
        sub = ks <= 1.0
        ks_s, diff_s = ks[sub], diff[sub]
        for i in range(len(ks_s) - 1):
            if diff_s[i] <= 0.0 and diff_s[i + 1] > 0.0:
                return float(0.5 * (ks_s[i] + ks_s[i + 1]))
        if np.all(diff_s > 0.0):
            return 0.0
        return None


@dataclass
class MarkovEconomy1D:
    """Two-regime Markov 1D economy supporting regime-dependent (A_w, q_w, g_w) and Red Queen shift."""
    regimes: Tuple[RegimeSpec, RegimeSpec]
    P_low: np.ndarray
    P_high: Optional[np.ndarray] = None
    h_switch: float = CANONICAL_HM
    beta: float = 0.97
    eta: float = 0.70

    def solve_red_queen_shift(self) -> np.ndarray:
        """
        Closed-form vector phi resolving (I - beta * P) phi = (eta / (1 - beta)) * log(1 + g)
        from Theorem 2 (Stochastic Red Queen Isomorphism).
        """
        g_vec = np.array([self.regimes[0].g, self.regimes[1].g], dtype=np.float64)
        rhs = (self.eta / (1.0 - self.beta)) * np.log(1.0 + g_vec)
        mat = np.eye(2, dtype=np.float64) - self.beta * np.asarray(self.P_low, dtype=np.float64)
        return np.linalg.solve(mat, rhs)

    def solve_vfi(self, k_grid: Optional[np.ndarray] = None) -> Dict[str, object]:
        if k_grid is None:
            k_grid = np.unique(np.concatenate([
                np.geomspace(1e-4, 0.004, 70, endpoint=False),
                np.geomspace(0.004, 0.05, 70, endpoint=False),
                np.geomspace(0.05, 0.40, 70, endpoint=False),
                np.geomspace(0.40, 60.0, 80),
            ]))
        r0, r1 = self.regimes
        V0, V1, kp0, L0, kp1, L1 = solve_markov_teacher_vfi(
            P_low=self.P_low,
            A0=r0.box.A_mid, A1=r1.box.A_mid,
            q0=r0.box.q_mid, q1=r1.box.q_mid,
            bv=self.beta, eL=self.eta, eU=self.eta, is_upper=False,
            k_grid=k_grid, P_high=self.P_high, h_switch=self.h_switch,
        )
        return {
            "k_grid": k_grid,
            "V0": V0, "V1": V1,
            "kp0": kp0, "L0": L0,
            "kp1": kp1, "L1": L1,
            "S0": Economy1D.estimate_skiba(k_grid, kp0),
            "S1": Economy1D.estimate_skiba(k_grid, kp1),
        }


def expected_markov_hitting_time(
    k_grid: np.ndarray,
    kp0: np.ndarray,
    kp1: np.ndarray,
    P: np.ndarray,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    n_pts: int = 40,
) -> Dict[str, float]:
    """
    Compute exact discrete-grid Markov expected exit time E_VFI[tau_H] from M=[b_m, h_m)
    to H=[h_m, inf) by solving (I - P_stay) * tau = 1 via fixed-point / linear solve
    over linear interpolation on a fine grid inside [b_m, h_m).
    """
    P_arr = np.asarray(P, dtype=np.float64)
    g = np.linspace(b_m, h_m, n_pts, endpoint=False)
    n_states = 2 * n_pts
    Q = np.zeros((n_states, n_states), dtype=np.float64)

    for w, kp_arr in ((0, kp0), (1, kp1)):
        k_next = np.interp(g, k_grid, kp_arr)
        for i in range(n_pts):
            row = w * n_pts + i
            kn = float(k_next[i])
            if kn >= h_m:
                continue  # absorbed in H immediately after this step
            if kn <= g[0]:
                idx_lo, idx_hi, w_hi = 0, 0, 0.0
            else:
                # Linear interpolation weights on uniform grid g
                pos = (kn - g[0]) / (g[1] - g[0])
                idx_lo = min(n_pts - 2, max(0, int(math.floor(pos))))
                idx_hi = idx_lo + 1
                w_hi = min(1.0, max(0.0, pos - idx_lo))
            w_lo = 1.0 - w_hi
            for wp in (0, 1):
                p_ww = float(P_arr[w, wp])
                if idx_lo == idx_hi:
                    Q[row, wp * n_pts + idx_lo] += p_ww
                else:
                    Q[row, wp * n_pts + idx_lo] += p_ww * w_lo
                    Q[row, wp * n_pts + idx_hi] += p_ww * w_hi

    A_mat = np.eye(n_states, dtype=np.float64) - Q
    tau = np.linalg.solve(A_mat, np.ones(n_states, dtype=np.float64))
    return {
        "max_E_tau_H": float(np.max(tau)),
        "E_tau_at_bm_0": float(tau[0]),
        "E_tau_at_bm_1": float(tau[n_pts]),
    }
