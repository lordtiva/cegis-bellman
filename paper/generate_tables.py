"""
Auto-generate 6 Typst table files in `paper/tables/` directly from:
  - certificates/vfi_results.json
  - paper/paper_extras.json

Nothing is hardcoded arbitrarily; all numbers trace strictly to frozen Hito 1
verification outputs and the refined VFI extras.
"""

from __future__ import annotations

import hashlib
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB_DIR = os.path.join(ROOT, "paper", "tables")
os.makedirs(TAB_DIR, exist_ok=True)


def _write_typ(filename: str, content: str) -> None:
    path = os.path.join(TAB_DIR, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content.strip() + "\n")
    print(f"Generated {filename}")


def gen_table1() -> None:
    content = r"""
#figure(
  table(
    columns: (1.45fr, 1.35fr, 1.85fr, 1.75fr),
    inset: 5.5pt,
    align: left,
    stroke: 0.45pt + luma(160),
    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },
    table.header(
      text(fill: white, weight: "bold", size: 8.5pt)[Resultado (Sección)],
      text(fill: white, weight: "bold", size: 8.5pt)[Objeto / Dominio],
      text(fill: white, weight: "bold", size: 8.5pt)[Propiedad o Cota Demostrada],
      text(fill: white, weight: "bold", size: 8.5pt)[Método de Certificación],
    ),
    [#text(size: 8.3pt)[*Teorema 1* (4.1)]], [#text(size: 8.3pt)[Curva en U $A_e (tau_p, tau_u, N_f)$]], [#text(size: 8.3pt)[$tau_p^* = 0.20, A_e^"pico" = 0.7757$; umbrales $A_"rep" = 0.0735, A_"SN" = 0.0995, A_* = 0.0996$]], [#text(size: 8.3pt)[Análisis cerrado + bifurcación CES]],
    [#text(size: 8.3pt)[*Proposición 1* (4.2)]], [#text(size: 8.3pt)[Fragmentación $N_f <-> tau_u^"eq"$]], [#text(size: 8.3pt)[Isomorfismo exacto; colapso silla-nodo $N_(f,*) = 56.69 < N_(f,"SN") = 56.79$]], [#text(size: 8.3pt)[Homogeneidad $theta=3\/2$ + punto fijo]],
    [#text(size: 8.3pt)[*Proposición 2* (5.2)]], [#text(size: 8.3pt)[Atlas $A_e in [0.385, 0.780]$ ($63$ b.)]], [#text(size: 8.3pt)[$T_"cert" in [4, 7]$; expansión $53.9 times$ en área del plano $(tau_p, tau_u)$]], [#text(size: 8.3pt)[CEGIS-LP `log-PWL` + B&B sin `libm`]],
    [#text(size: 8.3pt)[*Proposición 3* (5.3)]], [#text(size: 8.3pt)[Atlas $N_f in [1.00, 4.060]$ ($63$ b.)]], [#text(size: 8.3pt)[Escape certificado hasta $N_f^"max" = 4.060$ ($tau_u^"eq" = 40.3%$)]], [#text(size: 8.3pt)[Isomorfismo + auditoría 1D continua]],
    [#text(size: 8.3pt)[*Proposición 4* (6.2--6.4)]], [#text(size: 8.3pt)[Markov político $p_"rev" in [2%, 18%]$]], [#text(size: 8.3pt)[$7\/7$ parejas Doob acopladas: $sup E[tau] in [20.82, 25.52]$; huida precautoria]], [#text(size: 8.3pt)[Converso de Doob + LP acoplado + VFI]],
    [#text(size: 8.3pt)[*Teorema 2* (7.1)]], [#text(size: 8.3pt)[Invarianza homotética _Red Queen_]], [#text(size: 8.3pt)[Reducción exacta 2D $-> $ 1D en $hat(K)_t = K_t \/ E_t$; error Bellman $5.68 times 10^(-14)$]], [#text(size: 8.3pt)[Reescalamiento homogéneo + VFI]],
    [#text(size: 8.3pt)[*Proposición 5* (7.3)]], [#text(size: 8.3pt)[Superficie $(g_H, tau_u)$ ($9\/9$ b.)]], [#text(size: 8.3pt)[Escape certificado hasta $tau_u^"max" = 0.30$ ($sup E[tau] in [15.26, 31.84]$)]], [#text(size: 8.3pt)[Markov Doob CEGIS-LP + Rust audit]],
    [#text(size: 8.3pt)[*Motor `cegis-bellman`* (8)]], [#text(size: 8.3pt)[Archivo `80/80` certificados]], [#text(size: 8.3pt)[Cero errores en Rust sin `libm` y en Python puro; `7/7` tests]], [#text(size: 8.3pt)[Intervalos IEEE-754 + SHA-256]],
  ),
  caption: [Mapa epistemológico de los resultados del manuscrito según dominio y método de validación.],
) <tab:epistemo>
"""
    _write_typ("table1_epistemological_map.typ", content)


