"""
Stochastic Red Queen Model: Markov Technology Waves & Institutional Divergence (Section 7).

Global frontier advances as E_{t+1} = (1 + g(omega_t)) E_t on Omega = {L, H}.
In efficiency units K_hat_t = K_t / E_t, the problem reduces exactly (Theorem 2) to a
1D Markov Bellman system with regime-dependent effective parameters:
  A_tilde_w = A_e(tau_p, tau_u, N_f) / (1 + g_w),   q_tilde_w = q / (1 + g_w)
plus an exogenous finite constant vector phi solving (I - beta*P) phi = (eta/(1-beta)) log(1+g).
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import math
import os
from typing import Dict, List, Tuple
import numpy as np

from core.interval_arith import (
    CANONICAL_BETA,
    CANONICAL_BM,
    CANONICAL_ETA,
    CANONICAL_HM,
    CANONICAL_Q,
    F_A,
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


def verify_theorem2_isomorphism(
    g_L: float = 0.02,
    g_H: float = 0.05,
    p_wave: float = 0.10,
    p_end: float = 0.25,
    E0: float = 2.5,
    tau_u: float = 0.0,
) -> Dict[str, object]:
    """
    Numerically verify Theorem 2:
      1) Closed-form solution phi of (I - beta*P) phi = (eta/(1-beta)) * log(1+g),
      2) Exact identity between normalized Bellman operator T_hat[V_hat](K_hat, w) + eta*log(E0)/(1-beta) + phi_w
         and unnormalized Bellman operator T[V](K_hat*E0, E0, w) at arbitrary E0 > 0.
    """
    P = np.array([[1.0 - p_wave, p_wave], [p_end, 1.0 - p_end]], dtype=np.float64)
    A_e = effective_A(0.20, tau_u, 1.0)
    q, beta, eta = 0.92, 0.97, 0.70

    box_L = ParamBox(A_e / (1.0 + g_L), A_e / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta, "L")
    box_H = ParamBox(A_e / (1.0 + g_H), A_e / (1.0 + g_H), q / (1.0 + g_H), q / (1.0 + g_H), beta, beta, eta, eta, "H")
    eco = MarkovEconomy1D((RegimeSpec("L", box_L, g=g_L), RegimeSpec("H", box_H, g=g_H)), P, beta=beta, eta=eta)
    phi = eco.solve_red_queen_shift()
    vfi = eco.solve_vfi()

    k_grid = vfi["k_grid"]
    V0_hat, V1_hat = vfi["V0"], vfi["V1"]
    const_E0 = (eta / (1.0 - beta)) * math.log(E0)

    # Check exact Bellman shift identity at a sample of interior points (K_hat, L, s)
    rng = np.random.default_rng(123)
    max_err = 0.0
    for idx in range(40, len(k_grid) - 40, 10):
        k_hat = float(k_grid[idx])
        K_raw = k_hat * E0
        for w, gw, V_hat_arr in ((0, g_L, V0_hat), (1, g_H, V1_hat)):
            E1 = (1.0 + gw) * E0
            L = float(rng.uniform(0.1, 0.8))
            s = float(rng.uniform(0.2, 0.9))
            Y_raw = q * K_raw + float(F_A(A_e, K_raw, L * E0))
            K_next_raw = s * Y_raw
            C_raw = (1.0 - s) * Y_raw
            k_next_hat = K_next_raw / E1
            c_tilde = C_raw / E1
            # Unnormalized RHS: eta*log(C_raw) + (1-eta)*log(1-L) + beta * E_w[V_hat(k_next_hat) + eta*log(E1)/(1-beta) + phi_w']
            ev_hat = float(P[w, 0] * np.interp(np.log(k_next_hat), np.log(k_grid), V0_hat) +
                           P[w, 1] * np.interp(np.log(k_next_hat), np.log(k_grid), V1_hat))
            ev_phi = float(P[w, 0] * phi[0] + P[w, 1] * phi[1])
            rhs_raw = eta * math.log(C_raw) + (1.0 - eta) * math.log(1.0 - L) + beta * (ev_hat + (eta / (1.0 - beta)) * math.log(E1) + ev_phi)
            # Normalized RHS + constant shift
            rhs_norm = eta * math.log(c_tilde) + (1.0 - eta) * math.log(1.0 - L) + beta * ev_hat + const_E0 + float(phi[w])
            max_err = max(max_err, abs(rhs_raw - rhs_norm))

    return {
        "phi": [float(phi[0]), float(phi[1])],
        "E0_test": float(E0),
        "max_bellman_shift_error": float(max_err),
        "S_hat_L": vfi["S0"],
        "S_hat_H": vfi["S1"],
    }


def run_red_queen_vfi() -> Dict[str, object]:
    """VFI analysis for Section 7.2: Tech-wave paradox, hockey-stick vs divergence, and anticipatory flight."""
    k_grid = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.005, 40, endpoint=False),
        np.geomspace(0.005, 0.05, 40, endpoint=False),
        np.geomspace(0.05, 0.40, 40, endpoint=False),
        np.geomspace(0.40, 50.0, 45),
    ]))
    g_L, g_H = 0.02, 0.05
    p_wave, p_end = 0.10, 0.25
    q, beta, eta = 0.92, 0.97, 0.70

    # 1. Sweep over (g_H, tau_u) to map relative Skiba threshold S_hat(g_H, tau_u)
    gH_vals = [0.02, 0.04, 0.05, 0.06, 0.08]
    tu_vals = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]
    skiba_grid = []
    for gh in gH_vals:
        P = np.array([[1.0 - p_wave, p_wave], [p_end, 1.0 - p_end]])
        for tu in tu_vals:
            A_e = effective_A(0.20, tu, 1.0)
            bL = ParamBox(A_e / (1.0 + g_L), A_e / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta)
            bH = ParamBox(A_e / (1.0 + gh), A_e / (1.0 + gh), q / (1.0 + gh), q / (1.0 + gh), beta, beta, eta, eta)
            res = MarkovEconomy1D((RegimeSpec("L", bL, g_L), RegimeSpec("H", bH, gh)), P).solve_vfi(k_grid)
            skiba_grid.append({"g_H": float(gh), "tau_u": float(tu), "A_e": float(A_e), "S_hat_L": res["S0"], "S_hat_H": res["S1"]})

    # 2. Anticipatory precautionary investment in L (with p_wave=0.10 vs constant g_L=0.02)
    A_e_ref = effective_A(0.20, 0.0, 1.0)
    eco_const = Economy1D(A=A_e_ref / (1.0 + g_L), q=q / (1.0 + g_L), beta=beta, eta=eta).solve_vfi(k_grid)
    P_wave = np.array([[1.0 - p_wave, p_wave], [p_end, 1.0 - p_end]])
    bL_ref = ParamBox(A_e_ref / (1.0 + g_L), A_e_ref / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta)
    bH_ref = ParamBox(A_e_ref / (1.0 + g_H), A_e_ref / (1.0 + g_H), q / (1.0 + g_H), q / (1.0 + g_H), beta, beta, eta, eta)
    eco_wave = MarkovEconomy1D((RegimeSpec("L", bL_ref, g_L), RegimeSpec("H", bH_ref, g_H)), P_wave).solve_vfi(k_grid)
    idx_m = (k_grid >= CANONICAL_BM) & (k_grid < CANONICAL_HM)
    anticipatory_dk_M = float(np.mean(eco_wave["kp0"][idx_m] - eco_const["kp"][idx_m]))

    # 3. Deterministic wave simulation: reformed (tau_u=0.0) vs burdened (tau_u=0.52) starting at K_hat_0 = 0.025
    # Wave hits at t=5..14 (10 periods of g_H=0.05) then returns to g_L=0.02
    def _simulate_path(tu: float, k_hat_0: float = 0.025, T_sim: int = 30):
        A_e = effective_A(0.20, tu, 1.0)
        bL = ParamBox(A_e / (1.0 + g_L), A_e / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta)
        bH = ParamBox(A_e / (1.0 + g_H), A_e / (1.0 + g_H), q / (1.0 + g_H), q / (1.0 + g_H), beta, beta, eta, eta)
        vfi = MarkovEconomy1D((RegimeSpec("L", bL, g_L), RegimeSpec("H", bH, g_H)), P_wave).solve_vfi(k_grid)
        k_hat = k_hat_0
        E_cur = 1.0
        traj = []
        for t in range(T_sim + 1):
            is_H = 5 <= t < 15
            gw = g_H if is_H else g_L
            traj.append({"t": t, "regime": "H" if is_H else "L", "K_hat": float(k_hat), "K_real": float(k_hat * E_cur), "E": float(E_cur)})
            kp_arr = vfi["kp1"] if is_H else vfi["kp0"]
            k_hat = float(np.interp(k_hat, k_grid, kp_arr))
            E_cur *= (1.0 + gw)
        return {"tau_u": float(tu), "S_hat_L": vfi["S0"], "S_hat_H": vfi["S1"], "trajectory": traj}

    path_reformed = _simulate_path(0.0, k_hat_0=0.025)
    path_burdened = _simulate_path(0.55, k_hat_0=0.025)

    # 4. Exact VFI aligned with the 9 certified (g_H, tau_u) grids on M_pol=[0.10, 0.18)
    certified_grid_vfi = []
    for gh in (0.03, 0.05, 0.07):
        for tu in (0.00, 0.15, 0.30):
            A_e = effective_A(0.20, tu, 1.0)
            bL = ParamBox(A_e / (1.0 + g_L), A_e / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta)
            bH = ParamBox(A_e / (1.0 + gh), A_e / (1.0 + gh), q / (1.0 + gh), q / (1.0 + gh), beta, beta, eta, eta)
            res_c = MarkovEconomy1D((RegimeSpec("L", bL, g_L), RegimeSpec("H", bH, gh)), P_wave).solve_vfi(k_grid)
            hit = expected_markov_hitting_time(k_grid, res_c["kp0"], res_c["kp1"], P_wave, b_m=POLICY_BM, h_m=POLICY_HM)
            certified_grid_vfi.append({
                "g_H": float(gh),
                "tau_u": float(tu),
                "A_e": float(A_e),
                "S_hat_L": res_c["S0"],
                "S_hat_H": res_c["S1"],
                "max_E_tau_H_vfi_Mpol": hit["max_E_tau_H"],
                "E_tau_at_bm_L": hit["E_tau_at_bm_0"],
                "E_tau_at_bm_H": hit["E_tau_at_bm_1"],
            })

    return {
        "theorem2_check": verify_theorem2_isomorphism(),
        "skiba_grid": skiba_grid,
        "anticipatory_dk_M_at_tau_u0": anticipatory_dk_M,
        "path_reformed": path_reformed,
        "path_burdened": path_burdened,
        "certified_grid_vfi": certified_grid_vfi,
    }


def _rq_cert_worker(task):
    g_H, tau_u = task
    g_L = 0.02
    p_wave, p_end = 0.10, 0.25
    P = np.array([[1.0 - p_wave, p_wave], [p_end, 1.0 - p_end]], dtype=np.float64)

    box_L = build_policy_param_box(
        A0=A0_BASE, alpha_num=ALPHA_NUM, alpha_den=ALPHA_DEN,
        tau_p=(0.199, 0.201), tau_u=(max(0.0, tau_u - 0.0015), tau_u + 0.0015),
        nf=(1.0, 1.0), g=(g_L, g_L),
        q_rng=(0.92, 0.92), b_rng=(0.97, 0.97), e_rng=(0.70, 0.70),
        label=f"RQ_L_gH={g_H:.2f}_tu={tau_u:.2f}",
    )
    box_H = build_policy_param_box(
        A0=A0_BASE, alpha_num=ALPHA_NUM, alpha_den=ALPHA_DEN,
        tau_p=(0.199, 0.201), tau_u=(max(0.0, tau_u - 0.0015), tau_u + 0.0015),
        nf=(1.0, 1.0), g=(g_H, g_H),
        q_rng=(0.92, 0.92), b_rng=(0.97, 0.97), e_rng=(0.70, 0.70),
        label=f"RQ_H_gH={g_H:.2f}_tu={tau_u:.2f}",
    )
    try:
        cert = synth_coupled_markov_certificate(
            (RegimeSpec("L", box_L, g=g_L), RegimeSpec("H", box_H, g=g_H)), P,
            b_m=0.10, h_m=0.18, k_h2=0.80,
        )
        return {"g_H": float(g_H), "tau_u": float(tau_u), "certified": True, "cert": cert}
    except Exception as exc:
        return {"g_H": float(g_H), "tau_u": float(tau_u), "certified": False, "error": str(exc)}


def certify_red_queen_grid(parallel: bool = True) -> Dict[str, object]:
    """Proposition 5: Certify coupled (B_L, B_H) across (g_H, tau_u) and locate max tolerable tau_u(g_H)."""
    gH_list = [0.03, 0.05, 0.07]
    tu_list = [0.00, 0.15, 0.30, 0.40]
    tasks = [(gh, tu) for gh in gH_list for tu in tu_list]
    results = []
    if parallel:
        nw = min(8, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=nw) as pool:
            futs = [pool.submit(_rq_cert_worker, t) for t in tasks]
            for fut in as_completed(futs):
                results.append(fut.result())
    else:
        for t in tasks:
            results.append(_rq_cert_worker(t))
    results.sort(key=lambda r: (r["g_H"], r["tau_u"]))

    certified_list = [r["cert"] for r in results if r["certified"]]
    frontier = {}
    for gh in gH_list:
        ok_tus = [r["tau_u"] for r in results if r["g_H"] == gh and r["certified"]]
        frontier[f"{gh:.2f}"] = max(ok_tus) if ok_tus else None

    summary_rows = [
        {
            "g_H": r["g_H"],
            "tau_u": r["tau_u"],
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
        "tau_u_max_certified_by_gH": frontier,
    }


def run_red_queen_markov(parallel: bool = True) -> Dict[str, object]:
    vfi = run_red_queen_vfi()
    certs = certify_red_queen_grid(parallel=parallel)
    return {"vfi": vfi, "certification": certs}
