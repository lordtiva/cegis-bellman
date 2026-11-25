#figure(
  table(
    columns: (0.65fr, 0.65fr, 1.25fr, 1.25fr, 0.95fr, 1.0fr),
    inset: 3.2pt,
    align: (center, center, center, center, right, right),
    stroke: 0.45pt + luma(160),
    fill: (x, y) => if y == 0 { rgb("#0b2c4d") } else if calc.even(y) { rgb("#f6f9fc") } else { white },
    table.header(
      text(fill: white, weight: "bold", size: 8.1pt)[$T_"cert"$],
      text(fill: white, weight: "bold", size: 8.1pt)[Bandas],
      text(fill: white, weight: "bold", size: 8.1pt)[Rango $A_e$],
      text(fill: white, weight: "bold", size: 8.1pt)[Rango $N_f$ ($tau_u=0$)],
      text(fill: white, weight: "bold", size: 8.1pt)[$min Delta_"exit"^M$],
      text(fill: white, weight: "bold", size: 8.1pt)[$max d_"ub"^Psi$],
    ),
    [#text(size: 8.0pt)[`4`]], [#text(size: 8.0pt)[`24`]], [#text(size: 8.0pt)[`[0.5500, 0.7800]`]], [#text(size: 8.0pt)[`[1.000, 1.989]`]], [#text(size: 8.0pt)[`0.2134`]], [#text(size: 8.0pt)[`-1.48e-05`]],
    [#text(size: 8.0pt)[`5`]], [#text(size: 8.0pt)[`21`]], [#text(size: 8.0pt)[`[0.4430, 0.6150]`]], [#text(size: 8.0pt)[`[1.591, 3.066]`]], [#text(size: 8.0pt)[`0.2038`]], [#text(size: 8.0pt)[`-3.00e-06`]],
    [#text(size: 8.0pt)[`6`]], [#text(size: 8.0pt)[`15`]], [#text(size: 8.0pt)[`[0.3970, 0.4730]`]], [#text(size: 8.0pt)[`[2.690, 3.818]`]], [#text(size: 8.0pt)[`0.2103`]], [#text(size: 8.0pt)[`-1.36e-05`]],
    [#text(size: 8.0pt)[`7`]], [#text(size: 8.0pt)[`3`]], [#text(size: 8.0pt)[`[0.3850, 0.3970]`]], [#text(size: 8.0pt)[`[3.818, 4.060]`]], [#text(size: 8.0pt)[`0.1837`]], [#text(size: 8.0pt)[`-7.40e-06`]],
  ),
  caption: [Desglose por horizonte $T_"cert"$ de las $63$ bandas contiguas certificadas en `barro_Ae_atlas` ($A_e in [0.385, 0.780]$, $M_"pol" = [0.10, 0.18)$, peor holgura de techo $max d_"ub"^Psi < 0$ y menor margen de salida $min Delta_"exit"^M > 0$). Nota: el solapamiento en los rangos de $A_e$ y $N_f$ entre $T_"cert" in {4, 5, 6}$ refleja el ancho adaptativo variable de las sub-bandas sintetizadas.],
) <tab:atlas_tiers>