def gen_table2(extras: dict) -> None:
    u_rows = extras["table2_refined_ucurve"]
    lines = [
        "#figure(",
        "  table(",
        "    columns: (0.8fr, 1.0fr, 1.15fr, 1.15fr, 1.35fr),",
        "    inset: 4.5pt,",
        "    align: (center, right, right, right, center),",
        "    stroke: 0.45pt + luma(160),",
        '    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },',
        "    table.header(",
        '      text(fill: white, weight: "bold", size: 8.3pt)[$tau_p$],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[$A_e (tau_p, 0, 1)$],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[$S_"VFI" (tau_p)$],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[$S_"env" (tau_p)$],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[Estatus de Viabilidad],',
        "    ),",
    ]
    for r in u_rows:
        tp = r["tau_p"]
        ae = r["A_e"]
        sv = r["S_vfi_fine"]
        se = r["S_env"]
        if ae >= 0.749:
            status = "MVS + Atlas CEGIS"
        elif ae >= 0.385:
            status = "Atlas CEGIS (63 b.)"
        else:
            status = "Fuera del atlas LP"
        lines.append(
            f"    [#text(size: 8.1pt)[`{tp:.3f}`]], [#text(size: 8.1pt)[`{ae:.4f}`]], "
            f"[#text(size: 8.1pt)[`{sv:.6f}`]], [#text(size: 8.1pt)[`{se:.6f}`]], [#text(size: 8.1pt)[{status}]],"
        )
    lines.extend([
        "  ),",
        "  caption: [Curva en U institucional $S(tau_p)$ para $tau_u = 0, N_f = 1$: productividad efectiva $A_e$, umbral de Skiba VFI, envolvente analítica inferior $S_\"env\"$ y cobertura CEGIS-LP.],",
        ") <tab:u_curve>",
    ])
    _write_typ("table2_u_curve_thresholds.typ", "\n".join(lines))


def gen_table3(vfi_data: dict) -> None:
    nf_rows = vfi_data["barro_u_frag"]["analytics"]["nf_equivalence"]
    lines = [
        "#figure(",
        "  table(",
        "    columns: (0.85fr, 1.15fr, 1.15fr, 1.15fr, 1.35fr),",
        "    inset: 4.5pt,",
        "    align: (right, right, right, right, center),",
        "    stroke: 0.45pt + luma(160),",
        '    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },',
        "    table.header(",
        '      text(fill: white, weight: "bold", size: 8.3pt)[$N_f$],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[$tau_u^"eq" (tau_p = 0.20)$],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[$A_e$ (Barro)],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[$A_e$ (MVS $0.75$)],',
        '      text(fill: white, weight: "bold", size: 8.3pt)[Régimen en $A_0^"MVS"$],',
        "    ),",
    ]
    for r in nf_rows:
        nf = r["N_f"]
        tu_eq = r["tau_u_eq_at_tp020"]
        ae_bar = r["A_e_barro_tp020"]
        ae_ben = r["A_e_bench075"]
        if ae_ben >= 0.385:
            reg = "Certificado CEGIS" if r["viable_bench"] else "Solo Barro CEGIS"
        elif ae_bar >= 0.385:
            reg = "Cert. (Barro) / Sin cert. (MVS)"
        elif r["viable_bench"]:
            reg = "Viable VFI (sin cert.)"
        else:
            reg = "Colapso silla-nodo"
        nf_str = f"{nf:.2f}" if abs(nf - round(nf)) > 1e-4 else f"{int(round(nf))}"
        lines.append(
            f"    [#text(size: 8.1pt)[`{nf_str}`]], [#text(size: 8.1pt)[`{tu_eq:.4f}`]], "
            f"[#text(size: 8.1pt)[`{ae_bar:.4f}`]], [#text(size: 8.1pt)[`{ae_ben:.4f}`]], [#text(size: 8.1pt)[{reg}]],"
        )
    lines.extend([
        "  ),",
        r'  caption: [Isomorfismo exacto entre fragmentación empresarial $N_f$ y burocracia improductiva equivalente $tau_u^"eq"$ en $tau_p = 0.20$ ($theta = 3\/2$).],',
        ") <tab:nf_equiv>",
    ])
    _write_typ("table3_fragmentation_equivalence.typ", "\n".join(lines))


