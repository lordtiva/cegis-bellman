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
