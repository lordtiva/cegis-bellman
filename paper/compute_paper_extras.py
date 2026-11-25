"""
Lightweight Paper-Only VFI Refinements for Hito 2 Tables & Figures.

Does NOT touch or re-synthesize `certificates/cegis_certificates.json.xz`.
Generates `paper/paper_extras.json` containing:
  1. Fine-grid zero-crossing S_G_vfi and S_B_vfi on [0.0012, 0.0060] for Table 4
     (eliminating discrete grid jumps in `political_markov`).
  2. Three pure Red Queen simulation trajectories from an initial K_hat_0 strictly
     inside (S_hat_L, S_hat_H) for tau_u = 0.55:
       - reformed (tau_u = 0.0, with early g_H = 0.05 wave): hockey-stick takeoff
       - burdened counterfactual (tau_u = 0.55, no wave g = g_L): survives/escapes
       - burdened with wave (tau_u = 0.55, early g_H = 0.05 wave): falls into trap
"""

from __future__ import annotations

import json
import os
import sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.model_api import Economy1D, MarkovEconomy1D, ParamBox, RegimeSpec
from models.barro_u_frag import A0_BASE, ALPHA_BASE, effective_A


def _zero_cross_skiba(k_grid: np.ndarray, kp: np.ndarray, k_min: float = 2e-4) -> float | None:
    mask = (k_grid >= k_min) & (k_grid <= 1.0)
    ks, diff = k_grid[mask], (kp - k_grid)[mask]
    for i in range(len(ks) - 1):
        if diff[i] <= 0.0 and diff[i + 1] > 0.0:
            d0, d1 = float(diff[i]), float(diff[i + 1])
            w = -d0 / (d1 - d0) if abs(d1 - d0) > 1e-18 else 0.5
            return float(ks[i] + w * (ks[i + 1] - ks[i]))
    return None