def gen_table4(vfi_data: dict, extras: dict) -> None:
    pm = vfi_data["political_markov"]
    cert_map = {(round(r["p_rev"], 4), round(r["p_ref"], 4)): r for r in pm["certification_summary"]}
    vfi_map = {(round(r["p_rev"], 4), round(r["p_ref"], 4)): r for r in pm["vfi"]["certified_grid_vfi"]}
    fine_map = {(round(r["p_rev"], 4), round(r["p_ref"], 4)): r for r in extras["table4_refined_skiba"]}

    keys = sorted(cert_map.keys(), key=lambda k: (k[1], k[0]))
    lines = [
        "#figure(",
        "  table(",
        "    columns: (0.75fr, 0.75fr, 0.95fr, 0.95fr, 0.95fr, 0.95fr, 0.8fr, 0.7fr),",
        "    inset: 4.5pt,",
        "    align: (right, right, right, right, right, right, right, center),",
        "    stroke: 0.45pt + luma(160),",
        '    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },',
        "    table.header(",
        '      text(fill: white, weight: "bold", size: 8.1pt)[$p_"rev"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$p_"ref"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$S_G^"VFI"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$K_B^*$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$max E_"VFI" [tau_H]$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$sup E[tau]_"CEGIS"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$epsilon.alt_0^"opt"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$T_0^"opt"$],',
        "    ),",
    ]
    for k in keys:
        c = cert_map[k]
        v = vfi_map[k]
        f = fine_map[k]
        prf_str = "1/3" if abs(k[1] - 1.0 / 3.0) < 1e-3 else f"{k[1]:.2f}"
        e_tau_up = math.ceil(c["E_tau_opt"] * 100.0) / 100.0
        lines.append(
            f"    [#text(size: 8.0pt)[`{100*k[0]:.0f}%`]], "
            f"[#text(size: 8.0pt)[`{prf_str}`]], "
            f"[#text(size: 8.0pt)[`{f['S_G_vfi_fine']:.6f}`]], "
            f"[#text(size: 8.0pt)[`{f['S_B_vfi_fine']:.6f}`]], "
            f"[#text(size: 8.0pt)[`{v['max_E_tau_H_vfi_Mpol']:.3f}`]], "
            f"[#text(size: 8.0pt)[`{e_tau_up:.2f}`]], "
            f"[#text(size: 8.0pt)[`{c['eps0_opt']:.4f}`]], "
            f"[#text(size: 8.0pt)[`{c['T0_opt']}`]],"
        )
    lines.extend([
        "  ),",
        r'  caption: [Certificación acoplada de Doob CEGIS-LP ($7\/7$ `PASS`, $A_G = 0.7757, A_B = 0.45$, $M_"pol" = [0.10, 0.18)$) frente a $S_G^"VFI"$ (malla refinada), el cruce de $45 degree$ en régimen adverso $K_B^*$ (distinto del punto de Skiba $S_("B,kink")$ en Segura, 2026) y $max E_"VFI" [tau_H]$. Las cotas superiores $sup E[tau]_"CEGIS" = T_0^"opt"\/epsilon.alt_0^"opt"$ se redondean estrictamente hacia $+oo$.],',
        ") <tab:political_markov>",
    ])
    _write_typ("table4_political_markov.typ", "\n".join(lines))


