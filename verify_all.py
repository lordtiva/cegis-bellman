"""
Full Synthesis, VFI Execution & Audit Orchestrator for `cegis-bellman` v0.1.

Usage:
  python -u verify_all.py --full-audit       # Synthesize + VFI + save .json.xz + audit
  python -u verify_all.py --synthesize       # Synthesize + VFI + save .json.xz
  python -u verify_all.py --audit-only       # Re-audit existing certificates/cegis_certificates.json.xz
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from core.cert_schema import load_certificate_archive, save_certificate_archive
from core.interval_arith import CANONICAL_BM, CANONICAL_HM
from core.model_api import Economy1D
from core.pwl_basis import pwl_to_dict
from models.mvs_canonical import run_mvs_canonical
from models.barro_u_frag import (
    certify_fragmentation_nf,
    certify_policy_plane,
    compute_theorem1_analytics,
    run_barro_u_frag,
)
from models.political_markov import run_political_markov
from models.red_queen_markov import run_red_queen_markov
import numpy as np


ROOT = os.path.dirname(os.path.abspath(__file__))
CERT_ARCHIVE_PATH = os.path.join(ROOT, "certificates", "cegis_certificates.json.xz")
VFI_RESULTS_PATH = os.path.join(ROOT, "certificates", "vfi_results.json")


def _serialize_static_cert(cert: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in cert.items() if k not in ("Psi", "W", "kp", "L", "B")}
    for key in ("Psi", "W", "kp", "L", "B"):
        out[key] = pwl_to_dict(cert[key])
    return out


def _serialize_markov_cert(cert: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in cert.items() if k not in ("Psi", "W", "kp", "L", "B")}
    for key in ("Psi", "W", "kp", "L", "B"):
        out[key] = [pwl_to_dict(cert[key][0]), pwl_to_dict(cert[key][1])]
    return out


def run_synthesis(parallel: bool = True) -> None:
    t_start = time.time()
    print("=" * 72, flush=True)
    print("CEGIS-BELLMAN v0.1 | FULL SYNTHESIS & VFI SUITE", flush=True)
    print("=" * 72, flush=True)

    # 1. Canonical MVS benchmark
    t0 = time.time()
    print("\n[1/4] Running mvs_canonical (Paper 1 regression)...", flush=True)
    mvs_res = run_mvs_canonical(include_vfi=True, include_nonstationary=True)
    mvs_cert = mvs_res["certificate"]
    print(
        f"  -> T_cert={mvs_cert['T_cert']} (T_ns={mvs_cert.get('T_ns')}) | "
        f"Skiba={mvs_res['vfi']['skiba_point']:.6f} | {time.time() - t0:.2f}s",
        flush=True,
    )

    # 2. Barro-CES U-curve + Fragmentation N_f
    t0 = time.time()
    print("\n[2/4] Running barro_u_frag (Theorem 1, Prop 1, Prop 2, Prop 3)...", flush=True)
    barro_res = run_barro_u_frag(parallel=parallel)
    ps = barro_res["policy_plane"]["summary"]
    ns = barro_res["fragmentation"]["summary"]
    print(
        f"  -> Plane: {ps['n_certified_boxes']} certified boxes, area={ps['area_tau_plane']:.4f}, "
        f"A_e in [{ps['A_e_min_certified']:.4f}, {ps['A_e_max_certified']:.4f}], T_cert in [{ps['T_cert_min']}, {ps['T_cert_max']}]",
        flush=True,
    )
    print(
        f"  -> Fragmentation: N_f in [1, {ns['nf_max_certified']:.2f}] certified "
        f"(T_cert in {ns['T_cert_range']}) | {time.time() - t0:.2f}s",
        flush=True,
    )

    # 3. Political Markov G <-> B
    t0 = time.time()
    print("\n[3/4] Running political_markov (VFI + Prop 4 coupled Doob)...", flush=True)
    pol_res = run_political_markov(parallel=parallel)
    print(
        f"  -> Certified {len(pol_res['certification']['certificates'])} Markov grids | "
        f"max p_rev at p_ref=1/3: {pol_res['certification']['max_certified_p_rev_at_pref_1_3']:.2f} | {time.time() - t0:.2f}s",
        flush=True,
    )

    # 4. Stochastic Red Queen g_L <-> g_H
    t0 = time.time()
    print("\n[4/4] Running red_queen_markov (Theorem 2 + VFI + Prop 5)...", flush=True)
    rq_res = run_red_queen_markov(parallel=parallel)
    print(
        f"  -> Theorem 2 shift error={rq_res['vfi']['theorem2_check']['max_bellman_shift_error']:.2e} | "
        f"Certified {len(rq_res['certification']['certificates'])} RQ grids | "
        f"tau_u_max(g_H)={rq_res['certification']['tau_u_max_certified_by_gH']} | {time.time() - t0:.2f}s",
        flush=True,
    )

    # Package certificates archive
    models_payload = {
        "mvs_canonical": {
            "kind": "static",
            "certificates": [_serialize_static_cert(mvs_cert)],
        },
        "barro_Ae_atlas": {
            "kind": "static",
            "certificates": [
                {**_serialize_static_cert(lf["cert"]), "bounds_1d": lf["bounds_1d"], "depth": lf["depth"]}
                for lf in barro_res["atlas"]["certified_leaves"]
            ],
        },
        "political_markov": {
            "kind": "markov",
            "certificates": [_serialize_markov_cert(c) for c in pol_res["certification"]["certificates"]],
        },
        "red_queen_markov": {
            "kind": "markov",
            "certificates": [_serialize_markov_cert(c) for c in rq_res["certification"]["certificates"]],
        },
    }
    digest = save_certificate_archive(
        CERT_ARCHIVE_PATH,
        models_payload,
        metadata={"engine": "cegis-bellman", "version": "0.1.0"},
    )

    vfi_summary = {
        "mvs_canonical": {
            "T_cert": mvs_cert["T_cert"],
            "T_ns": mvs_cert.get("T_ns"),
            "margins": mvs_cert["margins"],
            "vfi": mvs_res["vfi"],
        },
        "barro_u_frag": {
            "analytics": barro_res["analytics"],
            "policy_plane_summary": ps,
            "atlas_bands": [
                {
                    "bounds_1d": lf["bounds_1d"],
                    "depth": lf["depth"],
                    "T_cert": lf["cert"]["T_cert"],
                    "margins": lf["cert"]["margins"],
                }
                for lf in barro_res["atlas"]["certified_leaves"]
            ],
            "fragmentation_summary": ns,
            "fragmentation_bands": barro_res["fragmentation"]["certified_bands"],
        },
        "political_markov": {
            "vfi": pol_res["vfi"],
            "certification_summary": pol_res["certification"]["summary_rows"],
            "max_certified_p_rev_at_pref_1_3": pol_res["certification"]["max_certified_p_rev_at_pref_1_3"],
        },
        "red_queen_markov": {
            "vfi": rq_res["vfi"],
            "certification_summary": rq_res["certification"]["summary_rows"],
            "tau_u_max_certified_by_gH": rq_res["certification"]["tau_u_max_certified_by_gH"],
        },
    }
    os.makedirs(os.path.dirname(VFI_RESULTS_PATH), exist_ok=True)
    with open(VFI_RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(vfi_summary, fh, indent=2)

    print(f"\nSaved archive: {CERT_ARCHIVE_PATH} ({os.path.getsize(CERT_ARCHIVE_PATH):,} bytes, sha256={digest[:16]}...)", flush=True)
    print(f"Saved VFI/summary JSON: {VFI_RESULTS_PATH}", flush=True)
    print(f"Total synthesis time: {time.time() - t_start:.2f}s", flush=True)


def refresh_markov_and_vfi(parallel: bool = True) -> None:
    """
    Re-use certified static certificates (mvs_canonical + barro_Ae_atlas) from archive,
    refresh VFI/analytics and re-synthesize political_markov (7/7) & red_queen_markov (9/9).
    """
    t_start = time.time()
    print("=" * 72, flush=True)
    print("CEGIS-BELLMAN v0.1 | REFRESH VFI, ANALYTICS & COUPLED MARKOV", flush=True)
    print("=" * 72, flush=True)

    env = load_certificate_archive(CERT_ARCHIVE_PATH, verify_hash=True)
    existing_models = env["models"]
    mvs_cert_rec = existing_models["mvs_canonical"]["certificates"][0]
    atlas_recs = existing_models["barro_Ae_atlas"]["certificates"]
    cached_atlas = {
        "certified_leaves": [
            {"status": "certified", "bounds_1d": rec["bounds_1d"], "depth": rec["depth"], "cert": rec}
            for rec in atlas_recs
        ],
        "uncertified_leaves": [],
        "A_min": float(atlas_recs[0]["bounds_1d"][0]),
        "A_max": float(atlas_recs[-1]["bounds_1d"][1]),
    }

    t0 = time.time()
    print("\n[1/4] Refreshing mvs_canonical fine-grid VFI...", flush=True)
    eco = Economy1D(A=0.75, q=0.92, beta=0.97, eta=0.70)
    k_fine = np.unique(np.concatenate([
        np.geomspace(1e-4, 0.0010, 25, endpoint=False),
        np.geomspace(0.0010, 0.0025, 90, endpoint=False),
        np.geomspace(0.0025, 0.05, 35, endpoint=False),
        np.geomspace(0.05, 0.50, 40, endpoint=False),
        np.geomspace(0.50, 50.0, 45),
    ]))
    vfi_mvs = eco.solve_vfi(k_grid=k_fine)
    k_g, kp_g = vfi_mvs["k_grid"], vfi_mvs["kp"]
    kc, steps = CANONICAL_BM, 0
    while kc < CANONICAL_HM and steps < 50:
        kc = float(np.interp(kc, k_g, kp_g))
        steps += 1
    mvs_vfi_dict = {
        "skiba_point": vfi_mvs["skiba"],
        "tau_H_vfi_from_010": int(steps),
        "V_010": float(np.interp(CANONICAL_BM, k_g, vfi_mvs["V"])),
        "V_028": float(np.interp(CANONICAL_HM, k_g, vfi_mvs["V"])),
    }
    print(f"  -> Skiba={mvs_vfi_dict['skiba_point']:.6f} | tau_H={steps} | {time.time() - t0:.2f}s", flush=True)

    t0 = time.time()
    print("\n[2/4] Refreshing barro_u_frag analytics (A0=1.45, Maxwell A_*, A_cross)...", flush=True)
    analytics = compute_theorem1_analytics()
    plane = certify_policy_plane(parallel=parallel, atlas=cached_atlas)
    nf_cert = certify_fragmentation_nf(parallel=parallel, atlas=cached_atlas)
    ps = plane["summary"]
    ns = nf_cert["summary"]
    print(
        f"  -> A_SN={analytics['A_SN']:.7f}, A_*={analytics['A_star']:.7f}, A_cross={analytics['A_cross']:.6f}, "
        f"A_peak={analytics['A_peak_tau_u0']:.6f}, N_f*={analytics['nf_collapse_bench075']:.2f} | {time.time() - t0:.2f}s",
        flush=True,
    )

    t0 = time.time()
    print("\n[3/4] Running political_markov (VFI + Prop 4 coupled Doob, max_rounds=28)...", flush=True)
    pol_res = run_political_markov(parallel=parallel)
    print(
        f"  -> Certified {len(pol_res['certification']['certificates'])}/7 Markov grids | "
        f"max p_rev at p_ref=1/3: {pol_res['certification']['max_certified_p_rev_at_pref_1_3']:.2f} | {time.time() - t0:.2f}s",
        flush=True,
    )

    t0 = time.time()
    print("\n[4/4] Running red_queen_markov (Theorem 2 + VFI + Prop 5, max_rounds=28)...", flush=True)
    rq_res = run_red_queen_markov(parallel=parallel)
    print(
        f"  -> Theorem 2 shift error={rq_res['vfi']['theorem2_check']['max_bellman_shift_error']:.2e} | "
        f"Certified {len(rq_res['certification']['certificates'])} RQ grids | "
        f"tau_u_max(g_H)={rq_res['certification']['tau_u_max_certified_by_gH']} | {time.time() - t0:.2f}s",
        flush=True,
    )

    models_payload = {
        "mvs_canonical": existing_models["mvs_canonical"],
        "barro_Ae_atlas": existing_models["barro_Ae_atlas"],
        "political_markov": {
            "kind": "markov",
            "certificates": [_serialize_markov_cert(c) for c in pol_res["certification"]["certificates"]],
        },
        "red_queen_markov": {
            "kind": "markov",
            "certificates": [_serialize_markov_cert(c) for c in rq_res["certification"]["certificates"]],
        },
    }
    digest = save_certificate_archive(
        CERT_ARCHIVE_PATH,
        models_payload,
        metadata={"engine": "cegis-bellman", "version": "0.1.0"},
    )

    vfi_summary = {
        "mvs_canonical": {
            "T_cert": mvs_cert_rec["T_cert"],
            "T_ns": mvs_cert_rec.get("T_ns"),
            "margins": mvs_cert_rec["margins"],
            "vfi": mvs_vfi_dict,
        },
        "barro_u_frag": {
            "analytics": analytics,
            "policy_plane_summary": ps,
            "atlas_bands": [
                {
                    "bounds_1d": lf["bounds_1d"],
                    "depth": lf["depth"],
                    "T_cert": lf["cert"]["T_cert"],
                    "margins": lf["cert"]["margins"],
                }
                for lf in cached_atlas["certified_leaves"]
            ],
            "fragmentation_summary": ns,
            "fragmentation_bands": nf_cert["certified_bands"],
        },
        "political_markov": {
            "vfi": pol_res["vfi"],
            "certification_summary": pol_res["certification"]["summary_rows"],
            "max_certified_p_rev_at_pref_1_3": pol_res["certification"]["max_certified_p_rev_at_pref_1_3"],
        },
        "red_queen_markov": {
            "vfi": rq_res["vfi"],
            "certification_summary": rq_res["certification"]["summary_rows"],
            "tau_u_max_certified_by_gH": rq_res["certification"]["tau_u_max_certified_by_gH"],
        },
    }
    os.makedirs(os.path.dirname(VFI_RESULTS_PATH), exist_ok=True)
    with open(VFI_RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(vfi_summary, fh, indent=2)
    print(f"\nSaved archive: {CERT_ARCHIVE_PATH} ({os.path.getsize(CERT_ARCHIVE_PATH):,} bytes, sha256={digest[:16]}...)", flush=True)
    print(f"Saved VFI/summary JSON: {VFI_RESULTS_PATH} | Total refresh time: {time.time() - t_start:.2f}s", flush=True)


def run_audit() -> int:
    auditor = os.path.join(ROOT, "core", "audit_standalone.py")
    res = subprocess.run([sys.executable, "-u", auditor, CERT_ARCHIVE_PATH])
    return res.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="CEGIS-Bellman v0.1 verification orchestrator")
    ap.add_argument("--synthesize", action="store_true", help="Run full synthesis + VFI")
    ap.add_argument("--audit-only", action="store_true", help="Only run standalone auditor on existing archive")
    ap.add_argument("--full-audit", action="store_true", help="Run full synthesis + VFI + standalone audit")
    ap.add_argument("--refresh-markov-and-vfi", action="store_true", help="Refresh VFI, analytics, and Markov grids keeping cached static atlas")
    ap.add_argument("--no-parallel", action="store_true", help="Disable ProcessPoolExecutor parallelism")
    args = ap.parse_args()

    if not (args.synthesize or args.audit_only or args.full_audit or args.refresh_markov_and_vfi):
        args.full_audit = True

    if args.refresh_markov_and_vfi:
        refresh_markov_and_vfi(parallel=not args.no_parallel)
        return run_audit()
    if args.synthesize or args.full_audit:
        run_synthesis(parallel=not args.no_parallel)
    if args.audit_only or args.full_audit:
        return run_audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
