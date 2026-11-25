"""
Adaptive Parametric Box Partitioner (1D / 2D) for Institutional Policy Sweeps.

Maps policy boxes (e.g., (tau_p, tau_u) or N_f intervals) conservatively into
`ParamBox` instances via 50-digit `Interval` arithmetic and recursively subdivides
boxes whenever CEGIS-LP certification fails or requires tighter parameter resolution.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from typing import Callable, Dict, List, Optional, Tuple

from core.cegis_lp import synth_static_certificate
from core.model_api import ParamBox


def _adaptive_leaf_2d(
    x_lo: float, x_hi: float,
    y_lo: float, y_hi: float,
    mapper_fn: Callable[[float, float, float, float], ParamBox],
    b_m: float, h_m: float, k_h2: float,
    depth: int, max_depth: int,
) -> List[Dict[str, object]]:
    box = mapper_fn(x_lo, x_hi, y_lo, y_hi)
    try:
        cert = synth_static_certificate(box, b_m=b_m, h_m=h_m, k_h2=k_h2)
        return [{
            "status": "certified",
            "bounds_2d": [[float(x_lo), float(x_hi)], [float(y_lo), float(y_hi)]],
            "depth": int(depth),
            "cert": cert,
        }]
    except Exception as exc:
        if depth >= max_depth:
            return [{
                "status": "uncertified",
                "bounds_2d": [[float(x_lo), float(x_hi)], [float(y_lo), float(y_hi)]],
                "depth": int(depth),
                "box": box.to_dict(),
                "error": str(exc),
            }]
        xm = 0.5 * (x_lo + x_hi)
        ym = 0.5 * (y_lo + y_hi)
        # Split along wider relative axis
        if (x_hi - x_lo) >= (y_hi - y_lo):
            left = _adaptive_leaf_2d(x_lo, xm, y_lo, y_hi, mapper_fn, b_m, h_m, k_h2, depth + 1, max_depth)
            right = _adaptive_leaf_2d(xm, x_hi, y_lo, y_hi, mapper_fn, b_m, h_m, k_h2, depth + 1, max_depth)
        else:
            left = _adaptive_leaf_2d(x_lo, x_hi, y_lo, ym, mapper_fn, b_m, h_m, k_h2, depth + 1, max_depth)
            right = _adaptive_leaf_2d(x_lo, x_hi, ym, y_hi, mapper_fn, b_m, h_m, k_h2, depth + 1, max_depth)
        return left + right


def _worker_2d_cell(task):
    idx, x0, x1, y0, y1, mapper_fn, b_m, h_m, k_h2, max_depth = task
    leaves = _adaptive_leaf_2d(x0, x1, y0, y1, mapper_fn, b_m, h_m, k_h2, 0, max_depth)
    return idx, leaves


def adaptive_certify_2d(
    x_edges: List[float],
    y_edges: List[float],
    mapper_fn: Callable[[float, float, float, float], ParamBox],
    b_m: float = 0.10,
    h_m: float = 0.28,
    k_h2: float = 0.80,
    max_depth: int = 2,
    parallel: bool = True,
    max_workers: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Sweep and adaptively subdivide a 2D grid of policy boxes."""
    tasks = []
    idx = 0
    for i in range(len(x_edges) - 1):
        for j in range(len(y_edges) - 1):
            tasks.append((
                idx, float(x_edges[i]), float(x_edges[i + 1]),
                float(y_edges[j]), float(y_edges[j + 1]),
                mapper_fn, b_m, h_m, k_h2, max_depth,
            ))
            idx += 1

    all_leaves: List[Tuple[int, List[Dict[str, object]]]] = []
    if parallel and len(tasks) > 1:
        nw = max_workers or min(8, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=nw) as pool:
            futs = [pool.submit(_worker_2d_cell, t) for t in tasks]
            for fut in as_completed(futs):
                all_leaves.append(fut.result())
    else:
        for t in tasks:
            all_leaves.append(_worker_2d_cell(t))

    all_leaves.sort(key=lambda pair: pair[0])
    flat: List[Dict[str, object]] = []
    for _, leaves in all_leaves:
        flat.extend(leaves)
    return flat


def _worker_1d_cell(task):
    idx, lo, hi, mapper_fn, b_m, h_m, k_h2, max_depth = task
    def _leaf_1d(x0: float, x1: float, depth: int) -> List[Dict[str, object]]:
        box = mapper_fn(x0, x1)
        try:
            cert = synth_static_certificate(box, b_m=b_m, h_m=h_m, k_h2=k_h2)
            return [{"status": "certified", "bounds_1d": [float(x0), float(x1)], "depth": depth, "cert": cert}]
        except Exception as exc:
            if depth >= max_depth:
                return [{"status": "uncertified", "bounds_1d": [float(x0), float(x1)], "depth": depth, "box": box.to_dict(), "error": str(exc)}]
            mid = 0.5 * (x0 + x1)
            return _leaf_1d(x0, mid, depth + 1) + _leaf_1d(mid, x1, depth + 1)
    return idx, _leaf_1d(lo, hi, 0)


def adaptive_certify_1d(
    edges: List[float],
    mapper_fn: Callable[[float, float], ParamBox],
    b_m: float = 0.10,
    h_m: float = 0.28,
    k_h2: float = 0.80,
    max_depth: int = 2,
    parallel: bool = False,
    max_workers: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Sweep and adaptively subdivide a 1D sequence of policy intervals."""
    tasks = [
        (i, float(a), float(b), mapper_fn, b_m, h_m, k_h2, max_depth)
        for i, (a, b) in enumerate(zip(edges[:-1], edges[1:]))
    ]
    all_leaves: List[Tuple[int, List[Dict[str, object]]]] = []
    if parallel and len(tasks) > 1:
        nw = max_workers or min(8, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=nw) as pool:
            futs = [pool.submit(_worker_1d_cell, t) for t in tasks]
            for fut in as_completed(futs):
                all_leaves.append(fut.result())
    else:
        for t in tasks:
            all_leaves.append(_worker_1d_cell(t))
    all_leaves.sort(key=lambda pair: pair[0])
    out: List[Dict[str, object]] = []
    for _, leaves in all_leaves:
        out.extend(leaves)
    return out