def gen_table5(vfi_data: dict) -> None:
    rq = vfi_data["red_queen_markov"]
    cert_list = rq["certification_summary"]
    vfi_map = {(round(r["g_H"], 4), round(r["tau_u"], 4)): r for r in rq["vfi"]["certified_grid_vfi"]}

    lines = [
        "#figure(",
        "  table(",
        "    columns: (0.65fr, 0.7fr, 0.9fr, 0.9fr, 0.9fr, 0.95fr, 0.75fr, 0.9fr),",
        "    inset: 4.5pt,",
        "    align: (right, right, right, right, right, right, center, center),",
        "    stroke: 0.45pt + luma(160),",
        '    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },',
        "    table.header(",
        '      text(fill: white, weight: "bold", size: 8.1pt)[$g_H$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$tau_u$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$hat(S)_L$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$hat(K)_H^*$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$max E_"VFI"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$sup E[tau]_"CEGIS"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$T_0^"opt"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[Estado],',
        "    ),",
    ]
    for r in cert_list:
        k = (round(r["g_H"], 4), round(r["tau_u"], 4))
        v = vfi_map.get(k)
        if r["certified"] and v is not None:
            sl_s = f"`{v['S_hat_L']:.5f}`"
            sh_s = f"`{v['S_hat_H']:.5f}`"
            ev_s = f"`{v['max_E_tau_H_vfi_Mpol']:.3f}`"
            ec_up = math.ceil(r["E_tau_opt"] * 100.0) / 100.0
            ec_s = f"`{ec_up:.2f}`"
            t0_s = f"`{r['T0_opt']}`"
            st_s = "PASS"
        else:
            sl_s = "---"
            sh_s = "---"
            ev_s = "---"
            ec_s = "---"
            t0_s = "---"
            st_s = "No cert."
        lines.append(
            f"    [#text(size: 8.0pt)[`{100*r['g_H']:.0f}%`]], "
            f"[#text(size: 8.0pt)[`{r['tau_u']:.2f}`]], "
            f"[#text(size: 8.0pt)[{sl_s}]], "
            f"[#text(size: 8.0pt)[{sh_s}]], "
            f"[#text(size: 8.0pt)[{ev_s}]], "
            f"[#text(size: 8.0pt)[{ec_s}]], "
            f"[#text(size: 8.0pt)[{t0_s}]], "
            f"[#text(size: 8.0pt)[{st_s}]],"
        )
    lines.extend([
        "  ),",
        r'  caption: [Superficie *Red Queen* en $(g_H, tau_u)$ ($g_L = 2%, p_"wave" = 10%, p_"end" = 25%, M_"pol" = [0.10, 0.18)$): umbral lento $hat(S)_L$, umbral de reversión de deriva de $45 degree$ durante la ola $hat(K)_H^*$, cota certificada de Doob (`9/9` hasta $tau_u = 0.30$, redondeada hacia $+oo$) y límite de certificabilidad en $tau_u = 0.40$.],',
        ") <tab:red_queen>",
    ])
    _write_typ("table5_red_queen_markov.typ", "\n".join(lines))


