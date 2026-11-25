"""
Generic Sparse HiGHS CEGIS-LP Proposer–Verifier Engine (Static & Coupled Markov).

Synthesizes and continuously verifies:
  1. Static / parameter-box certificates: global super-barrier Psi, continuous
     witness sub-solution (W, kp, L), staying barrier B_stay on [b_m, h_m],
     adverse exits on M / H1 / H2, and certified exit deadline T_cert.
  2. Coupled 2-regime Markov certificates: joint (Psi_0, Psi_1), (W_0, W_1),
     and compressed staying barriers (B_0, B_1) for general 2x2 transition matrix P
     and regime-specific (A_w, q_w), plus certified Doob E[tau_H] bounds.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np
from scipy import sparse as sp
from scipy.optimize import linprog

from core.interval_arith import (
    CANONICAL_BM,
    CANONICAL_HM,
    F_A,
    dF_dL,
    Interval,
)
from core.pwl_basis import (
    make_pwl_from_knots,
    eval_logpwl,
    eval_pwl_basis_sparse,
    monotone_diff_sparse,
)
from core.model_api import (
    ParamBox,
    RegimeSpec,
    _golden_L_vec,
    solve_teacher_vfi,
    solve_markov_teacher_vfi,
)
from core.verifier_bridge import (
    verify_staying_barrier_bb,
    verify_super_barrier_bb,
    verify_witness_subsolution_bb,
    verify_adverse_exit_bb,
    verify_witness_slope_on_M,
    verify_derivative_below_bound,
    verify_H2_global_interval,
    certify_staying_deadline_interval,
    compute_doob_eps0_coupled_pwl_interval,
)


def _safe_s_lo(eL: float, bL: float) -> float:
    iv_s = Interval(str(eL)) / (Interval("1") - Interval(str(bL)))
    return math.nextafter(iv_s.to_float_bounds()[0], -math.inf)


def _safe_D_hi(eU: float, bR: float) -> float:
    iv_D = Interval(str(eU)) / (Interval("1") - Interval(str(bR)))
    return math.nextafter(iv_D.to_float_bounds()[1], math.inf)


def _min_c_E_plus(Av: float, qv: float, K: float, a: float, l0: float, eL: float, eU: float) -> float:
    t = float(dF_dL(Av, K, l0))
    c_sup = qv * K + float(F_A(Av, K, l0)) + (1.0 - l0) * t - a
    if c_sup <= 0.0:
        return -1.0
    return min(c_sup - t * min(1.0, (1.0 - ev) * c_sup / t) for ev in (eL, eU))


def _pick_adverse_l0(Av_lo: float, Av_hi: float, qv_lo: float, K: float, a_exit: float, l_teacher: float, eL: float, eU: float) -> float:
    """Pick a safe interior l0 in (0.15, 0.85) maximizing c_min while staying near optimal teacher labor."""
    cands = [float(np.clip(l_teacher, 0.25, 0.80)), 0.44, 0.50, 0.57, 0.65, 0.72, 0.35]
    best_l = cands[0]
    best_score = -1e18
    for l0 in cands:
        cm = _min_c_E_plus(Av_lo, qv_lo, K, a_exit, l0, eL, eU)
        if cm > 1e-4:
            # Prefer near teacher labor among feasible candidates
            score = -abs(l0 - l_teacher) + 0.05 * math.log(min(cm, 1.0))
            if score > best_score:
                best_score = score
                best_l = l0
    if best_score < -1e17:
        for l0 in np.linspace(0.15, 0.90, 16):
            cm = _min_c_E_plus(Av_lo, qv_lo, K, a_exit, float(l0), eL, eU)
            if cm > best_score:
                best_score = cm
                best_l = float(l0)
    return best_l


def cegis_lp_super_barrier(
    Av: float,
    bL: float,
    bR: float,
    q_hi: float,
    eL: float,
    eU: float,
    k_lo: float,
    k_hi: float,
    init_vals_fn: Callable[[np.ndarray], np.ndarray],
    m_min_slope: float = 0.0,
    pre_b_slope: float = 0.0,
    pre_h_slope: float = 0.0,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    max_cegis_rounds: int = 16,
    tol_bb: float = 3e-4,
    p_ruin: float = 0.0,
    v_ruin: float = 0.0,
    h_safe: float = CANONICAL_HM,
    b_m_slope: Optional[float] = None,
) -> Tuple[Dict[str, object], Dict[str, object], List[Dict[str, object]]]:
    """Pure HiGHS-LP CEGIS loop synthesizing a global super-barrier Psi(log K) on (0, inf) x [bL, bR]."""
    if b_m_slope is None:
        b_m_slope = b_m
    b_lo_eff = bL * (1.0 - p_ruin)
    s_lo = _safe_s_lo(eL, b_lo_eff)
    D_hi = _safe_D_hi(eU, bR)

    extra_k = [b_m, h_m, 0.10, 0.28]
    if p_ruin > 0.0:
        extra_k.extend([h_safe * 0.996, h_safe])
    if b_m_slope < 0.10:
        extra_k.extend([b_m_slope, 0.003, 0.006, 0.015, 0.04])
    k_knots = np.unique(np.concatenate([
        [k_lo],
        [k for k in extra_k if k_lo < k < k_hi],
        np.geomspace(k_lo, 0.0012, 18, endpoint=False),
        np.geomspace(0.0012, 0.0150, 72, endpoint=False),
        np.geomspace(0.0150, 0.05, 24, endpoint=False),
        np.geomspace(0.05, b_m, 16, endpoint=False),
        np.linspace(b_m, h_m, 16, endpoint=False),
        np.geomspace(h_m, 1.0, 28, endpoint=False),
        np.geomspace(1.0, min(6.0, k_hi * 0.85), 14, endpoint=False),
        np.geomspace(min(6.0, k_hi * 0.85), k_hi, 10),
        [k_hi],
    ]))
    if k_lo < 1.0 < k_hi:
        k_knots = np.unique(np.concatenate([k_knots, [1.0]]))

    ce_x = np.array([], dtype=np.float64)
    ce_L = np.array([], dtype=np.float64)
    ce_s = np.array([], dtype=np.float64)
    history: List[Dict[str, object]] = []

    Ls_act = np.concatenate([[0.0], np.geomspace(1e-7, 0.08, 14, endpoint=False), np.linspace(0.08, 0.996, 48)])
    ss_act = np.unique(np.concatenate([
        np.linspace(0.30, 0.70, 8, endpoint=False),
        np.linspace(0.70, 0.95, 42, endpoint=False),
        1.0 - np.geomspace(1.0e-4, 0.05, 28),
    ]))
    rng = np.random.default_rng(77)

    omp_r = 1.0 - p_ruin
    pv_r = p_ruin * v_ruin
    r_top = q_hi + float(F_A(Av, k_lo, 1.0)) / k_lo
    tlo_consts = []
    for bv_t in (bL, bR):
        bv_t_eff = bv_t * omp_r if (p_ruin > 0.0 and k_lo <= h_safe) else bv_t
        c_slo = eL + bv_t_eff * s_lo
        s_lo_opt = (bv_t_eff * s_lo) / c_slo
        shift_lo = (bv_t * pv_r) if (p_ruin > 0.0 and k_lo <= h_safe) else 0.0
        tlo_consts.append((
            bv_t_eff,
            eL * math.log((1.0 - s_lo_opt) * k_lo) + bv_t_eff * s_lo * math.log(s_lo_opt) + c_slo * math.log(r_top) + shift_lo,
        ))

    Y_end = q_hi * k_hi + Av * (2.0 ** 1.5)
    thi_log_consts = []
    for bv_t in (bL, bR):
        c_dhi = eU + bv_t * D_hi
        s_hi_opt = (bv_t * D_hi) / c_dhi
        thi_log_consts.append((
            bv_t,
            eU * math.log(1.0 - s_hi_opt) + bv_t * D_hi * math.log(s_hi_opt) + c_dhi * math.log(Y_end / k_hi) + eU * math.log(k_hi),
        ))

    best_pwl = None
    last_pwl = None
    best_cert = None
    best_psi_h = float("inf")

    for rnd in range(1, max_cegis_rounds + 1):
        n_k = len(k_knots)
        z_knots = np.log(k_knots)
        dlk = np.diff(z_knots)
        k_mids = np.sqrt(k_knots[:-1] * k_knots[1:])
        sk_mask = k_knots[1:] <= h_m + 1e-9
        k_q1 = np.exp(0.75 * z_knots[:-1][sk_mask] + 0.25 * z_knots[1:][sk_mask])
        k_q3 = np.exp(0.25 * z_knots[:-1][sk_mask] + 0.75 * z_knots[1:][sk_mask])
        k_eval = np.unique(np.concatenate([k_knots, k_mids, k_q1, k_q3]))

        y_ref_eval = init_vals_fn(k_eval) if last_pwl is None else eval_logpwl(last_pwl, k_eval)
        Ya = q_hi * k_eval[:, None] + F_A(Av, k_eval[:, None], Ls_act[None, :])
        ca = np.maximum((1.0 - ss_act[None, None, :]) * Ya[:, :, None], 1e-18)
        ya = np.maximum(ss_act[None, None, :] * Ya[:, :, None], 1e-18)
        ua = np.where(ca < 1.0, eL, eU) * np.log(ca) + (1.0 - eU) * np.log(1.0 - Ls_act[None, :, None])
        eva_raw = init_vals_fn(ya.ravel()).reshape(ya.shape) if last_pwl is None else eval_logpwl(last_pwl, ya)
        eva = np.where((k_eval < h_safe)[:, None, None], omp_r * eva_raw + pv_r, eva_raw) if p_ruin > 0.0 else eva_raw
        ba = np.where(eva < 0.0, bL, bR)
        resa = (ua + ba * eva - y_ref_eval[:, None, None]).reshape(len(k_eval), -1)
        top_idx = np.argpartition(resa, -8, axis=1)[:, -8:].ravel()
        act_x = np.repeat(k_eval, 8)
        act_L = Ls_act[top_idx // len(ss_act)]
        act_s = ss_act[top_idx % len(ss_act)]

        xs_e = np.repeat(k_eval, 6)
        Ls_e = np.tile([0.0, 1e-6, 0.36, 0.58, 0.78, 0.95], len(k_eval))
        ss_e = np.tile([0.97, 0.92, 0.70, 0.88, 0.955, 0.9985], len(k_eval))
        xs_r = np.repeat(k_eval, 3)
        Ls_r = rng.uniform(0.0, 0.98, size=len(xs_r))
        ss_r = rng.uniform(0.25, 0.9995, size=len(xs_r))

        col_x = np.concatenate([act_x, xs_e, xs_r, ce_x]) if len(ce_x) > 0 else np.concatenate([act_x, xs_e, xs_r])
        col_L = np.concatenate([act_L, Ls_e, Ls_r, ce_L]) if len(ce_x) > 0 else np.concatenate([act_L, Ls_e, Ls_r])
        col_s = np.concatenate([act_s, ss_e, ss_r, ce_s]) if len(ce_x) > 0 else np.concatenate([act_s, ss_e, ss_r])

        Y_col = q_hi * col_x + F_A(Av, col_x, col_L)
        c_col = np.maximum((1.0 - col_s) * Y_col, 1e-18)
        y_col = np.maximum(col_s * Y_col, 1e-18)
        u_col = np.where(c_col < 1.0, eL, eU) * np.log(c_col) + (1.0 - eU) * np.log(1.0 - col_L)
        zx_col, zy_col = np.log(col_x), np.log(y_col)
        ruin_col = (col_x < h_safe) if p_ruin > 0.0 else np.zeros(len(col_x), dtype=bool)
        col_omp = np.where(ruin_col, omp_r, 1.0)
        col_pv = np.where(ruin_col, pv_r, 0.0)

        Mx, _ = eval_pwl_basis_sparse(z_knots, zx_col, s_lo, D_hi)
        My, oy = eval_pwl_basis_sparse(z_knots, zy_col, s_lo, D_hi)

        y_cur = init_vals_fn(k_knots) if last_pwl is None else eval_logpwl(last_pwl, k_knots)
        req_s = np.where((k_knots[:-1] >= b_m_slope - 1e-9) & (k_knots[1:] <= h_m + 1e-9), m_min_slope, 0.0)
        if pre_b_slope > 0.0:
            req_s = np.where(k_knots[:-1] < b_m + 1e-9, np.maximum(req_s, pre_b_slope), req_s)
        if pre_h_slope > 0.0:
            req_s = np.where(k_knots[:-1] < h_m + 1e-9, np.maximum(req_s, pre_h_slope), req_s)
        sl_hi_req = 0.135 if (Av >= 0.60 and q_hi >= 0.915) else 0.165
        req_s = np.where(k_knots[:-1] >= 1.0, np.maximum(req_s, sl_hi_req), req_s)
        A_mon = monotone_diff_sparse(n_k)
        req_log_s = np.maximum(req_s * k_knots[1:], np.where(k_knots[1:] <= 0.0012, s_lo, 0.0))
        b_mon = -(req_log_s * dlk)

        tv_idx = np.where((k_knots[1:-1] >= 0.05) | (k_knots[1:-1] <= 0.0010))[0]
        n_tv = len(tv_idx)
        if n_tv > 0:
            j_arr = np.arange(n_tv, dtype=np.int32)
            inv_d0 = 1.0 / dlk[tv_idx]
            inv_d1 = 1.0 / dlk[tv_idx + 1]
            r_tv = np.concatenate([np.repeat(2 * j_arr, 4), np.repeat(2 * j_arr + 1, 4)])
            c_tv = np.concatenate([
                np.column_stack([tv_idx, tv_idx + 1, tv_idx + 2, n_k + j_arr]).ravel(),
                np.column_stack([tv_idx, tv_idx + 1, tv_idx + 2, n_k + j_arr]).ravel(),
            ]).astype(np.int32)
            d_tv = np.concatenate([
                np.column_stack([inv_d0, -(inv_d0 + inv_d1), inv_d1, np.full(n_tv, -1.0)]).ravel(),
                np.column_stack([-inv_d0, (inv_d0 + inv_d1), -inv_d1, np.full(n_tv, -1.0)]).ravel(),
            ])
            A_tv = sp.csr_matrix((d_tv, (r_tv, c_tv)), shape=(2 * n_tv, n_k + n_tv))
        else:
            A_tv = sp.csr_matrix((0, n_k), dtype=np.float64)
        b_tv = np.zeros(2 * n_tv, dtype=np.float64)

        c_obj_y = np.zeros(n_k, dtype=np.float64)
        m_mask = (k_knots >= b_m_slope - 1e-9) & (k_knots <= h_m + 1e-9)
        c_obj_y[m_mask] = 1.0 / max(1, int(np.sum(m_mask)))
        c_obj_y += 1e-3 / n_k
        c_obj = np.concatenate([c_obj_y, np.full(n_tv, 5e-4, dtype=np.float64)])
        lp_bounds = [(-2500.0, 2500.0)] * n_k + [(0.0, None)] * n_tv

        m_base = np.where(col_x >= 0.05, 0.0020 if Av >= 0.60 else 0.0012, 0.018 if Av >= 0.60 else 0.012)
        solved = False
        for m_scale in (1.0, 0.65, 0.35, 0.15, 0.05):
            m_vec = m_scale * m_base
            m_t_lo = m_scale * 0.018
            m_t_hi = m_scale * 0.0020
            y_try = y_cur.copy()
            ok_pass = False
            for _sp in range(2):
                vy_est = col_omp * (My @ y_try + oy) + col_pv
                near0 = np.abs(vy_est) <= 1.5
                A_rows = [A_mon]
                b_rows = [b_mon]
                for bv_c, m_c in ((bL, (vy_est < 0.0) | near0), (bR, (vy_est >= 0.0) | near0)):
                    if np.any(m_c):
                        if p_ruin > 0.0:
                            A_rows.append(sp.diags(bv_c * col_omp[m_c]) @ My[m_c] - Mx[m_c])
                            b_rows.append(-(u_col[m_c] + bv_c * (col_omp[m_c] * oy[m_c] + col_pv[m_c]) + m_vec[m_c]))
                        else:
                            A_rows.append(bv_c * My[m_c] - Mx[m_c])
                            b_rows.append(-(u_col[m_c] + bv_c * oy[m_c] + m_vec[m_c]))
                for bv_t_eff, tc in tlo_consts:
                    A_rows.append(sp.csr_matrix(([-(1.0 - bv_t_eff)], ([0], [0])), shape=(1, n_k)))
                    b_rows.append(np.array([-(tc + m_t_lo)]))
                M1, o1 = eval_pwl_basis_sparse(z_knots, np.array([0.0]), s_lo, D_hi)
                e_last = sp.csr_matrix(([-1.0], ([0], [n_k - 1])), shape=(1, n_k))
                for bv_t, thc in thi_log_consts:
                    A_rows.append(bv_t * M1 + e_last)
                    b_rows.append(np.array([-(eU * math.log(Y_end) + bv_t * float(o1[0]) + m_t_hi)]))
                    A_rows.append(sp.csr_matrix(([-(1.0 - bv_t)], ([0], [n_k - 1])), shape=(1, n_k)))
                    b_rows.append(np.array([-(thc + m_t_hi)]))

                A_y_blk = sp.vstack(A_rows, format="csr")
                b_y_blk = np.concatenate(b_rows)
                if n_tv > 0:
                    A_full = sp.vstack([
                        sp.hstack([A_y_blk, sp.csr_matrix((A_y_blk.shape[0], n_tv), dtype=np.float64)], format="csr"),
                        A_tv,
                    ], format="csc")
                    b_full = np.concatenate([b_y_blk, b_tv])
                else:
                    A_full = A_y_blk.tocsc()
                    b_full = b_y_blk
                res = linprog(c_obj, A_ub=A_full, b_ub=b_full, bounds=lp_bounds, method="highs")
                if res.success:
                    y_try = res.x[:n_k].copy()
                    ok_pass = True
                else:
                    ok_pass = False
                    break
            if ok_pass:
                y_knots = y_try
                solved = True
                break
        if not solved:
            raise RuntimeError(f"Super-barrier LP failed at round {rnd}")

        pwl = make_pwl_from_knots(k_knots, y_knots, s_lo, D_hi)
        last_pwl = pwl
        cert = verify_super_barrier_bb(
            pwl, pwl, Av, bL, bR, q_hi=q_hi, eL=eL, eU=eU, tol=tol_bb,
            p_ruin=p_ruin, v_ruin=v_ruin, h_safe=h_safe,
        )
        psi_h = float(eval_logpwl(pwl, np.array([h_m]))[0])
        history.append({"round": rnd, "knots": int(n_k), "d_ub_iv": float(cert["d_ub_iv"]), "psi_h": psi_h})
        if cert["certified"] and psi_h < best_psi_h:
            best_pwl, best_cert, best_psi_h = pwl, cert, psi_h
        if cert["certified"]:
            break

        ce_list = cert["counterexamples"][:24]
        new_x, new_L, new_s, ins_k = [], [], [], []
        for cx, cL, cs, c_val in ce_list:
            if c_val > -1.5e-3:
                ins_k.append(float(np.clip(cx, k_lo * 1.05, k_hi * 0.95)))
            for sc in (0.992, 1.0, 1.008):
                new_x.append(float(np.clip(cx * sc, k_lo, k_hi)))
                new_L.append(float(np.clip(cL, 0.0, 0.9999)))
                new_s.append(float(np.clip(cs, 1e-4, 0.99999)))
        if new_x:
            ce_x = np.concatenate([ce_x, np.array(new_x)])
            ce_L = np.concatenate([ce_L, np.array(new_L)])
            ce_s = np.concatenate([ce_s, np.array(new_s)])
        if ins_k and len(k_knots) < 320:
            cand_add = []
            for ck in ins_k:
                if np.min(np.abs(np.log(k_knots) - math.log(ck))) > 2.0e-3:
                    if not cand_add or min(abs(math.log(c) - math.log(ck)) for c in cand_add) > 2.0e-3:
                        cand_add.append(ck)
                if len(cand_add) >= 18:
                    break
            if cand_add:
                k_knots = np.unique(np.concatenate([k_knots, np.array(cand_add)]))

    if best_pwl is None or not (best_cert["certified"] and best_cert["iv_certified"]):
        raise RuntimeError(f"Super-barrier failed certification: {history[-1]}")
    return best_pwl, best_cert, history


def cegis_lp_witness(
    Av: float,
    qv: float,
    bL: float,
    bR: float,
    eL: float,
    eU: float,
    k_domain: Tuple[float, float],
    m_req_M: float = 0.0,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    k_h2: float = 0.80,
    max_cegis_rounds: int = 8,
) -> Tuple[Dict[str, object], Dict[str, object], Dict[str, object], Dict[str, object], List[Dict[str, object]]]:
    """Pure HiGHS-LP CEGIS loop synthesizing continuous feasible sub-solution witness (W, kp, L) on [k_a, k_b]."""
    k_a, k_b = k_domain
    k_grid = np.unique(np.concatenate([
        [k_a],
        np.geomspace(k_a, min(h_m, k_b), 52, endpoint=False),
        np.geomspace(min(h_m, k_b), min(k_h2, k_b), 52, endpoint=False),
        np.geomspace(min(k_h2, k_b), k_b, 56),
        [k_b],
    ]))
    V_t, kp_t, L_t = solve_teacher_vfi(Av, qv, bR, eL, eU, False, k_grid)
    kp_t = np.clip(kp_t, k_a * 1.005, k_b * 0.995)
    L_t = np.clip(L_t, 0.0, 0.985)

    pol_idx = np.unique(np.concatenate([np.arange(0, len(k_grid), 2), [len(k_grid) - 1]]))
    kp_pwl = make_pwl_from_knots(k_grid[pol_idx], kp_t[pol_idx], 0.0, 0.0)
    L_pwl = make_pwl_from_knots(k_grid[pol_idx], L_t[pol_idx], 0.0, 0.0)

    chk_k = np.unique(np.concatenate([k_grid, np.sqrt(k_grid[:-1] * k_grid[1:])]))
    L_chk = eval_logpwl(L_pwl, chk_k)
    kp_chk = eval_logpwl(kp_pwl, chk_k)
    c_chk = qv * chk_k + F_A(Av, chk_k, np.clip(L_chk, 0.0, 0.999)) - kp_chk
    if np.any(c_chk <= 1e-6) or np.any(L_chk >= 0.999) or np.any(L_chk < 0.0) or np.any(kp_chk < k_a) or np.any(kp_chk > k_b):
        k_pol2 = np.unique(np.concatenate([[k_a], chk_k[1:-1:2], [k_b]]))
        kp_p2 = np.clip(np.interp(np.log(k_pol2), np.log(k_grid), kp_t), k_a * 1.005, k_b * 0.995)
        L_p2 = np.clip(np.interp(np.log(k_pol2), np.log(k_grid), L_t), 0.0, 0.985)
        kp_pwl = make_pwl_from_knots(k_pol2, kp_p2, 0.0, 0.0)
        L_pwl = make_pwl_from_knots(k_pol2, L_p2, 0.0, 0.0)

    k_knots_raw = [
        [k_a],
        [h_m] if (k_a < h_m < k_b) else [],
        [k_h2] if (k_a < k_h2 < k_b) else [],
        np.geomspace(k_a * 1.005, min(h_m, k_b * 0.995), 24, endpoint=False) if k_a * 1.005 < min(h_m, k_b * 0.995) else [],
        np.geomspace(max(k_a * 1.005, min(h_m, k_b * 0.995)), min(k_h2, k_b * 0.995), 24, endpoint=False) if max(k_a * 1.005, min(h_m, k_b * 0.995)) < min(k_h2, k_b * 0.995) else [],
        np.geomspace(max(k_a * 1.005, min(k_h2, k_b * 0.995)), k_b * 0.995, 24) if max(k_a * 1.005, min(k_h2, k_b * 0.995)) < k_b * 0.995 else [],
        [k_b],
    ]
    k_knots = np.unique(np.concatenate([arr for arr in k_knots_raw if len(arr) > 0]))
    ce_k = np.array([], dtype=np.float64)
    history: List[Dict[str, object]] = []
    best_W = None
    best_cert = None

    for rnd in range(1, max_cegis_rounds + 1):
        n_w = len(k_knots)
        z_knots = np.log(k_knots)
        dlk = np.diff(z_knots)
        k_mids = np.sqrt(k_knots[:-1] * k_knots[1:])
        col_k = np.unique(np.concatenate([k_knots, k_mids, np.sqrt(k_knots[:-1] * k_mids), np.sqrt(k_mids * k_knots[1:]), ce_k]))
        L_col = np.clip(eval_logpwl(L_pwl, col_k), 0.0, 0.999)
        kp_col = np.clip(eval_logpwl(kp_pwl, col_k), k_a, k_b)
        c_col = np.maximum(qv * col_k + F_A(Av, col_k, L_col) - kp_col, 1e-18)
        lc, ll = np.log(c_col), np.log(np.maximum(1.0 - L_col, 1e-18))
        u_col = np.minimum(eL * lc + (1.0 - eL) * ll, eU * lc + (1.0 - eU) * ll)

        Mx, _ = eval_pwl_basis_sparse(z_knots, np.log(col_k), 0.0, 0.0)
        My, oy = eval_pwl_basis_sparse(z_knots, np.log(kp_col), 0.0, 0.0)

        req_val_M = (m_req_M + 1e-4) if m_req_M > 0.0 else 0.0
        req_s = np.where((k_knots[:-1] < h_m - 1e-12) & (k_knots[1:] > b_m + 1e-12), req_val_M, 0.0)
        A_mon = monotone_diff_sparse(n_w)
        b_mon = -(req_s * k_knots[1:] * dlk)

        c_w = -np.ones(n_w, dtype=np.float64) / n_w
        c_w[0] -= 0.40
        i_h = int(np.argmin(np.abs(k_knots - h_m)))
        c_w[i_h] -= 0.25

        y_try = np.interp(z_knots, np.log(k_grid), V_t)
        solved_w = False
        for m_trg in (2.5e-4, 1.0e-4, 4.0e-5, 1.0e-5):
            yt = y_try.copy()
            ok_p = False
            for _sp in range(2):
                wy_est = My @ yt + oy
                near0 = np.abs(wy_est) <= 1.5
                A_rows = [A_mon]
                b_rows = [b_mon]
                for bv_c, m_c in ((bR, (wy_est < 0.0) | near0), (bL, (wy_est >= 0.0) | near0)):
                    if np.any(m_c):
                        A_rows.append(Mx[m_c] - bv_c * My[m_c])
                        b_rows.append(u_col[m_c] + bv_c * oy[m_c] - m_trg)
                res = linprog(c_w, A_ub=sp.vstack(A_rows, format="csc"), b_ub=np.concatenate(b_rows), bounds=[(-500.0, 2000.0)] * n_w, method="highs")
                if res.success:
                    yt = res.x.copy()
                    ok_p = True
                else:
                    ok_p = False
                    break
            if ok_p:
                y_knots = yt
                solved_w = True
                break
        if not solved_w:
            raise RuntimeError(f"Witness LP failed at round {rnd}")

        W_pwl = make_pwl_from_knots(k_knots, y_knots, 0.0, 0.0)
        cert = verify_witness_subsolution_bb(
            W_pwl, W_pwl, kp_pwl, L_pwl, Av, qv, bL, bR, eL=eL, eU=eU,
            k_domain=k_domain, tol=8e-5, interval_check=True, h_safe=h_m,
        )
        history.append({"round": rnd, "knots_W": int(n_w), "d_ub": float(cert["d_ub"]), "d_ub_iv": float(cert["d_ub_iv"])})
        if cert["certified"] and cert["iv_certified"]:
            best_W, best_cert = W_pwl, cert
            break

        ins_k, new_ce = [], []
        for cx, cval in cert["counterexamples"]:
            if cval > -5e-5:
                ins_k.append(float(np.clip(cx, k_a * 1.001, k_b * 0.999)))
            for f in (0.992, 1.0, 1.008):
                new_ce.append(float(np.clip(cx * f, k_a, k_b)))
        if new_ce:
            ce_k = np.unique(np.concatenate([ce_k, np.array(new_ce)]))
        if ins_k and len(k_knots) < 160 and rnd < max_cegis_rounds:
            cand_add = [ck for ck in ins_k if np.min(np.abs(np.log(k_knots) - math.log(ck))) > 1.5e-3]
            if cand_add:
                k_knots = np.unique(np.concatenate([k_knots, np.array(cand_add[:12])]))

    if best_W is None and len(k_knots) == len(y_knots) and 0.0 < float(cert["d_ub_iv"]) < 5.0e-4:
        shift_w = (float(cert["d_ub_iv"]) + 2.0e-5) / (1.0 - bL)
        W_sh = make_pwl_from_knots(k_knots, y_knots - shift_w, 0.0, 0.0)
        c_sh = verify_witness_subsolution_bb(
            W_sh, W_sh, kp_pwl, L_pwl, Av, qv, bL, bR, eL=eL, eU=eU,
            k_domain=k_domain, tol=8e-5, interval_check=True, h_safe=h_m,
        )
        if c_sh["certified"] and c_sh["iv_certified"]:
            best_W, best_cert = W_sh, c_sh

    if best_W is None or not (best_cert["certified"] and best_cert["iv_certified"]):
        raise RuntimeError(f"Witness CEGIS-LP failed certification: {history[-1]}")
    if m_req_M > 0.0:
        sl_ok, min_sl = verify_witness_slope_on_M(best_W, m_req_M, b_m=b_m, h_m=h_m)
        if not sl_ok:
            raise RuntimeError(f"Witness slope on [{b_m},{h_m}] failed: {min_sl:.4f} < {m_req_M:.4f}")
    return best_W, kp_pwl, L_pwl, best_cert, history


def cegis_lp_staying_barrier(
    b_m: float,
    h_m: float,
    A_hi: float,
    q_hi: float,
    b_lo: float,
    b_hi: float,
    e_lo: float,
    e_hi: float,
    B_ev_pwl: Optional[Dict[str, object]] = None,
    n_knots: int = 28,
    max_rounds: int = 12,
    tol_bb: float = 2e-4,
    fixed_knots: Optional[np.ndarray] = None,
    target_W_pwl: Optional[Dict[str, object]] = None,
    min_slope_M: float = 0.02,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Pure deterministic HiGHS-LP CEGIS synthesizer for a staying barrier B(log K) on [b_m, h_m]."""
    kB = np.asarray(fixed_knots, dtype=np.float64) if fixed_knots is not None else np.geomspace(b_m, h_m, n_knots)
    gx, gy = np.meshgrid(np.geomspace(b_m, h_m, 34), np.geomspace(b_m, h_m, 34), indexing="ij")
    fx0, fy0 = gx.ravel(), gy.ravel()
    x_diag = np.geomspace(b_m, h_m, 40)
    y_lim = q_hi * x_diag + F_A(A_hi, x_diag, 0.9999)
    d_fx, d_fy = [], []
    for xd, yl in zip(x_diag, y_lim):
        for f in (0.0, 0.2, 0.5, 0.8, 0.95, 0.99):
            yv = xd + f * (yl - xd)
            if b_m <= yv <= h_m:
                d_fx.append(float(xd)); d_fy.append(float(yv))
    fx = np.concatenate([fx0, np.array(d_fx, dtype=np.float64)]) if d_fx else fx0
    fy = np.concatenate([fy0, np.array(d_fy, dtype=np.float64)]) if d_fx else fy0
    feas = (q_hi * fx + F_A(A_hi, fx, 0.9999) - fy) > 1e-12
    fx, fy = fx[feas], fy[feas]
    _, fu = _golden_L_vec(A_hi, q_hi, e_lo, e_hi, fx, fy, is_upper=True)

    best_pwl = None
    best_cert = None
    for rnd in range(1, max_rounds + 1):
        zB = np.log(kB)
        dlB = np.diff(zB)
        nB = len(kB)
        A_mon = monotone_diff_sparse(nB)
        b_mon = -(min_slope_M * kB[1:] * dlB)
        Mx, _ = eval_pwl_basis_sparse(zB, np.log(fx), 0.0, 0.0)
        if B_ev_pwl is None:
            My, _ = eval_pwl_basis_sparse(zB, np.log(fy), 0.0, 0.0)
            y_init = np.full(nB, -45.0, dtype=np.float64)
            solved = False
            for m_slk in (3.0e-3, 1.0e-3, 3.0e-4, 5.0e-5):
                yt = y_init.copy()
                ok_p = False
                for _sp in range(2):
                    cb_est = My @ yt
                    near0 = np.abs(cb_est) <= 1.5
                    A_rows = [A_mon]
                    b_rows = [b_mon]
                    for bv_c, mc in ((b_lo, (cb_est < 0.0) | near0), (b_hi, (cb_est >= 0.0) | near0)):
                        if np.any(mc):
                            A_rows.append(bv_c * My[mc] - Mx[mc])
                            b_rows.append(-(fu[mc] + m_slk))
                    A_blk = sp.vstack(A_rows, format="csr")
                    b_blk = np.concatenate(b_rows)
                    if target_W_pwl is not None:
                        w_vals = eval_logpwl(target_W_pwl, kB)
                        A_gap = sp.hstack([sp.eye(nB, format="csr"), np.ones((nB, 1), dtype=np.float64)], format="csr")
                        A_ext = sp.hstack([A_blk, sp.csr_matrix((A_blk.shape[0], 1), dtype=np.float64)], format="csr")
                        c_obj = np.concatenate([np.full(nB, 1e-3 / nB), np.array([-1.0])])
                        bds = [(-500.0, 500.0)] * nB + [(-50.0, 200.0)]
                        res = linprog(c_obj, A_ub=sp.vstack([A_ext, A_gap], format="csc"), b_ub=np.concatenate([b_blk, w_vals]), bounds=bds, method="highs")
                    else:
                        c_obj = np.ones(nB, dtype=np.float64) / nB
                        res = linprog(c_obj, A_ub=A_blk.tocsc(), b_ub=b_blk, bounds=[(-500.0, 500.0)] * nB, method="highs")
                    if res.success:
                        yt = res.x[:nB].copy()
                        ok_p = True
                    else:
                        ok_p = False
                        break
                if ok_p:
                    y_knots = yt
                    solved = True
                    break
            if not solved:
                raise RuntimeError(f"Staying barrier LP failed on [{b_m},{h_m}]")
        else:
            cb_fy = eval_logpwl(B_ev_pwl, fy)
            rhs_val = fu + np.where(cb_fy < 0.0, b_lo * cb_fy, b_hi * cb_fy)
            for m_slk in (5e-4, 1e-4, 2e-5, 0.0):
                A_blk = sp.vstack([A_mon, -Mx], format="csc")
                b_blk = np.concatenate([b_mon, -(rhs_val + m_slk)])
                c_obj = np.ones(nB, dtype=np.float64) / nB
                res = linprog(c_obj, A_ub=A_blk, b_ub=b_blk, bounds=[(-500.0, 500.0)] * nB, method="highs")
                if res.success:
                    y_knots = res.x.copy()
                    break
            else:
                raise RuntimeError(f"Non-stationary staying LP failed on [{b_m},{h_m}]")

        B_pwl = make_pwl_from_knots(kB, y_knots, 0.0, 0.0)
        cert = verify_staying_barrier_bb(
            B_pwl, A_hi=A_hi, q_hi=q_hi, b_lo=b_lo, b_hi=b_hi, e_lo=e_lo, e_hi=e_hi,
            tol=tol_bb, B_ev_pwl=B_ev_pwl, b_m=b_m, h_m=h_m,
        )
        if cert["certified"] and cert["iv_certified"]:
            best_pwl, best_cert = B_pwl, cert
            break
        if rnd < max_rounds:
            for cx, cy, _, cval in cert["counterexamples"][:16]:
                _, cu = _golden_L_vec(A_hi, q_hi, e_lo, e_hi, np.array([cx]), np.array([cy]), is_upper=True)
                if cu[0] > -1e8:
                    fx = np.append(fx, cx); fy = np.append(fy, cy); fu = np.append(fu, float(cu[0]))
                if fixed_knots is None and cval > -1e-4 and len(kB) < 60:
                    if np.min(np.abs(np.log(kB) - math.log(max(b_m, min(h_m, cx))))) > 5e-3:
                        kB = np.unique(np.concatenate([kB, [float(np.clip(cx, b_m, h_m))]]))
        if rnd == max_rounds and best_pwl is None:
            shift = (max(cert["d_ub"], cert["d_ub_iv"]) + 4e-4) / (1.0 if B_ev_pwl is not None else (1.0 - b_hi))
            B_pwl = make_pwl_from_knots(kB, y_knots + shift, 0.0, 0.0)
            cert = verify_staying_barrier_bb(
                B_pwl, A_hi=A_hi, q_hi=q_hi, b_lo=b_lo, b_hi=b_hi, e_lo=e_lo, e_hi=e_hi,
                tol=tol_bb, B_ev_pwl=B_ev_pwl, b_m=b_m, h_m=h_m,
            )
            if cert["certified"] and cert["iv_certified"]:
                best_pwl, best_cert = B_pwl, cert

    if best_pwl is None or not (best_cert["certified"] and best_cert["iv_certified"]):
        raise RuntimeError(f"Staying barrier failed certification on [{b_m},{h_m}]: {best_cert}")
    return best_pwl, best_cert