def compute_refined_table4_skiba() -> list[dict]:
    k_fine = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.0012, 22, endpoint=False),
        np.geomspace(0.0012, 0.0022, 95, endpoint=False),
        np.geomspace(0.0022, 0.0046, 35, endpoint=False),
        np.geomspace(0.0046, 0.0056, 95, endpoint=False),
        np.geomspace(0.0056, 0.40, 40, endpoint=False),
        np.geomspace(0.40, 50.0, 40),
    ]))
    A_G = effective_A(0.20, 0.0, 1.0)
    A_B = 0.45
    reg_G = RegimeSpec("G", ParamBox(A_G, A_G, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
    reg_B = RegimeSpec("B", ParamBox(A_B, A_B, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))

    pts = [
        (0.02, 1.0 / 3.0),
        (0.05, 1.0 / 3.0),
        (0.08, 1.0 / 3.0),
        (0.12, 1.0 / 3.0),
        (0.18, 1.0 / 3.0),
        (0.08, 0.25),
        (0.08, 0.50),
    ]
    rows = []
    for prv, prf in pts:
        P = np.array([[1.0 - prv, prv], [prf, 1.0 - prf]], dtype=np.float64)
        res = MarkovEconomy1D((reg_G, reg_B), P).solve_vfi(k_fine)
        sg = _zero_cross_skiba(k_fine, res["kp0"])
        sb = _zero_cross_skiba(k_fine, res["kp1"])
        rows.append({
            "p_rev": float(prv),
            "p_ref": float(prf),
            "S_G_vfi_fine": sg,
            "S_B_vfi_fine": sb,
        })
    return rows


def compute_pure_red_queen_trajectories() -> dict:
    k_grid = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.0015, 25, endpoint=False),
        np.geomspace(0.0015, 0.065, 110, endpoint=False),
        np.geomspace(0.065, 0.50, 45, endpoint=False),
        np.geomspace(0.50, 50.0, 45),
    ]))
    g_L, g_H = 0.02, 0.05
    p_wave, p_end = 0.10, 0.25
    q, beta, eta = 0.92, 0.97, 0.70
    P_wave = np.array([[1.0 - p_wave, p_wave], [p_end, 1.0 - p_end]], dtype=np.float64)

    def _solve_rq(tu: float) -> dict:
        Ae = effective_A(0.20, tu, 1.0)
        bL = ParamBox(Ae / (1.0 + g_L), Ae / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta)
        bH = ParamBox(Ae / (1.0 + g_H), Ae / (1.0 + g_H), q / (1.0 + g_H), q / (1.0 + g_H), beta, beta, eta, eta)
        vfi = MarkovEconomy1D((RegimeSpec("L", bL, g_L), RegimeSpec("H", bH, g_H)), P_wave).solve_vfi(k_grid)
        return {
            "vfi": vfi,
            "S_hat_L": _zero_cross_skiba(k_grid, vfi["kp0"]),
            "S_hat_H": _zero_cross_skiba(k_grid, vfi["kp1"]),
        }

    # Also solve constant g_L economy for counterfactual no-wave policy at tau_u=0.55
    Ae_b = effective_A(0.20, 0.55, 1.0)
    bL_const = ParamBox(Ae_b / (1.0 + g_L), Ae_b / (1.0 + g_L), q / (1.0 + g_L), q / (1.0 + g_L), beta, beta, eta, eta)
    vfi_b_const = MarkovEconomy1D((RegimeSpec("L", bL_const, g_L), RegimeSpec("H", bL_const, g_L)), np.eye(2)).solve_vfi(k_grid)
    S_const_b = _zero_cross_skiba(k_grid, vfi_b_const["kp0"])

    sol_ref = _solve_rq(0.0)
    sol_bur = _solve_rq(0.55)

    T_sim = 45
    def _sim(vfi_dict: dict, k0: float, wave_start: int, wave_end: int, use_wave: bool, T_sim_steps: int = T_sim) -> list[dict]:
        kh, E = k0, 1.0
        traj = []
        for t in range(T_sim_steps + 1):
            is_H = use_wave and (wave_start <= t < wave_end)
            gw = g_H if is_H else g_L
            traj.append({"t": t, "regime": "H" if is_H else "L", "K_hat": float(kh), "K_real": float(kh * E), "E": float(E)})
            kp_arr = vfi_dict["kp1"] if is_H else vfi_dict["kp0"]
            kh = float(np.interp(kh, k_grid, kp_arr))
            E *= (1.0 + gw)
        return traj

    # Choose K_hat_0 = 0.034 strictly inside (S_hat_L, S_hat_H) with early wave [1, 16)
    sL, sH = sol_bur["S_hat_L"], sol_bur["S_hat_H"]
    wave_start, wave_end = 1, 16
    chosen = 0.034
    if not (sL < chosen < sH):
        chosen = 0.5 * (sL + sH)

    tr_nowave = _sim(sol_bur["vfi"], chosen, wave_start, wave_end, use_wave=False, T_sim_steps=T_sim)
    tr_const = _sim(vfi_b_const, chosen, wave_start, wave_end, use_wave=False, T_sim_steps=T_sim)
    tr_wave = _sim(sol_bur["vfi"], chosen, wave_start, wave_end, use_wave=True, T_sim_steps=T_sim)
    if not (tr_nowave[-1]["K_hat"] > 0.10 and tr_const[-1]["K_hat"] > 0.10 and tr_wave[-1]["K_hat"] < 0.015):
        raise RuntimeError(
            f"Unexpected separation at K_hat_0={chosen:.5f}: nowave={tr_nowave[-1]['K_hat']:.4f}, "
            f"const={tr_const[-1]['K_hat']:.4f}, wave={tr_wave[-1]['K_hat']:.5f}"
        )

    return {
        "k_hat_0": chosen,
        "T_sim": T_sim,
        "wave_window": [wave_start, wave_end],
        "g_L": g_L,
        "g_H": g_H,
        "reformed": {
            "tau_u": 0.0,
            "S_hat_L": sol_ref["S_hat_L"],
            "S_hat_H": sol_ref["S_hat_H"],
            "trajectory_wave": _sim(sol_ref["vfi"], chosen, wave_start, wave_end, use_wave=True, T_sim_steps=T_sim),
        },
        "burdened": {
            "tau_u": 0.55,
            "S_hat_L": sL,
            "S_hat_H": sH,
            "S_hat_const_gL": S_const_b,
            "trajectory_no_wave": tr_nowave,
            "trajectory_no_wave_const_gL": tr_const,
            "trajectory_wave": tr_wave,
        },
    }


def compute_refined_table2_ucurve() -> list[dict]:
    with open(os.path.join(ROOT, "certificates", "vfi_results.json"), "r", encoding="utf-8") as fh:
        vfi_data = json.load(fh)
    u_rows = vfi_data["barro_u_frag"]["analytics"]["u_curve"]
    k_fine = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.0010, 25, endpoint=False),
        np.geomspace(0.0010, 0.025, 180, endpoint=False),
        np.geomspace(0.025, 0.40, 45, endpoint=False),
        np.geomspace(0.40, 50.0, 40),
    ]))
    out_rows = []
    for r in u_rows:
        tp = float(r["tau_p"])
        Ae = effective_A(tp, 0.0, 1.0)
        res = Economy1D(A=Ae, q=0.92, beta=0.97, eta=0.70).solve_vfi(k_grid=k_fine)
        sk_fine = _zero_cross_skiba(k_fine, res["kp"])
        out_rows.append({
            "tau_p": tp,
            "A_e": float(r["A_e"]),
            "S_vfi_fine": sk_fine if sk_fine is not None else float(r["S_vfi"]),
            "S_env": float(r["S_env"]),
        })
    return out_rows


