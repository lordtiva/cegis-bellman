"""Core generic 1D CEGIS-LP Bellman barrier certification engine (v0.1)."""

from core.interval_arith import (
    CANONICAL_A,
    CANONICAL_BETA,
    CANONICAL_Q,
    CANONICAL_ETA,
    CANONICAL_BM,
    CANONICAL_HM,
    Interval,
    F_A,
    dF_dK,
    dF_dL,
    iv_F_A,
    iv_effective_A,
    iv_effective_q,
)
from core.pwl_basis import (
    make_pwl_from_knots,
    pwl_to_dict,
    pwl_from_dict,
    eval_logpwl,
    eval_pwl_basis_sparse,
    monotone_diff_sparse,
)

__all__ = [
    "CANONICAL_A",
    "CANONICAL_BETA",
    "CANONICAL_Q",
    "CANONICAL_ETA",
    "CANONICAL_BM",
    "CANONICAL_HM",
    "Interval",
    "F_A",
    "dF_dK",
    "dF_dL",
    "iv_F_A",
    "iv_effective_A",
    "iv_effective_q",
    "make_pwl_from_knots",
    "pwl_to_dict",
    "pwl_from_dict",
    "eval_logpwl",
    "eval_pwl_basis_sparse",
    "monotone_diff_sparse",
]
