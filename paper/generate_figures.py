"""
Generate 4 publication-grade figures (PDF + 300 dpi PNG) in Spanish for Paper 2.

Inputs (strictly read-only):
  - certificates/vfi_results.json
  - paper/paper_extras.json

Outputs:
  - paper/figures/fig1_u_curve_and_policy_plane.{pdf,png}
  - paper/figures/fig2_fragmentation_equivalence.{pdf,png}
  - paper/figures/fig3_political_volatility.{pdf,png}
  - paper/figures/fig4_red_queen_dynamics.{pdf,png}
"""

from __future__ import annotations

import json
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.model_api import Economy1D
from models.barro_u_frag import A0_BASE, ALPHA_BASE, effective_A

FIG_DIR = os.path.join(ROOT, "paper", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

NAVY = "#0b2c4d"
SLATE = "#1f4e78"
GREEN = "#1b7837"
AMBER = "#b45309"
CRIMSON = "#b91c1c"
TEAL = "#0f766e"
GRAY = "#64748b"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "legend.fontsize": 8.2,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def _save(fig: plt.Figure, stem: str) -> None:
    pdf_path = os.path.join(FIG_DIR, f"{stem}.pdf")
    png_path = os.path.join(FIG_DIR, f"{stem}.png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {stem}.{{pdf,png}}")


def _zero_cross_skiba(k_grid: np.ndarray, kp: np.ndarray) -> float | None:
    mask = (k_grid >= 2e-4) & (k_grid <= 1.0)
    ks, diff = k_grid[mask], (kp - k_grid)[mask]
    for i in range(len(ks) - 1):
        if diff[i] <= 0.0 and diff[i + 1] > 0.0:
            d0, d1 = float(diff[i]), float(diff[i + 1])
            w = -d0 / (d1 - d0) if abs(d1 - d0) > 1e-18 else 0.5
            return float(ks[i] + w * (ks[i + 1] - ks[i]))
    return None


def make_fig1(vfi_data: dict, extras: dict) -> None:
    an = vfi_data["barro_u_frag"]["analytics"]
    u_rows = extras["table2_refined_ucurve"]
    tp_pts = np.array([r["tau_p"] for r in u_rows])
    s_vfi_0 = np.array([r["S_vfi_fine"] for r in u_rows])
    s_env_0 = np.array([r["S_env"] for r in u_rows])

    # Compute thin companion U-curves for tau_u = 0.15 and tau_u = 0.30 across viable tau_p
    k_grid = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.002, 25, endpoint=False),
        np.geomspace(0.002, 0.06, 90, endpoint=False),
        np.geomspace(0.06, 0.50, 40, endpoint=False),
        np.geomspace(0.50, 50.0, 40),
    ]))
    tp_scan = np.array([0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60])
    s_tu15, tp_15 = [], []
    s_tu30, tp_30 = [], []
    for tp in tp_scan:
        if tp + 0.15 < 0.95:
            Ae = effective_A(float(tp), 0.15, 1.0)
            if Ae > 0.12:
                vfi = Economy1D(Ae, 0.92, 0.97, 0.70).solve_vfi(k_grid)
                sk = _zero_cross_skiba(k_grid, vfi["kp"])
                if sk is not None:
                    tp_15.append(tp)
                    s_tu15.append(sk)
        if tp + 0.30 < 0.95:
            Ae = effective_A(float(tp), 0.30, 1.0)
            if Ae > 0.12:
                vfi = Economy1D(Ae, 0.92, 0.97, 0.70).solve_vfi(k_grid)
                sk = _zero_cross_skiba(k_grid, vfi["kp"])
                if sk is not None:
                    tp_30.append(tp)
                    s_tu30.append(sk)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.0))
    fig.subplots_adjust(wspace=0.26)

    # Panel A: Institutional U-Curve S(tau_p; tau_u)
    ax1.axvspan(0.117245, 0.304799, color=GREEN, alpha=0.12, label=r"Isla MVS clásica ($A_e \geq 0.749$)")
    ax1.axvspan(0.00507, 0.71083, color=SLATE, alpha=0.07, label=r"Atlas CEGIS-LP ($\tau_u=0$, $A_e \geq 0.385$)")
    ax1.plot(tp_pts, s_vfi_0, "o-", color=NAVY, lw=2.1, ms=4.5, label=r"$S_{\mathrm{VFI}}(\tau_p;\,\tau_u=0)$")
    ax1.plot(tp_pts, s_env_0, "--", color=TEAL, lw=1.6, label=r"Envolvente $S_{\mathrm{env}}(\tau_p;\,\tau_u=0)$")
    ax1.plot(tp_15, s_tu15, "s--", color=AMBER, lw=1.5, ms=3.8, label=r"$S_{\mathrm{VFI}}(\tau_p;\,\tau_u=0.15)$")
    ax1.plot(tp_30, s_tu30, "^:", color=CRIMSON, lw=1.6, ms=4.0, label=r"$S_{\mathrm{VFI}}(\tau_p;\,\tau_u=0.30)$")
    ax1.axvline(0.20, color=NAVY, ls=":", lw=1.2)
    ax1.annotate(
        r"Óptimo de Barro" + "\n" + r"$\tau_p^* = 0.20$ ($A_e = 0.7757$)",
        xy=(0.20, s_vfi_0[np.argmin(np.abs(tp_pts - 0.20))]),
        xytext=(0.31, 0.0041),
        arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.0),
        fontsize=8.2,
        color=NAVY,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=NAVY, alpha=0.9),
    )
    ax1.set_xlim(0.0, 0.92)
    ax1.set_ylim(0.0, 0.0095)
    ax1.set_xlabel(r"Impuesto productivo $\tau_p$ (infraestructura)")
    ax1.set_ylabel(r"Umbral de Skiba $S(\tau_p, \tau_u)$")
    ax1.set_title("A. La Curva en U Institucional $S(\\tau_p; \\tau_u)$")
    ax1.grid(alpha=0.25, ls="--")
    ax1.legend(loc="upper center", frameon=True, framealpha=0.92, fontsize=7.8)

    # Panel B: Policy Plane (tau_p, tau_u)
    tp_g = np.linspace(1e-4, 0.94, 420)
    tu_g = np.linspace(0.0, 0.72, 360)
    TP, TU = np.meshgrid(tp_g, tu_g)
    valid = (TP + TU) < 1.0
    AE = np.where(valid, A0_BASE * (TP ** ALPHA_BASE) * np.maximum(1.0 - TP - TU, 0.0), np.nan)

    # Shaded regions
    ax2.contourf(TP, TU, AE, levels=[0.385, 0.80], colors=[SLATE], alpha=0.22)
    ax2.contourf(TP, TU, AE, levels=[0.749, 0.80], colors=[GREEN], alpha=0.45)

    # Level contours
    cs_rep = ax2.contour(TP, TU, AE, levels=[an["A_rep"]], colors=[GRAY], linestyles=":", linewidths=1.3)
    cs_sn = ax2.contour(TP, TU, AE, levels=[an["A_SN"]], colors=[CRIMSON], linestyles="-.", linewidths=1.4)
    cs_atlas = ax2.contour(TP, TU, AE, levels=[0.385], colors=[NAVY], linestyles="-", linewidths=2.0)
    cs_mvs = ax2.contour(TP, TU, AE, levels=[0.749], colors=[GREEN], linestyles="-", linewidths=1.8)

    # Fiscal feasibility line tau_p + tau_u = 1
    tp_line = np.linspace(0.28, 0.95, 100)
    ax2.plot(tp_line, 1.0 - tp_line, color="black", lw=1.2, ls="--")
    ax2.text(0.67, 0.36, r"$\tau_p + \tau_u = 1$", rotation=-44, fontsize=8.3, color="black")

    # Key points
    ax2.plot(0.20, 0.0, "*", color=AMBER, ms=11, mec="black", mew=0.6, zorder=6)
    ax2.annotate(
        r"Óptimo $(0.20, 0)$",
        xy=(0.20, 0.0), xytext=(0.24, 0.065),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
        fontsize=8.2, weight="bold", color=NAVY,
    )
    tu_max = vfi_data["barro_u_frag"]["policy_plane_summary"]["tau_u_max_at_tp020"]
    ax2.plot(0.20, tu_max, "o", color=NAVY, ms=5.5, zorder=6)
    ax2.annotate(
        rf"$\tau_u^{{\max}} = {tu_max:.3f}$" + "\n(borde $A_e=0.385$)",
        xy=(0.20, tu_max), xytext=(0.025, 0.545),
        arrowprops=dict(arrowstyle="->", color=NAVY, lw=0.9),
        fontsize=8.0, color=NAVY,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=NAVY, alpha=0.90),
    )

    legend_handles = [
        Patch(facecolor=GREEN, alpha=0.50, edgecolor=GREEN, label=r"MVS antiguo ($A_e \geq 0.749$, área $0.00345$)"),
        Patch(facecolor=SLATE, alpha=0.28, edgecolor=NAVY, label=r"Atlas CEGIS-LP ($A_e \geq 0.385$, área $0.1858 = 53.9\times$)"),
        plt.Line2D([0], [0], color=CRIMSON, ls="-.", lw=1.4, label=rf"Silla-nodo $A_{{\mathrm{{SN}}}} = {an['A_SN']:.4f}$"),
        plt.Line2D([0], [0], color=GRAY, ls=":", lw=1.3, label=rf"Repulsor $A_{{\mathrm{{rep}}}} = {an['A_rep']:.4f}$"),
    ]
    ax2.legend(handles=legend_handles, loc="upper right", frameon=True, framealpha=0.94, fontsize=7.6)
    ax2.set_xlim(0.0, 0.90)
    ax2.set_ylim(-0.015, 0.65)
    ax2.set_xlabel(r"Impuesto productivo $\tau_p$")
    ax2.set_ylabel(r"Burocracia improductiva $\tau_u$")
    ax2.set_title("B. Plano Institucional Certificado $(\\tau_p, \\tau_u)$")
    ax2.grid(alpha=0.25, ls="--")

    _save(fig, "fig1_u_curve_and_policy_plane")