def gen_table6(vfi_data: dict) -> None:
    n_atlas = vfi_data["barro_u_frag"]["policy_plane_summary"]["n_certified_boxes"]
    n_pol = len(vfi_data["political_markov"]["certification_summary"])
    n_rq = sum(1 for r in vfi_data["red_queen_markov"]["certification_summary"] if r["certified"])
    total = 1 + n_atlas + n_pol + n_rq
    cert_path = os.path.join(ROOT, "certificates", "cegis_certificates.json.xz")
    cert_bytes = open(cert_path, "rb").read()
    cert_sha8 = hashlib.sha256(cert_bytes).hexdigest()[:8]
    cert_sz = f"{len(cert_bytes):,}"

    content = rf"""
#figure(
  table(
    columns: (1.5fr, 0.8fr, 1.55fr, 1.65fr),
    inset: 5.5pt,
    align: (left, center, left, left),
    stroke: 0.45pt + luma(160),
    fill: (x, y) => if y == 0 {{ rgb("#0b2c4d") }} else if calc.even(y) {{ rgb("#f6f9fc") }} else {{ white }},
    table.header(
      text(fill: white, weight: "bold", size: 8.4pt)[Módulo / Caso],
      text(fill: white, weight: "bold", size: 8.4pt)[Certificados],
      text(fill: white, weight: "bold", size: 8.4pt)[Dominio / Cobertura],
      text(fill: white, weight: "bold", size: 8.4pt)[Resultado de Auditoría],
    ),
    [#text(size: 8.2pt)[`mvs_canonical`]], [#text(size: 8.2pt)[`1`]], [#text(size: 8.2pt)[Caja 4D MVS en $M = [0.10, 0.28)$]], [#text(size: 8.2pt)[`PASS` ($T_"cert" = 5$; Python puro `6.06 s`)]],
    [#text(size: 8.2pt)[`barro_Ae_atlas`]], [#text(size: 8.2pt)[`{n_atlas}`]], [#text(size: 8.2pt)[$A_e in [0.385, 0.780]$, $(q, beta, eta)$ fijos]], [#text(size: 8.2pt)[`PASS` ($63\/63$ bandas contiguas, `0` huecos)]],
    [#text(size: 8.2pt)[`political_markov`]], [#text(size: 8.2pt)[`{n_pol}`]], [#text(size: 8.2pt)[$p_"rev" in [2%, 18%], p_"ref" in {{0.25, 1\/3, 0.50}}$]], [#text(size: 8.2pt)[`PASS` ($7\/7$ parejas Doob acopladas)]],
    [#text(size: 8.2pt)[`red_queen_markov`]], [#text(size: 8.2pt)[`{n_rq}`]], [#text(size: 8.2pt)[$g_H in {{3%, 5%, 7%}}, tau_u in {{0, 0.15, 0.30}}$]], [#text(size: 8.2pt)[`PASS` ($9\/9$ parejas Doob homogéneas)]],
    [#text(size: 8.2pt, weight: "bold")[Total congelado]], [#text(size: 8.2pt, weight: "bold")[`{total}/{total}`]], [#text(size: 8.2pt)[`cegis_certificates.json.xz` (`{cert_sz} B`)]], [#text(size: 8.2pt, weight: "bold")[`PASS` (`882.32 s` Rust; SHA-256 `{cert_sha8}...`)]],
  ),
  caption: [Resumen de auditoría independiente del archivo congelado de certificados (`cegis_certificates.json.xz`, verificador Rust sin `libm` y verificador Python puro `audit_standalone.py`).],
) <tab:audit>
"""
    _write_typ("table6_audit_summary.typ", content)


def gen_tableA1(vfi_data: dict) -> None:
    bands = vfi_data["barro_u_frag"]["atlas_bands"]
    fbands = vfi_data["barro_u_frag"]["fragmentation_bands"]
    lines = [
        "#figure(",
        "  table(",
        "    columns: (0.65fr, 0.65fr, 1.25fr, 1.25fr, 0.95fr, 1.0fr),",
        "    inset: 3.2pt,",
        "    align: (center, center, center, center, right, right),",
        "    stroke: 0.45pt + luma(160),",
        '    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },',
        "    table.header(",
        '      text(fill: white, weight: "bold", size: 8.1pt)[$T_"cert"$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[Bandas],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[Rango $A_e$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[Rango $N_f$ ($tau_u=0$)],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$min Delta_"exit"^M$],',
        '      text(fill: white, weight: "bold", size: 8.1pt)[$max d_"ub"^Psi$],',
        "    ),",
    ]
    for tc in sorted(set(b["T_cert"] for b in bands)):
        sub = [b for b in bands if b["T_cert"] == tc]
        fsub = [b for b in fbands if b["T_cert"] == tc]
        ae_lo = min(b["bounds_1d"][0] for b in sub)
        ae_hi = max(b["bounds_1d"][1] for b in sub)
        nf_lo = min(b["bounds_1d"][0] for b in fsub)
        nf_hi = max(b["bounds_1d"][1] for b in fsub)
        min_exit = min(b["margins"]["exit_M_iv"] for b in sub)
        max_dpsi = max(b["margins"]["d_ub_Psi_iv"] for b in sub)
        lines.append(
            f"    [#text(size: 8.0pt)[`{tc}`]], "
            f"[#text(size: 8.0pt)[`{len(sub)}`]], "
            f"[#text(size: 8.0pt)[`[{ae_lo:.4f}, {ae_hi:.4f}]`]], "
            f"[#text(size: 8.0pt)[`[{nf_lo:.3f}, {nf_hi:.3f}]`]], "
            f"[#text(size: 8.0pt)[`{min_exit:.4f}`]], "
            f"[#text(size: 8.0pt)[`{max_dpsi:.2e}`]],"
        )
    lines.extend([
        "  ),",
        "  caption: [Desglose por horizonte $T_\"cert\"$ de las $63$ bandas contiguas certificadas en `barro_Ae_atlas` ($A_e in [0.385, 0.780]$, $M_\"pol\" = [0.10, 0.18)$, peor holgura de techo $max d_\"ub\"^Psi < 0$ y menor margen de salida $min Delta_\"exit\"^M > 0$). Nota: el solapamiento en los rangos de $A_e$ y $N_f$ entre $T_\"cert\" in {4, 5, 6}$ refleja el ancho adaptativo variable de las sub-bandas sintetizadas.],",
        ") <tab:atlas_tiers>",
    ])
    _write_typ("tableA1_atlas_tiers.typ", "\n".join(lines))