def compute_refined_iso_skiba() -> list[dict]:
    k_iso = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.0012, 20, endpoint=False),
        np.geomspace(0.0012, 0.0042, 130, endpoint=False),
        np.geomspace(0.0042, 0.40, 45, endpoint=False),
        np.geomspace(0.40, 50.0, 35),
    ]))
    reg_B = RegimeSpec("B", ParamBox(0.35, 0.35, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
    tau_u_G_vals = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25]
    p_rev_vals = [0.00, 0.02, 0.05, 0.08, 0.12, 0.18, 0.25]
    p_ref = 1.0 / 3.0
    out_rows = []
    for tuG in tau_u_G_vals:
        AG = effective_A(0.20, tuG, 1.0)
        reg_G = RegimeSpec("G", ParamBox(AG, AG, 0.92, 0.92, 0.97, 0.97, 0.70, 0.70))
        by_prev = {}
        for prv in p_rev_vals:
            P = np.array([[1.0 - prv, prv], [p_ref, 1.0 - p_ref]], dtype=np.float64)
            res = MarkovEconomy1D((reg_G, reg_B), P).solve_vfi(k_iso)
            sg = _zero_cross_skiba(k_iso, res["kp0"])
            by_prev[f"{prv:.2f}"] = {"S_G_fine": sg}
        out_rows.append({"tau_u_G": float(tuG), "A_e_G": float(AG), "by_p_rev": by_prev})
    return out_rows


def main() -> None:
    t2 = compute_refined_table2_ucurve()
    t4 = compute_refined_table4_skiba()
    iso_fine = compute_refined_iso_skiba()
    rq_traj = compute_pure_red_queen_trajectories()
    out = {
        "table2_refined_ucurve": t2,
        "table4_refined_skiba": t4,
        "iso_skiba_fine": iso_fine,
        "pure_red_queen": rq_traj,
    }
    out_path = os.path.join(ROOT, "paper", "paper_extras.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("Saved:", out_path)
    print("\n--- Refined Table 2 U-Curve ---")
    for r in t2:
        print(f"tau_p={r['tau_p']:.3f}: A_e={r['A_e']:.4f}, S_vfi_fine={r['S_vfi_fine']:.6f}, S_env={r['S_env']:.6f}")
    print("\n--- Refined Table 4 S_G / S_B ---")
    for r in t4:
        print(f"p_rev={r['p_rev']:.2f}, p_ref={r['p_ref']:.3f}: S_G={r['S_G_vfi_fine']:.6f}, S_B={r['S_B_vfi_fine']:.6f}")
    print("\n--- Pure Red Queen Fig 4 Trajectories ---")
    b = rq_traj["burdened"]
    rf = rq_traj["reformed"]
    T_sim = rq_traj["T_sim"]
    print(f"K_hat_0={rq_traj['k_hat_0']:.5f} strictly inside (S_L={b['S_hat_L']:.5f}, S_H={b['S_hat_H']:.5f}) | wave={rq_traj['wave_window']}, T_sim={T_sim}")
    print(f"  Reformed (tau_u=0.0, wave):        K_hat[{T_sim}]={rf['trajectory_wave'][-1]['K_hat']:.4f}, K_real[{T_sim}]={rf['trajectory_wave'][-1]['K_real']:.4f}")
    print(f"  Burdened (tau_u=0.55, NO wave):     K_hat[{T_sim}]={b['trajectory_no_wave'][-1]['K_hat']:.4f}, K_real[{T_sim}]={b['trajectory_no_wave'][-1]['K_real']:.4f}")
    print(f"  Burdened (tau_u=0.55, const g_L):   K_hat[{T_sim}]={b['trajectory_no_wave_const_gL'][-1]['K_hat']:.4f}, K_real[{T_sim}]={b['trajectory_no_wave_const_gL'][-1]['K_real']:.4f}")
    print(f"  Burdened (tau_u=0.55, wave):        K_hat[{T_sim}]={b['trajectory_wave'][-1]['K_hat']:.5f}, K_real[{T_sim}]={b['trajectory_wave'][-1]['K_real']:.5f}")


if __name__ == "__main__":
    main()