def make_fig2(vfi_data: dict) -> None:
    an = vfi_data["barro_u_frag"]["analytics"]
    fbands = vfi_data["barro_u_frag"]["fragmentation_bands"]
    nf_max_cert = vfi_data["barro_u_frag"]["fragmentation_summary"]["nf_max_certified"]
    nf_max_mvs = vfi_data["barro_u_frag"]["fragmentation_summary"]["nf_max_bench075"]

    nf_grid = np.geomspace(1.0, 75.0, 400)
    Ae_barro = np.array([effective_A(0.20, 0.0, float(nf)) for nf in nf_grid])
    Ae_bench = 0.75 * (nf_grid ** (-0.5))
    tau_u_eq = 0.80 * (1.0 - nf_grid ** (-0.5))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.0))
    fig.subplots_adjust(wspace=0.28)

    # Panel A: Exact Equivalence N_f <-> tau_u^eq and Saddle-Node Collapse
    l1, = ax1.plot(nf_grid, Ae_barro, color=NAVY, lw=2.2, label=r"$A_e(N_f)$ con $\tau_p=0.20, \tau_u=0$")
    l2, = ax1.plot(nf_grid, Ae_bench, "--", color=TEAL, lw=1.6, label=r"$A_e^{\mathrm{MVS}}(N_f) = 0.75\,N_f^{-1/2}$")
    ax1.axhline(0.385, color=SLATE, ls="--", lw=1.2, label=r"Frontera certificada CEGIS ($A_e=0.385$)")
    ax1.axhline(an["A_SN"], color=CRIMSON, ls="-.", lw=1.3, label=rf"Colapso silla-nodo ($A_{{\mathrm{{SN}}}}={an['A_SN']:.4f}$)")

    ax1.plot(4.0, effective_A(0.20, 0.0, 4.0), "o", color=AMBER, ms=6.5, zorder=6)
    ax1.annotate(
        r"$N_f=4 \Leftrightarrow \tau_u^{\mathrm{eq}}=0.40$",
        xy=(4.0, effective_A(0.20, 0.0, 4.0)), xytext=(2.1, 0.14),
        arrowprops=dict(arrowstyle="->", color=AMBER, lw=1.0),
        fontsize=8.2, color=AMBER, weight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=AMBER, alpha=0.92),
    )

    nf_col_75 = an["nf_collapse_bench075"]
    ax1.plot(nf_col_75, an["A_star"], "X", color=CRIMSON, ms=7.5, zorder=6)
    ax1.annotate(
        rf"$N_{{f,*}}={nf_col_75:.2f}$" + "\n(extinción $A_0=0.75$)",
        xy=(nf_col_75, an["A_star"]), xytext=(14.0, 0.21),
        arrowprops=dict(arrowstyle="->", color=CRIMSON, lw=1.0),
        fontsize=8.0, color=CRIMSON,
    )

    ax1_r = ax1.twinx()
    l3, = ax1_r.plot(nf_grid, tau_u_eq, color=AMBER, ls=":", lw=1.8, label=r"$\tau_u^{\mathrm{eq}}(N_f) = 0.8(1 - N_f^{-1/2})$")
    ax1_r.set_ylabel(r"Burocracia equivalente $\tau_u^{\mathrm{eq}}$", color=AMBER)
    ax1_r.tick_params(axis="y", colors=AMBER)
    ax1_r.set_ylim(0.0, 0.82)
    ax1_r.spines["top"].set_visible(False)

    ax1.set_xscale("log")
    ax1.set_xlim(1.0, 75.0)
    ax1.set_ylim(0.05, 0.83)
    ax1.set_xlabel(r"Número efectivo de fragmentos de firma $N_f$ (escala log)")
    ax1.set_ylabel(r"Productividad efectiva $A_e$")
    ax1.set_title("A. Equivalencia $N_f \\leftrightarrow \\tau_u^{\\mathrm{eq}}$ y Colapso Silla-Nodo")
    ax1.grid(alpha=0.25, ls="--", which="both")
    lines = [l1, l2, l3]
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="center right", frameon=True, framealpha=0.92, fontsize=7.6)

    # Panel B: 63 Certified Fragmentation Bands N_f in [1.0, 4.060]
    nf_lo = np.array([b["bounds_1d"][0] for b in fbands])
    nf_hi = np.array([b["bounds_1d"][1] for b in fbands])
    nf_mid = 0.5 * (nf_lo + nf_hi)
    t_cert = np.array([b["T_cert"] for b in fbands])
    exit_m = np.array([b["margins"]["exit_M_iv"] for b in fbands])

    # Sort increasing by N_f
    order = np.argsort(nf_lo)
    nf_lo, nf_hi, nf_mid, t_cert, exit_m = nf_lo[order], nf_hi[order], nf_mid[order], t_cert[order], exit_m[order]

    # Plot T_cert step-bars across bands
    for lo, hi, tc in zip(nf_lo, nf_hi, t_cert):
        col = {4: TEAL, 5: SLATE, 6: NAVY, 7: AMBER}.get(int(tc), NAVY)
        ax2.fill_between([lo, hi], 0, tc, color=col, alpha=0.72, edgecolor="white", linewidth=0.3)

    ax2.axvline(nf_max_mvs, color=GREEN, ls="--", lw=1.6, label=rf"$N_f^{{\max}}(0.75) = {nf_max_mvs:.3f}$")
    ax2.axvline(nf_max_cert, color=CRIMSON, ls="-.", lw=1.6, label=rf"$N_f^{{\max,\mathrm{{cert}}}} = {nf_max_cert:.3f}$ ($T=7$)")

    ax2_r = ax2.twinx()
    ax2_r.plot(nf_mid, exit_m, "k-", lw=1.5, label=r"Margen de salida en $M$ ($\min \Delta_{\mathrm{exit}}$)")
    ax2_r.set_ylabel(r"Margen mínimo de salida en $M$ (intervalo)", color="black")
    ax2_r.set_ylim(0.0, 0.80)
    ax2_r.spines["top"].set_visible(False)

    ax2.set_xlim(0.95, 4.20)
    ax2.set_ylim(0.0, 9.8)
    ax2.set_xlabel(r"Escala de fragmentación certificada $N_f \in [1.00, 4.060]$ (63 bandas)")
    ax2.set_ylabel(r"Plazo certificado determinista $T_{\mathrm{cert}}(N_f)$")
    ax2.set_title("B. Atlas de Fragmentación Certificado CEGIS-LP ($63$ Bandas)")
    ax2.grid(alpha=0.25, ls="--")

    handles_b = [
        Patch(facecolor=TEAL, alpha=0.75, label=r"$T_{\mathrm{cert}}=4$"),
        Patch(facecolor=SLATE, alpha=0.75, label=r"$T_{\mathrm{cert}}=5$"),
        Patch(facecolor=NAVY, alpha=0.75, label=r"$T_{\mathrm{cert}}=6$"),
        Patch(facecolor=AMBER, alpha=0.75, label=r"$T_{\mathrm{cert}}=7$"),
        plt.Line2D([0], [0], color="black", lw=1.5, label="Margen salida $M$ (eje der.)"),
        plt.Line2D([0], [0], color=CRIMSON, ls="-.", lw=1.6, label=rf"Borde certificado $N_f={nf_max_cert:.3f}$"),
    ]
    ax2.legend(handles=handles_b, loc="upper left", ncol=2, frameon=True, framealpha=0.94, fontsize=7.3)

    _save(fig, "fig2_fragmentation_equivalence")


