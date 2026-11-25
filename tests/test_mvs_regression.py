"""Regression test verifying Paper 1 canonical MVS benchmark on core/."""

from models.mvs_canonical import run_mvs_canonical


def test_mvs_canonical_regression():
    res = run_mvs_canonical(include_vfi=True, include_nonstationary=True)
    cert = res["certificate"]
    assert cert["T_cert"] <= 5
    assert cert["T_ns"] is not None and cert["T_ns"] <= 5
    assert cert["margins"]["d_ub_Psi_iv"] <= 0.0
    assert cert["margins"]["d_ub_W_iv"] <= 0.0
    assert cert["margins"]["d_ub_B_iv"] <= 0.0
    assert cert["margins"]["exit_M_iv"] > 0.0
    assert cert["margins"]["exit_H1_iv"] > 0.0
    assert cert["margins"]["exit_H2_iv"] > 0.0
    assert 0.0012 < res["vfi"]["skiba_point"] < 0.0025
    assert res["vfi"]["tau_H_vfi_from_010"] == 4
