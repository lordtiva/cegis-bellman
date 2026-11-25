"""
Political Volatility & Markov Fiscal Regime-Switching Model (Section 6).

Two regimes Omega = {G, B}:
  - G (Reformist / pro-investment): (tau_p_G, tau_u_G) -> high A_{e,G}
  - B (Bureaucratic / confiscatory): (tau_p_B, tau_u_B) -> low A_{e,B}
    (including extreme VFI case A_{e,B} < A_* where B is inviable alone!)

Includes:
  - VFI quantification of marginal rate of substitution between bureaucracy tau_{u,G}
    and political reversal risk p_rev, precautionary flight-to-safety, and
    endogenous political risk p_rev(K) = p_rev * 1_{K < h}.
  - Coupled CEGIS-LP certification (B_G, B_B) + Doob E[tau_H] upper bounds over
    (p_rev, p_ref) grids and credibility frontier identification.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from typing import Dict, List, Tuple
import numpy as np

from core.interval_arith import (
    CANONICAL_BETA,
    CANONICAL_BM,
    CANONICAL_ETA,
    CANONICAL_HM,
    CANONICAL_Q,
)
from core.model_api import (
    Economy1D,
    MarkovEconomy1D,
    ParamBox,
    RegimeSpec,
    build_policy_param_box,
    expected_markov_hitting_time,
)
from core.cegis_lp import synth_coupled_markov_certificate
from models.barro_u_frag import A0_BASE, ALPHA_DEN, ALPHA_NUM, POLICY_BM, POLICY_HM, effective_A


def run_political_markov_vfi() -> Dict[str, object]:
    """VFI experiments for Section 6.2: iso-Skiba MRS, precautionary investment, and endogenous risk."""
    k_grid = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.005, 40, endpoint=False),
        np.geomspace(0.005, 0.05, 40, endpoint=False),
        np.geomspace(0.05, 0.40, 40, endpoint=False),
        np.geomspace(0.40, 50.0, 45),
    ]))

    A_G_base = 0.75
    A_B_mod = 0.35
    A_B_ext = 0.095  # Below A_* = 0.0996091 (inviable in isolation)
    p_ref_base = 1.0 / 3.0

    # 1. Static benchmark at A_G = 0.75
    eco_static = Economy1D(A=A_G_base, q=0.92, beta=0.97, eta=0.70).solve_vfi(k_grid)
    idx_m = (k_grid >= CANONICAL_BM) & (k_grid < CANONICAL_HM)

    # 2. Iso-Skiba sweep over (tau_{u,G}, p_rev) with A_B = 0.35 and extreme A_B = 0.095
    tu_vals = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
    prev_vals = [0.0, 0.02, 0.05, 0.08, 0.12, 0.18, 0.25]
    iso_table_mod = []
    for tu in tu_vals:
        A_g = effective_A(0.20, tu, 1.0)
        row = {"tau_u_G": float(tu), "A_e_G": float(A_g), "by_p_rev": {}}
        for prv in prev_vals:
            P = np.array([[1.0 - prv, prv], [p_ref_base, 1.0 - p_ref_base]])
            reg_G = RegimeSpec("G", ParamBox(A_g, A_g, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
            reg_B = RegimeSpec("B", ParamBox(A_B_mod, A_B_mod, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
            res = MarkovEconomy1D((reg_G, reg_B), P).solve_vfi(k_grid)
            row["by_p_rev"][f"{prv:.2f}"] = {"S_G": res["S0"], "S_B": res["S1"]}
        iso_table_mod.append(row)

    # 3. Precautionary flight-to-safety & extreme regime B (A_B = 0.095 < A_*)
    flight_rows = []
    for label_b, A_b in [("moderate_0.35", A_B_mod), ("inviable_0.095", A_B_ext)]:
        for prv in (0.02, 0.08, 0.15):
            for prf in (0.3333333333, 0.10):
                P = np.array([[1.0 - prv, prv], [prf, 1.0 - prf]])
                reg_G = RegimeSpec("G", ParamBox(A_G_base, A_G_base, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
                reg_B = RegimeSpec("B", ParamBox(A_b, A_b, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
                res = MarkovEconomy1D((reg_G, reg_B), P).solve_vfi(k_grid)
                dk_mean = float(np.mean(res["kp0"][idx_m] - eco_static["kp"][idx_m]))
                dk_max = float(np.max(res["kp0"][idx_m] - eco_static["kp"][idx_m]))
                flight_rows.append({
                    "regime_B": label_b,
                    "A_B": float(A_b),
                    "p_rev": float(prv),
                    "p_ref": float(prf),
                    "S_G": res["S0"],
                    "S_B": res["S1"],
                    "delta_kpG_mean_M": dk_mean,
                    "delta_kpG_max_M": dk_max,
                })

    # 4. Endogenous political risk p_rev(K) = p_rev * 1_{K < h_m}
    endo_rows = []
    for prv in (0.05, 0.12, 0.20):
        P_lo = np.array([[1.0 - prv, prv], [p_ref_base, 1.0 - p_ref_base]])
        P_hi = np.array([[1.0, 0.0], [p_ref_base, 1.0 - p_ref_base]])
        reg_G = RegimeSpec("G", ParamBox(A_G_base, A_G_base, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
        reg_B = RegimeSpec("B", ParamBox(A_B_mod, A_B_mod, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
        res_exo = MarkovEconomy1D((reg_G, reg_B), P_lo).solve_vfi(k_grid)
        res_endo = MarkovEconomy1D((reg_G, reg_B), P_lo, P_high=P_hi, h_switch=CANONICAL_HM).solve_vfi(k_grid)

        def _esc_steps(kp_arr):
            kc, st = CANONICAL_BM, 0
            while kc < CANONICAL_HM and st < 60:
                kc = float(np.interp(kc, k_grid, kp_arr))
                st += 1
            return st

        endo_rows.append({
            "p_rev": float(prv),
            "S_G_exogenous": res_exo["S0"],
            "S_G_endogenous": res_endo["S0"],
            "tau_G_exogenous": _esc_steps(res_exo["kp0"]),
            "tau_G_endogenous": _esc_steps(res_endo["kp0"]),
            "dkp_endo_minus_exo_M": float(np.mean(res_endo["kp0"][idx_m] - res_exo["kp0"][idx_m])),
        })

    # 5. Exact VFI aligned with the 7 certified Markov (p_rev, p_ref) grids on M_pol=[0.10, 0.18)
    A_G_cert = effective_A(0.20, 0.0, 1.0)
    A_B_cert = 0.45
    cert_grid_pts = [
        (0.02, 1.0 / 3.0),
        (0.05, 1.0 / 3.0),
        (0.08, 1.0 / 3.0),
        (0.12, 1.0 / 3.0),
        (0.18, 1.0 / 3.0),
        (0.08, 0.25),
        (0.08, 0.50),
    ]
    certified_grid_vfi = []
    reg_Gc = RegimeSpec("G", ParamBox(A_G_cert, A_G_cert, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
    reg_Bc = RegimeSpec("B", ParamBox(A_B_cert, A_B_cert, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
    for prv, prf in cert_grid_pts:
        Pc = np.array([[1.0 - prv, prv], [prf, 1.0 - prf]], dtype=np.float64)
        res_c = MarkovEconomy1D((reg_Gc, reg_Bc), Pc).solve_vfi(k_grid)
        hit = expected_markov_hitting_time(k_grid, res_c["kp0"], res_c["kp1"], Pc, b_m=POLICY_BM, h_m=POLICY_HM)
        certified_grid_vfi.append({
            "p_rev": float(prv),
            "p_ref": float(prf),
            "A_G": float(A_G_cert),
            "A_B": float(A_B_cert),
            "S_G": res_c["S0"],
            "S_B": res_c["S1"],
            "max_E_tau_H_vfi_Mpol": hit["max_E_tau_H"],
            "E_tau_at_bm_G": hit["E_tau_at_bm_0"],
            "E_tau_at_bm_B": hit["E_tau_at_bm_1"],
        })

    return {
        "static_S_075": eco_static["skiba"],
        "iso_skiba_table": iso_table_mod,
        "flight_to_safety": flight_rows,
        "endogenous_risk": endo_rows,
        "certified_grid_vfi": certified_grid_vfi,
    }


def _markov_cert_worker(task):
    p_rev, p_ref = task
    box_G = build_policy_param_box(
        A0=A0_BASE, alpha_num=ALPHA_NUM, alpha_den=ALPHA_DEN,
        tau_p=(0.198, 0.202), tau_u=(0.0, 0.005), nf=(1.0, 1.0), g=(0.0, 0.0),
        q_rng=(0.92, 0.92), b_rng=(0.97, 0.97), e_rng=(0.70, 0.70),
        label=f"G_prev={p_rev:.3f}_pref={p_ref:.3f}",
    )
    # Regime B: tau_p = 0.20, high bureaucracy tau_u ~ 0.420 -> A_{e,B} ~ 0.45
    box_B = ParamBox(
        A_lo=0.449, A_hi=0.451,
        q_lo=0.92, q_hi=0.92,
        b_lo=0.97, b_hi=0.97,
        e_lo=0.70, e_hi=0.70,
        label=f"B_prev={p_rev:.3f}_pref={p_ref:.3f}",
    )
    P = np.array([[1.0 - p_rev, p_rev], [p_ref, 1.0 - p_ref]], dtype=np.float64)
    try:
        cert = synth_coupled_markov_certificate(
            (RegimeSpec("G", box_G), RegimeSpec("B", box_B)), P,
            b_m=0.10, h_m=0.18, k_h2=0.80,
        )
        return {"p_rev": float(p_rev), "p_ref": float(p_ref), "certified": True, "cert": cert}
    except Exception as exc:
        return {"p_rev": float(p_rev), "p_ref": float(p_ref), "certified": False, "error": str(exc)}


def certify_political_markov_grid(parallel: bool = True) -> Dict[str, object]:
    """Proposition 4: Certify coupled (B_G, B_B) across (p_rev, p_ref) grid."""
    grid = [
        (0.02, 1.0 / 3.0),
        (0.05, 1.0 / 3.0),
        (0.08, 1.0 / 3.0),
        (0.12, 1.0 / 3.0),
        (0.18, 1.0 / 3.0),
        (0.08, 0.25),
        (0.08, 0.50),
    ]
    results = []
    if parallel:
        nw = min(7, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=nw) as pool:
            futs = [pool.submit(_markov_cert_worker, t) for t in grid]
            for fut in as_completed(futs):
                results.append(fut.result())
    else:
        for t in grid:
            results.append(_markov_cert_worker(t))
    results.sort(key=lambda r: (r["p_ref"], r["p_rev"]))
    certified_list = [r["cert"] for r in results if r["certified"]]
    summary_rows = [
        {
            "p_rev": r["p_rev"],
            "p_ref": r["p_ref"],
            "certified": r["certified"],
            "E_tau_opt": r["cert"]["doob"]["E_tau_opt"] if r["certified"] else None,
            "eps0_opt": r["cert"]["doob"]["eps0_opt"] if r["certified"] else None,
            "T0_opt": r["cert"]["doob"]["T0_opt"] if r["certified"] else None,
        }
        for r in results
    ]
    return {
        "certificates": certified_list,
        "summary_rows": summary_rows,
        "max_certified_p_rev_at_pref_1_3": max((r["p_rev"] for r in results if r["certified"] and abs(r["p_ref"] - 1.0 / 3.0) < 1e-4), default=0.0),
    }


def run_political_markov(parallel: bool = True) -> Dict[str, object]:
    vfi = run_political_markov_vfi()
    certs = certify_political_markov_grid(parallel=parallel)
    return {"vfi": vfi, "certification": certs}