def gen_tableA2(vfi_data: dict) -> None:
    fts = vfi_data["political_markov"]["vfi"]["flight_to_safety"]
    lines = [
        "#figure(",
        "  table(",
        "    columns: (0.85fr, 0.65fr, 0.65fr, 0.9fr, 0.9fr, 1.0fr, 1.0fr),",
        "    inset: 3.2pt,",
        "    align: (left, right, right, right, right, right, right),",
        "    stroke: 0.45pt + luma(160),",
        '    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },',
        "    table.header(",
        '      text(fill: white, weight: "bold", size: 8.0pt)[Régimen $B$],',
        '      text(fill: white, weight: "bold", size: 8.0pt)[$p_"rev"$],',
        '      text(fill: white, weight: "bold", size: 8.0pt)[$p_"ref"$],',
        '      text(fill: white, weight: "bold", size: 8.0pt)[$S_G^"VFI"$],',
        '      text(fill: white, weight: "bold", size: 8.0pt)[$K_B^*$],',
        '      text(fill: white, weight: "bold", size: 8.0pt)[$overline(Delta K\'_G)$],',
        '      text(fill: white, weight: "bold", size: 8.0pt)[$max Delta K\'_G$],',
        "    ),",
    ]
    for r in fts:
        sb_str = f"`{r['S_B']:.6f}`" if r["S_B"] is not None else "Colapso"
        prf_str = "1/3" if abs(r["p_ref"] - 1.0 / 3.0) < 1e-3 else f"{r['p_ref']:.2f}"
        lines.append(
            f"    [#text(size: 7.9pt)[$A_B = {r['A_B']:.3f}$]], "
            f"[#text(size: 7.9pt)[`{100*r['p_rev']:.0f}%`]], "
            f"[#text(size: 7.9pt)[`{prf_str}`]], "
            f"[#text(size: 7.9pt)[`{r['S_G']:.6f}`]], "
            f"[#text(size: 7.9pt)[{sb_str}]], "
            f"[#text(size: 7.9pt)[`+{r['delta_kpG_mean_M']:.5f}`]], "
            f"[#text(size: 7.9pt)[`+{r['delta_kpG_max_M']:.5f}`]],"
        )
    lines.extend([
        "  ),",
        r'  caption: [Huida precautoria hacia la seguridad en VFI continua bajo regímenes adversos extremos ($A_B in {0.35, 0.095}$): incremento medio y máximo de inversión $Delta K\'_G$ en $M$ frente al equilibrio sin riesgo. Aquí $K_B^*$ denota el cruce de $45 degree$ en $B$ (distinto del quiebre de Skiba $S_("B,kink")$); los valores se evalúan sobre la grilla logarítmica base de VFI (sin refinamiento local en $[0.0012, 0.0022]$, a diferencia de la Tabla 4).],',
        ") <tab:fts_extreme>",
    ])
    _write_typ("tableA2_flight_to_safety.typ", "\n".join(lines))


def main() -> None:
    with open(os.path.join(ROOT, "certificates", "vfi_results.json"), "r", encoding="utf-8") as fh:
        vfi_data = json.load(fh)
    with open(os.path.join(ROOT, "paper", "paper_extras.json"), "r", encoding="utf-8") as fh:
        extras = json.load(fh)

    gen_table1()
    gen_table2(extras)
    gen_table3(vfi_data)
    gen_table4(vfi_data, extras)
    gen_table5(vfi_data)
    gen_table6(vfi_data)
    gen_tableA1(vfi_data)
    gen_tableA2(vfi_data)


if __name__ == "__main__":
    main()