def make_fig3(vfi_data: dict, extras: dict) -> None:
    pm = vfi_data["political_markov"]
    iso = extras["iso_skiba_fine"]
    p_vals = np.array([float(k) for k in iso[0]["by_p_rev"].keys()])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.0))
    fig.subplots_adjust(wspace=0.28)

    # Panel A: Iso-Skiba curves S_G(p_rev) by tau_u_G (locally refined VFI)
    palette = [NAVY, SLATE, TEAL, AMBER, CRIMSON, "#6d28d9"]
    markers = ["o", "s", "^", "D", "v", "P"]
    for idx, row in enumerate(iso):
        tuG = row["tau_u_G"]
        sg_list = [row["by_p_rev"][f"{pv:.2f}"]["S_G_fine"] for pv in p_vals]
        ax1.plot(
            100.0 * p_vals,
            sg_list,
            marker=markers[idx % len(markers)],
            color=palette[idx % len(palette)],
            lw=1.7,
            ms=4.5,
            label=rf"$\tau_{{u,G}} = {tuG:.2f}$ ($A_G={row['A_e_G']:.3f}$)",
        )
    ax1.set_ylim(0.0013, 0.0044)
    ax1.set_xlabel(r"Probabilidad anual de reversión $p_{\mathrm{rev}}$ (%)")
    ax1.set_ylabel(r"Umbral de Skiba en régimen bueno $S_G^{\mathrm{VFI}}$")
    ax1.set_title("A. Curvas Iso-Skiba $S_G(p_{\\mathrm{rev}}, \\tau_{u,G})$ bajo Riesgo Político")
    ax1.grid(alpha=0.25, ls="--")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.93, fontsize=7.6, ncol=2)

    # Panel B: Certified Doob E[tau] vs VFI precautionary drop (p_ref = 1/3)
    cert_rows = [r for r in pm["certification_summary"] if abs(r["p_ref"] - 1.0 / 3.0) < 1e-6]
    cert_rows.sort(key=lambda r: r["p_rev"])
    vfi_by_key = {(round(r["p_rev"], 4), round(r["p_ref"], 4)): r for r in pm["vfi"]["certified_grid_vfi"]}

    prev_pct = np.array([100.0 * r["p_rev"] for r in cert_rows])
    e_doob = np.array([math.ceil(r["E_tau_opt"] * 100.0) / 100.0 for r in cert_rows])
    e_vfi = np.array([vfi_by_key[(round(r["p_rev"], 4), round(r["p_ref"], 4))]["max_E_tau_H_vfi_Mpol"] for r in cert_rows])

    l1, = ax2.plot(prev_pct, e_doob, "o-", color=NAVY, lw=2.2, ms=6.0, label=r"Cota Doob CEGIS-LP ($\sup E[\tau]$)")
    for x, y in zip(prev_pct, e_doob):
        off = (14, -14) if abs(x - 8.0) < 0.1 else (0, 8)
        ax2.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=off, ha="center", fontsize=7.8, color=NAVY)

    ax2.set_ylim(21.6, 25.1)
    ax2.set_xlabel(r"Probabilidad de reversión política $p_{\mathrm{rev}}$ (%) ($p_{\mathrm{ref}}=1/3$)")
    ax2.set_ylabel(r"Cota certificada CEGIS-LP $E[\tau]$ (períodos)", color=NAVY)
    ax2.tick_params(axis="y", colors=NAVY)

    ax2_r = ax2.twinx()
    l2, = ax2_r.plot(prev_pct, e_vfi, "s--", color=CRIMSON, lw=2.0, ms=5.5, label=r"VFI $\max_{M_{\mathrm{pol}}\times\Omega} E_{\mathrm{VFI}}[\tau_H]$")
    ax2_r.set_ylabel(r"Máximo esperado VFI $E_{\mathrm{VFI}}[\tau_H]$", color=CRIMSON)
    ax2_r.tick_params(axis="y", colors=CRIMSON)
    ax2_r.set_ylim(3.41, 3.51)
    ax2_r.spines["top"].set_visible(False)

    ax2_r.annotate(
        "Huida precautoria:\n$3.483 \\to 3.444$",
        xy=(18.0, e_vfi[-1]), xytext=(9.2, 3.428),
        arrowprops=dict(arrowstyle="->", color=CRIMSON, lw=1.2),
        fontsize=8.2, color=CRIMSON, weight="bold",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=CRIMSON, alpha=0.92),
    )

    ax2.set_title("B. Certificación de Doob vs. Huida Precautoria en VFI")
    ax2.grid(alpha=0.25, ls="--")
    ax2.legend([l1, l2], [l1.get_label(), l2.get_label()], loc="upper left", frameon=True, framealpha=0.93, fontsize=7.8)

    _save(fig, "fig3_political_volatility")