def synth_static_certificate(
    box: ParamBox,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    k_h2: float = 0.80,
    k_lo: float = 1e-4,
    k_hi: float = 90.0,
    include_nonstationary: bool = False,
) -> Dict[str, object]:
    """Synthesize and certify a complete 1D static certificate on `box`."""
    k_hi = float(k_hi)
    k_t_g = np.unique(np.concatenate([
        np.geomspace(k_lo, 0.0012, 20, endpoint=False),
        np.geomspace(0.0012, 0.0060, 48, endpoint=False),
        np.geomspace(0.0060, 0.05, 32, endpoint=False),
        np.geomspace(0.05, 0.40, 40, endpoint=False),
        np.geomspace(0.40, 60.0, 60),
    ]))
    k_w_g = np.unique(np.concatenate([
        np.geomspace(b_m, h_m, 48, endpoint=False),
        np.geomspace(h_m, k_h2, 48, endpoint=False),
        np.geomspace(k_h2, 5.5, 48),
    ]))

    V_up, _, _ = solve_teacher_vfi(box.A_hi, box.q_hi, box.b_lo, box.e_lo, box.e_hi, True, k_t_g)
    V_lo, kp_lo, L_lo = solve_teacher_vfi(box.A_lo, box.q_lo, box.b_hi, box.e_lo, box.e_hi, False, k_w_g)

    C_max = box.q_hi * h_m + float(F_A(box.A_hi, h_m, 1.0)) - b_m
    m_req_M = (box.e_lo * box.q_lo) / C_max
    l0_M = _pick_adverse_l0(box.A_lo, box.A_hi, box.q_lo, b_m, b_m, float(L_lo[0]), box.e_lo, box.e_hi)
    i_h = int(np.argmin(np.abs(k_w_g - h_m)))
    l0_H1 = _pick_adverse_l0(box.A_lo, box.A_hi, box.q_lo, h_m, h_m, float(L_lo[i_h]), box.e_lo, box.e_hi)

    c_b_min = _min_c_E_plus(box.A_lo, box.q_lo, b_m, b_m, l0_M, box.e_lo, box.e_hi)
    c_h_min = _min_c_E_plus(box.A_lo, box.q_lo, h_m, h_m, l0_H1, box.e_lo, box.e_hi)
    if c_b_min <= 1e-6 or c_h_min <= 1e-6:
        raise RuntimeError(f"Adverse exit infeasible at {box.label}: c_b={c_b_min:.4g}, c_h={c_h_min:.4g}")

    req_b = (box.e_hi / c_b_min) / box.b_lo + 0.5
    req_h = (box.e_hi / c_h_min) / box.b_lo + 0.5

    s_lo = _safe_s_lo(box.e_lo, box.b_lo)
    D_hi = _safe_D_hi(box.e_hi, box.b_hi)

    def init_psi(kq: np.ndarray) -> np.ndarray:
        kq_a = np.asarray(kq, dtype=np.float64)
        v = np.interp(np.log(np.clip(kq_a, k_t_g[0], k_t_g[-1])), np.log(k_t_g), V_up)
        v = np.where(kq_a < k_t_g[0], V_up[0] + s_lo * np.log(kq_a / k_t_g[0]), v)
        return np.where(kq_a > k_t_g[-1], V_up[-1] + D_hi * np.log(kq_a / k_t_g[-1]), v)

    Psi_pwl, cert_Psi, _ = cegis_lp_super_barrier(
        box.A_hi, box.b_lo, box.b_hi, box.q_hi, box.e_lo, box.e_hi,
        k_lo=k_lo, k_hi=k_hi, init_vals_fn=init_psi,
        m_min_slope=m_req_M, pre_b_slope=req_b, pre_h_slope=req_h, b_m=b_m, h_m=h_m,
    )
    W_pwl, kp_pwl, L_pwl, cert_W, _ = cegis_lp_witness(
        box.A_lo, box.q_lo, box.b_lo, box.b_hi, box.e_lo, box.e_hi,
        k_domain=(b_m, 5.5), m_req_M=m_req_M, b_m=b_m, h_m=h_m, k_h2=k_h2,
    )

    psi_b = float(eval_logpwl(Psi_pwl, np.array([b_m]))[0])
    psi_h = float(eval_logpwl(Psi_pwl, np.array([h_m]))[0])

    exit_M = verify_adverse_exit_bb(
        W_pwl, psi_b, box.A_hi, box.q_hi, box.b_lo, box.b_hi, box.e_lo, box.e_hi,
        b_m, l0_M, (b_m, h_m), h_m=h_m,
    )
    exit_H1 = verify_adverse_exit_bb(
        W_pwl, psi_h, box.A_hi, box.q_hi, box.b_lo, box.b_hi, box.e_lo, box.e_hi,
        h_m, l0_H1, (h_m, k_h2), h_m=h_m,
    )
    kp80 = float(eval_logpwl(kp_pwl, np.array([k_h2]))[0])
    L80 = float(eval_logpwl(L_pwl, np.array([k_h2]))[0])
    ew80 = float(eval_logpwl(W_pwl, np.array([kp80]))[0])
    h2_ok, h2_gap = verify_H2_global_interval(
        W_pwl, kp80, L80, ew80, psi_h,
        box.A_lo, box.A_hi, box.q_lo, box.q_hi, box.b_lo, box.b_hi, box.e_lo, box.e_hi,
        h_m=h_m, k_h2=k_h2,
    )
    ok_db, m_db, _ = verify_derivative_below_bound(
        Psi_pwl, b_m, box.b_lo, box.A_lo, box.q_lo, b_m, l0_M, box.e_lo, box.e_hi,
    )
    ok_dh, m_dh, _ = verify_derivative_below_bound(
        Psi_pwl, h_m, box.b_lo, box.A_lo, box.q_lo, h_m, l0_H1, box.e_lo, box.e_hi,
    )
    if not (exit_M["certified"] and exit_H1["certified"] and h2_ok and ok_db and ok_dh):
        raise RuntimeError(
            f"Adverse exit/deriv check failed on {box.label}: M={exit_M['m_lb_iv']:.4f}, "
            f"H1={exit_H1['m_lb_iv']:.4f}, H2={h2_gap:.4f}, db={m_db:.3f}, dh={m_dh:.3f}"
        )

    B_pwl, cert_B = cegis_lp_staying_barrier(
        b_m, h_m, box.A_hi, box.q_hi, box.b_lo, box.b_hi, box.e_lo, box.e_hi,
        target_W_pwl=W_pwl, min_slope_M=0.02,
    )
    T_cert, inf_W_B, sup_Psi_B = certify_staying_deadline_interval(
        B_pwl, Psi_pwl, W_pwl, b_max=box.b_hi, b_m=b_m, h_m=h_m,
    )

    out = {
        "box": box.to_dict(),
        "b_m": float(b_m),
        "h_m": float(h_m),
        "k_h2": float(k_h2),
        "l0_M": float(l0_M),
        "l0_H1": float(l0_H1),
        "m_req_M": float(m_req_M),
        "T_cert": int(T_cert),
        "inf_W_B": float(inf_W_B),
        "sup_Psi_B": float(sup_Psi_B),
        "margins": {
            "d_ub_Psi_iv": float(cert_Psi["d_ub_iv"]),
            "d_ub_W_iv": float(cert_W["d_ub_iv"]),
            "d_ub_B_iv": float(cert_B["d_ub_iv"]),
            "exit_M_iv": float(exit_M["m_lb_iv"]),
            "exit_H1_iv": float(exit_H1["m_lb_iv"]),
            "exit_H2_iv": float(h2_gap),
            "deriv_b_margin": float(m_db),
            "deriv_h_margin": float(m_dh),
        },
        "Psi": Psi_pwl,
        "W": W_pwl,
        "kp": kp_pwl,
        "L": L_pwl,
        "B": B_pwl,
    }
    if include_nonstationary:
        from core.pwl_basis import eval_logpwl as _ev
        ks_r = np.unique(np.concatenate([[b_m], [float(k) for k in Psi_pwl["ks"] if b_m < k < h_m], [h_m]]))
        J0 = make_pwl_from_knots(ks_r, _ev(Psi_pwl, ks_r) + 1e-10, 0.0, 0.0)
        J_cur = J0
        T_ns = None
        for step in range(1, 11):
            Jk, _ = cegis_lp_staying_barrier(
                b_m, h_m, box.A_hi, box.q_hi, box.b_lo, box.b_hi, box.e_lo, box.e_hi,
                B_ev_pwl=J_cur, n_knots=32, min_slope_M=0.0,
            )
            J_cur = Jk
            ks_chk = np.geomspace(b_m, h_m, 40)
            if float(np.min(_ev(W_pwl, ks_chk) - _ev(Jk, ks_chk))) > 1e-4:
                T_ns = step
                break
        out["T_ns"] = T_ns
    return out


