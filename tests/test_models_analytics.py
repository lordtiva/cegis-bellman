"""Analytical theorem and proposition identity tests (Theorems 1-2, Proposition 1)."""

import math
from core.model_api import Economy1D
from models.barro_u_frag import (
    compute_theorem1_analytics,
    effective_A,
    equivalent_tau_u,
    optimal_tau_p,
)
from models.red_queen_markov import verify_theorem2_isomorphism


def test_theorem1_and_prop1_identities():
    assert abs(Economy1D.a_rep(0.92) - 0.07348469228) < 1e-8
    assert abs(optimal_tau_p(0.0, 0.20) - 0.20) < 1e-12
    assert abs(optimal_tau_p(0.25, 0.20) - 0.15) < 1e-12
    # Exact bureaucracy-fragmentation equivalence example: theta=3/2, tau_p=0.20, N_f=4 -> tau_u^eq = 0.40
    assert abs(equivalent_tau_u(4.0, 0.20, 1.5) - 0.40) < 1e-12
    # Verify effective_A(0.20, 0.0, 4) == effective_A(0.20, 0.40, 1)
    assert abs(effective_A(0.20, 0.0, 4.0) - effective_A(0.20, 0.40, 1.0)) < 1e-12

    an = compute_theorem1_analytics()
    assert abs(an["A_SN"] - 0.0995245) < 5e-4
    assert abs(an["A_star"] - 0.0996091) < 5e-4
    assert an["A_SN"] < an["A_star"]
    assert abs(an["A_peak_tau_u0"] - 0.775739) < 1e-5
    assert abs(an["A_cross"] - 0.110038) < 1.5e-3
    assert abs(an["nf_collapse_bench075"] - 56.69) < 0.5
    assert an["nf_collapse_bench075"] < an["nf_SN_bench075"]
    assert an["tau_old_mvs_island"][0] <= 0.118 and an["tau_old_mvs_island"][1] >= 0.304


def test_theorem2_red_queen_isomorphism():
    res = verify_theorem2_isomorphism(g_L=0.02, g_H=0.05, E0=3.7)
    assert res["max_bellman_shift_error"] < 1e-9
    assert len(res["phi"]) == 2 and res["phi"][1] > res["phi"][0] > 0.0
