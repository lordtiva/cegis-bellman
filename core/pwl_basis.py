"""
Exact Log-PWL Representation & Sparse Basis Utilities for CEGIS-LP Synthesis.

Provides:
  - `make_pwl_from_knots`, `pwl_to_dict`, `pwl_from_dict`, `build_slope_tables`
  - `eval_logpwl`, `deriv_bounds_logpwl`, `range_bounds_logpwl`
  - `eval_pwl_basis_sparse`, `monotone_diff_sparse`
  - 50-digit Decimal `Interval` evaluators `iv_eval_logpwl`, `iv_deriv_bounds_logpwl`
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Tuple
import numpy as np
from scipy import sparse as sp

from core.interval_arith import Interval


def make_pwl_from_knots(
    ks: np.ndarray,
    vals: np.ndarray,
    s_lo: float,
    s_hi: float,
) -> Dict[str, object]:
    """Build exact log-PWL dictionary from sorted knots ks and values vals."""
    ks_arr = np.asarray(ks, dtype=np.float64)
    vals_arr = np.asarray(vals, dtype=np.float64)
    assert ks_arr.ndim == 1 and len(ks_arr) >= 2
    assert len(ks_arr) == len(vals_arr)
    assert np.all(np.diff(ks_arr) > 0.0)
    lks = np.log(ks_arr)
    slopes = np.diff(vals_arr) / np.diff(lks)
    return {
        "ks": ks_arr,
        "lks": lks,
        "vals": vals_arr,
        "slopes": slopes,
        "s_lo": float(s_lo),
        "s_hi": float(s_hi),
    }


def pwl_to_dict(pwl: Dict[str, object]) -> Dict[str, object]:
    """Serialize log-PWL table directly into JSON-safe dict."""
    return {
        "type": "log_pwl",
        "ks": np.asarray(pwl["ks"], dtype=np.float64).tolist(),
        "vals": np.asarray(pwl["vals"], dtype=np.float64).tolist(),
        "s_lo": float(pwl["s_lo"]),
        "s_hi": float(pwl["s_hi"]),
    }


def pwl_from_dict(data: Dict[str, object]) -> Dict[str, object]:
    """Deserialize a `log_pwl` dictionary."""
    if data.get("type") != "log_pwl":
        raise ValueError(f"Unsupported PWL serialization type: {data.get('type')}")
    return make_pwl_from_knots(
        np.asarray(data["ks"], dtype=np.float64),
        np.asarray(data["vals"], dtype=np.float64),
        float(data["s_lo"]),
        float(data["s_hi"]),
    )


def build_slope_tables(slopes_arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Precompute O(1) min/max slope lookup tables over contiguous knot ranges."""
    m = len(slopes_arr)
    smin = np.full((m, m), np.inf, dtype=np.float64)
    smax = np.full((m, m), -np.inf, dtype=np.float64)
    for i in range(m):
        smin[i, i:] = np.minimum.accumulate(slopes_arr[i:])
        smax[i, i:] = np.maximum.accumulate(slopes_arr[i:])
    return smin, smax


def eval_logpwl(pwl: Dict[str, object], k_arr) -> np.ndarray:
    """Evaluate exact continuous log-PWL function in float64."""
    ks = pwl["ks"]
    lks = pwl["lks"]
    vals = pwl["vals"]
    s_lo = float(pwl["s_lo"])
    s_hi = float(pwl["s_hi"])
    k = np.asarray(k_arr, dtype=np.float64)
    lk = np.log(np.maximum(k, 1e-300))
    r = np.interp(np.clip(lk, lks[0], lks[-1]), lks, vals)
    below = k < ks[0]
    if np.any(below):
        r = np.where(below, vals[0] + s_lo * (lk - lks[0]), r)
    above = k > ks[-1]
    if np.any(above):
        r = np.where(above, vals[-1] + s_hi * (lk - lks[-1]), r)
    return r