# ---------------------------------------------------------------------------
# Coupled 2-Regime Markov CEGIS-LP Synthesizer
# ---------------------------------------------------------------------------
def synth_coupled_markov_certificate(
    regimes: Tuple[RegimeSpec, RegimeSpec],
    P: np.ndarray,
    b_m: float = CANONICAL_BM,
    h_m: float = CANONICAL_HM,
    k_h2: float = 0.80,
    max_rounds: int = 28,
) -> Dict[str, object]:
    """
    Synthesize and certify a coupled 2-regime Markov system (Psi_0, Psi_1),
    (W_0, W_1), (B_0, B_1) with regime-specific (A_w, q_w) and transition matrix P.
    """
    r0, r1 = regimes
    P = np.asarray(P, dtype=np.float64)
    assert P.shape == (2, 2) and np.allclose(P.sum(axis=1), 1.0)
    bL = min(r0.box.b_lo, r1.box.b_lo)
    bR = max(r0.box.b_hi, r1.box.b_hi)
    eL = min(r0.box.e_lo, r1.box.e_lo)
    eU = max(r0.box.e_hi, r1.box.e_hi)

    k_lo, k_hi = 1e-4, 90.0
    s_lo = _safe_s_lo(eL, bL)
    D_hi = _safe_D_hi(eU, bR)

    k_t_g = np.unique(np.concatenate([
        np.geomspace(k_lo, 0.0012, 18, endpoint=False),
        np.geomspace(0.0012, 0.0060, 44, endpoint=False),
        np.geomspace(0.0060, 0.04, 24, endpoint=False),
        np.geomspace(0.04, 0.30, 36, endpoint=False),
        np.geomspace(0.30, 60.0, 70),
    ]))
    k_w_g = np.unique(np.concatenate([
        np.geomspace(b_m, h_m, 48, endpoint=False),
        np.geomspace(h_m, k_h2, 48, endpoint=False),
        np.geomspace(k_h2, 5.5, 48),
    ]))

    V0_u, V1_u, _, _, _, _ = solve_markov_teacher_vfi(
        P, r0.box.A_hi, r1.box.A_hi, r0.box.q_hi, r1.box.q_hi, bL, eL, eU, True, k_t_g,
    )
    V0_l, V1_l, kp0_l, L0_l, kp1_l, L1_l = solve_markov_teacher_vfi(
        P, r0.box.A_lo, r1.box.A_lo, r0.box.q_lo, r1.box.q_lo, bR, eL, eU, False, k_w_g,
    )

    C_max_0 = r0.box.q_hi * h_m + float(F_A(r0.box.A_hi, h_m, 1.0)) - b_m
    C_max_1 = r1.box.q_hi * h_m + float(F_A(r1.box.A_hi, h_m, 1.0)) - b_m
    m_0 = (eL * r0.box.q_lo) / C_max_0
    m_1 = (eL * r1.box.q_lo) / C_max_1

    i_h = int(np.argmin(np.abs(k_w_g - h_m)))
    l0_M_0 = _pick_adverse_l0(r0.box.A_lo, r0.box.A_hi, r0.box.q_lo, b_m, b_m, float(L0_l[0]), eL, eU)
    l0_M_1 = _pick_adverse_l0(r1.box.A_lo, r1.box.A_hi, r1.box.q_lo, b_m, b_m, float(L1_l[0]), eL, eU)
    l0_H1_0 = _pick_adverse_l0(r0.box.A_lo, r0.box.A_hi, r0.box.q_lo, h_m, h_m, float(L0_l[i_h]), eL, eU)
    l0_H1_1 = _pick_adverse_l0(r1.box.A_lo, r1.box.A_hi, r1.box.q_lo, h_m, h_m, float(L1_l[i_h]), eL, eU)

    req_b_0 = (eU / _min_c_E_plus(r0.box.A_lo, r0.box.q_lo, b_m, b_m, l0_M_0, eL, eU)) / bL + 2.5
    req_b_1 = (eU / _min_c_E_plus(r1.box.A_lo, r1.box.q_lo, b_m, b_m, l0_M_1, eL, eU)) / bL + 2.5
    req_h_0 = (eU / _min_c_E_plus(r0.box.A_lo, r0.box.q_lo, h_m, h_m, l0_H1_0, eL, eU)) / bL + 2.5
    req_h_1 = (eU / _min_c_E_plus(r1.box.A_lo, r1.box.q_lo, h_m, h_m, l0_H1_1, eL, eU)) / bL + 2.5

    # --- Phase 1: Joint Coupled Super-Barriers (Psi_0, Psi_1) ---
    k_knots = np.unique(np.concatenate([
        [k_lo],
        np.geomspace(k_lo, 0.0012, 18, endpoint=False),
        np.geomspace(0.0012, 0.0150, 72, endpoint=False),
        np.geomspace(0.0150, 0.05, 24, endpoint=False),
        np.geomspace(0.05, b_m, 14, endpoint=False),
        np.linspace(b_m, h_m, 14, endpoint=False),
        np.geomspace(h_m, 1.0, 32, endpoint=False),
        np.geomspace(1.0, 6.0, 28, endpoint=False),
        np.geomspace(6.0, k_hi, 16),
        [1.0, k_hi],
    ]))

    def _init_vals(V_g: np.ndarray, k_q: np.ndarray) -> np.ndarray:
        kq = np.asarray(k_q, dtype=np.float64)
        v = np.interp(np.log(np.clip(kq, k_t_g[0], k_t_g[-1])), np.log(k_t_g), V_g)
        v = np.where(kq < k_t_g[0], V_g[0] + s_lo * np.log(kq / k_t_g[0]), v)
        return np.where(kq > k_t_g[-1], V_g[-1] + D_hi * np.log(kq / k_t_g[-1]), v)

    Ls_act = np.concatenate([[0.0], np.geomspace(1e-7, 0.08, 14, endpoint=False), np.linspace(0.08, 0.996, 46)])
    ss_act = np.unique(np.concatenate([
        np.linspace(0.30, 0.70, 8, endpoint=False),
        np.linspace(0.70, 0.95, 42, endpoint=False),
        1.0 - np.geomspace(1.0e-4, 0.05, 28),
    ]))
    ce_x0, ce_L0, ce_s0 = np.array([]), np.array([]), np.array([])
    ce_x1, ce_L1, ce_s1 = np.array([]), np.array([]), np.array([])

    r_top_0 = r0.box.q_hi + float(F_A(r0.box.A_hi, k_lo, 1.0)) / k_lo
    r_top_1 = r1.box.q_hi + float(F_A(r1.box.A_hi, k_lo, 1.0)) / k_lo
    Y_end_0 = r0.box.q_hi * k_hi + r0.box.A_hi * (2.0 ** 1.5)
    Y_end_1 = r1.box.q_hi * k_hi + r1.box.A_hi * (2.0 ** 1.5)

    p00, p01 = float(P[0, 0]), float(P[0, 1])
    p10, p11 = float(P[1, 0]), float(P[1, 1])

    best_0 = best_1 = best_c0 = best_c1 = None
    last_0 = last_1 = None
    best_score = float("inf")

    for rnd in range(1, max_rounds + 1):
        n_k = len(k_knots)
        z_knots = np.log(k_knots)
        dlk = np.diff(z_knots)
        k_mids = np.sqrt(k_knots[:-1] * k_knots[1:])
        sk_mask = k_knots[1:] <= h_m + 1e-9
        k_q1 = np.exp(0.75 * z_knots[:-1][sk_mask] + 0.25 * z_knots[1:][sk_mask])
        k_q3 = np.exp(0.25 * z_knots[:-1][sk_mask] + 0.75 * z_knots[1:][sk_mask])
        k_eval = np.unique(np.concatenate([k_knots, k_mids, k_q1, k_q3]))

        def _col_st(Av, qv, V_ref, pwl_self, pwl_ev, state_idx: int):
            v_s = _init_vals(V_ref, k_eval) if pwl_self is None else eval_logpwl(pwl_self, k_eval)
            Ya = qv * k_eval[:, None] + F_A(Av, k_eval[:, None], Ls_act[None, :])
            ca = np.maximum((1.0 - ss_act[None, None, :]) * Ya[:, :, None], 1e-18)
            ya = np.maximum(ss_act[None, None, :] * Ya[:, :, None], 1e-18)
            ua = np.where(ca < 1.0, eL, eU) * np.log(ca) + (1.0 - eU) * np.log(1.0 - Ls_act[None, :, None])
            if pwl_ev is None:
                ev0 = _init_vals(V0_u, ya.ravel()).reshape(ya.shape)
                ev1 = _init_vals(V1_u, ya.ravel()).reshape(ya.shape)
                eva = (p00 * ev0 + p01 * ev1) if state_idx == 0 else (p10 * ev0 + p11 * ev1)
            else:
                eva = eval_logpwl(pwl_ev, ya)
            ba = np.where(eva < 0.0, bL, bR)
            resa = (ua + ba * eva - v_s[:, None, None]).reshape(len(k_eval), -1)
            top_idx = np.argpartition(resa, -6, axis=1)[:, -6:].ravel()
            ax = np.repeat(k_eval, 6); aL = Ls_act[top_idx // len(ss_act)]; aS = ss_act[top_idx % len(ss_act)]
            xs_e = np.repeat(k_eval, 6)
            Ls_e = np.tile([0.0, 1e-6, 0.36, 0.58, 0.78, 0.95], len(k_eval))
            ss_e = np.tile([0.97, 0.92, 0.70, 0.88, 0.955, 0.9985], len(k_eval))
            cx, cL, cs = (ce_x0, ce_L0, ce_s0) if state_idx == 0 else (ce_x1, ce_L1, ce_s1)
            px = np.concatenate([ax, xs_e, cx]) if len(cx) > 0 else np.concatenate([ax, xs_e])
            pL = np.concatenate([aL, Ls_e, cL]) if len(cx) > 0 else np.concatenate([aL, Ls_e])
            ps = np.concatenate([aS, ss_e, cs]) if len(cx) > 0 else np.concatenate([aS, ss_e])
            Yp = qv * px + F_A(Av, px, pL)
            cp = np.maximum((1.0 - ps) * Yp, 1e-18)
            yp = np.maximum(ps * Yp, 1e-18)
            up = np.where(cp < 1.0, eL, eU) * np.log(cp) + (1.0 - eU) * np.log(1.0 - pL)
            return np.log(px), np.log(yp), up

        ev0_cur = None if last_0 is None else make_pwl_from_knots(last_0["ks"], p00 * last_0["vals"] + p01 * last_1["vals"], s_lo, D_hi)
        ev1_cur = None if last_0 is None else make_pwl_from_knots(last_0["ks"], p10 * last_0["vals"] + p11 * last_1["vals"], s_lo, D_hi)
        zx0, zy0, u0 = _col_st(r0.box.A_hi, r0.box.q_hi, V0_u, last_0, ev0_cur, 0)
        zx1, zy1, u1 = _col_st(r1.box.A_hi, r1.box.q_hi, V1_u, last_1, ev1_cur, 1)

        Mx0, _ = eval_pwl_basis_sparse(z_knots, zx0, s_lo, D_hi)
        My0, oy0 = eval_pwl_basis_sparse(z_knots, zy0, s_lo, D_hi)
        Mx1, _ = eval_pwl_basis_sparse(z_knots, zx1, s_lo, D_hi)
        My1, oy1 = eval_pwl_basis_sparse(z_knots, zy1, s_lo, D_hi)

        sl0_hi = 0.165
        sl1_hi = 0.165
        req0 = np.where((k_knots[:-1] >= b_m - 1e-9) & (k_knots[1:] <= h_m + 1e-9), m_0, 0.0)
        req1 = np.where((k_knots[:-1] >= b_m - 1e-9) & (k_knots[1:] <= h_m + 1e-9), m_1, 0.0)
        req0 = np.where(k_knots[:-1] >= 1.0, np.maximum(req0, sl0_hi), req0)
        req1 = np.where(k_knots[:-1] >= 1.0, np.maximum(req1, sl1_hi), req1)

        A_mon_base = monotone_diff_sparse(n_k)
        Z_blk = sp.csr_matrix((n_k - 1, n_k), dtype=np.float64)
        A_mon_0 = sp.hstack([A_mon_base, Z_blk], format="csr")
        A_mon_1 = sp.hstack([Z_blk, A_mon_base], format="csr")
        b_mon_0 = -np.maximum(np.maximum(req0 * k_knots[1:], np.where(k_knots[1:] <= 0.0012, s_lo, 0.0)) * dlk, 1e-6)
        b_mon_1 = -np.maximum(np.maximum(req1 * k_knots[1:], np.where(k_knots[1:] <= 0.0012, s_lo, 0.0)) * dlk, 1e-6)

        req_ev0 = np.where(k_knots[:-1] < b_m + 1e-9, req_b_0, np.where(k_knots[:-1] < h_m + 1e-9, req_h_0, 0.0))
        req_ev1 = np.where(k_knots[:-1] < b_m + 1e-9, req_b_1, np.where(k_knots[:-1] < h_m + 1e-9, req_h_1, 0.0))
        m_d0, m_d1 = req_ev0 > 0.0, req_ev1 > 0.0
        A_ev0 = sp.hstack([p00 * A_mon_base[m_d0], p01 * A_mon_base[m_d0]], format="csr")
        b_ev0 = -(req_ev0[m_d0] * k_knots[1:][m_d0] * dlk[m_d0])
        A_ev1 = sp.hstack([p10 * A_mon_base[m_d1], p11 * A_mon_base[m_d1]], format="csr")
        b_ev1 = -(req_ev1[m_d1] * k_knots[1:][m_d1] * dlk[m_d1])

        tv_idx = np.where((k_knots[1:-1] >= 0.05) | (k_knots[1:-1] <= 0.0010))[0]
        n_tv = len(tv_idx)
        if n_tv > 0:
            j_arr = np.arange(n_tv, dtype=np.int32)
            inv_d0 = 1.0 / dlk[tv_idx]; inv_d1 = 1.0 / dlk[tv_idx + 1]
            r_tvm = np.concatenate([
                np.repeat(4 * j_arr, 4), np.repeat(4 * j_arr + 1, 4),
                np.repeat(4 * j_arr + 2, 4), np.repeat(4 * j_arr + 3, 4),
            ])
            c_tvm = np.concatenate([
                np.column_stack([tv_idx, tv_idx + 1, tv_idx + 2, 2 * n_k + j_arr]).ravel(),
                np.column_stack([tv_idx, tv_idx + 1, tv_idx + 2, 2 * n_k + j_arr]).ravel(),
                np.column_stack([n_k + tv_idx, n_k + tv_idx + 1, n_k + tv_idx + 2, 2 * n_k + n_tv + j_arr]).ravel(),
                np.column_stack([n_k + tv_idx, n_k + tv_idx + 1, n_k + tv_idx + 2, 2 * n_k + n_tv + j_arr]).ravel(),
            ]).astype(np.int32)
            d_tvm = np.concatenate([
                np.column_stack([inv_d0, -(inv_d0 + inv_d1), inv_d1, np.full(n_tv, -1.0)]).ravel(),
                np.column_stack([-inv_d0, (inv_d0 + inv_d1), -inv_d1, np.full(n_tv, -1.0)]).ravel(),
                np.column_stack([inv_d0, -(inv_d0 + inv_d1), inv_d1, np.full(n_tv, -1.0)]).ravel(),
                np.column_stack([-inv_d0, (inv_d0 + inv_d1), -inv_d1, np.full(n_tv, -1.0)]).ravel(),
            ])
            A_tv_m = sp.csr_matrix((d_tvm, (r_tvm, c_tvm)), shape=(4 * n_tv, 2 * n_k + 2 * n_tv))
        else:
            A_tv_m = sp.csr_matrix((0, 2 * n_k), dtype=np.float64)
        b_tv_m = np.zeros(4 * n_tv, dtype=np.float64)

        M1, o1 = eval_pwl_basis_sparse(z_knots, np.array([0.0]), s_lo, D_hi)
        c_obj_y = np.zeros(2 * n_k, dtype=np.float64)
        m_mask = (k_knots >= b_m - 1e-9) & (k_knots <= h_m + 1e-9)
        c_obj_y[:n_k][m_mask] = 0.80 / max(1, int(np.sum(m_mask)))
        c_obj_y[n_k:][m_mask] = 0.80 / max(1, int(np.sum(m_mask)))
        c_obj_y += 1e-3 / (2 * n_k)
        c_obj = np.concatenate([c_obj_y, np.full(2 * n_tv, 2.5e-4, dtype=np.float64)])
        lp_bounds_m = [(-2500.0, 2500.0)] * (2 * n_k) + [(0.0, None)] * (2 * n_tv)

        y0_cur = _init_vals(V0_u, k_knots) if last_0 is None else eval_logpwl(last_0, k_knots)
        y1_cur = _init_vals(V1_u, k_knots) if last_1 is None else eval_logpwl(last_1, k_knots)
        px0, px1 = np.exp(zx0), np.exp(zx1)
        m_base_0 = np.where(px0 >= 0.25, 0.0018, np.where(px0 >= 0.05, 0.0022, np.where(px0 >= 0.015, 0.0080, 0.018)))
        m_base_1 = np.where(px1 >= 0.25, 0.0018, np.where(px1 >= 0.05, 0.0022, np.where(px1 >= 0.015, 0.0080, 0.018)))

        e_0_last = sp.csr_matrix(([-1.0], ([0], [n_k - 1])), shape=(1, 2 * n_k))
        e_1_last = sp.csr_matrix(([-1.0], ([0], [2 * n_k - 1])), shape=(1, 2 * n_k))
        solved = False
        for m_scale in (1.0, 0.65, 0.35, 0.15, 0.05):
            m_vec_0, m_vec_1 = m_scale * m_base_0, m_scale * m_base_1
            m_t_lo, m_t_hi = m_scale * 0.018, m_scale * 0.0012
            y0_t, y1_t = y0_cur.copy(), y1_cur.copy()
            ok_pass = False
            for _sp in range(2):
                ev0_y = p00 * (My0 @ y0_t + oy0) + p01 * (My0 @ y1_t + oy0)
                ev1_y = p10 * (My1 @ y0_t + oy1) + p11 * (My1 @ y1_t + oy1)
                n00, n01 = np.abs(ev0_y) <= 1.5, np.abs(ev1_y) <= 1.5
                A_rows = [A_mon_0, A_mon_1, A_ev0, A_ev1]
                b_rows = [b_mon_0, b_mon_1, b_ev0, b_ev1]
                for bv_c, m_c in ((bL, (ev0_y < 0.0) | n00), (bR, (ev0_y >= 0.0) | n00)):
                    if np.any(m_c):
                        A_rows.append(sp.hstack([bv_c * p00 * My0[m_c] - Mx0[m_c], bv_c * p01 * My0[m_c]], format="csr"))
                        b_rows.append(-(u0[m_c] + bv_c * oy0[m_c] + m_vec_0[m_c]))
                for bv_c, m_c in ((bL, (ev1_y < 0.0) | n01), (bR, (ev1_y >= 0.0) | n01)):
                    if np.any(m_c):
                        A_rows.append(sp.hstack([bv_c * p10 * My1[m_c], bv_c * p11 * My1[m_c] - Mx1[m_c]], format="csr"))
                        b_rows.append(-(u1[m_c] + bv_c * oy1[m_c] + m_vec_1[m_c]))
                for bv_t in (bL, bR):
                    c_slo = eL + bv_t * s_lo
                    s_lo_opt = (bv_t * s_lo) / c_slo
                    tl0 = eL * math.log((1.0 - s_lo_opt) * k_lo) + bv_t * s_lo * math.log(s_lo_opt) + c_slo * math.log(r_top_0)
                    tl1 = eL * math.log((1.0 - s_lo_opt) * k_lo) + bv_t * s_lo * math.log(s_lo_opt) + c_slo * math.log(r_top_1)
                    A_rows.extend([
                        sp.csr_matrix(([bv_t * p00 - 1.0, bv_t * p01], ([0, 0], [0, n_k])), shape=(1, 2 * n_k)),
                        sp.csr_matrix(([bv_t * p10, bv_t * p11 - 1.0], ([0, 0], [0, n_k])), shape=(1, 2 * n_k)),
                    ])
                    b_rows.extend([np.array([-(tl0 + m_t_lo)]), np.array([-(tl1 + m_t_lo)])])

                    c_dhi = eU + bv_t * D_hi
                    s_hi_opt = (bv_t * D_hi) / c_dhi
                    th0 = eU * math.log(1.0 - s_hi_opt) + bv_t * D_hi * math.log(s_hi_opt) + c_dhi * math.log(Y_end_0 / k_hi) + eU * math.log(k_hi)
                    th1 = eU * math.log(1.0 - s_hi_opt) + bv_t * D_hi * math.log(s_hi_opt) + c_dhi * math.log(Y_end_1 / k_hi) + eU * math.log(k_hi)
                    A_rows.extend([
                        sp.csr_matrix(([bv_t * p00 - 1.0, bv_t * p01], ([0, 0], [n_k - 1, 2 * n_k - 1])), shape=(1, 2 * n_k)),
                        sp.csr_matrix(([bv_t * p10, bv_t * p11 - 1.0], ([0, 0], [n_k - 1, 2 * n_k - 1])), shape=(1, 2 * n_k)),
                        sp.hstack([bv_t * p00 * M1, bv_t * p01 * M1], format="csr") + e_0_last,
                        sp.hstack([bv_t * p10 * M1, bv_t * p11 * M1], format="csr") + e_1_last,
                    ])
                    b_rows.extend([
                        np.array([-(th0 + m_t_hi)]), np.array([-(th1 + m_t_hi)]),
                        np.array([-(eU * math.log(Y_end_0) + bv_t * float(o1[0]) + m_t_hi)]),
                        np.array([-(eU * math.log(Y_end_1) + bv_t * float(o1[0]) + m_t_hi)]),
                    ])
                A_y_blk = sp.vstack(A_rows, format="csr")
                b_y_blk = np.concatenate(b_rows)
                A_full = sp.vstack([
                    sp.hstack([A_y_blk, sp.csr_matrix((A_y_blk.shape[0], 2 * n_tv), dtype=np.float64)], format="csr"),
                    A_tv_m,
                ], format="csc") if n_tv > 0 else A_y_blk.tocsc()
                b_full = np.concatenate([b_y_blk, b_tv_m]) if n_tv > 0 else b_y_blk
                res = linprog(c_obj, A_ub=A_full, b_ub=b_full, bounds=lp_bounds_m, method="highs")
                if res.success:
                    y0_t, y1_t = res.x[:n_k].copy(), res.x[n_k:2 * n_k].copy()
                    ok_pass = True
                else:
                    ok_pass = False
                    break
            if ok_pass:
                y0_knots, y1_knots = y0_t, y1_t
                solved = True
                break
        if not solved:
            raise RuntimeError(f"Coupled Markov super-barrier LP failed at round {rnd}")

        p0 = make_pwl_from_knots(k_knots, y0_knots, s_lo, D_hi)
        p1 = make_pwl_from_knots(k_knots, y1_knots, s_lo, D_hi)
        last_0, last_1 = p0, p1
        ev0_pwl = make_pwl_from_knots(k_knots, p00 * y0_knots + p01 * y1_knots, s_lo, D_hi)
        ev1_pwl = make_pwl_from_knots(k_knots, p10 * y0_knots + p11 * y1_knots, s_lo, D_hi)
        c0 = verify_super_barrier_bb(p0, ev0_pwl, r0.box.A_hi, bL, bR, q_hi=r0.box.q_hi, eL=eL, eU=eU, tol=3e-4)
        c1 = verify_super_barrier_bb(p1, ev1_pwl, r1.box.A_hi, bL, bR, q_hi=r1.box.q_hi, eL=eL, eU=eU, tol=3e-4)
        score = float(eval_logpwl(p0, np.array([h_m]))[0] + eval_logpwl(p1, np.array([h_m]))[0])
        if c0["certified"] and c1["certified"] and score < best_score:
            best_0, best_1, best_c0, best_c1 = p0, p1, c0, c1
            best_score = score
        if c0["certified"] and c1["certified"]:
            break

        ins_k = []
        for c_res, st_i in ((c0, 0), (c1, 1)):
            if not c_res["certified"]:
                ce_list_m = sorted(c_res["counterexamples"], key=lambda t: t[3], reverse=True)[:16]
                nx, nL, ns = [], [], []
                for cx, cL, cs, cv in ce_list_m:
                    if cv > -1.5e-3:
                        ins_k.append(float(np.clip(cx, k_lo * 1.05, k_hi * 0.95)))
                    for sc in (0.992, 1.0, 1.008):
                        nx.append(float(np.clip(cx * sc, k_lo, k_hi)))
                        nL.append(float(np.clip(cL, 0.0, 0.9999)))
                        ns.append(float(np.clip(cs, 1e-4, 0.99999)))
                if nx:
                    if st_i == 0:
                        ce_x0 = np.concatenate([ce_x0, np.array(nx)]); ce_L0 = np.concatenate([ce_L0, np.array(nL)]); ce_s0 = np.concatenate([ce_s0, np.array(ns)])
                    else:
                        ce_x1 = np.concatenate([ce_x1, np.array(nx)]); ce_L1 = np.concatenate([ce_L1, np.array(nL)]); ce_s1 = np.concatenate([ce_s1, np.array(ns)])
        if ins_k and len(k_knots) < 320:
            cand_add = [ck for ck in ins_k if np.min(np.abs(np.log(k_knots) - math.log(ck))) > 2.0e-3]
            if cand_add:
                k_knots = np.unique(np.concatenate([k_knots, np.array(cand_add[:14])]))

    if best_0 is None or not (best_c0["certified"] and best_c0["iv_certified"] and best_c1["certified"] and best_c1["iv_certified"]):
        raise RuntimeError("Coupled Markov super-barrier failed certification")
    Psi0_pwl, Psi1_pwl = best_0, best_1

    # --- Phase 2: Joint Coupled Witnesses (W_0, W_1) ---
    k_a, k_b = b_m, 5.5
    pol_idx = np.unique(np.concatenate([np.arange(0, len(k_w_g), 2), [len(k_w_g) - 1]]))
    kp0_pwl = make_pwl_from_knots(k_w_g[pol_idx], np.clip(kp0_l[pol_idx], k_a * 1.005, k_b * 0.995), 0.0, 0.0)
    L0_pwl = make_pwl_from_knots(k_w_g[pol_idx], np.clip(L0_l[pol_idx], 0.0, 0.985), 0.0, 0.0)
    kp1_pwl = make_pwl_from_knots(k_w_g[pol_idx], np.clip(kp1_l[pol_idx], k_a * 1.005, k_b * 0.995), 0.0, 0.0)
    L1_pwl = make_pwl_from_knots(k_w_g[pol_idx], np.clip(L1_l[pol_idx], 0.0, 0.985), 0.0, 0.0)

    k_knots_w = np.unique(np.concatenate([
        [k_a, h_m, k_h2, k_b],
        np.geomspace(k_a * 1.005, h_m * 0.995, 22, endpoint=False),
        np.geomspace(h_m * 1.005, k_h2 * 0.995, 22, endpoint=False),
        np.geomspace(k_h2 * 1.005, k_b * 0.995, 22),
    ]))
    ce_k0, ce_k1 = np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    best_W0 = best_W1 = best_cW0 = best_cW1 = None

    for rnd in range(1, max_rounds + 1):
        n_w = len(k_knots_w)
        z_knots = np.log(k_knots_w)
        dlk = np.diff(z_knots)
        k_mids = np.sqrt(k_knots_w[:-1] * k_knots_w[1:])
        col_k0 = np.unique(np.concatenate([k_knots_w, k_mids, np.sqrt(k_knots_w[:-1] * k_mids), np.sqrt(k_mids * k_knots_w[1:]), ce_k0]))
        col_k1 = np.unique(np.concatenate([k_knots_w, k_mids, np.sqrt(k_knots_w[:-1] * k_mids), np.sqrt(k_mids * k_knots_w[1:]), ce_k1]))

        def _st_rows(Av, qv, kp_p, L_p, ck):
            Lc = np.clip(eval_logpwl(L_p, ck), 0.0, 0.999)
            kpc = np.clip(eval_logpwl(kp_p, ck), k_a, k_b)
            cc = np.maximum(qv * ck + F_A(Av, ck, Lc) - kpc, 1e-18)
            lc, ll = np.log(cc), np.log(np.maximum(1.0 - Lc, 1e-18))
            uc = np.minimum(eL * lc + (1.0 - eL) * ll, eU * lc + (1.0 - eU) * ll)
            Mx, _ = eval_pwl_basis_sparse(z_knots, np.log(ck), 0.0, 0.0)
            My, _ = eval_pwl_basis_sparse(z_knots, np.log(kpc), 0.0, 0.0)
            return Mx, My, uc

        Mx0, My0, u0 = _st_rows(r0.box.A_lo, r0.box.q_lo, kp0_pwl, L0_pwl, col_k0)
        Mx1, My1, u1 = _st_rows(r1.box.A_lo, r1.box.q_lo, kp1_pwl, L1_pwl, col_k1)
        req0_w = np.where((k_knots_w[:-1] < h_m - 1e-12) & (k_knots_w[1:] > b_m + 1e-12), m_0 + 1e-4, 0.0)
        req1_w = np.where((k_knots_w[:-1] < h_m - 1e-12) & (k_knots_w[1:] > b_m + 1e-12), m_1 + 1e-4, 0.0)
        A_mon_b = monotone_diff_sparse(n_w)
        Z_blk = sp.csr_matrix((n_w - 1, n_w), dtype=np.float64)
        A_mon_0 = sp.hstack([A_mon_b, Z_blk], format="csr"); b_mon_0 = -(req0_w * k_knots_w[1:] * dlk)
        A_mon_1 = sp.hstack([Z_blk, A_mon_b], format="csr"); b_mon_1 = -(req1_w * k_knots_w[1:] * dlk)

        c_w = -np.ones(2 * n_w, dtype=np.float64) / (2 * n_w)
        c_w[0] -= 0.25; c_w[n_w] -= 0.25
        i_h_w = int(np.argmin(np.abs(k_knots_w - h_m)))
        c_w[i_h_w] -= 0.20; c_w[n_w + i_h_w] -= 0.25

        y0_t = np.interp(z_knots, np.log(k_w_g), V0_l)
        y1_t = np.interp(z_knots, np.log(k_w_g), V1_l)
        solved_w = False
        for m_trg in (2.0e-4, 8.0e-5, 3.0e-5):
            y0t, y1t = y0_t.copy(), y1_t.copy()
            ok_p = False
            for _sp in range(2):
                ew0_est = p00 * (My0 @ y0t) + p01 * (My0 @ y1t)
                ew1_est = p10 * (My1 @ y0t) + p11 * (My1 @ y1t)
                n00, n01 = np.abs(ew0_est) <= 1.5, np.abs(ew1_est) <= 1.5
                A_rows = [A_mon_0, A_mon_1]
                b_rows = [b_mon_0, b_mon_1]
                for bv_c, m_c in ((bR, (ew0_est < 0.0) | n00), (bL, (ew0_est >= 0.0) | n00)):
                    if np.any(m_c):
                        A_rows.append(sp.hstack([Mx0[m_c] - bv_c * p00 * My0[m_c], -bv_c * p01 * My0[m_c]], format="csr"))
                        b_rows.append(u0[m_c] - m_trg)
                for bv_c, m_c in ((bR, (ew1_est < 0.0) | n01), (bL, (ew1_est >= 0.0) | n01)):
                    if np.any(m_c):
                        A_rows.append(sp.hstack([-bv_c * p10 * My1[m_c], Mx1[m_c] - bv_c * p11 * My1[m_c]], format="csr"))
                        b_rows.append(u1[m_c] - m_trg)
                res = linprog(c_w, A_ub=sp.vstack(A_rows, format="csc"), b_ub=np.concatenate(b_rows), bounds=[(-500.0, 500.0)] * (2 * n_w), method="highs")
                if res.success:
                    y0t, y1t = res.x[:n_w].copy(), res.x[n_w:].copy()
                    ok_p = True
                else:
                    ok_p = False; break
            if ok_p:
                y0_kw, y1_kw = y0t, y1t
                solved_w = True; break
        if not solved_w:
            raise RuntimeError("Coupled Markov witness LP failed")

        W0 = make_pwl_from_knots(k_knots_w, y0_kw, 0.0, 0.0)
        W1 = make_pwl_from_knots(k_knots_w, y1_kw, 0.0, 0.0)
        evW0 = make_pwl_from_knots(k_knots_w, p00 * y0_kw + p01 * y1_kw, 0.0, 0.0)
        evW1 = make_pwl_from_knots(k_knots_w, p10 * y0_kw + p11 * y1_kw, 0.0, 0.0)
        cW0 = verify_witness_subsolution_bb(W0, evW0, kp0_pwl, L0_pwl, r0.box.A_lo, r0.box.q_lo, bL, bR, eL=eL, eU=eU, k_domain=(k_a, k_b), tol=8e-5, interval_check=True, h_safe=h_m)
        cW1 = verify_witness_subsolution_bb(W1, evW1, kp1_pwl, L1_pwl, r1.box.A_lo, r1.box.q_lo, bL, bR, eL=eL, eU=eU, k_domain=(k_a, k_b), tol=8e-5, interval_check=True, h_safe=h_m)
        if cW0["certified"] and cW1["certified"]:
            best_W0, best_W1, best_cW0, best_cW1 = W0, W1, cW0, cW1
            break
        ins_k = []
        for c_res, st_i in ((cW0, 0), (cW1, 1)):
            if not c_res["certified"]:
                nx = []
                for cx, cv in c_res["counterexamples"]:
                    if cv > -5e-5:
                        ins_k.append(float(np.clip(cx, k_a * 1.001, k_b * 0.999)))
                    for sc in (0.992, 1.0, 1.008):
                        nx.append(float(np.clip(cx * sc, k_a, k_b)))
                if nx:
                    if st_i == 0: ce_k0 = np.unique(np.concatenate([ce_k0, np.array(nx)]))
                    else: ce_k1 = np.unique(np.concatenate([ce_k1, np.array(nx)]))
        if ins_k and len(k_knots_w) < 160:
            cand_add = [ck for ck in ins_k if np.min(np.abs(np.log(k_knots_w) - math.log(ck))) > 1.5e-3]
            if cand_add:
                k_knots_w = np.unique(np.concatenate([k_knots_w, np.array(cand_add[:12])]))

    if best_W0 is None or not (best_cW0["certified"] and best_cW1["certified"]):
        raise RuntimeError("Coupled Markov witness failed certification")

    # Adverse exits for both regimes using coupled continuation E_w[Psi(K)]
    psi0_b = float(eval_logpwl(Psi0_pwl, np.array([b_m]))[0]); psi1_b = float(eval_logpwl(Psi1_pwl, np.array([b_m]))[0])
    psi0_h = float(eval_logpwl(Psi0_pwl, np.array([h_m]))[0]); psi1_h = float(eval_logpwl(Psi1_pwl, np.array([h_m]))[0])
    epsi_b_0 = p00 * psi0_b + p01 * psi1_b
    epsi_b_1 = p10 * psi0_b + p11 * psi1_b
    epsi_h_0 = p00 * psi0_h + p01 * psi1_h
    epsi_h_1 = p10 * psi0_h + p11 * psi1_h

    exM_0 = verify_adverse_exit_bb(best_W0, epsi_b_0, r0.box.A_hi, r0.box.q_hi, bL, bR, eL, eU, b_m, l0_M_0, (b_m, h_m), h_m=h_m)
    exM_1 = verify_adverse_exit_bb(best_W1, epsi_b_1, r1.box.A_hi, r1.box.q_hi, bL, bR, eL, eU, b_m, l0_M_1, (b_m, h_m), h_m=h_m)
    exH1_0 = verify_adverse_exit_bb(best_W0, epsi_h_0, r0.box.A_hi, r0.box.q_hi, bL, bR, eL, eU, h_m, l0_H1_0, (h_m, k_h2), h_m=h_m)
    exH1_1 = verify_adverse_exit_bb(best_W1, epsi_h_1, r1.box.A_hi, r1.box.q_hi, bL, bR, eL, eU, h_m, l0_H1_1, (h_m, k_h2), h_m=h_m)

    kp80_0 = float(eval_logpwl(kp0_pwl, np.array([k_h2]))[0]); L80_0 = float(eval_logpwl(L0_pwl, np.array([k_h2]))[0])
    ew80_0 = float(p00 * eval_logpwl(best_W0, np.array([kp80_0]))[0] + p01 * eval_logpwl(best_W1, np.array([kp80_0]))[0])
    kp80_1 = float(eval_logpwl(kp1_pwl, np.array([k_h2]))[0]); L80_1 = float(eval_logpwl(L1_pwl, np.array([k_h2]))[0])
    ew80_1 = float(p10 * eval_logpwl(best_W0, np.array([kp80_1]))[0] + p11 * eval_logpwl(best_W1, np.array([kp80_1]))[0])
    h2_ok0, h2_g0 = verify_H2_global_interval(best_W0, kp80_0, L80_0, ew80_0, epsi_h_0, r0.box.A_lo, r0.box.A_hi, r0.box.q_lo, r0.box.q_hi, bL, bR, eL, eU, h_m=h_m, k_h2=k_h2)
    h2_ok1, h2_g1 = verify_H2_global_interval(best_W1, kp80_1, L80_1, ew80_1, epsi_h_1, r1.box.A_lo, r1.box.A_hi, r1.box.q_lo, r1.box.q_hi, bL, bR, eL, eU, h_m=h_m, k_h2=k_h2)

    evPsi0 = make_pwl_from_knots(Psi0_pwl["ks"], p00 * Psi0_pwl["vals"] + p01 * Psi1_pwl["vals"], s_lo, D_hi)
    evPsi1 = make_pwl_from_knots(Psi0_pwl["ks"], p10 * Psi0_pwl["vals"] + p11 * Psi1_pwl["vals"], s_lo, D_hi)
    ok_db0, m_db0, _ = verify_derivative_below_bound(evPsi0, b_m, bL, r0.box.A_lo, r0.box.q_lo, b_m, l0_M_0, eL, eU)
    ok_db1, m_db1, _ = verify_derivative_below_bound(evPsi1, b_m, bL, r1.box.A_lo, r1.box.q_lo, b_m, l0_M_1, eL, eU)
    ok_dh0, m_dh0, _ = verify_derivative_below_bound(evPsi0, h_m, bL, r0.box.A_lo, r0.box.q_lo, h_m, l0_H1_0, eL, eU)
    ok_dh1, m_dh1, _ = verify_derivative_below_bound(evPsi1, h_m, bL, r1.box.A_lo, r1.box.q_lo, h_m, l0_H1_1, eL, eU)

    if not (exM_0["certified"] and exM_1["certified"] and exH1_0["certified"] and exH1_1["certified"]
            and h2_ok0 and h2_ok1 and ok_db0 and ok_db1 and ok_dh0 and ok_dh1):
        raise RuntimeError(
            f"Coupled Markov adverse exit/deriv failed: M=({exM_0['m_lb_iv']:.3f},{exM_1['m_lb_iv']:.3f}), "
            f"H1=({exH1_0['m_lb_iv']:.3f},{exH1_1['m_lb_iv']:.3f}), H2=({h2_g0:.3f},{h2_g1:.3f}), "
            f"db=({m_db0:.2f},{m_db1:.2f}), dh=({m_dh0:.2f},{m_dh1:.2f}), "
            f"flags=({exM_0['certified']},{exM_1['certified']},{exH1_0['certified']},{exH1_1['certified']},{h2_ok0},{h2_ok1},{ok_db0},{ok_db1},{ok_dh0},{ok_dh1})"
        )

    # --- Phase 3: Joint Coupled Staying Barriers (B_0, B_1) ---
    kB = np.geomspace(b_m, h_m, 28)
    gx, gy = np.meshgrid(np.geomspace(b_m, h_m, 32), np.geomspace(b_m, h_m, 32), indexing="ij")
    fx_base, fy_base = gx.ravel(), gy.ravel()
    feas0 = (r0.box.q_hi * fx_base + F_A(r0.box.A_hi, fx_base, 0.9999) - fy_base) > 1e-6
    feas1 = (r1.box.q_hi * fx_base + F_A(r1.box.A_hi, fx_base, 0.9999) - fy_base) > 1e-6
    fx0, fy0 = fx_base[feas0], fy_base[feas0]
    fx1, fy1 = fx_base[feas1], fy_base[feas1]
    _, fu0 = _golden_L_vec(r0.box.A_hi, r0.box.q_hi, eL, eU, fx0, fy0, is_upper=True)
    _, fu1 = _golden_L_vec(r1.box.A_hi, r1.box.q_hi, eL, eU, fx1, fy1, is_upper=True)

    best_B0 = best_B1 = best_cB0 = best_cB1 = None
    for rnd in range(1, max_rounds + 1):
        zB = np.log(kB)
        dlB = np.diff(zB)
        nB = len(kB)
        A_mon_1 = monotone_diff_sparse(nB)
        Z_blk = sp.csr_matrix((nB - 1, nB), dtype=np.float64)
        A_mon_0 = sp.hstack([A_mon_1, Z_blk], format="csr")
        A_mon_1_b = sp.hstack([Z_blk, A_mon_1], format="csr")
        b_mon_1 = -(0.02 * kB[1:] * dlB)

        Mx0, _ = eval_pwl_basis_sparse(zB, np.log(fx0), 0.0, 0.0)
        My0, _ = eval_pwl_basis_sparse(zB, np.log(fy0), 0.0, 0.0)
        Mx1, _ = eval_pwl_basis_sparse(zB, np.log(fx1), 0.0, 0.0)
        My1, _ = eval_pwl_basis_sparse(zB, np.log(fy1), 0.0, 0.0)

        w0_v = eval_logpwl(best_W0, kB)
        w1_v = eval_logpwl(best_W1, kB)
        A_gap = sp.hstack([sp.eye(2 * nB, format="csr"), np.ones((2 * nB, 1), dtype=np.float64)], format="csr")
        b_gap = np.concatenate([w0_v, w1_v])
        c_obj = np.concatenate([np.full(2 * nB, 1e-3 / (2 * nB)), np.array([-1.0])])
        bds = [(-500.0, 500.0)] * (2 * nB) + [(-50.0, 200.0)]

        y0_t, y1_t = np.full(nB, -45.0), np.full(nB, -48.0)
        solved_b = False
        for m_slk in (3.0e-3, 1.0e-3, 3.0e-4, 5.0e-5):
            y0t, y1t = y0_t.copy(), y1_t.copy()
            ok_p = False
            for _sp in range(2):
                ev0_y = p00 * (My0 @ y0t) + p01 * (My0 @ y1t)
                ev1_y = p10 * (My1 @ y0t) + p11 * (My1 @ y1t)
                n00, n01 = np.abs(ev0_y) <= 1.5, np.abs(ev1_y) <= 1.5
                A_rows = [A_mon_0, A_mon_1_b]
                b_rows = [b_mon_1, b_mon_1]
                for bv_c, mc in ((bL, (ev0_y < 0.0) | n00), (bR, (ev0_y >= 0.0) | n00)):
                    if np.any(mc):
                        A_rows.append(sp.hstack([bv_c * p00 * My0[mc] - Mx0[mc], bv_c * p01 * My0[mc]], format="csr"))
                        b_rows.append(-(fu0[mc] + m_slk))
                for bv_c, mc in ((bL, (ev1_y < 0.0) | n01), (bR, (ev1_y >= 0.0) | n01)):
                    if np.any(mc):
                        A_rows.append(sp.hstack([bv_c * p10 * My1[mc], bv_c * p11 * My1[mc] - Mx1[mc]], format="csr"))
                        b_rows.append(-(fu1[mc] + m_slk))
                A_y = sp.vstack(A_rows, format="csr")
                A_ext = sp.hstack([A_y, sp.csr_matrix((A_y.shape[0], 1), dtype=np.float64)], format="csr")
                res = linprog(c_obj, A_ub=sp.vstack([A_ext, A_gap], format="csc"), b_ub=np.concatenate(b_rows + [b_gap]), bounds=bds, method="highs")
                if res.success:
                    y0t, y1t = res.x[:nB].copy(), res.x[nB:2 * nB].copy()
                    ok_p = True
                else:
                    ok_p = False; break
            if ok_p:
                y0_k, y1_k = y0t, y1t
                solved_b = True; break
        if not solved_b:
            raise RuntimeError("Coupled staying LP failed")

        B0_pwl = make_pwl_from_knots(kB, y0_k, 0.0, 0.0)
        B1_pwl = make_pwl_from_knots(kB, y1_k, 0.0, 0.0)
        evB0 = make_pwl_from_knots(kB, p00 * y0_k + p01 * y1_k, 0.0, 0.0)
        evB1 = make_pwl_from_knots(kB, p10 * y0_k + p11 * y1_k, 0.0, 0.0)
        cB0 = verify_staying_barrier_bb(B0_pwl, A_hi=r0.box.A_hi, q_hi=r0.box.q_hi, b_lo=bL, b_hi=bR, e_lo=eL, e_hi=eU, tol=2e-4, B_ev_pwl=evB0, b_m=b_m, h_m=h_m)
        cB1 = verify_staying_barrier_bb(B1_pwl, A_hi=r1.box.A_hi, q_hi=r1.box.q_hi, b_lo=bL, b_hi=bR, e_lo=eL, e_hi=eU, tol=2e-4, B_ev_pwl=evB1, b_m=b_m, h_m=h_m)
        if cB0["certified"] and cB0["iv_certified"] and cB1["certified"] and cB1["iv_certified"]:
            best_B0, best_B1, best_cB0, best_cB1 = B0_pwl, B1_pwl, cB0, cB1
            break
        if rnd < max_rounds:
            if not cB0["certified"]:
                for cx, cy, _, _ in cB0["counterexamples"][:16]:
                    _, cu = _golden_L_vec(r0.box.A_hi, r0.box.q_hi, eL, eU, np.array([cx]), np.array([cy]), is_upper=True)
                    if cu[0] > -1e8:
                        fx0 = np.append(fx0, cx); fy0 = np.append(fy0, cy); fu0 = np.append(fu0, float(cu[0]))
            if not cB1["certified"]:
                for cx, cy, _, _ in cB1["counterexamples"][:16]:
                    _, cu = _golden_L_vec(r1.box.A_hi, r1.box.q_hi, eL, eU, np.array([cx]), np.array([cy]), is_upper=True)
                    if cu[0] > -1e8:
                        fx1 = np.append(fx1, cx); fy1 = np.append(fy1, cy); fu1 = np.append(fu1, float(cu[0]))
        elif best_B0 is None:
            mx_res = max(float(cB0["d_ub"]), float(cB0["d_ub_iv"]), float(cB1["d_ub"]), float(cB1["d_ub_iv"]))
            if mx_res > 0.0:
                shift = (mx_res + 4e-4) / (1.0 - bR)
                y0s, y1s = y0_k + shift, y1_k + shift
                B0_pwl = make_pwl_from_knots(kB, y0s, 0.0, 0.0)
                B1_pwl = make_pwl_from_knots(kB, y1s, 0.0, 0.0)
                evB0 = make_pwl_from_knots(kB, p00 * y0s + p01 * y1s, 0.0, 0.0)
                evB1 = make_pwl_from_knots(kB, p10 * y0s + p11 * y1s, 0.0, 0.0)
                cB0 = verify_staying_barrier_bb(B0_pwl, A_hi=r0.box.A_hi, q_hi=r0.box.q_hi, b_lo=bL, b_hi=bR, e_lo=eL, e_hi=eU, tol=2e-4, B_ev_pwl=evB0, b_m=b_m, h_m=h_m)
                cB1 = verify_staying_barrier_bb(B1_pwl, A_hi=r1.box.A_hi, q_hi=r1.box.q_hi, b_lo=bL, b_hi=bR, e_lo=eL, e_hi=eU, tol=2e-4, B_ev_pwl=evB1, b_m=b_m, h_m=h_m)
                if cB0["certified"] and cB0["iv_certified"] and cB1["certified"] and cB1["iv_certified"]:
                    best_B0, best_B1, best_cB0, best_cB1 = B0_pwl, B1_pwl, cB0, cB1

    if best_B0 is None or not (best_cB0["certified"] and best_cB1["certified"]):
        raise RuntimeError("Coupled staying barrier failed certification")

    doob = compute_doob_eps0_coupled_pwl_interval(
        best_B0, best_B1, best_W0, best_W1, Psi0_pwl, Psi1_pwl,
        b_max=bR, A0_hi=r0.box.A_hi, A1_hi=r1.box.A_hi, q0_hi=r0.box.q_hi, q1_hi=r1.box.q_hi,
        b_m=b_m, h_m=h_m,
    )

    return {
        "regimes": [
            {"name": r0.name, "g": float(r0.g), "box": r0.box.to_dict()},
            {"name": r1.name, "g": float(r1.g), "box": r1.box.to_dict()},
        ],
        "P": P.tolist(),
        "b_m": float(b_m),
        "h_m": float(h_m),
        "k_h2": float(k_h2),
        "l0_M": [float(l0_M_0), float(l0_M_1)],
        "l0_H1": [float(l0_H1_0), float(l0_H1_1)],
        "doob": doob,
        "margins": {
            "d_ub_Psi0_iv": float(best_c0["d_ub_iv"]),
            "d_ub_Psi1_iv": float(best_c1["d_ub_iv"]),
            "d_ub_W0_iv": float(best_cW0["d_ub_iv"]),
            "d_ub_W1_iv": float(best_cW1["d_ub_iv"]),
            "d_ub_B0_iv": float(best_cB0["d_ub_iv"]),
            "d_ub_B1_iv": float(best_cB1["d_ub_iv"]),
            "exit_M0_iv": float(exM_0["m_lb_iv"]),
            "exit_M1_iv": float(exM_1["m_lb_iv"]),
            "exit_H1_0_iv": float(exH1_0["m_lb_iv"]),
            "exit_H1_1_iv": float(exH1_1["m_lb_iv"]),
            "exit_H2_0_iv": float(h2_g0),
            "exit_H2_1_iv": float(h2_g1),
            "deriv_b_margins": [float(m_db0), float(m_db1)],
            "deriv_h_margins": [float(m_dh0), float(m_dh1)],
        },
        "Psi": [Psi0_pwl, Psi1_pwl],
        "W": [best_W0, best_W1],
        "kp": [kp0_pwl, kp1_pwl],
        "L": [L0_pwl, L1_pwl],
        "B": [best_B0, best_B1],
    }
