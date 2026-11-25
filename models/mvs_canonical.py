"""
Canonical MVS Benchmark Model (Paper 1 Regression / Validation).
"""

from __future__ import annotations

from typing import Dict
import numpy as np

from core.interval_arith import (
    CANONICAL_A,
    CANONICAL_BETA,
    CANONICAL_BM,
    CANONICAL_ETA,
    CANONICAL_HM,
    CANONICAL_Q,
)
from core.model_api import Economy1D, ParamBox
from core.cegis_lp import synth_static_certificate


def canonical_mvs_box() -> ParamBox:
    return ParamBox(
        A_lo=CANONICAL_A[0], A_hi=CANONICAL_A[1],
        q_lo=CANONICAL_Q[0], q_hi=CANONICAL_Q[1],
        b_lo=CANONICAL_BETA[0], b_hi=CANONICAL_BETA[1],
        e_lo=CANONICAL_ETA[0], e_hi=CANONICAL_ETA[1],
        label="mvs_canonical",
    )


def run_mvs_canonical(include_vfi: bool = True, include_nonstationary: bool = True) -> Dict[str, object]:
    box = canonical_mvs_box()
    cert = synth_static_certificate(
        box, b_m=CANONICAL_BM, h_m=CANONICAL_HM, k_h2=0.80,
        include_nonstationary=include_nonstationary,
    )
    vfi_summary = {}
    if include_vfi:
        eco = Economy1D(A=0.75, q=0.92, beta=0.97, eta=0.70)
        k_fine = np.unique(np.concatenate([
            np.geomspace(1e-4, 0.0010, 25, endpoint=False),
            np.geomspace(0.0010, 0.0025, 90, endpoint=False),
            np.geomspace(0.0025, 0.05, 35, endpoint=False),
            np.geomspace(0.05, 0.50, 40, endpoint=False),
            np.geomspace(0.50, 50.0, 45),
        ]))
        vfi = eco.solve_vfi(k_grid=k_fine)
        # Simulate escape time from K_0 = 0.10 to >= 0.28 under VFI policy
        k_g, kp_g = vfi["k_grid"], vfi["kp"]
        k_cur = CANONICAL_BM
        steps = 0
        while k_cur < CANONICAL_HM and steps < 50:
            k_cur = float(np.interp(k_cur, k_g, kp_g))
            steps += 1
        vfi_summary = {
            "skiba_point": vfi["skiba"],
            "tau_H_vfi_from_010": int(steps),
            "V_010": float(np.interp(CANONICAL_BM, k_g, vfi["V"])),
            "V_028": float(np.interp(CANONICAL_HM, k_g, vfi["V"])),
        }
    return {
        "certificate": cert,
        "vfi": vfi_summary,
    }
