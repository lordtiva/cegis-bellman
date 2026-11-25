"""
Dual Rust/Python Outward-Rounded Interval Verifier Bridge.

Exposes all continuous B&B and 50-digit Decimal Interval verification routines
for staying barriers, global super-barriers, witness sub-solutions, adverse exits,
deadlines, and coupled Markov Doob bounds with regime-dependent (A_w, q_w).
"""

from __future__ import annotations

import ctypes
from decimal import Decimal
import math
import os
import platform
from typing import Dict, List, Optional, Tuple
import numpy as np

from core.interval_arith import (
    CANONICAL_A,
    CANONICAL_BETA,
    CANONICAL_Q,
    CANONICAL_ETA,
    CANONICAL_BM,
    CANONICAL_HM,
    F_A,
    dF_dK,
    dF_dL,
    Interval,
    iv_F_A,
    iv_prod_Y,
    iv_prod_dY_dK,
    iv_prod_dY_dL,
    iv_box_worst_u,
    iv_E_plus_exact,
    iv_dE_plus_dK,
)
from core.pwl_basis import (
    build_slope_tables,
    eval_logpwl,
    deriv_bounds_logpwl,
    range_bounds_logpwl,
    iv_eval_logpwl,
    iv_deriv_bounds_logpwl,
)


class _RustBbOut(ctypes.Structure):
    _fields_ = [
        ("certified", ctypes.c_int32),
        ("iv_certified", ctypes.c_int32),
        ("d_ub", ctypes.c_double),
        ("d_ub_iv", ctypes.c_double),
        ("d_lb", ctypes.c_double),
        ("leaf_count", ctypes.c_size_t),
        ("n_ce", ctypes.c_size_t),
    ]


def _load_rust_verifier():
    if os.environ.get("CEGIS_USE_RUST", "1") == "0":
        return None
    sysname = platform.system()
    lib_name = (
        "cegis_bellman_verifier.dll" if sysname == "Windows"
        else ("libcegis_bellman_verifier.dylib" if sysname == "Darwin" else "libcegis_bellman_verifier.so")
    )
    lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rust_verifier", lib_name)
    if not os.path.exists(lib_path):
        return None
    try:
        lib = ctypes.CDLL(lib_path)
        c_dbl_p = ctypes.POINTER(ctypes.c_double)
        c_dbl = ctypes.c_double
        c_sz = ctypes.c_size_t
        c_i32 = ctypes.c_int32

        lib.rs_test_iv_ln.argtypes = [c_dbl, c_dbl_p, c_dbl_p]
        lib.rs_test_iv_ln.restype = None

        lib.rs_verify_staying_barrier_bb_ext.argtypes = [
            c_dbl_p, c_dbl_p, c_dbl_p, c_dbl_p, c_sz, c_dbl, c_dbl,
            c_dbl_p, c_dbl_p, c_dbl_p, c_dbl_p, c_sz, c_dbl, c_dbl,
            c_dbl, c_dbl,
            c_dbl, c_dbl, c_dbl, c_dbl, c_dbl, c_dbl,
            c_dbl, c_dbl,
            c_dbl, c_sz, c_dbl_p, c_sz,
        ]
        lib.rs_verify_staying_barrier_bb_ext.restype = _RustBbOut

        lib.rs_verify_super_barrier_bb_ext.argtypes = [
            c_dbl_p, c_dbl_p, c_dbl_p, c_dbl_p, c_sz, c_dbl, c_dbl,
            c_dbl_p, c_dbl_p, c_dbl_p, c_dbl_p, c_sz, c_dbl, c_dbl,
            c_dbl, c_dbl, c_dbl, c_dbl, c_dbl, c_dbl,
            c_dbl, c_dbl, c_dbl,
            c_dbl, c_dbl, c_i32, c_sz, c_sz, c_dbl_p, c_sz,
        ]
        lib.rs_verify_super_barrier_bb_ext.restype = _RustBbOut

        lib.rs_verify_adverse_exit_bb_ext.argtypes = [
            c_dbl_p, c_dbl_p, c_dbl_p, c_dbl_p, c_sz, c_dbl, c_dbl,
            c_dbl, c_dbl, c_dbl, c_dbl, c_dbl, c_dbl, c_dbl,
            c_dbl, c_dbl, c_dbl, c_dbl, c_dbl, c_i32,
            c_dbl, c_sz, c_i32, c_dbl_p, c_sz,
        ]
        lib.rs_verify_adverse_exit_bb_ext.restype = _RustBbOut
        return lib
    except Exception:
        return None


_RUST_LIB = _load_rust_verifier()


def get_rust_lib():
    return _RUST_LIB


def using_rust_verifier() -> bool:
    return _RUST_LIB is not None and os.environ.get("CEGIS_USE_RUST", "1") != "0"


def prod_Y(A: float, K: np.ndarray, L: np.ndarray, h_m: float = CANONICAL_HM, ak_mode: bool = False) -> np.ndarray:
    if not ak_mode:
        return F_A(A, K, L)
    return np.where(K < h_m, F_A(A, K, L), (K / h_m) * F_A(A, h_m, L))


