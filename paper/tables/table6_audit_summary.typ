#figure(
  table(
    columns: (1.5fr, 0.8fr, 1.55fr, 1.65fr),
    inset: 5.5pt,
    align: (left, center, left, left),
    stroke: 0.45pt + luma(160),
    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },
    table.header(
      text(fill: white, weight: "bold", size: 8.4pt)[Módulo / Caso],
      text(fill: white, weight: "bold", size: 8.4pt)[Certificados],
      text(fill: white, weight: "bold", size: 8.4pt)[Dominio / Cobertura],
      text(fill: white, weight: "bold", size: 8.4pt)[Resultado de Auditoría],
    ),
    [#text(size: 8.2pt)[`mvs_canonical`]], [#text(size: 8.2pt)[`1`]], [#text(size: 8.2pt)[Caja 4D MVS en $M = [0.10, 0.28)$]], [#text(size: 8.2pt)[`PASS` ($T_"cert" = 5$; Python puro `6.06 s`)]],
    [#text(size: 8.2pt)[`barro_Ae_atlas`]], [#text(size: 8.2pt)[`63`]], [#text(size: 8.2pt)[$A_e in [0.385, 0.780]$, $(q, beta, eta)$ fijos]], [#text(size: 8.2pt)[`PASS` ($63\/63$ bandas contiguas, `0` huecos)]],
    [#text(size: 8.2pt)[`political_markov`]], [#text(size: 8.2pt)[`7`]], [#text(size: 8.2pt)[$p_"rev" in [2%, 18%], p_"ref" in {0.25, 1\/3, 0.50}$]], [#text(size: 8.2pt)[`PASS` ($7\/7$ parejas Doob acopladas)]],
    [#text(size: 8.2pt)[`red_queen_markov`]], [#text(size: 8.2pt)[`9`]], [#text(size: 8.2pt)[$g_H in {3%, 5%, 7%}, tau_u in {0, 0.15, 0.30}$]], [#text(size: 8.2pt)[`PASS` ($9\/9$ parejas Doob homogéneas)]],
    [#text(size: 8.2pt, weight: "bold")[Total congelado]], [#text(size: 8.2pt, weight: "bold")[`80/80`]], [#text(size: 8.2pt)[`cegis_certificates.json.xz` (`376,368 B`)]], [#text(size: 8.2pt, weight: "bold")[`PASS` (`882.32 s` Rust; SHA-256 `a2f9707b...`)]],
  ),
  caption: [Resumen de auditoría independiente del archivo congelado de certificados (`cegis_certificates.json.xz`, verificador Rust sin `libm` y verificador Python puro `audit_standalone.py`).],
) <tab:audit>
