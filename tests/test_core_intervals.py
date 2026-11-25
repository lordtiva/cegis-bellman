"""Unit tests for outward-rounded Decimal intervals, Rust ln(), PWL basis, and policy mappers."""

import ctypes
import math
import numpy as np

from core.interval_arith import Interval, iv_effective_A, iv_effective_q
from core.pwl_basis import make_pwl_from_knots, eval_logpwl, iv_eval_logpwl
from core.verifier_bridge import get_rust_lib


def test_decimal_interval_ln_soundness():
    for x in [0.001, 0.10, 0.28, 1.0, 2.0, math.e, 10.5, 100.0]:
        iv = Interval(x).ln()
        val = math.log(x)
        assert float(iv.lo) <= val <= float(iv.hi)


def test_rust_iv_ln_soundness():
    lib = get_rust_lib()
    if lib is None:
        return
    lo, hi = ctypes.c_double(), ctypes.c_double()
    for x in [1e-4, 0.05, 0.10, 0.28, 1.0, 1.9999, 2.0, 50.0]:
        lib.rs_test_iv_ln(x, ctypes.byref(lo), ctypes.byref(hi))
        val = math.log(x)
        assert lo.value <= val <= hi.value


def test_policy_box_mapper_enclosure():
    A0 = 1.4504
    tp = Interval("0.18", "0.22")
    tu = Interval("0.00", "0.05")
    nf = Interval("1.0", "2.0")
    g = Interval("0.02", "0.05")
    A_iv = iv_effective_A(A0, 1, 4, tp, tu, nf, g)
    q_iv = iv_effective_q(Interval("0.9199", "0.9201"), g)
    # Sample interior points
    for tp_v in (0.18, 0.20, 0.22):
        for tu_v in (0.00, 0.05):
            for nf_v in (1.0, 2.0):
                for g_v in (0.02, 0.05):
                    ae = A0 * (tp_v ** 0.25) * (1.0 - tp_v - tu_v) * (nf_v ** -0.5) / (1.0 + g_v)
                    assert float(A_iv.lo) <= ae <= float(A_iv.hi)
                    assert float(q_iv.lo) <= 0.92 / (1.0 + g_v) <= float(q_iv.hi)


def test_pwl_eval_consistency():
    ks = np.array([0.10, 0.18, 0.28, 0.80])
    vals = np.array([-40.0, -37.0, -35.0, -30.0])
    pwl = make_pwl_from_knots(ks, vals, 0.5, 1.2)
    for x in [0.05, 0.10, 0.14, 0.28, 1.5]:
        fv = float(eval_logpwl(pwl, np.array([x]))[0])
        iv = iv_eval_logpwl(pwl, Interval(x))
        assert float(iv.lo) <= fv + 1e-12 and float(iv.hi) >= fv - 1e-12