def prod_dY_dK_bounds(
    A: float, xL: np.ndarray, xR: np.ndarray, LL: np.ndarray, LR: np.ndarray,
    h_m: float = CANONICAL_HM, ak_mode: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    px_hi = np.clip(LR / 4.0, xL, xR)
    lo_ces = np.minimum(dF_dK(A, xL, LL), dF_dK(A, xR, LL))
    hi_ces = np.maximum(np.maximum(dF_dK(A, xL, LR), dF_dK(A, xR, LR)), dF_dK(A, px_hi, LR))
    if not ak_mode:
        return lo_ces, hi_ces
    ak_lo = F_A(A, h_m, LL) / h_m
    ak_hi = F_A(A, h_m, LR) / h_m
    only_ak = xL >= h_m
    only_ces = xR <= h_m
    lo = np.where(only_ak, ak_lo, np.where(only_ces, lo_ces, np.minimum(lo_ces, ak_lo)))
    hi = np.where(only_ak, ak_hi, np.where(only_ces, hi_ces, np.maximum(hi_ces, ak_hi)))
    return lo, hi


def prod_dY_dL_bounds(
    A: float, xL: np.ndarray, xR: np.ndarray, LL: np.ndarray, LR: np.ndarray,
    h_m: float = CANONICAL_HM, ak_mode: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    pL_hi = np.clip(xR / 4.0, LL, LR)
    lo_ces = np.minimum(dF_dL(A, xL, LL), dF_dL(A, xL, LR))
    hi_ces = np.maximum(np.maximum(dF_dL(A, xR, LL), dF_dL(A, xR, LR)), dF_dL(A, xR, pL_hi))
    if not ak_mode:
        return lo_ces, hi_ces
    pL_h = np.clip(h_m / 4.0, LL, LR)
    dFh_lo = np.minimum(dF_dL(A, h_m, LL), dF_dL(A, h_m, LR))
    dFh_hi = np.maximum(np.maximum(dF_dL(A, h_m, LL), dF_dL(A, h_m, LR)), dF_dL(A, h_m, pL_h))
    ak_lo = (xL / h_m) * dFh_lo
    ak_hi = (xR / h_m) * dFh_hi
    only_ak = xL >= h_m
    only_ces = xR <= h_m
    lo = np.where(only_ak, ak_lo, np.where(only_ces, lo_ces, np.minimum(lo_ces, ak_lo)))
    hi = np.where(only_ak, ak_hi, np.where(only_ces, hi_ces, np.maximum(hi_ces, ak_hi)))
    return lo, hi


def verify_staying_barrier_bb(
    B_pwl: Dict[str, object],
    A_hi: float = CANONICAL_A[1],
    q_hi: float = CANONICAL_Q[1],
    b_lo: float = CANONICAL_BETA[0],
    b_hi: float = CANONICAL_BETA[1],
    e_lo: float = CANONICAL_ETA[0],
    e_hi: float = CANONICAL_ETA[1],
    tol: float = 2e-4,
    max_iter: int = 45,
    B_ev_pwl: Optional[Dict[str, object]] = None,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    p_ruin: float = 0.0,
    v_ruin: float = 0.0,
) -> Dict[str, object]:
    """Certify staying Bellman inequality on [b_m, h_m]^2 x [0, 1)."""
    B_ev = B_pwl if B_ev_pwl is None else B_ev_pwl
    if using_rust_verifier():
        ks_l = np.ascontiguousarray(B_pwl["ks"], dtype=np.float64)
        lks_l = np.ascontiguousarray(B_pwl["lks"], dtype=np.float64)
        vals_l = np.ascontiguousarray(B_pwl["vals"], dtype=np.float64)
        sl_l = np.ascontiguousarray(B_pwl["slopes"], dtype=np.float64)
        ks_e = np.ascontiguousarray(B_ev["ks"], dtype=np.float64)
        lks_e = np.ascontiguousarray(B_ev["lks"], dtype=np.float64)
        vals_e = np.ascontiguousarray(B_ev["vals"], dtype=np.float64)
        sl_e = np.ascontiguousarray(B_ev["slopes"], dtype=np.float64)
        c_dbl_p = ctypes.POINTER(ctypes.c_double)
        ce_buf = np.empty(64 * 4, dtype=np.float64)
        res = _RUST_LIB.rs_verify_staying_barrier_bb_ext(
            ks_l.ctypes.data_as(c_dbl_p), lks_l.ctypes.data_as(c_dbl_p),
            vals_l.ctypes.data_as(c_dbl_p), sl_l.ctypes.data_as(c_dbl_p),
            len(ks_l), float(B_pwl["s_lo"]), float(B_pwl["s_hi"]),
            ks_e.ctypes.data_as(c_dbl_p), lks_e.ctypes.data_as(c_dbl_p),
            vals_e.ctypes.data_as(c_dbl_p), sl_e.ctypes.data_as(c_dbl_p),
            len(ks_e), float(B_ev["s_lo"]), float(B_ev["s_hi"]),
            float(b_m), float(h_m),
            float(A_hi), float(q_hi), float(b_lo), float(b_hi), float(e_lo), float(e_hi),
            float(p_ruin), float(v_ruin),
            float(tol), int(max_iter), ce_buf.ctypes.data_as(c_dbl_p), 64,
        )
        ces = [(float(ce_buf[4 * i]), float(ce_buf[4 * i + 1]), float(ce_buf[4 * i + 2]), float(ce_buf[4 * i + 3])) for i in range(res.n_ce)]
        return {
            "certified": bool(res.certified),
            "d_ub": float(res.d_ub),
            "d_ub_iv": float(res.d_ub_iv),
            "d_lb": float(res.d_lb),
            "leaf_count": int(res.leaf_count),
            "counterexamples": ces,
            "iv_certified": bool(res.iv_certified),
        }
    raise RuntimeError("Native Rust verifier required for 3D staying barrier B&B; compile via core/rust_verifier/build.py")


def verify_super_barrier_bb(
    V_self_pwl: Dict[str, object],
    EV_pwl: Dict[str, object],
    Av: float,
    bL: float,
    bR: float,
    q_hi: float = CANONICAL_Q[1],
    eL: float = CANONICAL_ETA[0],
    eU: float = CANONICAL_ETA[1],
    tol: float = 3e-4,
    ak_mode: bool = False,
    max_iter: int = 55,
    max_boxes: int = 350_000,
    p_ruin: float = 0.0,
    v_ruin: float = 0.0,
    h_safe: float = CANONICAL_HM,
) -> Dict[str, object]:
    """Continuously certify log-PWL super-barrier V_self(K) on (0, inf) x [bL, bR]."""
    ks_s = V_self_pwl["ks"]
    ks_e = EV_pwl["ks"]
    x_lo = float(ks_s[0])
    x_cut = float(ks_s[-1])
    s_tail = float(V_self_pwl["s_lo"])
    D_hi = float(V_self_pwl["s_hi"])
    s_tail_e = float(EV_pwl["s_lo"])
    D_hi_e = float(EV_pwl["s_hi"])

    assert float(np.min(EV_pwl["slopes"])) >= -1e-12 and s_tail_e >= 0.0 and D_hi_e >= 0.0, (
        f"EV_pwl is not non-decreasing: min_slope={np.min(EV_pwl['slopes'])}"
    )
    assert float(np.min(V_self_pwl["slopes"])) >= -1e-12 and s_tail >= 0.0 and D_hi >= 0.0, (
        "V_self_pwl must be non-decreasing"
    )

    iv_Av = Interval(str(Av))
    iv_q = Interval(str(q_hi))
    iv_eL = Interval(str(eL))
    iv_eU = Interval(str(eU))
    iv_one = Interval("1")
    iv_xlo = Interval(x_lo)
    iv_xcut = Interval(x_cut)
    iv_s_tail = Interval(s_tail)
    iv_D_hi = Interval(D_hi)
    iv_s_tail_e = Interval(s_tail_e)
    iv_D_hi_e = Interval(D_hi_e)
    iv_vs0 = Interval(float(V_self_pwl["vals"][0]))
    iv_ve0 = Interval(float(EV_pwl["vals"][0]))
    iv_vs_end = Interval(float(V_self_pwl["vals"][-1]))
    iv_ve_end = Interval(float(EV_pwl["vals"][-1]))
    iv_p_ruin = Interval(str(p_ruin))
    iv_omp = iv_one - iv_p_ruin
    iv_pv = iv_p_ruin * Interval(str(v_ruin))

    iv_r_top = iv_q + iv_F_A(iv_Av, iv_xlo, iv_one) / iv_xlo
    assert iv_r_top.hi < Decimal("1"), f"Lower tail contraction failed at x_lo={x_lo}: r_top={iv_r_top.hi}"

    def iv_tails_for_b(bv_float: float) -> Tuple[Interval, Interval]:
        iv_b = Interval(str(bv_float))
        iv_b_lo_eff = iv_b * iv_omp if (p_ruin > 0.0 and x_lo <= h_safe) else iv_b
        iv_c_slo = iv_eL + iv_b_lo_eff * iv_s_tail_e
        assert (iv_c_slo - iv_s_tail).lo >= Decimal("0"), (
            f"Lower tail log(x) coeff negative at b={bv_float}: {(iv_c_slo - iv_s_tail).lo}"
        )
        iv_s_lo_opt = (iv_b_lo_eff * iv_s_tail_e) / iv_c_slo
        iv_shift_lo = (iv_b * iv_pv) if (p_ruin > 0.0 and x_lo <= h_safe) else Interval("0")
        iv_tail_lo = (
            iv_eL * ((iv_one - iv_s_lo_opt) * iv_xlo).ln()
            + iv_b_lo_eff * iv_s_tail_e * iv_s_lo_opt.ln()
            + iv_c_slo * iv_r_top.ln()
            + iv_b_lo_eff * iv_ve0
            + iv_shift_lo
            - iv_vs0
        )

        assert not ak_mode, "AK mode tail not used in v0.1 core"
        iv_F_inf = iv_Av * Interval("2").pow_half_int(3)
        iv_Y_end = iv_q * iv_xcut + iv_F_inf
        assert iv_Y_end.hi < iv_xcut.lo, f"Upper tail cut x_cut={x_cut} too small vs Y_end={iv_Y_end.hi}"
        iv_V1 = iv_eval_logpwl(EV_pwl, iv_one)
        idx1 = max(0, int(np.searchsorted(ks_e, 1.0)) - 1)
        sl_min_dec = Decimal("1e30")
        for ii in range(idx1, len(ks_e) - 1):
            seg_sl = (Interval(float(EV_pwl["vals"][ii + 1])) - Interval(float(EV_pwl["vals"][ii]))) / (
                Interval(float(ks_e[ii + 1])).ln() - Interval(float(ks_e[ii])).ln()
            ) / Interval(float(ks_e[ii + 1]))
            sl_min_dec = min(sl_min_dec, seg_sl.lo)
        iv_sl_min = Interval._raw(sl_min_dec, sl_min_dec)
        iv_tail_hi_lt1 = iv_eU * iv_Y_end.ln() + iv_b * iv_V1 - iv_vs_end

        assert sl_min_dec > Decimal("0"), f"Non-positive EV slope on [1, x_cut]: {sl_min_dec}"
        assert iv_D_hi.lo > iv_eU.hi and iv_xcut.lo > iv_F_inf.hi
        iv_c_star = iv_eU / (iv_b * iv_sl_min)
        iv_x_zero = (iv_xcut - iv_F_inf) / iv_q
        iv_x_cross = (iv_xcut + iv_c_star - iv_F_inf) / iv_q
        iv_x_peak = (iv_D_hi * (iv_xcut - iv_F_inf)) / ((iv_D_hi - iv_eU) * iv_q)
        assert iv_x_cross.lo > iv_xcut.hi and iv_x_peak.lo > iv_x_zero.hi

        def _iv_g1(iv_x: Interval) -> Interval:
            iv_Yt = iv_q * iv_x + iv_F_inf
            return (
                iv_eU * iv_c_star.ln()
                + iv_b * (iv_ve_end + iv_sl_min * (iv_Yt - iv_c_star - iv_xcut))
                - (iv_vs_end + iv_D_hi * (iv_x / iv_xcut).ln())
            )

        iv_g2_peak = (
            iv_eU * (iv_q * iv_x_peak + iv_F_inf - iv_xcut).ln()
            + iv_b * iv_ve_end
            - (iv_vs_end + iv_D_hi * (iv_x_peak / iv_xcut).ln())
        )
        tail_mid_hi = max(_iv_g1(iv_xcut).hi, _iv_g1(iv_x_cross).hi, iv_g2_peak.hi)
        iv_c_dhi = iv_eU + iv_b * iv_D_hi_e
        assert (iv_c_dhi - iv_D_hi).hi <= Decimal("0"), (
            f"Upper tail log(x) coeff positive: {(iv_c_dhi - iv_D_hi).hi}"
        )
        iv_s_hi_opt = (iv_b * iv_D_hi_e) / iv_c_dhi
        iv_tail_hi_log = (
            iv_eU * (iv_one - iv_s_hi_opt).ln()
            + iv_b * iv_D_hi_e * iv_s_hi_opt.ln()
            + iv_c_dhi * (iv_Y_end / iv_xcut).ln()
            + iv_eU * iv_xcut.ln()
            + iv_b * iv_ve_end
            - iv_vs_end
        )
        hi_all = max(iv_tail_hi_lt1.hi, tail_mid_hi, iv_tail_hi_log.hi)
        lo_all = max(iv_tail_hi_lt1.lo, iv_tail_hi_log.lo)
        return iv_tail_lo, Interval._raw(lo_all, hi_all)

    iv_t_lo_L, iv_t_hi_L = iv_tails_for_b(bL)
    iv_t_lo_R, iv_t_hi_R = iv_tails_for_b(bR)
    tail_iv_hi = float(Interval._raw(
        max(iv_t_lo_L.lo, iv_t_hi_L.lo, iv_t_lo_R.lo, iv_t_hi_R.lo),
        max(iv_t_lo_L.hi, iv_t_hi_L.hi, iv_t_lo_R.hi, iv_t_hi_R.hi),
    ).to_float_bounds()[1])
    tail_lo_hi = float(Interval._raw(iv_t_lo_L.lo, max(iv_t_lo_L.hi, iv_t_lo_R.hi)).to_float_bounds()[1])
    tail_hi_hi = float(Interval._raw(iv_t_hi_L.lo, max(iv_t_hi_L.hi, iv_t_hi_R.hi)).to_float_bounds()[1])
    tail_max = tail_iv_hi

    assert using_rust_verifier(), "Native Rust verifier required for 3D super-barrier B&B"
    ks_s_c = np.ascontiguousarray(V_self_pwl["ks"], dtype=np.float64)
    lks_s_c = np.ascontiguousarray(V_self_pwl["lks"], dtype=np.float64)
    vals_s_c = np.ascontiguousarray(V_self_pwl["vals"], dtype=np.float64)
    sl_s_c = np.ascontiguousarray(V_self_pwl["slopes"], dtype=np.float64)
    ks_e_c = np.ascontiguousarray(EV_pwl["ks"], dtype=np.float64)
    lks_e_c = np.ascontiguousarray(EV_pwl["lks"], dtype=np.float64)
    vals_e_c = np.ascontiguousarray(EV_pwl["vals"], dtype=np.float64)
    sl_e_c = np.ascontiguousarray(EV_pwl["slopes"], dtype=np.float64)
    c_dbl_p = ctypes.POINTER(ctypes.c_double)
    ce_buf = np.empty(64 * 4, dtype=np.float64)
    res = _RUST_LIB.rs_verify_super_barrier_bb_ext(
        ks_s_c.ctypes.data_as(c_dbl_p), lks_s_c.ctypes.data_as(c_dbl_p),
        vals_s_c.ctypes.data_as(c_dbl_p), sl_s_c.ctypes.data_as(c_dbl_p),
        len(ks_s_c), float(s_tail), float(D_hi),
        ks_e_c.ctypes.data_as(c_dbl_p), lks_e_c.ctypes.data_as(c_dbl_p),
        vals_e_c.ctypes.data_as(c_dbl_p), sl_e_c.ctypes.data_as(c_dbl_p),
        len(ks_e_c), float(s_tail_e), float(D_hi_e),
        float(Av), float(q_hi), float(bL), float(bR), float(eL), float(eU),
        float(p_ruin), float(v_ruin), float(h_safe),
        float(tail_max), float(tol), 1 if ak_mode else 0, int(max_iter), int(max_boxes),
        ce_buf.ctypes.data_as(c_dbl_p), 64,
    )
    ces = [(float(ce_buf[4 * i]), float(ce_buf[4 * i + 1]), float(ce_buf[4 * i + 2]), float(ce_buf[4 * i + 3])) for i in range(res.n_ce)]
    return {
        "certified": bool(res.certified),
        "d_ub": float(res.d_ub),
        "d_ub_iv": float(res.d_ub_iv),
        "d_lb": float(res.d_lb),
        "tail_max": float(tail_iv_hi),
        "tail_lo": float(tail_lo_hi),
        "tail_hi": float(tail_hi_hi),
        "leaf_count": int(res.leaf_count),
        "counterexamples": ces,
        "iv_certified": bool(res.iv_certified),
    }


def verify_witness_subsolution_bb(
    W_pwl: Dict[str, object],
    EW_pwl: Dict[str, object],
    kp_pwl: Dict[str, object],
    L_pwl: Dict[str, object],
    A_lo: float,
    q_lo: float,
    bL: float,
    bR: float,
    eL: float = CANONICAL_ETA[0],
    eU: float = CANONICAL_ETA[1],
    k_domain: Tuple[float, float] = (CANONICAL_BM, 3.0),
    ak_mode: bool = False,
    tol: float = 2e-4,
    max_iter: int = 35,
    interval_check: bool = True,
    p_ruin: float = 0.0,
    v_ruin: float = 0.0,
    h_safe: float = CANONICAL_HM,
) -> Dict[str, object]:
    """Certify 1D witness Bellman subsolution via adaptive B&B + 50-digit Interval audit."""
    k_a, k_b = k_domain
    all_ks = np.unique(np.concatenate([
        [k_a, k_b], W_pwl["ks"], kp_pwl["ks"], L_pwl["ks"], np.geomspace(k_a, k_b, 96),
    ]))
    all_ks = all_ks[(all_ks >= k_a) & (all_ks <= k_b)]
    if p_ruin > 0.0 and k_a < h_safe < k_b:
        all_ks = np.unique(np.concatenate([all_ks, [h_safe]]))

    omp = 1.0 - p_ruin
    pv = p_ruin * v_ruin

    L_grid = np.clip(eval_logpwl(L_pwl, all_ks), 0.0, 0.999)
    kp_grid = eval_logpwl(kp_pwl, all_ks)
    c_grid = q_lo * all_ks + prod_Y(A_lo, all_ks, L_grid, h_m=h_safe, ak_mode=ak_mode) - kp_grid
    if np.any(c_grid <= 1e-12) or np.any(kp_grid < k_a - 1e-12) or (not ak_mode and np.any(kp_grid > k_b + 1e-12)):
        bad_idx = int(np.argmin(np.minimum(c_grid, kp_grid - k_a if ak_mode else np.minimum(kp_grid - k_a, k_b - kp_grid))))
        return {
            "certified": False, "d_ub": 1e9, "d_ub_iv": 1e9, "d_lb": 1e9,
            "counterexamples": [(float(all_ks[bad_idx]), 1e9)], "iv_certified": False,
        }

    lc_g = np.log(c_grid)
    ll_g = np.log(1.0 - L_grid)
    u_g = np.minimum(eL * lc_g + (1.0 - eL) * ll_g, eU * lc_g + (1.0 - eU) * ll_g)
    ew_g = eval_logpwl(EW_pwl, kp_grid)
    if p_ruin > 0.0:
        ew_g = np.where(all_ks < h_safe, omp * ew_g + pv, ew_g)
    b_g = np.where(ew_g < 0.0, bR, bL)
    res_g = eval_logpwl(W_pwl, all_ks) - (u_g + b_g * ew_g)
    i_w = int(np.argmax(res_g))
    best_lb = float(res_g[i_w])
    counterexamples: List[Tuple[float, float]] = [(float(all_ks[i_w]), best_lb)]
    target = max(best_lb + tol, -2.0e-4) if best_lb < -tol else (best_lb + tol)

    bxL, bxR = all_ks[:-1].copy(), all_ks[1:].copy()
    d_ub = None
    rem_appended = False
    done_L: List[np.ndarray] = []
    done_R: List[np.ndarray] = []

    smin_W, smax_W = build_slope_tables(W_pwl["slopes"])
    smin_EW, smax_EW = build_slope_tables(EW_pwl["slopes"])
    smin_kp, smax_kp = build_slope_tables(kp_pwl["slopes"])
    smin_L, smax_L = build_slope_tables(L_pwl["slopes"])

    def _iv_prod(aL: np.ndarray, aH: np.ndarray, bL_v: np.ndarray, bH_v: np.ndarray):
        p1, p2, p3, p4 = aL * bL_v, aL * bH_v, aH * bL_v, aH * bH_v
        return np.minimum(np.minimum(p1, p2), np.minimum(p3, p4)), np.maximum(np.maximum(p1, p2), np.maximum(p3, p4))

    for _it in range(max_iter):
        LL_lo, LL_hi = range_bounds_logpwl(L_pwl, bxL, bxR)
        LL_lo_c = np.clip(LL_lo, 0.0, 0.9999)
        LL_hi_c = np.clip(LL_hi, 0.0, 0.9999)
        kp_lo, kp_hi = range_bounds_logpwl(kp_pwl, bxL, bxR)
        if np.any(LL_hi >= 0.9999) or np.any(kp_lo < k_a) or (not ak_mode and np.any(kp_hi > k_b)):
            return {
                "certified": False, "d_ub": 1e6, "d_ub_iv": 1e6, "d_lb": best_lb,
                "counterexamples": counterexamples, "iv_certified": False,
            }

        Y_min = q_lo * bxL + prod_Y(A_lo, bxL, LL_lo_c, h_m=h_safe, ak_mode=ak_mode)
        Y_max = q_lo * bxR + prod_Y(A_lo, bxR, LL_hi_c, h_m=h_safe, ak_mode=ak_mode)
        c_min_box = Y_min - kp_hi
        c_max_box = Y_max - kp_lo
        infeasible = c_min_box <= 1e-12
        lc_min = np.log(np.maximum(c_min_box, 1e-300))
        ll_min = np.log(np.maximum(1.0 - LL_hi_c, 1e-300))
        u_min_box = np.minimum(eL * lc_min + (1.0 - eL) * ll_min, eU * lc_min + (1.0 - eU) * ll_min)
        ew_lo, ew_hi = range_bounds_logpwl(EW_pwl, kp_lo, kp_hi)
        if p_ruin > 0.0:
            xr_ruin = bxR <= h_safe
            ew_lo = np.where(xr_ruin, omp * ew_lo + pv, ew_lo)
            ew_hi = np.where(xr_ruin, omp * ew_hi + pv, ew_hi)
        bew_lb = np.minimum(
            np.where(ew_lo < 0.0, bR * ew_lo, bL * ew_lo),
            np.where(ew_hi < 0.0, bR * ew_hi, bL * ew_hi),
        )
        _, W_max_box = range_bounds_logpwl(W_pwl, bxL, bxR)
        ub_mono = np.where(infeasible, 1e6, W_max_box - (u_min_box + bew_lb))

        xm = 0.5 * (bxL + bxR)
        Lm = np.clip(eval_logpwl(L_pwl, xm), 0.0, 0.9999)
        kpm = eval_logpwl(kp_pwl, xm)
        cm = q_lo * xm + prod_Y(A_lo, xm, Lm, h_m=h_safe, ak_mode=ak_mode) - kpm
        ewm = eval_logpwl(EW_pwl, kpm)
        if p_ruin > 0.0:
            ewm = np.where(bxR <= h_safe, omp * ewm + pv, ewm)
        bm = np.where(ewm < 0.0, bR, bL)
        um = np.minimum(eL * np.log(np.maximum(cm, 1e-300)) + (1.0 - eL) * np.log(1.0 - Lm),
                        eU * np.log(np.maximum(cm, 1e-300)) + (1.0 - eU) * np.log(1.0 - Lm))
        res_m = np.where(cm > 1e-12, eval_logpwl(W_pwl, xm) - (um + bm * ewm), 1e6)

        dW_lo, dW_hi = deriv_bounds_logpwl(W_pwl, smin_W, smax_W, bxL, bxR)
        dL_lo, dL_hi = deriv_bounds_logpwl(L_pwl, smin_L, smax_L, bxL, bxR)
        dkp_lo, dkp_hi = deriv_bounds_logpwl(kp_pwl, smin_kp, smax_kp, bxL, bxR)
        dEW_lo, dEW_hi = deriv_bounds_logpwl(EW_pwl, smin_EW, smax_EW, kp_lo, kp_hi)
        if p_ruin > 0.0:
            xr_ruin = bxR <= h_safe
            dEW_lo = np.where(xr_ruin, omp * dEW_lo, dEW_lo)
            dEW_hi = np.where(xr_ruin, omp * dEW_hi, dEW_hi)
        YK_lo, YK_hi = prod_dY_dK_bounds(A_lo, bxL, bxR, LL_lo_c, LL_hi_c, h_m=h_safe, ak_mode=ak_mode)
        YK_lo = q_lo + YK_lo; YK_hi = q_lo + YK_hi
        YL_lo, YL_hi = prod_dY_dL_bounds(A_lo, bxL, bxR, LL_lo_c, LL_hi_c, h_m=h_safe, ak_mode=ak_mode)
        YLdL_lo, YLdL_hi = _iv_prod(YL_lo, YL_hi, dL_lo, dL_hi)
        dc_lo = YK_lo + YLdL_lo - dkp_hi
        dc_hi = YK_hi + YLdL_hi - dkp_lo
        ec_lo = np.where(c_min_box >= 1.0, eU, eL)
        ec_hi = np.where(c_max_box < 1.0, eL, eU)
        duc_lo, duc_hi = _iv_prod(ec_lo / np.maximum(c_max_box, 1e-300), ec_hi / np.maximum(c_min_box, 1e-300), dc_lo, dc_hi)
        dul_lo, dul_hi = _iv_prod((1.0 - ec_hi) / np.maximum(1.0 - LL_lo_c, 1e-300), (1.0 - ec_lo) / np.maximum(1.0 - LL_hi_c, 1e-300), dL_lo, dL_hi)
        du_lo = duc_lo - dul_hi
        du_hi = duc_hi - dul_lo
        dEWz_lo, dEWz_hi = _iv_prod(dEW_lo, dEW_hi, dkp_lo, dkp_hi)
        bv_lo = np.where(ew_lo >= 0.0, bL, np.where(ew_hi < 0.0, bR, bL))
        bv_hi = np.where(ew_lo >= 0.0, bL, np.where(ew_hi < 0.0, bR, bR))
        dbEW_lo, dbEW_hi = _iv_prod(bv_lo, bv_hi, dEWz_lo, dEWz_hi)
        df_lo = dW_lo - du_hi - dbEW_hi
        df_hi = dW_hi - du_lo - dbEW_lo
        ub_cent = np.where(infeasible, 1e6, res_m + np.maximum(np.abs(df_lo), np.abs(df_hi)) * 0.5 * (bxR - bxL))
        ub = np.minimum(ub_mono, ub_cent)

        ib = int(np.argmax(res_m))
        if res_m[ib] > best_lb:
            best_lb = float(res_m[ib])
            target = max(best_lb + tol, -2.0e-4) if best_lb < -tol else (best_lb + tol)
            counterexamples.append((float(xm[ib]), best_lb))

        keep = ub > target
        if np.any(~keep):
            done_L.append(bxL[~keep])
            done_R.append(bxR[~keep])
        if not np.any(keep):
            d_ub = target
            break

        bxL, bxR = bxL[keep], bxR[keep]
        xm = xm[keep]
        if len(bxL) > 80_000:
            done_L.append(bxL); done_R.append(bxR)
            rem_appended = True
            break
        bxL = np.concatenate([bxL, xm])
        bxR = np.concatenate([xm, bxR])

    if d_ub is None:
        d_ub = float(np.max(ub))
        if not rem_appended and len(bxL) > 0:
            done_L.append(bxL); done_R.append(bxR)
        xm = 0.5 * (bxL + bxR)
        for j in range(min(6, len(xm))):
            counterexamples.append((float(xm[j]), float(ub[j])))

    iv_certified = False
    d_ub_iv = float(d_ub)
    if interval_check and d_ub <= 0.0 and len(done_L) > 0:
        iv_A = Interval(str(A_lo))
        iv_q = Interval(str(q_lo))
        iv_bL = Interval(str(bL))
        iv_bR = Interval(str(bR))
        iv_eL = Interval(str(eL))
        iv_eU = Interval(str(eU))
        iv_one = Interval("1")
        iv_ka = Interval(str(k_a))
        iv_kb = Interval(str(k_b))
        iv_p_r = Interval(str(p_ruin))
        iv_omp = iv_one - iv_p_r
        iv_pv = iv_p_r * Interval(str(v_ruin))
        iv_hs = Interval(str(h_safe))
        term_L = np.concatenate(done_L)
        term_R = np.concatenate(done_R)
        iv_max_res = Decimal("-1e9")
        ok_all = True

        def _audit_seg(kL_d: Decimal, kR_d: Decimal, depth: int = 0) -> Decimal:
            nonlocal ok_all
            k_iv = Interval._raw(kL_d, kR_d)
            has_ruin = p_ruin > 0.0 and kR_d <= iv_hs.lo
            if p_ruin > 0.0 and kL_d < iv_hs.hi and kR_d > iv_hs.lo:
                mid_s = iv_hs.lo if kL_d < iv_hs.lo < kR_d else (kL_d + kR_d) / Decimal("2")
                return max(_audit_seg(kL_d, mid_s, depth + 1), _audit_seg(mid_s, kR_d, depth + 1))
            L_iv = iv_eval_logpwl(L_pwl, k_iv)
            kp_iv = iv_eval_logpwl(kp_pwl, k_iv)
            if L_iv.lo < 0 or L_iv.hi >= 1 or kp_iv.lo < iv_ka.lo or (not ak_mode and kp_iv.hi > iv_kb.hi):
                ok_all = False
                return Decimal("1e9")
            c_iv = iv_q * k_iv + iv_prod_Y(iv_A, k_iv, L_iv, h_m=h_safe, ak_mode=ak_mode) - kp_iv
            if c_iv.lo <= 0:
                if depth < 8:
                    mid_d = (kL_d + kR_d) / Decimal("2")
                    return max(_audit_seg(kL_d, mid_d, depth + 1), _audit_seg(mid_d, kR_d, depth + 1))
                ok_all = False
                return Decimal("1e9")
            lc_iv = c_iv.ln()
            ll_iv = (iv_one - L_iv).ln()
            u1 = iv_eL * lc_iv + (iv_one - iv_eL) * ll_iv
            u2 = iv_eU * lc_iv + (iv_one - iv_eU) * ll_iv
            u_iv = Interval._raw(min(u1.lo, u2.lo), min(u1.hi, u2.hi))
            ew_iv_raw = iv_eval_logpwl(EW_pwl, kp_iv)
            ew_iv = (iv_omp * ew_iv_raw + iv_pv) if has_ruin else ew_iv_raw
            bew_lo = min(
                (iv_bR * ew_iv).lo if ew_iv.lo < 0 else (iv_bL * ew_iv).lo,
                (iv_bR * ew_iv).lo if ew_iv.hi < 0 else (iv_bL * ew_iv).lo,
            )
            W_iv = iv_eval_logpwl(W_pwl, k_iv)
            res_hi = W_iv.hi - (u_iv.lo + bew_lo)
            if res_hi <= Decimal("0"):
                return res_hi

            xm_d = (kL_d + kR_d) / Decimal("2")
            xm_iv = Interval._raw(xm_d, xm_d)
            hx_iv = Interval._raw((kR_d - kL_d) / Decimal("2"), (kR_d - kL_d) / Decimal("2"))
            Lm_iv = iv_eval_logpwl(L_pwl, xm_iv)
            kpm_iv = iv_eval_logpwl(kp_pwl, xm_iv)
            cm_iv = iv_q * xm_iv + iv_prod_Y(iv_A, xm_iv, Lm_iv, h_m=h_safe, ak_mode=ak_mode) - kpm_iv
            if cm_iv.lo <= 0:
                ok_all = False
                return Decimal("1e9")
            lcm_iv = cm_iv.ln()
            llm_iv = (iv_one - Lm_iv).ln()
            um1 = iv_eL * lcm_iv + (iv_one - iv_eL) * llm_iv
            um2 = iv_eU * lcm_iv + (iv_one - iv_eU) * llm_iv
            um_lo = min(um1.lo, um2.lo)
            ewm_iv_raw = iv_eval_logpwl(EW_pwl, kpm_iv)
            ewm_iv = (iv_omp * ewm_iv_raw + iv_pv) if has_ruin else ewm_iv_raw
            bewm_lo = min(
                (iv_bR * ewm_iv).lo if ewm_iv.lo < 0 else (iv_bL * ewm_iv).lo,
                (iv_bR * ewm_iv).lo if ewm_iv.hi < 0 else (iv_bL * ewm_iv).lo,
            )
            res_m_hi = iv_eval_logpwl(W_pwl, xm_iv).hi - (um_lo + bewm_lo)

            dW_iv = iv_deriv_bounds_logpwl(W_pwl, k_iv)
            dL_iv = iv_deriv_bounds_logpwl(L_pwl, k_iv)
            dkp_iv = iv_deriv_bounds_logpwl(kp_pwl, k_iv)
            dEW_iv_raw = iv_deriv_bounds_logpwl(EW_pwl, kp_iv)
            dEW_iv = (iv_omp * dEW_iv_raw) if has_ruin else dEW_iv_raw
            YK_iv = iv_q + iv_prod_dY_dK(iv_A, k_iv, L_iv, h_m=h_safe, ak_mode=ak_mode)
            YL_iv = iv_prod_dY_dL(iv_A, k_iv, L_iv, h_m=h_safe, ak_mode=ak_mode)
            dc_iv = YK_iv + YL_iv * dL_iv - dkp_iv

            ec_iv = iv_eU if c_iv.lo >= Decimal("1") else (iv_eL if c_iv.hi < Decimal("1") else iv_eL.hull(iv_eU))
            du_iv = (ec_iv / c_iv) * dc_iv - ((iv_one - ec_iv) / (iv_one - L_iv)) * dL_iv
            bv_iv = iv_bL if ew_iv.lo >= Decimal("0") else (iv_bR if ew_iv.hi < Decimal("0") else iv_bL.hull(iv_bR))
            df_iv = dW_iv - du_iv - bv_iv * dEW_iv * dkp_iv
            cent_hi = res_m_hi + (Interval._raw(df_iv.max_abs(), df_iv.max_abs()) * hx_iv).hi
            ub_seg = min(res_hi, cent_hi)
            if ub_seg > Decimal("0") and depth < 8:
                return max(_audit_seg(kL_d, xm_d, depth + 1), _audit_seg(xm_d, kR_d, depth + 1))
            return ub_seg

        for i in range(len(term_L)):
            kL_d = Interval(float(term_L[i])).lo
            kR_d = Interval(float(term_R[i])).hi
            r_seg = _audit_seg(kL_d, kR_d, 0)
            iv_max_res = max(iv_max_res, r_seg)
            if not ok_all:
                break
        iv_certified = bool(ok_all and iv_max_res <= Decimal("0"))
        d_ub_iv = float(Interval._raw(iv_max_res, iv_max_res).to_float_bounds()[1])

    return {
        "certified": bool(d_ub <= 0.0 and (not interval_check or iv_certified)),
        "d_ub": float(d_ub),
        "d_ub_iv": float(d_ub_iv),
        "d_lb": float(best_lb),
        "counterexamples": counterexamples,
        "iv_certified": iv_certified,
    }


def verify_adverse_exit_bb(
    W_pwl: Dict[str, object],
    E_Psi_cont_val: float,
    A_hi: float,
    q_hi: float,
    bL: float,
    bR: float,
    eL: float,
    eU: float,
    a_exit: float,
    l0_exit: float,
    k_range: Tuple[float, float],
    h_m: float = CANONICAL_HM,
    ak_mode: bool = False,
    tol: float = 2e-4,
    max_iter: int = 35,
    interval_check: bool = True,
) -> Dict[str, object]:
    """Certify adverse-exit margin W(K) - (E^+(K, a; l0) + beta * E_Psi_cont_val) > 0 on k_range."""
    k_a, k_b = k_range
    assert using_rust_verifier(), "Native Rust verifier required for adverse exit B&B"
    ks_w = np.ascontiguousarray(W_pwl["ks"], dtype=np.float64)
    lks_w = np.ascontiguousarray(W_pwl["lks"], dtype=np.float64)
    vals_w = np.ascontiguousarray(W_pwl["vals"], dtype=np.float64)
    sl_w = np.ascontiguousarray(W_pwl["slopes"], dtype=np.float64)
    c_dbl_p = ctypes.POINTER(ctypes.c_double)
    ce_buf = np.empty(64 * 2, dtype=np.float64)
    res = _RUST_LIB.rs_verify_adverse_exit_bb_ext(
        ks_w.ctypes.data_as(c_dbl_p), lks_w.ctypes.data_as(c_dbl_p),
        vals_w.ctypes.data_as(c_dbl_p), sl_w.ctypes.data_as(c_dbl_p),
        len(ks_w), float(W_pwl["s_lo"]), float(W_pwl["s_hi"]),
        float(E_Psi_cont_val), float(A_hi), float(q_hi), float(bL), float(bR), float(eL), float(eU),
        float(a_exit), float(l0_exit), float(k_a), float(k_b), float(h_m), 1 if ak_mode else 0,
        float(tol), int(max_iter), 1 if interval_check else 0,
        ce_buf.ctypes.data_as(c_dbl_p), 64,
    )
    ces = [(float(ce_buf[2 * i]), float(ce_buf[2 * i + 1])) for i in range(res.n_ce)]
    return {
        "certified": bool(res.certified),
        "m_lb": float(res.d_ub),
        "m_lb_iv": float(res.d_ub_iv),
        "m_ub": float(res.d_lb),
        "counterexamples": ces,
        "iv_certified": bool(res.iv_certified),
    }


def verify_witness_slope_on_M(
    W_pwl: Dict[str, object],
    m_req: float,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
) -> Tuple[bool, float]:
    ks = W_pwl["ks"]
    vals = W_pwl["vals"]
    iv_m = Interval(str(m_req))
    min_d_lo = Decimal("1e30")
    for i in range(len(ks) - 1):
        if ks[i + 1] <= b_m or ks[i] >= h_m:
            continue
        kR_eff = min(float(ks[i + 1]), h_m)
        sl_log = (Interval(float(vals[i + 1])) - Interval(float(vals[i]))) / (
            Interval(float(ks[i + 1])).ln() - Interval(float(ks[i])).ln()
        )
        if sl_log.lo <= Decimal("0"):
            return False, float(sl_log.lo)
        dW_seg = sl_log / Interval(kR_eff)
        min_d_lo = min(min_d_lo, dW_seg.lo)
        if dW_seg.lo < iv_m.hi:
            return False, float(Interval._raw(dW_seg.lo, dW_seg.lo).to_float_bounds()[0])
    return True, float(Interval._raw(min_d_lo, min_d_lo).to_float_bounds()[0])


def verify_derivative_below_bound(
    EV_pwl: Dict[str, object],
    K_bound: float,
    beta_lo: float,
    A_lo: float,
    q_lo: float,
    a_exit: float,
    l0_exit: float,
    eL: float = CANONICAL_ETA[0],
    eU: float = CANONICAL_ETA[1],
) -> Tuple[bool, float, float]:
    iv_A = Interval(str(A_lo))
    iv_q = Interval(str(q_lo))
    iv_K = Interval(str(K_bound))
    iv_a = Interval(str(a_exit))
    iv_l0 = Interval(str(l0_exit))
    iv_eL = Interval(str(eL))
    iv_eU = Interval(str(eU))
    iv_one = Interval("1")

    two_3_2 = Interval("2").pow_half_int(3)
    t_iv = Interval("1.5") * iv_A * two_3_2 * iv_K.pow_half_int(5) * iv_l0.pow_half_int(1) * (iv_K + iv_l0).pow_half_int(-5)
    c_sup_iv = iv_q * iv_K + iv_F_A(iv_A, iv_K, iv_l0) + (iv_one - iv_l0) * t_iv - iv_a
    c_opt_lo = Decimal("1e30")
    for eta_iv in (iv_eL, iv_eU):
        om_raw = (iv_one - eta_iv) * c_sup_iv / t_iv
        om_L = Interval._raw(min(om_raw.lo, Decimal(1)), min(om_raw.hi, Decimal(1)))
        c_opt_lo = min(c_opt_lo, (c_sup_iv - t_iv * om_L).lo)
    req_rhs = iv_eU / Interval._raw(c_opt_lo, c_opt_lo)

    ks = EV_pwl["ks"]
    vals = EV_pwl["vals"]
    s_lo = float(EV_pwl["s_lo"])
    min_d_lo = (Interval(s_lo) / Interval(float(ks[0]))).lo
    for i in range(len(ks) - 1):
        if ks[i] >= K_bound:
            break
        k_right = min(float(ks[i + 1]), K_bound)
        sl_log = (Interval(float(vals[i + 1])) - Interval(float(vals[i]))) / (
            Interval(float(ks[i + 1])).ln() - Interval(float(ks[i])).ln()
        )
        if sl_log.lo <= Decimal("0"):
            return False, -1e9, float(req_rhs.hi)
        min_d_lo = min(min_d_lo, (sl_log / Interval(k_right)).lo)

    lhs_iv = Interval(str(beta_lo)) * Interval._raw(min_d_lo, min_d_lo)
    margin_iv = lhs_iv - req_rhs
    return bool(margin_iv.lo > Decimal("0")), float(margin_iv.to_float_bounds()[0]), float(lhs_iv.to_float_bounds()[0])


def verify_H2_global_interval(
    W_pwl: Dict[str, object],
    kp80: float,
    L80: float,
    EW_at_kp80_lo: float,
    E_Psi_h_hi: float,
    A_lo: float,
    A_hi: float,
    q_lo: float,
    q_hi: float,
    bL: float,
    bR: float,
    eL: float = CANONICAL_ETA[0],
    eU: float = CANONICAL_ETA[1],
    h_m: float = CANONICAL_HM,
    k_h2: float = 0.80,
) -> Tuple[bool, float]:
    """Certify adverse exit on H2 = [k_h2, inf) in 50-digit Decimal Interval arithmetic."""
    from scipy.optimize import brentq as _brentq

    iv_Al = Interval(str(A_lo)); iv_Ah = Interval(str(A_hi))
    iv_ql = Interval(str(q_lo)); iv_qh = Interval(str(q_hi))
    iv_bL = Interval(str(bL)); iv_bR = Interval(str(bR))
    iv_eL = Interval(str(eL)); iv_eU = Interval(str(eU))
    iv_one = Interval("1")
    iv_h = Interval(str(h_m))
    iv_ep_cont = (iv_bL if E_Psi_h_hi < 0 else iv_bR) * Interval(str(E_Psi_h_hi))

    kp_plus = float(_brentq(lambda K: float(F_A(A_hi, K, 1.0)) - (1.0 - q_hi) * K, 1.0, 200.0))
    iv_kp80 = Interval(kp80)
    iv_L80 = Interval(L80)
    iv_ew = Interval(EW_at_kp80_lo)
    iv_tail_W = (iv_bR if iv_ew.lo < 0 else iv_bL) * iv_ew

    Ks_H2 = np.geomspace(k_h2, max(k_h2 * 1.1, kp_plus), 31)
    min_gap_lo = Decimal("1e30")
    for j in range(30):
        kL_iv = Interval(float(Ks_H2[j]))
        kR_iv = Interval(float(Ks_H2[j + 1]))
        cW_iv = iv_ql * kL_iv + iv_F_A(iv_Al, kL_iv, iv_L80) - iv_kp80
        uW_iv = iv_box_worst_u(cW_iv, iv_L80, iv_eL, iv_eU)
        cE_iv = iv_qh * kR_iv + iv_F_A(iv_Ah, kR_iv, iv_one) - iv_h
        ec_iv = iv_eL if cE_iv.hi < 1 else (iv_eU if cE_iv.lo >= 1 else iv_eL.hull(iv_eU))
        gap_iv = (uW_iv + iv_tail_W) - (ec_iv * cE_iv.ln() + iv_ep_cont)
        min_gap_lo = min(min_gap_lo, gap_iv.lo)

    iv_kpp = Interval(max(k_h2 * 1.1, kp_plus))
    iv_cW_inf = iv_ql * iv_kpp + iv_F_A(iv_Al, iv_kpp, iv_L80) - iv_kp80
    iv_cE_inf = iv_qh * iv_kpp + iv_Ah * Interval("2").pow_half_int(3) - iv_h
    ratio_c = iv_cW_inf / iv_cE_inf
    ratio_q = iv_ql / iv_qh
    min_rat = Interval._raw(min(ratio_c.lo, ratio_q.lo), min(ratio_c.hi, ratio_q.hi))
    gap_inf_iv = iv_eU * min_rat.ln() + (iv_one - iv_eU) * (iv_one - iv_L80).ln() + iv_tail_W - iv_ep_cont
    min_gap_lo = min(min_gap_lo, gap_inf_iv.lo)
    return bool(min_gap_lo > Decimal("0")), float(Interval._raw(min_gap_lo, min_gap_lo).to_float_bounds()[0])


def certify_affine_deadline_interval(
    iv_marg_stay: Interval,
    iv_max_exit: Interval,
    b_max: float,
) -> int:
    iv_bH = Interval(str(b_max))
    assert iv_marg_stay.lo > Decimal("0") and iv_max_exit.hi > Decimal("0")
    T = 1
    while T < 500:
        if (iv_bH.pow_int(T) * iv_max_exit).hi < iv_marg_stay.lo:
            return T
        T += 1
    raise AssertionError(f"Deadline failed to converge in 500 steps: marg={iv_marg_stay}, exit={iv_max_exit}")


def certify_staying_deadline_interval(
    B_pwl: Dict[str, object],
    Psi_pwl: Dict[str, object],
    W_pwl: Dict[str, object],
    b_max: float = CANONICAL_BETA[1],
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    p_ruin: float = 0.0,
) -> Tuple[int, float, float]:
    bm_d = min(Decimal(str(b_m)), Decimal.from_float(float(b_m)))
    hm_d = max(Decimal(str(h_m)), Decimal.from_float(float(h_m)))
    ks = [bm_d, hm_d]
    for p in (B_pwl, Psi_pwl, W_pwl):
        for k in p["ks"]:
            kd = Decimal.from_float(float(k))
            if bm_d < kd < hm_d:
                ks.append(kd)
    for k_grid in np.geomspace(float(b_m), float(h_m), 42)[1:-1]:
        kd = Decimal.from_float(float(k_grid))
        if bm_d < kd < hm_d:
            ks.append(kd)
    ks = sorted(set(ks))

    inf_W_B_lo = Decimal("1e30")
    sup_Psi_B_hi = Decimal("-1e30")
    for kL_d, kR_d in zip(ks[:-1], ks[1:]):
        k_iv = Interval._raw(kL_d, kR_d)
        B_iv = iv_eval_logpwl(B_pwl, k_iv)
        W_iv = iv_eval_logpwl(W_pwl, k_iv)
        Psi_iv = iv_eval_logpwl(Psi_pwl, k_iv)
        inf_W_B_lo = min(inf_W_B_lo, (W_iv - B_iv).lo)
        sup_Psi_B_hi = max(sup_Psi_B_hi, (Psi_iv - B_iv).hi)

    iv_inf = Interval._raw(inf_W_B_lo, inf_W_B_lo)
    iv_sup = Interval._raw(sup_Psi_B_hi, sup_Psi_B_hi)
    iv_b_eff = Interval(str(b_max)) * (Interval("1") - Interval(str(p_ruin)))
    b_eff_hi = float(iv_b_eff.to_float_bounds()[1])
    T = certify_affine_deadline_interval(iv_inf, iv_sup, b_eff_hi)
    return T, float(iv_inf.to_float_bounds()[0]), float(iv_sup.to_float_bounds()[1])


def certify_nonstationary_deadline_interval(
    Psi_pwl: Dict[str, object],
    W_pwl: Dict[str, object],
    J_list: List[Dict[str, object]],
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
) -> Tuple[bool, float, float]:
    assert len(J_list) >= 2
    bm_d = min(Decimal(str(b_m)), Decimal.from_float(float(b_m)))
    hm_d = max(Decimal(str(h_m)), Decimal.from_float(float(h_m)))
    ks = [bm_d, hm_d]
    for p in (Psi_pwl, W_pwl, J_list[0], J_list[-1]):
        for k in p["ks"]:
            kd = Decimal.from_float(float(k))
            if bm_d < kd < hm_d:
                ks.append(kd)
    for k_grid in np.geomspace(float(b_m), float(h_m), 42)[1:-1]:
        kd = Decimal.from_float(float(k_grid))
        if bm_d < kd < hm_d:
            ks.append(kd)
    ks = sorted(set(ks))

    min_j0_psi = Decimal("1e30")
    min_w_jk = Decimal("1e30")
    J0, JK = J_list[0], J_list[-1]
    for kd in ks:
        k_iv = Interval._raw(kd, kd)
        j0_iv = iv_eval_logpwl(J0, k_iv)
        psi_iv = iv_eval_logpwl(Psi_pwl, k_iv)
        w_iv = iv_eval_logpwl(W_pwl, k_iv)
        jk_iv = iv_eval_logpwl(JK, k_iv)
        min_j0_psi = min(min_j0_psi, (j0_iv - psi_iv).lo)
        min_w_jk = min(min_w_jk, (w_iv - jk_iv).lo)

    ok = (min_j0_psi >= Decimal("0")) and (min_w_jk > Decimal("0"))
    return (
        bool(ok),
        float(Interval._raw(min_j0_psi, min_j0_psi).to_float_bounds()[0]),
        float(Interval._raw(min_w_jk, min_w_jk).to_float_bounds()[0]),
    )


def compute_doob_eps0_coupled_pwl_interval(
    B0_pwl: Dict[str, object],
    B1_pwl: Dict[str, object],
    W0_pwl: Dict[str, object],
    W1_pwl: Dict[str, object],
    Psi0_pwl: Dict[str, object],
    Psi1_pwl: Dict[str, object],
    b_max: float = CANONICAL_BETA[1],
    A0_hi: float = CANONICAL_A[1],
    A1_hi: float = CANONICAL_A[1],
    q0_hi: float = CANONICAL_Q[1],
    q1_hi: float = CANONICAL_Q[1],
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
) -> Dict[str, object]:
    """
    Rigorous 50-digit Interval Doob uniform escape bound for coupled 2-regime Markov
    staying barriers (B0, B1) with regime-specific (A_w, q_w) and constant s_hi = 0.0 on [h_m, inf).
    """
    bm_d = min(Decimal(str(b_m)), Decimal.from_float(float(b_m)))
    hm_d = max(Decimal(str(h_m)), Decimal.from_float(float(h_m)))
    ks = [bm_d, hm_d]
    for p in (B0_pwl, B1_pwl, W0_pwl, W1_pwl, Psi0_pwl, Psi1_pwl):
        for k in p["ks"]:
            kd = Decimal.from_float(float(k))
            if bm_d < kd < hm_d:
                ks.append(kd)
    for k_grid in np.geomspace(float(b_m), float(h_m), 42)[1:-1]:
        kd = Decimal.from_float(float(k_grid))
        if bm_d < kd < hm_d:
            ks.append(kd)
    ks = sorted(set(ks))

    m_inf_lo = Decimal("1e30")
    d_stay_hi = Decimal("-1e30")
    for kL_d, kR_d in zip(ks[:-1], ks[1:]):
        k_iv = Interval._raw(kL_d, kR_d)
        b0 = iv_eval_logpwl(B0_pwl, k_iv)
        b1 = iv_eval_logpwl(B1_pwl, k_iv)
        w0 = iv_eval_logpwl(W0_pwl, k_iv)
        w1 = iv_eval_logpwl(W1_pwl, k_iv)
        p0 = iv_eval_logpwl(Psi0_pwl, k_iv)
        p1 = iv_eval_logpwl(Psi1_pwl, k_iv)
        m_inf_lo = min(m_inf_lo, (w0 - b0).lo, (w1 - b1).lo)
        d_stay_hi = max(d_stay_hi, (p0 - b0).hi, (p1 - b1).hi)

    assert m_inf_lo > Decimal("0"), f"Coupled Markov staying margin <= 0: {m_inf_lo}"

    iv_h = Interval(str(h_m))
    iv_bH = Interval(str(b_max))
    iv_one = Interval("1")
    iv_ymax0 = Interval(str(q0_hi)) * iv_h + iv_F_A(Interval(str(A0_hi)), iv_h, iv_one)
    iv_ymax1 = Interval(str(q1_hi)) * iv_h + iv_F_A(Interval(str(A1_hi)), iv_h, iv_one)
    iv_ymax = Interval._raw(max(iv_ymax0.lo, iv_ymax1.lo), max(iv_ymax0.hi, iv_ymax1.hi))

    b0h = iv_eval_logpwl(B0_pwl, iv_h)
    b1h = iv_eval_logpwl(B1_pwl, iv_h)
    psi0y = iv_eval_logpwl(Psi0_pwl, iv_ymax)
    psi1y = iv_eval_logpwl(Psi1_pwl, iv_ymax)
    d_exit_0 = psi0y - b0h
    d_exit_1 = psi1y - b1h
    iv_D_exit = Interval._raw(max(d_exit_0.lo, d_exit_1.lo), max(d_exit_0.hi, d_exit_1.hi))
    assert iv_D_exit.lo > Decimal("0"), f"Exit overshoot must be positive: {iv_D_exit}"

    iv_m_inf = Interval._raw(m_inf_lo, m_inf_lo)
    iv_D_stay = Interval._raw(d_stay_hi, d_stay_hi)
    iv_exit_term = iv_bH * iv_D_exit

    T0_min = None
    eps0_at_min = None
    best_E_tau_hi = Decimal("1e30")
    T0_opt = None
    eps0_at_opt = None

    for T in range(1, 401):
        tail = iv_bH.pow_int(T) * iv_D_stay
        if tail.hi >= iv_m_inf.lo:
            continue
        den = iv_exit_term - tail
        if den.lo <= Decimal("0"):
            continue
        eps0 = (iv_m_inf - tail) / den
        if eps0.lo <= Decimal("0"):
            continue
        if T0_min is None:
            T0_min = T
            eps0_at_min = float(eps0.to_float_bounds()[0])
        E_tau = Interval(str(T)) / eps0
        if E_tau.hi < best_E_tau_hi:
            best_E_tau_hi = E_tau.hi
            T0_opt = T
            eps0_at_opt = float(eps0.to_float_bounds()[0])
        if T0_min is not None and T >= T0_min + 120:
            break

    assert T0_min is not None and T0_opt is not None, "Coupled Doob gap failed to turn positive in 400 steps"
    iv_E_min = Interval(str(T0_min)) / Interval._raw(
        Decimal.from_float(eps0_at_min), Decimal.from_float(eps0_at_min)
    )
    return {
        "T0_min": int(T0_min),
        "eps0_min": float(eps0_at_min),
        "E_tau_at_min": float(iv_E_min.to_float_bounds()[1]),
        "T0_opt": int(T0_opt),
        "eps0_opt": float(eps0_at_opt),
        "E_tau_opt": float(Interval._raw(best_E_tau_hi, best_E_tau_hi).to_float_bounds()[1]),
        "m_inf_lo": float(Interval._raw(m_inf_lo, m_inf_lo).to_float_bounds()[0]),
        "D_stay_hi": float(Interval._raw(d_stay_hi, d_stay_hi).to_float_bounds()[1]),
        "D_exit_hi": float(iv_D_exit.to_float_bounds()[1]),
    }
