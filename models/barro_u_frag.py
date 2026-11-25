"""
Barro-CES Institutional U-Curve & Firm Fragmentation Model (Sections 4-5).

Unifies productive public expenditure (tau_p), unproductive bureaucracy (tau_u),
and regulatory firm fragmentation (N_f) into the effective TFP scalar:
  A_e(tau_p, tau_u, N_f) = A0 * tau_p^alpha * (1 - tau_p - tau_u) * N_f^-(theta - 1)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import brentq, minimize_scalar

from core.interval_arith import (
    CANONICAL_BETA,
    CANONICAL_BM,
    CANONICAL_ETA,
    CANONICAL_HM,
    CANONICAL_Q,
    F_A,
)
from core.model_api import Economy1D, ParamBox
from core.box_partition import adaptive_certify_1d


GAMMA_BASE = 0.20
ALPHA_NUM = 1
ALPHA_DEN = 4
ALPHA_BASE = 0.25  # gamma / (1 - gamma)
A0_BASE = 1.45
THETA_BASE = 1.5
S_INF_STAR = 0.000800  # (delta / c_K)^(1/r) from MVS Theorem 2
POLICY_BM = 0.10
POLICY_HM = 0.18


def effective_A(
    tau_p: float,
    tau_u: float = 0.0,
    nf: float = 1.0,
    A0: float = A0_BASE,
    alpha: float = ALPHA_BASE,
    theta: float = THETA_BASE,
) -> float:
    if tau_p <= 0.0 or (1.0 - tau_p - tau_u) <= 0.0 or nf < 1.0:
        return 0.0
    return float(A0 * (tau_p ** alpha) * (1.0 - tau_p - tau_u) * (nf ** (-(theta - 1.0))))


def optimal_tau_p(tau_u: float, gamma: float = GAMMA_BASE) -> float:
    """Unique productivity-maximizing public spending share tau_p^*(tau_u) = gamma*(1 - tau_u)."""
    return float(gamma * (1.0 - tau_u))


def equivalent_tau_u(nf: float, tau_p: float, theta: float = THETA_BASE) -> float:
    """Proposition 1: Bureaucracy-Fragmentation equivalence tau_u^eq(N_f; tau_p)."""
    return float((1.0 - tau_p) * (1.0 - (nf ** (-(theta - 1.0)))))


def asymptotic_skiba_profile(
    tau_p: float,
    tau_u: float = 0.0,
    nf: float = 1.0,
    A0: float = A0_BASE,
    alpha: float = ALPHA_BASE,
    s_inf_star: float = S_INF_STAR,
    r: float = THETA_BASE - 1.0,
) -> float:
    """Asymptotic envelope A0^(-1/r) * s_inf^* * [tau_p^alpha * (1 - tau_p - tau_u)]^(-1/r) * N_f."""
    core = (tau_p ** alpha) * (1.0 - tau_p - tau_u)
    return float((A0 ** (-1.0 / r)) * s_inf_star * (core ** (-1.0 / r)) * nf)


def compute_exact_A_SN(q: float = 0.92, beta: float = 0.97, eta: float = 0.70) -> Tuple[float, float]:
    """
    Compute the exact saddle-node bifurcation A_SN where a stationary interior
    steady state (K*, L*) with Euler return q + F_K(K*, L*) = 1/beta first appears.
    """
    target_r = (1.0 / beta) - q

    def _f_max_ratio(A_val: float) -> float:
        # At steady state c = (q - 1)K + F_A(K, L), intratemporal FOC:
        # (1 - eta) c = eta (1 - L) F_L(K, L) => solves L*(K; A), then maximize F_K(K, L*(K; A)).
        def _L_ss(K: float) -> float:
            def _foc(L: float) -> float:
                if L <= 1e-12:
                    return -1.0
                fl = 1.5 * A_val * (2.0 ** 1.5) * (K ** 2.5) * (L ** 0.5) * ((K + L) ** -2.5)
                fa = A_val * ((2.0 * K * L) / (K + L)) ** 1.5
                c = (q - 1.0) * K + fa
                return (1.0 - eta) * c - eta * (1.0 - L) * fl

            if _foc(1e-7) > 0:
                return 1e-7
            if _foc(1.0 - 1e-9) < 0:
                return 1.0 - 1e-9
            return float(brentq(_foc, 1e-7, 1.0 - 1e-9, xtol=1e-12))

        def _neg_fk(K: float) -> float:
            L = _L_ss(K)
            c = (q - 1.0) * K + A_val * ((2.0 * K * L) / (K + L)) ** 1.5
            if c <= 0:
                return 1e6
            fk = 1.5 * A_val * (2.0 ** 1.5) * (K ** 0.5) * (L ** 2.5) * ((K + L) ** -2.5)
            return -fk

        ks_scan = np.linspace(0.05, 0.80, 80)
        vals_scan = [_neg_fk(float(kv)) for kv in ks_scan]
        i_best = int(np.argmin(vals_scan))
        lo_b = float(ks_scan[max(0, i_best - 2)])
        hi_b = float(ks_scan[min(len(ks_scan) - 1, i_best + 2)])
        res = minimize_scalar(_neg_fk, bounds=(lo_b, hi_b), method="bounded")
        return float(-res.fun - target_r)

    A_sn = float(brentq(_f_max_ratio, 0.075, 0.14, xtol=1e-9))
    return A_sn, target_r


def compute_A_star_vfi(q: float = 0.92, beta: float = 0.97, eta: float = 0.70, A_sn: float = 0.0995245) -> float:
    """
    Locate the global Skiba/Maxwell emergence threshold A_* > A_SN via exact Maxwell equality
    V_H^*(A) = V_contract(K_H^*(A); A) between the upper interior steady state and the
    strictly contracting poverty-trap branch.
    """
    target_r = (1.0 / beta) - q
    s_lo = eta / (1.0 - beta)
    V_cake0 = s_lo * (math.log((1.0 - beta) * q) + (beta / (1.0 - beta)) * math.log(beta * q))
    Ls = np.unique(np.concatenate([
        [0.0],
        np.geomspace(1e-5, 0.1, 10, endpoint=False),
        np.linspace(0.1, 0.995, 45),
    ]))
    rs = np.unique(np.concatenate([
        np.linspace(0.20, 0.85, 14, endpoint=False),
        np.linspace(0.85, 0.996, 42),
    ]))

    def _maxwell_gap(Av: float) -> float:
        def _L_ss(K: float) -> float:
            def _foc(L: float) -> float:
                if L <= 1e-12:
                    return -1.0
                fl = 1.5 * Av * (2.0 ** 1.5) * (K ** 2.5) * (L ** 0.5) * ((K + L) ** -2.5)
                fa = Av * ((2.0 * K * L) / (K + L)) ** 1.5
                return (1.0 - eta) * ((q - 1.0) * K + fa) - eta * (1.0 - L) * fl

            if _foc(1e-7) > 0:
                return 1e-7
            if _foc(1.0 - 1e-9) < 0:
                return 1.0 - 1e-9
            return float(brentq(_foc, 1e-7, 1.0 - 1e-9, xtol=1e-12))

        def _g(K: float) -> float:
            L = _L_ss(K)
            return float(1.5 * Av * (2.0 ** 1.5) * (K ** 0.5) * (L ** 2.5) * ((K + L) ** -2.5) - target_r)

        res_pk = minimize_scalar(lambda K: -_g(K), bounds=(0.12, 0.30), method="bounded")
        kh = float(brentq(_g, float(res_pk.x), 2.0, xtol=1e-12))
        Lh = _L_ss(kh)
        ch = (q - 1.0) * kh + Av * ((2.0 * kh * Lh) / (kh + Lh)) ** 1.5
        Vh = float((eta * math.log(ch) + (1.0 - eta) * math.log(1.0 - Lh)) / (1.0 - beta))

        k_g = np.geomspace(1e-4, kh, 220)
        lk_g = np.log(k_g)
        V_c = V_cake0 + s_lo * lk_g
        Y = q * k_g[:, None] + F_A(Av, k_g[:, None], Ls[None, :])
        kp3 = k_g[:, None, None] * rs[None, None, :]
        c3 = Y[:, :, None] - kp3
        u3 = np.where(
            c3 > 1e-12,
            eta * np.log(np.maximum(c3, 1e-30)) + (1.0 - eta) * np.log(1.0 - Ls[None, :, None]),
            -1e9,
        )
        lkp = np.log(kp3)
        for _ in range(150):
            ev3 = np.where(
                kp3 < k_g[0],
                V_c[0] + s_lo * (lkp - lk_g[0]),
                np.interp(np.clip(lkp, lk_g[0], lk_g[-1]), lk_g, V_c),
            )
            Vn = np.max(u3 + beta * ev3, axis=(1, 2))
            if float(np.max(np.abs(Vn - V_c))) < 1e-8:
                V_c = Vn
                break
            V_c = Vn
        return float(Vh - V_c[-1])

    return float(brentq(_maxwell_gap, A_sn + 1e-6, 0.1005, xtol=1e-7))


def compute_A_cross(q: float = 0.92, beta: float = 0.97, eta: float = 0.70) -> float:
    """Locate the crossing A_cross ~ 0.110 between S_VFI(A) and the Euler asymptotic envelope."""
    k_d = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.05, 35, endpoint=False),
        np.geomspace(0.05, 0.45, 140, endpoint=False),
        np.geomspace(0.45, 10.0, 35),
    ]))
    s_euler_const = (((1.0 / beta) - q) / (2.0 ** 1.5)) ** 2

    def _gap(Av: float) -> float:
        res = Economy1D(A=Av, q=q, beta=beta, eta=eta).solve_vfi(k_grid=k_d)
        sk = res["skiba"]
        if sk is None:
            return 1.0
        return float(sk - (s_euler_const / (Av * Av)))

    return float(brentq(_gap, 0.105, 0.118, xtol=1e-5))


def compute_theorem1_analytics() -> Dict[str, object]:
    """Compute all exact analytical thresholds, physical vs economic regimes, and U-curve profile."""
    A_rep = Economy1D.a_rep(0.92)
    A_sn, _ = compute_exact_A_SN(0.92, 0.97, 0.70)
    A_star = compute_A_star_vfi(0.92, 0.97, 0.70, A_sn=A_sn)
    A_cross = compute_A_cross(0.92, 0.97, 0.70)
    A_peak = effective_A(optimal_tau_p(0.0), 0.0, 1.0)

    def _roots_for_A(A_target: float, tau_u: float = 0.0) -> Tuple[float, float]:
        t_star = optimal_tau_p(tau_u)
        if effective_A(t_star, tau_u) < A_target:
            return (float("nan"), float("nan"))
        lo = float(brentq(lambda t: effective_A(t, tau_u) - A_target, 1e-6, t_star))
        hi = float(brentq(lambda t: effective_A(t, tau_u) - A_target, t_star, 1.0 - tau_u - 1e-6))
        return lo, hi

    tau_phys = _roots_for_A(A_rep, 0.0)
    tau_econ = _roots_for_A(A_star, 0.0)
    tau_mvs_island = _roots_for_A(0.749, 0.0)

    # U-curve S(tau) vs asymptotic envelope across tau_p
    taus = [0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.88]
    u_curve_rows = []
    k_ucurve = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.05, 45, endpoint=False),
        np.geomspace(0.05, 0.50, 45, endpoint=False),
        np.geomspace(0.50, 50.0, 50),
    ]))
    for tp in taus:
        Ae = effective_A(tp, 0.0, 1.0)
        S_env = asymptotic_skiba_profile(tp, 0.0, 1.0)
        S_vfi = Economy1D(A=Ae, q=0.92, beta=0.97, eta=0.70).solve_vfi(k_grid=k_ucurve)["skiba"] if Ae >= A_star else None
        u_curve_rows.append({
            "tau_p": float(tp),
            "A_e": float(Ae),
            "S_vfi": None if S_vfi is None else float(S_vfi),
            "S_env": float(S_env),
        })

    # Bureaucracy-Fragmentation equivalence table (Prop 1)
    nf_eq_rows = []
    for nf in [1, 2, 3, 4, 6, 9, 16, 25, 56, 57]:
        Ae_bench = 0.75 * (nf ** -0.5)
        Ae_barro = effective_A(0.20, 0.0, float(nf))
        nf_eq_rows.append({
            "N_f": int(nf),
            "tau_u_eq_at_tp020": equivalent_tau_u(float(nf), 0.20),
            "A_e_bench075": float(Ae_bench),
            "A_e_barro_tp020": float(Ae_barro),
            "viable_bench": bool(Ae_bench >= A_star),
        })

    nf_collapse_bench075 = float((0.75 / A_star) ** 2)
    nf_SN_bench075 = float((0.75 / A_sn) ** 2)
    nf_collapse_peak = float((A_peak / A_star) ** 2)

    return {
        "A0": A0_BASE,
        "gamma": GAMMA_BASE,
        "alpha": ALPHA_BASE,
        "A_rep": float(A_rep),
        "A_SN": float(A_sn),
        "A_star": float(A_star),
        "A_cross": float(A_cross),
        "A_peak_tau_u0": float(A_peak),
        "tau_phys_bounds": [float(tau_phys[0]), float(tau_phys[1])],
        "tau_econ_bounds": [float(tau_econ[0]), float(tau_econ[1])],
        "tau_old_mvs_island": [float(tau_mvs_island[0]), float(tau_mvs_island[1])],
        "tau_u_eq_example_nf4_tp020": equivalent_tau_u(4.0, 0.20),
        "nf_collapse_bench075": nf_collapse_bench075,
        "nf_SN_bench075": nf_SN_bench075,
        "nf_collapse_peak": nf_collapse_peak,
        "u_curve": u_curve_rows,
        "nf_equivalence": nf_eq_rows,
    }


def _map_Ae_band(a0: float, a1: float) -> ParamBox:
    return ParamBox(
        A_lo=float(a0), A_hi=float(a1),
        q_lo=0.92, q_hi=0.92,
        b_lo=0.97, b_hi=0.97,
        e_lo=0.70, e_hi=0.70,
        label=f"Ae=[{a0:.4f},{a1:.4f}]",
    )


def certify_Ae_atlas(
    A_floor: float = 0.385,
    A_ceil: float = 0.780,
    max_depth: int = 2,
    parallel: bool = True,
) -> Dict[str, object]:
    """Certify contiguous zero-gap 1D A_e atlas on [A_floor, A_ceil] with M_pol=[0.10, 0.18)."""
    segs = []
    if A_floor < 0.425:
        segs.append(np.linspace(A_floor, min(0.425, A_ceil), 10, endpoint=False))
    if A_ceil > 0.425 and A_floor < 0.545:
        segs.append(np.linspace(max(A_floor, 0.425), min(0.545, A_ceil), 20, endpoint=False))
    if A_ceil > 0.545 and A_floor < 0.665:
        segs.append(np.linspace(max(A_floor, 0.545), min(0.665, A_ceil), 12, endpoint=False))
    segs.append(np.linspace(max(A_floor, 0.665), A_ceil, 9))
    edges = np.unique(np.concatenate(segs)).tolist()

    leaves = adaptive_certify_1d(
        edges=edges,
        mapper_fn=_map_Ae_band,
        b_m=POLICY_BM,
        h_m=POLICY_HM,
        k_h2=0.80,
        max_depth=max_depth,
        parallel=parallel,
    )
    certified = [lf for lf in leaves if lf["status"] == "certified"]
    uncertified = [lf for lf in leaves if lf["status"] != "certified"]
    if uncertified:
        errs = [(u["bounds_1d"], u.get("error", "")) for u in uncertified[:3]]
        raise RuntimeError(f"Non-contiguous A_e atlas: {len(uncertified)} uncertified band(s), sample={errs}")

    # Verify strict contiguity
    for prev, cur in zip(certified[:-1], certified[1:]):
        if abs(prev["bounds_1d"][1] - cur["bounds_1d"][0]) > 1e-12:
            raise RuntimeError(f"Gap in A_e atlas: {prev['bounds_1d']} -> {cur['bounds_1d']}")

    return {
        "certified_leaves": certified,
        "uncertified_leaves": uncertified,
        "A_min": float(certified[0]["bounds_1d"][0]),
        "A_max": float(certified[-1]["bounds_1d"][1]),
        "b_m": float(POLICY_BM),
        "h_m": float(POLICY_HM),
    }


def _policy_region_area_above(A_cut: float) -> Tuple[float, Tuple[float, float], float]:
    """Compute area and intercepts of {(tau_p, tau_u): A_e(tau_p, tau_u, 1) >= A_cut}."""
    A_peak = effective_A(0.20, 0.0, 1.0)
    if A_cut >= A_peak:
        return 0.0, (0.20, 0.20), 0.0
    tp_lo = float(brentq(lambda t: effective_A(t, 0.0, 1.0) - A_cut, 1e-5, 0.20))
    tp_hi = float(brentq(lambda t: effective_A(t, 0.0, 1.0) - A_cut, 0.20, 0.995))
    tp_grid = np.linspace(tp_lo, tp_hi, 4000)
    tu_max = np.maximum(0.0, (1.0 - tp_grid) - A_cut / (A0_BASE * (tp_grid ** ALPHA_BASE)))
    area = float(0.5 * np.sum((tu_max[:-1] + tu_max[1:]) * np.diff(tp_grid)))
    tu_max_tp020 = float(max(0.0, 0.80 * (1.0 - A_cut / A_peak)))
    return area, (tp_lo, tp_hi), tu_max_tp020


def certify_policy_plane(
    A_floor_target: float = 0.385,
    max_depth: int = 2,
    parallel: bool = True,
    atlas: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """
    Proposition 2: Exact certified region in (tau_p, tau_u) pulled back from the
    contiguous 1D A_e-atlas on [A_floor, 0.780] with persistence band [0.10, 0.18).
    """
    if atlas is None:
        atlas = certify_Ae_atlas(A_floor=A_floor_target, A_ceil=0.780, max_depth=max_depth, parallel=parallel)
    certified = atlas["certified_leaves"]
    A_min = float(atlas["A_min"])
    A_max = float(atlas["A_max"])
    T_min = min(lf["cert"]["T_cert"] for lf in certified)
    T_max = max(lf["cert"]["T_cert"] for lf in certified)

    area_cert, tp_bounds_tu0, tu_max_tp020 = _policy_region_area_above(A_min)
    area_old, old_tp_bounds, old_tu_max = _policy_region_area_above(0.749)

    return {
        "certified_leaves": certified,
        "uncertified_leaves": atlas["uncertified_leaves"],
        "summary": {
            "n_certified_boxes": len(certified),
            "n_uncertified_boxes": len(atlas["uncertified_leaves"]),
            "area_tau_plane": float(area_cert),
            "area_old_mvs_island": float(area_old),
            "area_expansion_ratio": float(area_cert / max(area_old, 1e-12)),
            "tau_p_bounds_at_tu0": [float(tp_bounds_tu0[0]), float(tp_bounds_tu0[1])],
            "tau_u_max_at_tp020": float(tu_max_tp020),
            "old_island_tau_p_bounds": [float(old_tp_bounds[0]), float(old_tp_bounds[1])],
            "old_island_tau_u_max_at_tp020": float(old_tu_max),
            "A_e_min_certified": A_min,
            "A_e_max_certified": A_max,
            "T_cert_min": int(T_min),
            "T_cert_max": int(T_max),
            "b_m": float(POLICY_BM),
            "h_m": float(POLICY_HM),
        },
    }


def certify_fragmentation_nf(
    A_floor_target: float = 0.385,
    max_depth: int = 2,
    parallel: bool = True,
    atlas: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """
    Proposition 3: Continuous CEGIS-LP certification over firm fragmentation N_f
    at optimal spending tau_p = 0.20, tau_u = 0.0 (and benchmark A_e = 0.75 * N_f^-0.5)
    derived directly from the contiguous A_e-atlas.
    """
    if atlas is None:
        atlas = certify_Ae_atlas(A_floor=A_floor_target, A_ceil=0.780, max_depth=max_depth, parallel=parallel)
    A_peak = effective_A(0.20, 0.0, 1.0)
    certified_atlas = atlas["certified_leaves"]
    A_min = float(atlas["A_min"])

    nf_bands = []
    for lf in reversed(certified_atlas):
        a_lo, a_hi = lf["bounds_1d"]
        if a_lo >= A_peak:
            continue
        nf_lo = max(1.0, (A_peak / a_hi) ** 2)
        nf_hi = (A_peak / a_lo) ** 2
        if nf_hi > nf_lo:
            nf_bands.append({
                "bounds_1d": [float(nf_lo), float(nf_hi)],
                "A_e": lf["cert"]["box"]["A"],
                "T_cert": int(lf["cert"]["T_cert"]),
                "margins": lf["cert"]["margins"],
            })

    nf_max_barro = float((A_peak / A_min) ** 2)
    nf_max_bench075 = float((0.75 / A_min) ** 2)
    return {
        "certified_bands": nf_bands,
        "summary": {
            "nf_min": 1.0,
            "nf_max_certified": nf_max_barro,
            "nf_max_bench075": nf_max_bench075,
            "n_bands": len(nf_bands),
            "T_cert_range": [
                min(b["T_cert"] for b in nf_bands),
                max(b["T_cert"] for b in nf_bands),
            ],
        },
    }


def run_barro_u_frag(parallel: bool = True) -> Dict[str, object]:
    analytics = compute_theorem1_analytics()
    atlas = certify_Ae_atlas(A_floor=0.385, A_ceil=0.780, max_depth=2, parallel=parallel)
    plane = certify_policy_plane(parallel=parallel, atlas=atlas)
    nf_cert = certify_fragmentation_nf(parallel=parallel, atlas=atlas)
    return {
        "analytics": analytics,
        "atlas": atlas,
        "policy_plane": plane,
        "fragmentation": nf_cert,
    }