def make_fig4(vfi_data: dict, extras: dict) -> None:
    rq_traj = extras["pure_red_queen"]
    b = rq_traj["burdened"]
    rf = rq_traj["reformed"]
    w0, w1 = rq_traj["wave_window"]

    t_ref = np.array([pt["t"] for pt in rf["trajectory_wave"]])
    k_ref = np.array([pt["K_hat"] for pt in rf["trajectory_wave"]])
    k_nw_const = np.array([pt["K_hat"] for pt in b["trajectory_no_wave_const_gL"]])
    k_nw_stoch = np.array([pt["K_hat"] for pt in b["trajectory_no_wave"]])
    k_wave = np.array([pt["K_hat"] for pt in b["trajectory_wave"]])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.0))
    fig.subplots_adjust(wspace=0.26)

    # Panel A: Pure Red Queen trajectories
    ax1.axvspan(w0, w1, color=AMBER, alpha=0.14, label=rf"Ola tecnológica $g_H = 5\%$ ($t \in [{w0}, {w1})$)")
    ax1.axhspan(b["S_hat_L"], b["S_hat_H"], color=CRIMSON, alpha=0.10, label=r"Ventana «Red Queen» $(\hat{S}_L, \hat{K}_H^*)$ para $\tau_u=0.55$")
    ax1.axhline(b["S_hat_L"], color=NAVY, ls=":", lw=1.2)
    ax1.axhline(b["S_hat_H"], color=CRIMSON, ls="--", lw=1.3)

    ax1.plot(t_ref, k_ref, color=GREEN, lw=2.3, label=r"Reformado ($\tau_u=0$, con ola): despegue")
    ax1.plot(t_ref, k_nw_const, color=NAVY, ls="--", lw=2.0, label=r"Burocrático ($\tau_u=0.55$, SIN ola $g \equiv g_L$): sobrevive")
    ax1.plot(t_ref, k_nw_stoch, color=SLATE, ls="-.", lw=1.4, alpha=0.85, label=r"Burocrático ($\tau_u=0.55$, sin realización de ola)")
    ax1.plot(t_ref, k_wave, color=CRIMSON, lw=2.3, label=r"Burocrático ($\tau_u=0.55$, CON ola): colapso")

    ax1.plot(0, rq_traj["k_hat_0"], "ko", ms=5.5, zorder=6)
    ax1.annotate(
        rf"$\hat{{K}}_0 = {rq_traj['k_hat_0']:.3f}$",
        xy=(0, rq_traj["k_hat_0"]), xytext=(3.0, 0.015),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
        fontsize=8.2, weight="bold",
    )
    ax1.text(28.0, b["S_hat_H"] * 0.83, rf"$\hat{{K}}_H^* = {b['S_hat_H']:.4f}$", color=CRIMSON, fontsize=7.8)
    ax1.text(30.5, b["S_hat_L"] * 0.78, rf"$\hat{{S}}_L = {b['S_hat_L']:.4f}$", color=NAVY, fontsize=7.8)

    ax1.set_yscale("log")
    ax1.set_xlim(0, rq_traj["T_sim"])
    ax1.set_ylim(0.008, 18.0)
    ax1.set_xlabel(r"Período $t$")
    ax1.set_ylabel(r"Capital por unidad de eficiencia $\hat{K}_t$ (escala log)")
    ax1.set_title("A. Paradoja «Red Queen» Pura: Contrafactual vs. Ola")
    ax1.grid(alpha=0.25, ls="--", which="both")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.93, fontsize=7.0)

    # Panel B: Certified Doob Surface in (g_H, tau_u)
    rq_cert = vfi_data["red_queen_markov"]["certification_summary"]
    gH_vals = sorted(set(r["g_H"] for r in rq_cert))
    tu_vals = sorted(set(r["tau_u"] for r in rq_cert))

    g_colors = {0.03: TEAL, 0.05: SLATE, 0.07: NAVY}
    g_markers = {0.03: "o", 0.05: "s", 0.07: "^"}
    y_offsets = {0.03: (5, -11), 0.05: (9, -11), 0.07: (-16, 7)}
    for gH in gH_vals:
        sub = [r for r in rq_cert if r["g_H"] == gH and r["certified"]]
        sub.sort(key=lambda r: r["tau_u"])
        xs = [r["tau_u"] for r in sub]
        ys = [math.ceil(r["E_tau_opt"] * 100.0) / 100.0 for r in sub]
        ax2.plot(
            xs, ys,
            marker=g_markers[gH], color=g_colors[gH], lw=2.1, ms=6.0,
            label=rf"$g_H = {int(round(100*gH))}\%$ (certificado)",
        )
        for x, y in zip(xs, ys):
            y_lbl = math.ceil(y * 10.0) / 10.0
            off = y_offsets[gH]
            if x == 0.0:
                off = {0.03: (8, -11), 0.05: (8, -2), 0.07: (-4, 7)}[gH]
            elif x >= 0.29:
                off = {0.03: (6, -11), 0.05: (6, -3), 0.07: (-26, 7)}[gH]
            ax2.annotate(f"{y_lbl:.1f}", (x, y), textcoords="offset points", xytext=off, fontsize=7.5, color=g_colors[gH])

    ax2.axvspan(0.30, 0.42, color=CRIMSON, alpha=0.10)
    ax2.axvline(0.30, color=CRIMSON, ls="--", lw=1.6, label=r"Frontera certificada $\tau_u^{\max} = 0.30$")
    ax2.scatter([0.40, 0.40, 0.40], [33.5, 34.8, 36.1], marker="x", color=CRIMSON, s=55, zorder=6)
    ax2.text(
        0.355, 22.0,
        "No certificable\nen LP ($\\tau_u = 0.40$)\n(bajo margen en $M$)",
        ha="center", va="center", fontsize=8.0, color=CRIMSON,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=CRIMSON, alpha=0.9),
    )

    ax2.set_xlim(-0.02, 0.43)
    ax2.set_ylim(13.0, 38.0)
    ax2.set_xlabel(r"Burocracia improductiva $\tau_u$")
    ax2.set_ylabel(r"Tiempo esperado certificado CEGIS-LP $\sup E[\tau]$")
    ax2.set_title("B. Superficie Certificada Doob en $(g_H, \\tau_u)$ ($9/9$ hasta $\\tau_u=0.30$)")
    ax2.grid(alpha=0.25, ls="--")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.93, fontsize=7.8)

    _save(fig, "fig4_red_queen_dynamics")


def main() -> None:
    with open(os.path.join(ROOT, "certificates", "vfi_results.json"), "r", encoding="utf-8") as fh:
        vfi_data = json.load(fh)
    with open(os.path.join(ROOT, "paper", "paper_extras.json"), "r", encoding="utf-8") as fh:
        extras = json.load(fh)

    make_fig1(vfi_data, extras)
    make_fig2(vfi_data)
    make_fig3(vfi_data, extras)
    make_fig4(vfi_data, extras)


if __name__ == "__main__":
    main()