def deriv_bounds_logpwl(
    pwl: Dict[str, object],
    smin_tbl: np.ndarray,
    smax_tbl: np.ndarray,
    kL: np.ndarray,
    kR: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Fast float64 derivative bounds [dN/dK_lo, dN/dK_hi] on [kL, kR] for B&B pruning."""
    ks = pwl["ks"]
    nk = len(ks)
    s_lo = float(pwl["s_lo"])
    s_hi = float(pwl["s_hi"])
    iL = np.clip(np.searchsorted(ks, kL, side="right") - 1, 0, nk - 2)
    iR = np.maximum(iL, np.clip(np.searchsorted(ks, kR, side="left") - 1, 0, nk - 2))
    lo_s = smin_tbl[iL, iR].copy()
    hi_s = smax_tbl[iL, iR].copy()
    below = kL < ks[0]
    if np.any(below):
        lo_s = np.where(below, np.minimum(lo_s, s_lo), lo_s)
        hi_s = np.where(below, np.maximum(hi_s, s_lo), hi_s)
    above = kR > ks[-1]
    if np.any(above):
        lo_s = np.where(above, np.minimum(lo_s, s_hi), lo_s)
        hi_s = np.where(above, np.maximum(hi_s, s_hi), hi_s)
    d_lo = np.where(lo_s >= 0.0, lo_s / kR, lo_s / kL)
    d_hi = np.where(hi_s >= 0.0, hi_s / kL, hi_s / kR)
    return d_lo, d_hi


def range_bounds_logpwl(
    pwl: Dict[str, object],
    kL: np.ndarray,
    kR: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Fast vectorized range enclosure [min_{K in [kL,kR]} N(K), max_{K in [kL,kR]} N(K)]."""
    ks = pwl["ks"]
    vals = pwl["vals"]
    nk = len(ks)
    vL = eval_logpwl(pwl, kL)
    vR = eval_logpwl(pwl, kR)
    vmin = np.minimum(vL, vR)
    vmax = np.maximum(vL, vR)
    if nk > 2:
        i_first = np.searchsorted(ks, kL, side="right")
        i_last = np.searchsorted(ks, kR, side="left") - 1
        has_int = i_first <= i_last
        if np.any(has_int):
            idxs = np.where(has_int)[0]
            for idx in idxs:
                sl = vals[i_first[idx]:i_last[idx] + 1]
                vmin[idx] = min(vmin[idx], float(np.min(sl)))
                vmax[idx] = max(vmax[idx], float(np.max(sl)))
    return vmin, vmax


def eval_pwl_basis_sparse(
    z_k: np.ndarray,
    z_q: np.ndarray,
    s_lo: float,
    s_hi: float,
) -> Tuple[sp.csr_matrix, np.ndarray]:
    """Exact sparse linear decomposition V(z_q) = M @ y_k + offset (2 nonzeros/row)."""
    n_k = len(z_k)
    n_q = len(z_q)
    zc = np.clip(z_q, z_k[0], z_k[-1])
    idx = np.clip(np.searchsorted(z_k, zc, side="right") - 1, 0, n_k - 2)
    t = (zc - z_k[idx]) / (z_k[idx + 1] - z_k[idx])
    rows = np.repeat(np.arange(n_q, dtype=np.int32), 2)
    cols = np.empty(2 * n_q, dtype=np.int32)
    cols[0::2] = idx
    cols[1::2] = idx + 1
    data = np.empty(2 * n_q, dtype=np.float64)
    data[0::2] = 1.0 - t
    data[1::2] = t
    M = sp.csr_matrix((data, (rows, cols)), shape=(n_q, n_k))
    offset = np.zeros(n_q, dtype=np.float64)
    if s_lo != 0.0:
        below = z_q < z_k[0]
        if np.any(below):
            offset = np.where(below, s_lo * (z_q - z_k[0]), offset)
    if s_hi != 0.0:
        above = z_q > z_k[-1]
        if np.any(above):
            offset = np.where(above, s_hi * (z_q - z_k[-1]), offset)
    return M, offset


def monotone_diff_sparse(n_k: int) -> sp.csr_matrix:
    """Sparse (n_k - 1, n_k) difference matrix enforcing y_i - y_{i+1} <= -rhs."""
    r = np.repeat(np.arange(n_k - 1, dtype=np.int32), 2)
    c = np.empty(2 * (n_k - 1), dtype=np.int32)
    c[0::2] = np.arange(n_k - 1, dtype=np.int32)
    c[1::2] = c[0::2] + 1
    d = np.tile(np.array([1.0, -1.0], dtype=np.float64), n_k - 1)
    return sp.csr_matrix((d, (r, c)), shape=(n_k - 1, n_k))


def _get_pwl_iv_cache(pwl: Dict[str, object]) -> Dict[str, object]:
    cache = pwl.get("_iv_cache")
    if cache is not None:
        return cache
    ks_dec = [Decimal.from_float(float(x)) for x in pwl["ks"]]
    vals_iv = [Interval(float(v)) for v in pwl["vals"]]
    lks_iv = [Interval._raw(kd, kd).ln() for kd in ks_dec]
    slopes_iv = [
        (vals_iv[i + 1] - vals_iv[i]) / (lks_iv[i + 1] - lks_iv[i])
        for i in range(len(ks_dec) - 1)
    ]
    cache = {
        "ks_dec": ks_dec,
        "vals_iv": vals_iv,
        "lks_iv": lks_iv,
        "slopes_iv": slopes_iv,
        "s_lo_iv": Interval(float(pwl["s_lo"])),
        "s_hi_iv": Interval(float(pwl["s_hi"])),
    }
    pwl["_iv_cache"] = cache
    return cache


def iv_eval_logpwl(pwl: Dict[str, object], k_iv: Interval) -> Interval:
    """Outward-rounded 50-digit Interval enclosure of exact log-PWL on interval k_iv."""
    c = _get_pwl_iv_cache(pwl)
    ks_dec = c["ks_dec"]
    vals_iv = c["vals_iv"]
    lks_iv = c["lks_iv"]
    slopes_iv = c["slopes_iv"]
    s_lo_iv = c["s_lo_iv"]
    s_hi_iv = c["s_hi_iv"]

    def _eval_pt(k_val: Decimal) -> Interval:
        kv = Interval._raw(k_val, k_val)
        if k_val <= ks_dec[0]:
            return vals_iv[0] + s_lo_iv * (kv.ln() - lks_iv[0])
        if k_val >= ks_dec[-1]:
            return vals_iv[-1] + s_hi_iv * (kv.ln() - lks_iv[-1])
        lo_i, hi_i = 0, len(ks_dec) - 2
        idx = 0
        while lo_i <= hi_i:
            mid = (lo_i + hi_i) // 2
            if ks_dec[mid] <= k_val <= ks_dec[mid + 1]:
                idx = mid
                break
            elif k_val < ks_dec[mid]:
                hi_i = mid - 1
            else:
                lo_i = mid + 1
        else:
            idx = max(0, min(len(ks_dec) - 2, lo_i))
        return vals_iv[idx] + slopes_iv[idx] * (kv.ln() - lks_iv[idx])

    out = _eval_pt(k_iv.lo).hull(_eval_pt(k_iv.hi))
    for i, kd in enumerate(ks_dec):
        if k_iv.lo < kd < k_iv.hi:
            out = out.hull(vals_iv[i])
    return out


def iv_deriv_bounds_logpwl(pwl: Dict[str, object], k_iv: Interval) -> Interval:
    """Outward-rounded 50-digit Interval enclosure of dN/dK on k_iv."""
    c = _get_pwl_iv_cache(pwl)
    ks_dec = c["ks_dec"]
    slopes_iv = c["slopes_iv"]
    s_lo_iv = c["s_lo_iv"]
    s_hi_iv = c["s_hi_iv"]

    s_min_dec = None
    s_max_dec = None

    def _upd_iv(iv_s: Interval):
        nonlocal s_min_dec, s_max_dec
        if s_min_dec is None:
            s_min_dec, s_max_dec = iv_s.lo, iv_s.hi
        else:
            s_min_dec = min(s_min_dec, iv_s.lo)
            s_max_dec = max(s_max_dec, iv_s.hi)

    if k_iv.lo < ks_dec[0]:
        _upd_iv(s_lo_iv)
    for i, sl_iv in enumerate(slopes_iv):
        if k_iv.hi > ks_dec[i] and k_iv.lo < ks_dec[i + 1]:
            _upd_iv(sl_iv)
    if k_iv.hi > ks_dec[-1]:
        _upd_iv(s_hi_iv)
    if s_min_dec is None:
        if k_iv.lo <= ks_dec[0]:
            _upd_iv(s_lo_iv)
        if k_iv.hi >= ks_dec[-1]:
            _upd_iv(s_hi_iv)
        for i, sl_iv in enumerate(slopes_iv):
            if ks_dec[i] <= k_iv.lo <= ks_dec[i + 1]:
                _upd_iv(sl_iv)

    return Interval._raw(s_min_dec, s_max_dec) / k_iv
