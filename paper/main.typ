// ============================================================================
// Manuscrito Principal (Typst):
// La Curva en U Institucional, Volatilidad Política y Dinámica «Red Queen»:
// Supervivencia Económica Certificada bajo Rendimientos Crecientes
// ============================================================================

#set document(
  title: "La Curva en U Institucional, Volatilidad Política y Dinámica Red Queen: Supervivencia Económica Certificada bajo Rendimientos Crecientes",
  author: "Marcelo Segura",
)

#set page(
  paper: "a4",
  margin: (top: 2.2cm, bottom: 2.3cm, left: 2.1cm, right: 2.1cm),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 8.2pt, fill: luma(110))
      #grid(
        columns: (1fr, auto),
        [La Curva en U Institucional, Volatilidad Política y Dinámica «Red Queen»],
        [Barreras de Bellman CEGIS-LP],
      )
      #v(-0.4em)
      #line(length: 100%, stroke: 0.35pt + luma(195))
    ]
  },
  footer: context {
    set text(size: 8.5pt, fill: luma(110))
    align(center)[— #counter(page).display() —]
  },
)

#set text(
  font: ("Linux Libertine", "Libertinus Serif", "Georgia", "DejaVu Serif"),
  size: 10.2pt,
  lang: "es",
  hyphenate: true,
)

#set par(
  justify: true,
  leading: 0.65em,
  spacing: 0.88em,
)

#set math.equation(numbering: "(1)")
#show ref: it => {
  let el = it.element
  if el != none and el.func() == math.equation {
    link(el.location(), numbering(el.numbering, ..counter(math.equation).at(el.location())))
  } else {
    it
  }
}
#set heading(numbering: "1.1.")

#show heading.where(level: 1): it => block(
  above: 1.55em,
  below: 0.72em,
  breakable: false,
  [
    #text(size: 13.0pt, weight: "bold", fill: rgb("#0b2c4d"))[#it]
    #v(-0.5em)
    #line(length: 100%, stroke: 0.7pt + rgb("#0b2c4d"))
  ],
)

#show heading.where(level: 2): it => block(
  above: 1.2em,
  below: 0.58em,
  breakable: false,
  text(size: 11.2pt, weight: "bold", fill: rgb("#1f4e78"))[#it],
)

#show heading.where(level: 3): it => block(
  above: 0.9em,
  below: 0.45em,
  breakable: false,
  text(size: 10.3pt, weight: "bold", fill: rgb("#2c3e50"))[#it],
)

#show figure.caption: it => block(
  width: 94%,
  text(size: 8.8pt, fill: luma(60))[#it],
)

// Cajas tipográficas con breakable: false para evitar cortes huérfanos entre páginas
#let thm_box(title, body) = block(
  width: 100%,
  breakable: false,
  inset: 9.5pt,
  radius: 3.5pt,
  fill: rgb("#f3f7fb"),
  stroke: (left: 3pt + rgb("#0b2c4d"), top: 0.4pt + luma(205), right: 0.4pt + luma(205), bottom: 0.4pt + luma(205)),
  [
    #text(weight: "bold", fill: rgb("#0b2c4d"))[#title.]
    #h(4pt)
    #body
  ],
)

#let cert_box(title, body) = block(
  width: 100%,
  breakable: false,
  inset: 9.5pt,
  radius: 3.5pt,
  fill: rgb("#f2faf5"),
  stroke: (left: 3pt + rgb("#1b7837"), top: 0.4pt + luma(205), right: 0.4pt + luma(205), bottom: 0.4pt + luma(205)),
  [
    #text(weight: "bold", fill: rgb("#1b7837"))[#title.]
    #h(4pt)
    #body
  ],
)

#let obs_box(title, body) = block(
  width: 100%,
  breakable: false,
  inset: 9.5pt,
  radius: 3.5pt,
  fill: rgb("#fffaf0"),
  stroke: (left: 3pt + rgb("#b45309"), top: 0.4pt + luma(205), right: 0.4pt + luma(205), bottom: 0.4pt + luma(205)),
  [
    #text(weight: "bold", fill: rgb("#b45309"))[#title.]
    #h(4pt)
    #body
  ],
)

#let alg_box(title, body) = block(
  width: 100%,
  breakable: false,
  inset: 9.5pt,
  radius: 3.5pt,
  fill: rgb("#f8fafc"),
  stroke: 0.6pt + rgb("#1f4e78"),
  [
    #text(weight: "bold", fill: rgb("#1f4e78"))[#title]
    #v(0.25em)
    #body
  ],
)

#let proof_block(body) = block(
  width: 100%,
  inset: (left: 6pt, right: 2pt, top: 2pt, bottom: 4pt),
  [
    _Demostración._ #body #h(1fr) #sym.square.stroked
  ],
)

// ============================================================================
// PORTADA Y RESUMEN
// ============================================================================

#align(center)[
  #v(0.4em)
  #text(size: 16.5pt, weight: "bold", fill: rgb("#0b2c4d"))[
    La Curva en U Institucional, Volatilidad Política y Dinámica «Red Queen»: Supervivencia Económica Certificada bajo Rendimientos Crecientes
  ]
  #v(0.45em)
  #text(size: 11.4pt, style: "italic", fill: rgb("#1f4e78"))[
    Gasto Público Productivo, Fragmentación Empresarial y Olas Tecnológicas mediante Barreras de Bellman CEGIS-LP
  ]
  #v(0.65em)
  #text(size: 10.6pt, weight: "bold")[Marcelo Segura]
  #v(0.2em)
  #text(size: 9.6pt, fill: luma(85))[Manuscrito Técnico Autónomo — Arquitectura `cegis-bellman` v0.1 ($d=1$)]
  #v(0.2em)
  #text(size: 9.0pt, fill: luma(105))[Noviembre de 2026 #h(6pt) · #h(6pt) #link("https://doi.org/10.5281/zenodo.24536780")[DOI: `10.5281/zenodo.24536780`] #h(6pt) · #h(6pt) Reproducibilidad Determinista y Verificación Libre de `libm`]
]

#v(0.75em)
#block(
  width: 100%,
  breakable: false,
  inset: 11pt,
  radius: 4pt,
  fill: rgb("#f9fafb"),
  stroke: 0.5pt + luma(200),
  [
    #text(weight: "bold", fill: rgb("#0b2c4d"))[Resumen.]
    ¿Por qué numerosas economías que ejecutan reformas fiscales parciales continúan atrapadas en equilibrios de bajo ingreso o divergen frente a aceleraciones tecnológicas globales? En este artículo unificamos tres distorsiones institucionales internas —déficit o exceso de gasto público productivo ($tau_p$), burocracia improductiva ($tau_u$) y fragmentación regulatoria del tamaño empresarial ($N_f$)— en un escalar exacto de productividad efectiva $A_e (tau_p, tau_u, N_f) = A_0 tau_p^alpha (1 - tau_p - tau_u) N_f^(-(theta - 1))$ bajo tecnología CES armónica con rendimientos crecientes ($theta = 3\/2$). Al acoplar esta tríada institucional con alternancia político-fiscal Markoviana y una frontera tecnológica exógena estocástica $E_(t+1) = (1 + g_omega) E_t$ (dinámica *Red Queen*), demostramos mediante reescalamiento homotético que el problema bidimensional colapsa exactamente a un proceso de decisión Markoviano unidimensional en unidades de eficiencia con parámetros dependientes del régimen $tilde(A)_omega = A_(e,omega)\/(1 + g_omega)$ y $tilde(q)_omega = q\/(1 + g_omega)$. Combinando teoría analítica cerrada con síntesis determinista *CEGIS-LP* (`log-PWL`), parada opcional de Doob y auditoría continua por intervalos libre de `libm` tomando como banco de pruebas la arquitectura *Minimum Viable Scale* de Milei y Reidel (2026), aportamos cuatro resultados principales: (i) derivamos la *Curva en U Institucional* del umbral crítico de Skiba ($tau_p^* = 0.20$, $A_e^"pico" = 0.7757$) y el isomorfismo exacto entre fragmentación de firmas y burocracia ($N_f = 4 <==> tau_u^"eq" = 0.40$; colapso silla-nodo en $N_(f,*) = 56.69 < N_(f,"SN") = 56.79$); (ii) multiplicamos por $53.9 times$ el área institucional certificada respecto del marco base mediante un atlas continuo de $63$ bandas sin huecos ($A_e in [0.385, 0.780]$, $N_f in [1.00, 4.060]$, $T_"cert" in [4, 7]$); (iii) certificamos $7\/7$ parejas acopladas de Doob bajo volatilidad política ($sup E[tau] in [20.82, 25.52]$) y descubrimos en VFI continua una *huida precautoria hacia la seguridad* (al subir el riesgo de reversión $p_"rev"$ de $2%$ a $18%$, $max E_"VFI" [tau_H]$ desciende de `3.483` a `3.444`); y (iv) verificamos numérica y formalmente la paradoja *Red Queen* pura sobre trayectorias contrafactuales, certificando $9\/9$ regímenes $(g_H, tau_u)$ hasta $tau_u^"max" = 0.30$ sobre un archivo congelado de `80/80` certificados auditados independientemente con Rust puro sin `libm` y verificación cruzada en Python puro sin dependencias externas.

    #v(0.35em)
    #text(weight: "bold", fill: rgb("#0b2c4d"))[Códigos JEL:] `O11` (Desarrollo macroeconómico), `O41` (Modelos agregados de crecimiento), `H21` (Eficiencia tributaria), `H54` (Infraestructura y gasto público), `L11` (Escala y estructura industrial), `C61` (Programación dinámica y optimización).

    #v(0.2em)
    #text(weight: "bold", fill: rgb("#0b2c4d"))[Palabras clave:] Curva en U institucional, fragmentación empresarial, dinámica Red Queen, puntos de Skiba, barreras de Bellman, CEGIS-LP, parada opcional de Doob, aritmética de intervalos.
  ],
)

// ============================================================================
// SECCIÓN 1: INTRODUCCIÓN Y MAPA EPISTEMOLÓGICO
// ============================================================================
= Introducción y Mapa Epistemológico

Una cuestión central en la macroeconomía del desarrollo consiste en explicar por qué las reformas fiscales o regulatorias incompletas suelen fracasar en detonar un crecimiento sostenido. Muchos países en desarrollo mejoran parcialmente su infraestructura pública o recortan una alícuota impositiva aislada, pero permanecen estancados en una cuenca de bajo ingreso o sufren reversiones periódicas que abortan la acumulación de capital antes de cruzar el umbral crítico de despegue. Desde las contribuciones seminales de Skiba (1978), Majumdar y Mitra (1982) y Dechert y Nishimura (1983), sabemos que en presencia de rendimientos crecientes a escala la función valor del planificador deja de ser globalmente cóncava y emerge un punto crítico de indiferencia (punto de Skiba): por debajo de ese umbral, la economía converge inexorablemente hacia la extinción productiva o una trampa de pobreza; por encima, escapa hacia un estado estacionario próspero.

Sin embargo, la literatura clásica de trampas de pobreza analiza mayoritariamente un entorno determinista con productividad total de los factores exógena y fija. En la práctica, la capacidad real de una economía para escapar de la trampa depende de la interacción simultánea de cuatro fuerzas económicas e institucionales:
1. *Infraestructura pública productiva frente a distorsión tributaria ($tau_p$):* siguiendo a Barro (1990), la provisión insuficiente de bienes públicos paraliza la productividad marginal del capital privado, mientras que una presión fiscal excesiva confisca el excedente necesario para ahorrar, induciendo una relación no monótona en forma de U sobre el capital mínimo viable.
2. *Burocracia improductiva y captura de rentas ($tau_u$):* el gasto corriente que no incrementa el producto ni la utilidad del hogar reduce la apropiabilidad neta del ingreso privado sin generar externalidades productivas compensatorias.
3. *Fragmentación regulatoria del tamaño empresarial ($N_f$):* las regulaciones laborales, crediticias y tributarias dependientes del tamaño (Restuccia y Rogerson, 2008; Hsieh y Klenow, 2009) obligan a atomizar la producción en múltiples establecimientos subóptimos, destruyendo las economías de escala agregadas de grado $theta > 1$.
4. *Volatilidad político-fiscal y dinámica «Red Queen»:* aun con buenas instituciones presentes, los agentes descuentan la probabilidad de reversión política hacia regímenes populistas o extractivos, al tiempo que la frontera tecnológica mundial $E_t$ avanza a tasa estocástica Markoviana $E_(t+1) = (1 + g_omega) E_t$. Como la Reina Roja de Carroll (Van Valen, 1973), una economía que acumula lentamente respecto de $E_t$ puede sobrevivir en un mundo estático pero caer en la trampa cuando estalla una ola tecnológica acelerada.

Para evitar que estos cuatro bloques operen como capítulos desconectados y dotar al análisis de garantías matemáticas rigurosas más allá de mallas discretas heurísticas o redes neuronales, construimos sobre el marco de *Barreras de Bellman de Primer Paso* (_First Passage Bellman Barriers_, FPBB) de Milei y Reidel (2026) —sobre su especificación *Minimum Viable Scale* (MVS)— y sobre la arquitectura de síntesis certificada *CEGIS-LP* y teorema converso estocástico de Doob establecida en Segura (2026). El puente metodológico unificador descansa en dos identidades algebraicas exactas establecidas en la Sección 3: primero, toda la tríada institucional interna colapsa sin aproximación en un único escalar de productividad efectiva:
$ A_e (tau_p, tau_u, N_f) = A_0 thin tau_p^alpha (1 - tau_p - tau_u) N_f^(-(theta - 1)), $ <eq:master_Ae>
y segundo, bajo crecimiento estocástico de la frontera tecnológica mundial $E_(t+1) = (1 + g_omega) E_t$, la dinámica en unidades de eficiencia $hat(K)_t = K_t \/ E_t$ colapsa exactamente a un *único proceso de decisión Markoviano unidimensional* con parámetros efectivos dependientes del régimen:
$ tilde(A)_omega = (A_e (tau_(p,omega), tau_(u,omega), N_(f,omega))) / (1 + g_omega), #h(18pt) tilde(q)_omega = q / (1 + g_omega). $ <eq:master_markov>

Con esta unificación exacta, el artículo responde una única pregunta económica cuantitativa: *bajo qué combinaciones de instituciones internas, riesgo de alternancia política y velocidad de la frontera tecnológica global es posible certificar en tiempo finito el escape desde la región vulnerable de desarrollo —y cuándo la economía queda condenada a la divergencia o extinción.*

== Cuatro Contribuciones Estructurales

El manuscrito articula cuatro aportes concretos en teoría económica, certificación continua y computación científica reproducible:

1. *Curva en U Institucional e Isomorfismo Burocracia--Fragmentación (Sección 4):* Caracterizamos analíticamente la dependencia en forma de U del umbral crítico de Skiba respecto de la alícuota de infraestructura $tau_p$ (*Teorema 1*), probando un único máximo productivo en $tau_p^* (tau_u) = gamma (1 - tau_u)$ ($tau_p^*(0) = 0.20$, $A_e^"pico" = 0.775739$) y acotando exactamente el repulsor físico ($A_"rep" = 0.073485$), la bifurcación silla-nodo ($A_"SN" = 0.099524$), el umbral global de Skiba/Maxwell ($A_* = 0.099611$) y el cruce numérico con la envolvente de producto medio ($A_"cross" = 0.110400$). Además, probamos un isomorfismo exacto entre fragmentación industrial y gasto burocrático improductivo: $tau_u^"eq" (N_f; tau_p) = (1 - tau_p)(1 - N_f^(-(theta - 1)))$ (*Proposición 1*). En $tau_p = 0.20$, fragmentar una empresa en $N_f = 4$ unidades equivale exactamente a una extracción burocrática del $40%$, mientras la existencia del equilibrio próspero colapsa en $N_(f,*) = 56.69 < N_(f,"SN") = 56.79$ (o $N_(f,*)^"pico" = 60.65 < N_(f,"SN")^"pico" = 60.75$ bajo el óptimo de Barro).

2. *Expansión $53.9 times$ del Espacio Institucional Certificado (Sección 5):* Mediante síntesis determinista *CEGIS-LP* sobre splines `log-PWL` y particionamiento adaptativo 1D verificado en aritmética de intervalos libre de `libm`, reemplazamos la diminuta isla de viabilidad original ($A_e >= 0.749$, $tau_p in [0.117245, 0.304799]$) por un atlas continuo de $63$ bandas contiguas sobre $A_e in [0.385, 0.780]$ fijando $(q, beta, eta) = (0.92, 0.97, 0.70)$ (*Proposición 2*). Ello amplía en un factor $53.93 times$ el área certificada del plano $(tau_p, tau_u)$ (de $0.003445$ a $0.18579$), extiende la banda viable hasta $tau_p in [0.00507, 0.71083]$ con burocracia tolerable hasta $tau_u^"max" = 0.4030$, y transfiere la certificación determinista a todo el corredor de fragmentación empresarial $N_f in [1.00, 4.060]$ con plazos $T_"cert" in [4, 7]$ (*Proposición 3*).

3. *Volatilidad Político-Fiscal y Huida Precautoria Certificada (Sección 6):* Modelamos la alternancia Markoviana entre un régimen reformista $G$ ($A_G = 0.775739$) y un régimen adverso $B$ ($A_B = 0.45$), certificando $7\/7$ parejas acopladas de barreras de permanencia de Doob (súper-soluciones restringidas de Bellman) en $M_"pol" = [0.10, 0.18)$ para $p_"rev" in [2%, 18%]$ y $p_"ref" in {0.25, 1\/3, 0.50}$ con tiempos esperados acotados $sup E[tau] in [20.82, 25.52]$ períodos (*Proposición 4*). En iteración continua de función valor (VFI) localmente refinada, demostramos la existencia de *huida precautoria hacia la seguridad*: al elevarse el riesgo de reversión $p_"rev"$ de $2%$ a $18%$ ($p_"ref" = 1\/3$), el máximo esperado VFI del tiempo de permanencia $max_(M_"pol" times Omega) E_"VFI" [tau_H]$ **desciende de `3.483` a `3.444` períodos** porque el planificador acelera preventivamente el ahorro para escapar de la zona vulnerable antes de sufrir un giro político adverso.

4. *Dinámica «Red Queen» Estocástica y Motor Modular `cegis-bellman` v0.1 (Secciones 7 y 8):* Demostramos el colapso homotético exacto hacia $hat(K)_t = K_t \/ E_t$ (*Teorema 2*, desplazamiento $phi = [21.3207, 23.1512]$ con error máximo de Bellman $5.68 times 10^(-14)$), ilustramos la paradoja *Red Queen* pura mediante simulaciones contrafactuales desde $hat(K)_0 = 0.034 in (hat(S)_L, hat(K)_H^*)$ para $tau_u = 0.55$, y certificamos $9\/9$ configuraciones $(g_H, tau_u)$ hasta $tau_u^"max" = 0.30$ con cotas de Doob entre $15.26$ y $31.84$ períodos (*Proposición 5*). Toda la arquitectura computacional se consolida en el paquete reutilizable `cegis-bellman` v0.1 ($d = 1$), respaldado por un archivo congelado de `80/80` certificados aprobados en Rust puro sin `libm` (`882.32 s`) y auditoría independiente Python puro.

== Mapa Epistemológico

Siguiendo la disciplina de rigor metodológico, la Tabla 1 delimita con exactitud qué afirmaciones se demuestran analíticamente en forma cerrada, cuáles se certifican sobre regiones continuas de parámetros y estados mediante CEGIS-LP e intervalos dirigidos, y cuáles se exploran numéricamente con VFI continua de alta resolución.

#include "tables/table1_epistemological_map.typ"

// ============================================================================
// SECCIÓN 2: LITERATURA RELACIONADA
// ============================================================================
= Literatura Relacionada

Nuestro trabajo converge tres corrientes habitualmente tratadas por separado en macroeconomía del crecimiento, finanzas públicas y verificación formal de sistemas dinámicos.

== Trampas de Pobreza, Rendimientos Crecientes y Puntos de Skiba

Desde los artículos clásicos de Skiba (1978), Majumdar y Mitra (1982) y Dechert y Nishimura (1983), es bien conocido que las tecnologías no cóncavas generan múltiples estados estacionarios separados por un umbral crítico o punto de indiferencia $S > 0$. Economías idénticas en tecnología y preferencias divergen según si su acervo inicial de capital $K_0$ se ubica por encima o por debajo de $S$. Trabajos posteriores rigurizaron las condiciones de existencia, continuidad y estática comparativa de estos umbrales (Kamihigashi y Roy, 2007; Akao, Kamihigashi y Nishimura, 2011; Akao et al., 2022) y clasificaron sus bifurcaciones globales heteroclinas (Wagener, 2003), mientras Kraay y McKenzie (2014) debatieron la relevancia empírica de las trampas de pobreza frente a episodios de crecimiento lento bajo restricciones institucionales.

A diferencia de la tradición centrada en teoremas asintóticos cualitativos o simulaciones de punto fijo en mallas finitas, Milei y Reidel (2026) propusieron certificar cotas explícitas de tiempo finito mediante *Barreras de Bellman de Primer Paso* sobre un modelo CES armónico con rendimientos crecientes ($theta = 3\/2$, $rho = -1$) y trabajo elástico. En Segura (2026) afilamos las cotas analíticas deterministas de ese banco de pruebas, construimos el sintetizador *CEGIS-LP* sobre bases `log-PWL` y demostramos un teorema converso estocástico de Doob acoplado a selección óptima. El presente artículo despliega dicha maquinaria sobre preguntas centrales de economía institucional y desarrollo: cómo el diseño fiscal, la estructura industrial, la credibilidad política y el progreso técnico exógeno moldean la geometría y la supervivencia sobre esos umbrales de Skiba.

== Gasto Productivo de Barro, Burocracia y Fragmentación Empresarial ($N_f$)

La modelización del gasto público productivo financiado con impuestos distorsivos proviene de Barro (1990), cuya curva en U invertida sobre la tasa de crecimiento ($g$ maximizada cuando la alícuota fiscal iguala la elasticidad del bien público) fue ampliada hacia la composición entre gasto productivo e improductivo por Futagami, Morita y Shibata (1993), Glomm y Ravikumar (1994) y Devarajan, Swaroop y Zou (1996). Nuestro primer aporte respecto de esta literatura es trasladar el dilema de Barro desde economías linealmente crecientes ($"AK"$) sin trampas hacia un entorno CES con rendimientos crecientes y umbral de Skiba: en nuestro modelo, el error fiscal no solo reduce la tasa de crecimiento de largo plazo, sino que eleva dramáticamente el umbral crítico $S(tau_p, tau_u)$ en forma de U hasta provocar bifurcaciones silla-nodo donde desaparece todo estado estacionario próspero.

En paralelo, la literatura sobre mala asignación de factores (*misallocation*) ha documentado empíricamente cómo las regulaciones dependientes del tamaño de firma restringen el crecimiento de las plantas eficientes y fragmentan el tejido productivo (Restuccia y Rogerson, 2008; Guner, Ventura y Xu, 2008; Hsieh y Klenow, 2009; Garicano, Lelarge y Van Reenen, 2016). Bajo rendimientos crecientes agregados ($theta = 3\/2$), mostramos que dividir el capital y el trabajo agregados entre $N_f$ fragmentos subóptimos contrae la productividad efectiva en $N_f^(-(theta - 1))$ y establece un isomorfismo exacto con el desperdicio fiscal burocrático $tau_u^"eq"$. Hasta donde alcanza nuestro conocimiento, la proyección continua de estas dos distorsiones sobre regiones certificadas CEGIS-LP sin huecos no había sido realizada previamente.

== Volatilidad Política, Dinámica «Red Queen» y Certificación CEGIS-LP

El impacto de la inestabilidad política y la probabilidad de reversión de reformas sobre la inversión privada fue destacado por Alesina y Tabellini (1991), Rodrik (1991) y Acemoglu (2005). En programación dinámica discreta, estos choques discretos corresponden a procesos de control Markovianos con salto de régimen (Kushner, 1967; Hernández-Lerma y Lasserre, 1996; Meyn y Tweedie, 2009). Mediante la VFI estocástica continua identificamos que la presencia de un régimen malo *recuperable* induce una *huida precautoria hacia la seguridad* —elevando temporalmente el esfuerzo de acumulación en el buen régimen para alcanzar zonas de capital inmunes—, fenómeno que convive con cotas constructivas uniformes obtenidas a través del teorema de parada opcional de Doob (Doob, 1953) y certificados de barrera estocástica (Prajna, Jadbabaie y Pappas, 2007).

Finalmente, el principio evolutivo *Red Queen* (Van Valen, 1973), formalizado en teoría del crecimiento multipaís y transferencia tecnológica por Howitt (2000) y Acemoglu (2009), sostiene que una economía rezagada debe acumular al menos al paso de la frontera tecnológica mundial para evitar la divergencia relativa. Demostramos que, bajo preferencias logarítmicas y homogeneidad CES, el crecimiento estocástico de la frontera colapsa exactamente en la ecuación reducida en unidades de eficiencia, posibilitando certificar el escape relativo mediante *CEGIS-LP* (Solar-Lezama, 2008; Ravanbakhsh y Sankaranarayanan, 2019; Abate et al., 2021) implementado con programación lineal dispersa HiGHS (Huangfu y Hall, 2018) y verificación por intervalos libre de `libm` (Moore, Kearfott y Cloud, 2009; Tucker, 2011).

// ============================================================================
// SECCIÓN 3: EL MODELO UNIFICADO
// ============================================================================
= El Modelo Unificado: Tríada Institucional y Frontera Tecnológica

Esta sección deduce la ecuación maestra que integra infraestructura, burocracia y fragmentación industrial dentro de un único escalar institucional $A_e$, y prueba el colapso exacto de la dinámica con olas tecnológicas globales hacia un proceso de decisión Markoviano unidimensional.

== Ecuación Maestra Institucional: Barro--CES con $N_f$

Consideremos una economía en tiempo discreto $t in {0, 1, 2, dots}$ habitada por un continuo unitario de agentes con horizonte infinito y preferencias separables en consumo $c_t > 0$ y fracción de trabajo $L_t in [0, 1)$:
$ U = E_0 sum_(t=0)^oo beta^t thin u(c_t, L_t), #h(16pt) u(c, L) = eta log c + (1 - eta) log(1 - L), $ <eq:prefs>
con factor de descuento $beta in (0, 1)$ y ponderación de consumo $eta in (0, 1)$. La tecnología agregada de base adopta la forma CES armónica simétrica con rendimientos crecientes a escala de grado $theta = 3\/2$ y complementariedad bruta $rho = -1$ (elasticidad de sustitución $sigma = 1\/(1 - rho) = 1\/2$):
$ F_A (K, L) = A [ 1 / 2 K^(-1) + 1 / 2 L^(-1) ]^(-3\/2) = A ( (2 K L) / (K + L) )^(3\/2). $ <eq:ces_prod>

En cada período $t$, dado un régimen vigente $omega_t in Omega$, las instituciones internas operan a través de tres canales simultáneos:

1. *Gasto público productivo ($tau_p$) y burocracia improductiva ($tau_u$):* El Estado aplica una alícuota impositiva agregada $tau = tau_p + tau_u in (0, 1)$ sobre el producto bruto $Y_"bruto"$. Una fracción $tau_p > 0$ se destina íntegramente al flujo de bienes e infraestructura pública productiva $G_t = tau_p Y_"bruto"$, mientras que el resto $tau_u >= 0$ representa gasto burocrático improductivo o captura rentista que no incrementa la productividad ni genera utilidad al consumidor. Adoptando la formulación clásica de Barro (1990) combinada con la tecnología CES $F_1$:
   $ Y_"bruto" = tilde(A)_0 thin G_t^gamma thin [ F_1 (K_t, L_t) ]^(1 - gamma), #h(16pt) gamma in (0, 1). $
   Sustituyendo $G_t = tau_p Y_"bruto"$ y resolviendo explícitamente para $Y_"bruto"$ resulta:
   $ Y_"bruto"^(1 - gamma) = tilde(A)_0 thin tau_p^gamma thin [ F_1 (K_t, L_t) ]^(1 - gamma) #h(8pt) ==> #h(8pt) Y_"bruto" = A_0 thin tau_p^alpha thin F_1 (K_t, L_t), $
   donde definimos la elasticidad reducida del gasto productivo $alpha := gamma \/ (1 - gamma) > 0$ y la productividad base $A_0 := tilde(A)_0^(1\/(1 - gamma))$. Obsérvese que el factor privado $[F_1 (K_t, L_t)]^(1 - gamma)$ conserva homogeneidad de grado $theta_0 = (1 - gamma) theta = 0.80 times 1.50 = 1.20 > 1$ antes de incorporar el escalado de la infraestructura pública $G_t = tau_p Y_"bruto"$. Descontando la carga fiscal total $(tau_p + tau_u)$, el ingreso privado disponible neto asciende a:
   $ Y_"disp" = (1 - tau_p - tau_u) Y_"bruto" = A_0 thin tau_p^alpha (1 - tau_p - tau_u) thin F_1 (K_t, L_t). $

2. *Fragmentación regulatoria del tamaño empresarial ($N_f >= 1$):* Supongamos que restricciones legales, umbrales laborales o segmentación crediticia obligan a repartir simétricamente el capital y el trabajo agregados $(K_t, L_t)$ entre $N_f >= 1$ establecimientos o firmas fragmentadas de escala $(K_t \/ N_f, L_t \/ N_f)$, impidiendo capturar economías de escala de nivel superior. Suponemos explícitamente congestión proporcional por establecimiento en la infraestructura pública ($g_(i,t) = G_t \/ N_f = tau_p y_(i,t)$, en la tradición de Barro y Sala-i-Martin) —o, de forma equivalente, que $G_t$ se combina en nivel agregado con el compuesto privado fragmentado $F_"priv" = sum_(i=1)^(N_f) F_1 (K_t \/ N_f, L_t \/ N_f)$— pues un bien público puro no rival dentro de cada establecimiento arrojaría el exponente $N_f^(-(theta - 1 - alpha)) = N_f^(-1\/4)$. Dado que $F_1$ es homogénea de grado $theta = 3\/2$, cada unidad genera $F_1 (K_t \/ N_f, L_t \/ N_f) = N_f^(-theta) F_1 (K_t, L_t)$, de modo que la producción agregada neta sumada a través de las $N_f$ unidades vale:
   $ sum_(i=1)^(N_f) (1 - tau_p - tau_u) A_0 thin tau_p^alpha thin F_1 (K_t / N_f, L_t / N_f) = A_0 thin tau_p^alpha (1 - tau_p - tau_u) thin N_f^(-(theta - 1)) thin F_1 (K_t, L_t). $
   Más generalmente, bajo establecimientos heterogéneos de participaciones $\{s_i\}_(i=1)^M$ ($sum s_i = 1$), el factor exacto de pérdida de escala asciende a $sum_(i=1)^M s_i^theta equiv N_f^(-(theta - 1))$, un índice efectivo de fragmentación de tipo Herfindahl--Rényi de orden $theta$ que justifica de modo natural valores continuos $N_f in R_(>= 1)$.

En consecuencia, la restricción de recursos física en ausencia de cambio en la frontera tecnológica ($c_t + K_(t+1) = q K_t + Y_"disp"$, donde $q = 1 - delta$ es la fracción no depreciada del capital) colapsa de manera algebraicamente exacta en $c_t + K_(t+1) = q K_t + F_(A_e) (K_t, L_t)$, con el único escalar de productividad efectiva definido en @eq:master_Ae:
$ A_e (tau_p, tau_u, N_f) = A_0 thin tau_p^alpha (1 - tau_p - tau_u) thin N_f^(-(theta - 1)). $

En nuestra parametrización central fijamos los valores canónicos de MR ($q = 0.92$, $beta = 0.97$, $eta = 0.70$, $theta = 3\/2$, $rho = -1$), junto con la elasticidad de infraestructura estándar de la literatura fiscal $gamma = 0.20$ ($alpha = 1\/4$) y la escala base $A_0 = 1.45$. Esta calibración asegura que en el óptimo fiscal libre de burocracia y fragmentación ($tau_p = 0.20, tau_u = 0, N_f = 1$) el producto efectivo alcance $A_e^"pico" = 0.775739$, envolviendo con holgura al valor de referencia $A_"MVS" = 0.75$.

#obs_box([Observación 1 (Alcance del planificador fiscal y frontera multidimensional $d >= 2$)])[
  En la ecuación @eq:master_Ae, la política fiscal $(tau_p, tau_u)$ y el grado de fragmentación regulatoria $N_f$ operan como parámetros de régimen tomados como dados en un problema de **planificador fiscal** que internaliza plenamente la regla presupuestaria equilibrada período a período $G_t = tau_p Y_"bruto" (K_t, L_t)$. Una economía estrictamente descentralizada donde las firmas atomísticas toman $G_t$ y la escala agregada como externalidades marshallianas no internalizadas —o donde operan bajo poder de mercado con margen precio--costo $mu > 1$— introduce una cuña marginal en las condiciones de primer orden de inversión y trabajo que rompe el isomorfismo exacto de Bellman con el programa de $F_(A_e)$, cuyo estudio detallado se reserva para trabajo futuro. Adicionalmente, dos extensiones dinámicas quedan fuera del alcance unidimensional ($d = 1$): (i) acumular un *stock público independiente* de infraestructura $K_(g,t+1) = (1 - delta_g) K_(g,t) + tau_p Y_"bruto"$; y (ii) incorporar deuda soberana o activos múltiples $(K_t, B_t)$, ambas dentro de la agenda `cegis-bellman` v0.2 ($d >= 2$) en la Sección 9.
]

== Reducción Exacta en Unidades de Eficiencia y Bellman Unificada

Incorporemos ahora tanto la incertidumbre político-institucional como el progreso tecnológico global estocástico. Sea $omega_t in Omega$ una cadena de Markov finita e irreducible con matriz de transición $P = [p_(omega omega')]_(omega, omega' in Omega)$. Cada estado $omega$ determina simultáneamente el bloque institucional $(tau_(p,omega), tau_(u,omega), N_(f,omega))$ —y por tanto $A_(e,omega) = A_e (tau_(p,omega), tau_(u,omega), N_(f,omega))$— y la tasa de expansión de la frontera tecnológica exógena $E_t$:
$ E_(t+1) = (1 + g_(omega_t)) E_t, #h(16pt) E_0 > 0, #h(12pt) g_omega >= 0. $ <eq:frontier_law>

Para preservar una trayectoria balanceada en presencia de crecimiento de la frontera cuando el insumo laboral $L_t in [0, 1)$ representa tiempo acotado del hogar, consideramos la tecnología aumentadora de eficiencia global donde $E_t$ reescala la productividad en unidades comparables al capital acumulado: definiendo las variables normalizadas $hat(K)_t := K_t \/ E_t$ y $hat(c)_t := c_t \/ E_t$, la tecnología homogénea de escala $E_t dot F_(A_(e,omega)) (K_t \/ E_t, L_t)$ transforma la restricción presupuestaria agregada $c_t + K_(t+1) = q K_t + E_t F_(A_(e,omega)) (K_t \/ E_t, L_t)$ en:
$ E_t hat(c)_t + (1 + g_omega) E_t hat(K)_(t+1) = q E_t hat(K)_t + E_t F_(A_(e,omega)) (hat(K)_t, L_t). $
Dividiendo ambos lados por $(1 + g_omega) E_t$ y definiendo el consumo ajustado por crecimiento $tilde(c)_t := hat(c)_t \/ (1 + g_omega) = c_t \/ E_(t+1)$, obtenemos la ley de movimiento reducida en el espacio unidimensional de eficiencia $hat(K)_t$:
$ tilde(c)_t + hat(K)_(t+1) = tilde(q)_omega hat(K)_t + tilde(A)_omega F_1 (hat(K)_t, L_t), $ <eq:eff_budget>
donde $tilde(A)_omega = A_(e,omega) \/ (1 + g_omega)$ y $tilde(q)_omega = q \/ (1 + g_omega)$ coinciden exactamente con la ecuación maestra @eq:master_markov. En niveles absolutos, la tecnología homogénea $Y_t = E_t F_(A_(e,omega)) (K_t \/ E_t, L_t) = A_(e,omega) (2 K_t L_t)^(3\/2) E_t \/ (K_t + E_t L_t)^(3\/2)$ exhibe derivada parcial $partial Y_t \/ partial E_t prop (K_t - (1\/2) E_t L_t)\/(K_t + E_t L_t)^(5\/2)$: es negativa en la vecindad de baja escala $hat(K)_t < L_t \/ 2$ (incluyendo todo el entorno del punto de Skiba y el corredor $M_"pol"$) y positiva por encima de escala ($hat(K)_t > L_t \/ 2$). Económicamente, ello formaliza un mecanismo schumpeteriano de *obsolescencia tecnológica* (_vintage effect_): a medida que la frontera global $E_t$ se vuelve más compleja, la escala mínima viable para operar tecnología competitiva crece proporcionalmente con $E_t$, penalizando al capital rezagado a $(K_t, L_t)$ fijos y premiando al capital por encima de escala. Al sustituir $c_t = (1 + g_omega) E_t tilde(c)_t$ en la utilidad logarítmica @eq:prefs, resulta $u(c_t, L_t) = u(tilde(c)_t, L_t) + eta log(1 + g_omega) + eta log E_t$. Como demostramos en el Teorema 2 (Sección 7), tanto el término aditivo $eta log E_t$ como el flujo constante $eta log(1 + g_omega)$ son absorbidos por el corrimiento separable $phi_omega + (eta\/(1 - beta)) log E$, de modo que la componente dependiente del capital normalizado $hat(V)(hat(K), omega)$ resuelve la ecuación de Bellman Markoviana reducida:
$ hat(V)(hat(K), omega) = max_((hat(K)' > 0, L in [0, 1) \ tilde(c) = tilde(q)_omega hat(K) + tilde(A)_omega F_1 (hat(K), L) - hat(K)' > 0)) { u(tilde(c), L) + beta sum_(omega' in Omega) p_(omega omega') hat(V)(hat(K)', omega') }. $ <eq:master_bellman>

Esta representación unificada abarca como casos especiales los tres entornos estudiados en las Secciones 4--7:
- *Régimen institucional estático (Secciones 4 y 5):* $|Omega| = 1$, $g = 0$, $tilde(A) = A_e (tau_p, tau_u, N_f)$, $tilde(q) = q$.
- *Alternancia político-fiscal Markoviana (Sección 6):* $Omega = {G, B}$, $g_G = g_B = 0$, $p_(G B) = p_"rev"$, $p_(B G) = p_"ref"$, con deterioro institucional $A_(e,G) -> A_(e,B)$.
- *Dinámica «Red Queen» estocástica (Sección 7):* $Omega = {L, H}$, instituciones internas fijas $(tau_p, tau_u, N_f)$ pero frontera global alternando entre expansión lenta $g_L = 2%$ y ola tecnológica $g_H in {3%, 5%, 7%}$, con tasas de transición $p_(L H) = p_"wave"$ y $p_(H L) = p_"end"$.

// ============================================================================
// SECCIÓN 4: TEORÍA ANALÍTICA — CURVA EN U Y EQUIVALENCIA
// ============================================================================
= Teoría Analítica: La Curva en U Institucional y Equivalencia Burocracia--Fragmentación

Esta sección extrae las propiedades analíticas exactas del bloque institucional determinista ($omega$ fijo, $g = 0$), caracterizando la Curva en U del umbral de Skiba, las bifurcaciones silla-nodo y el isomorfismo exacto entre fragmentación empresarial y gasto burocrático improductivo.

== La Curva en U Institucional y las Cuatro Fronteras Críticas

Cuando una economía fija el nivel de burocracia $tau_u in [0, 1)$ y la fragmentación $N_f >= 1$, variar la inversión en infraestructura productiva $tau_p in (0, 1 - tau_u)$ induce dos fuerzas opuestas sobre el excedente privado: mejora inicialmente la eficiencia física del capital y del trabajo vía $tau_p^alpha$, pero a partir de cierto punto la confiscación tributaria $(1 - tau_p - tau_u)$ domina y deprime los retornos privados.

#thm_box("Teorema 1 (Curva en U Institucional y Bifurcaciones Críticas)")[
  Para toda burocracia factible $tau_u in [0, 1)$ y fragmentación $N_f >= 1$, la productividad efectiva $A_e (tau_p, tau_u, N_f)$ de @eq:master_Ae es estrictamente log-cóncava en $tau_p in (0, 1 - tau_u)$ y alcanza su único máximo global en:
  $ tau_p^* (tau_u) = gamma (1 - tau_u), #h(16pt) A_e^"max" (tau_u, N_f) = A_0 thin gamma^alpha (1 - gamma) (1 - tau_u)^(1 + alpha) N_f^(-(theta - 1)). $ <eq:barro_opt>
  En la calibración de referencia ($A_0 = 1.45, gamma = 0.20, alpha = 0.25, q = 0.92, beta = 0.97, eta = 0.70$):
  1. Con burocracia nula y escala unificada ($tau_u = 0, N_f = 1$), el máximo productivo ocurre en $tau_p^* = 0.20$ con $A_e^"pico" = 1.45 times 0.20^(0.25) times 0.80 = 0.775739$, superando la cota inferior $A_"MVS"^- = 0.749$ de la caja canónica MVS sobre la estrecha isla fiscal $tau_p in [0.117245, 0.304799]$.
  2. La viabilidad física básica —existencia de algún capital $K > 0$ donde el producto bruto con trabajo máximo ($L = 1$) compense al menos la depreciación, $F_(A_e)(K, 1) >= (1 - q) K$— exige superar el piso algebraico de repulsor $A_e > A_"rep" = (3 sqrt(6) \/ 8)(1 - q) = 0.073485$ (correspondiente a $tau_p in [6.597 times 10^(-6), 0.94865]$ cuando $tau_u = 0, N_f = 1$).
  3. Con oferta laboral endógena $L^*$, el primer equilibrio estacionario interior compatible con la ecuación de Euler del planificador aparece en la bifurcación silla-nodo local $A_"SN" = 0.099524$; ligeramente por encima, en el umbral global de Skiba/Maxwell $A_* = 0.099611$, el valor estacionario alto $V_H^*(A)$ supera a la rama estrictamente contractiva $V_"contract" (K_H^*; A)$.
  4. En todo el intervalo factible $tau_p in (0, 1 - tau_u)$, la envolvente asintótica analítica de Skiba adopta una estricta forma de *U*: desciende hasta su mínimo global en $tau_p^* (tau_u)$ y diverge hacia ambos extremos, dada por:
     $ S_"env" (tau_p, tau_u, N_f) = s_oo^* [ A_e (tau_p, tau_u, N_f) ]^(-1\/r), #h(14pt) s_oo^* = 0.000800, #h(10pt) r = theta - 1 = 0.50, $ <eq:s_env_law>
     cota que la verificación numérica VFI confirma en la Tabla 2 sobre $tau_p in [0.005, 0.880]$ ($tau_u = 0$), con mínimo en $tau_p^* = 0.20$ ($S_"VFI" (0.20; 0) = 0.001498$).
]

#proof_block[
  Tomando logaritmos en @eq:master_Ae y diferenciando respecto de $tau_p$ con $(tau_u, N_f)$ constantes se obtiene:
  $ (partial log A_e) / (partial tau_p) = alpha / tau_p - 1 / (1 - tau_p - tau_u), #h(16pt) (partial^2 log A_e) / (partial tau_p^2) = -alpha / tau_p^2 - 1 / (1 - tau_p - tau_u)^2 < 0. $
  Igualando la derivada primera a cero resulta $alpha (1 - tau_u - tau_p) = tau_p$, de donde $tau_p^* (tau_u) = [alpha\/(1 + alpha)](1 - tau_u) = gamma (1 - tau_u)$. Al sustituir en @eq:master_Ae emerge la expresión cerrada @eq:barro_opt, que para $gamma = 0.20, alpha = 0.25, A_0 = 1.45, tau_u = 0, N_f = 1$ entrega $tau_p^* = 0.20$ y $A_e^"pico" = 0.77573875$. Para el repulsor físico con trabajo pleno $L = 1$, la condición $A_e (2 K \/ (K + 1))^(3\/2) >= (1 - q) K$ equivale a $A_e >= 2^(-3\/2)(1 - q)(K + 1)^(3\/2) K^(-1\/2)$. Minimizando $phi(K) := (K + 1)^(3\/2) K^(-1\/2)$ para $K > 0$, la derivada logarítmica $phi'\/phi = (3\/2)/(K + 1) - 1\/(2 K)$ se anula únicamente en $K = 1\/2$, donde $phi(1\/2) = (3\/2)^(3\/2) sqrt(2) = 3 sqrt(3) \/ 2$; multiplicando por $2^(-3\/2)(1 - q)$ se obtiene $A_"rep" = (3 sqrt(6) \/ 8)(1 - q) = 0.08 times (3sqrt(6)\/8) = 0.07348469$. La bifurcación silla-nodo local $A_"SN" = 0.0995245$ se caracteriza por la tangencia simultánea de la ecuación de Euler $q + partial_K F_(A_e) (K^*, L^*) = 1\/beta$, la condición intratemporal de trabajo $((1 - eta)\/eta) c^* \/ (1 - L^*) = partial_L F_(A_e) (K^*, L^*)$ y la igualdad estacionaria $c^* = (q - 1) K^* + F_(A_e) (K^*, L^*)$, mientras en $A_* = 0.0996111$ se igualan los valores globales de Maxwell $V_H^*(A_*) = V_"contract" (K_H^*; A_*)$. Por último, la ley @eq:s_env_law se deduce aplicando el escalado asintótico $A_e^(1\/r) S_(A_e) -> s_oo^* = (delta \/ c_K)^(1\/r) = 0.000800$ (Milei y Reidel, 2026; Segura, 2026): puesto que $S_(A_e)$ decrece con $A_e$ como $A_e^(-2)$ ($r = 1\/2$) y la razón de escala envolvente es monótona, la función compuesta $tau_p |-> S_"env" (tau_p)$ hereda una geometría estrictamente en U (inversa a la campana $A_e (tau_p)$).
]

La Tabla 2 presenta quince puntos representativos a lo largo de la Curva en U para $tau_u = 0, N_f = 1$, evaluando el umbral $S_"VFI" (tau_p)$ sobre una malla localmente refinada alrededor de la cuenca de Skiba frente a la cota inferior asintótica $S_"env" (tau_p)$ y la cobertura lograda tanto por la ventana MVS clásica ($A_e >= 0.749$) como por nuestro atlas CEGIS-LP. Numéricamente, en $A_"cross" = 0.110400$ el umbral VFI $S_"VFI" (A)$ cruza por debajo la envolvente de producto medio $s_"medio" \/ A^2$ con $s_"medio" = (D\/c_K)^2 = ((1\/beta - q)\/2^(3\/2))^2 = 0.001538$ (donde $F_A (K, 1)\/K = D = 1\/0.97 - 0.92 = 0.110928$; nótese que la raíz marginal estacionaria de Euler lleva $theta$ en el denominador, $(D\/(theta c_K))^2 = 0.000684 < s_oo^* = 0.000800$, al verificarse paciencia local $beta(q + theta delta) = 1.0088 > 1$).

#include "tables/table2_u_curve_thresholds.typ"

Tres rasgos cuantitativos emergen inmediatamente de la Tabla 2. Primero, mientras el umbral de Skiba alcanza su mínimo estricto en $tau_p^* = 0.20$ con $S_"VFI" = 0.001498$, desatender la infraestructura pública hasta $tau_p = 0.005$ más que cuadruplica la barrera de despegue ($S_"VFI" = 0.006381$), y sobredimensionar la tributación hasta $tau_p = 0.80$ multiplica por cerca de $8.6 times$ el umbral mínimo ($S_"VFI" = 0.012816$, elevándose hasta $0.040066$ en $tau_p = 0.88$). Segundo, la razón $S_"VFI" \/ S_"env"$ permanece notablemente estable entre $1.12$ y $1.21$ en todo el corredor central, validando la potencia predictiva de la ley asintótica cerrada @eq:s_env_law incluso para $A_e < 0.40$. Tercero, al incorporar burocracia improductiva ($tau_u > 0$), el techo fiscal se estrecha a $tau_p^* (tau_u) = 0.20(1 - tau_u)$ mientras toda la Curva en U se eleva verticalmente, como muestra el Panel A de la Figura 1.

== Isomorfismo Exacto Burocracia--Fragmentación

Demostramos ahora que la fragmentación regulatoria del tamaño empresarial actúa matemáticamente como un impuesto burocrático improductivo encubierto.

#thm_box("Proposición 1 (Isomorfismo Exacto entre Fragmentación y Burocracia Improductiva)")[
  Fijado cualquier gasto productivo $tau_p in (0, 1)$, la economía con escala empresarial fragmentada en $N_f >= 1$ establecimientos y cero burocracia ($tau_u = 0$) posee exactamente la misma productividad efectiva, idéntica función valor $V(K)$, idénticas reglas de decisión óptima $(K'(K), L(K))$ y exactamente el mismo punto de Skiba $S$ que una economía de escala unificada ($N_f = 1$) gravada con una burocracia improductiva equivalente igual a:
  $ tau_u^"eq" (N_f; tau_p) = (1 - tau_p) [ 1 - N_f^(-(theta - 1)) ]. $ <eq:nf_equiv>
  Bajo la tecnología armónica ($theta = 3\/2$) y $tau_p = 0.20$:
  1. Operar con $N_f = 4$ fragmentos industriales equivale exactamente a sostener una burocracia improductiva del $tau_u^"eq" = 0.80 (1 - 4^(-0.5)) = 0.40$ ($40%$ del producto bruto).
  2. Bajo la escala canónica de referencia $A_0^"MVS" = 0.75$ ($N_f = 1$), la viabilidad económica dinámica colapsa en el umbral global de Maxwell $N_(f,*) = 56.69$ fragmentos ($A_e = A_* = 0.099611$), justo antes de la extinción silla-nodo local $N_(f,"SN") = 56.79$ ($A_e = A_"SN" = 0.099524$). Bajo el pico óptimo de Barro ($A_e^"pico" = 0.775739$), dichos umbrales de extinción se ubican en $N_(f,*)^"pico" = 60.65$ y $N_(f,"SN")^"pico" = 60.75$.
]

#proof_block[
  Igualando $A_e (tau_p, 0, N_f) = A_e (tau_p, tau_u^"eq", 1)$ en @eq:master_Ae y cancelando el factor positivo común $A_0 tau_p^alpha > 0$ se obtiene $(1 - tau_p) N_f^(-(theta - 1)) = 1 - tau_p - tau_u^"eq"$, de donde se despeja inmediatamente @eq:nf_equiv. Como el programa dinámico determinista depende de las instituciones exclusivamente a través de $A_e$, ambos sistemas son matemáticamente indistinguibles. Con $tau_p = 0.20$ y $theta = 3\/2$, evaluar en $N_f = 4$ da $0.80 times (1 - 1\/2) = 0.40$. Resolviendo $0.75 thin N_f^(-1\/2) = A_*$ se halla $N_(f,*) = (0.75 \/ 0.0996111)^2 = 56.6901$, y para $A_"SN" = 0.0995245$ resulta $N_(f,"SN") = 56.7888$, mientras $(0.7757388 \/ 0.0996111)^2 = 60.6478$ y $(0.7757388 \/ 0.0995245)^2 = 60.7535$.
]

La Tabla 3 exhibe el espectro completo de esta equivalencia desde $N_f = 1$ hasta $N_f = 57$. Nótese que ya duplicar artificialmente la fragmentación ($N_f = 2$) equivale a un desperdicio burocrático $tau_u^"eq" = 23.43%$, y cuadruplicarla ($N_f = 4$) consume la mitad de la productividad efectiva ($0.7757 -> 0.3879$), llevando la economía al borde exacto de nuestro atlas determinista certificado. En el extremo opuesto, por encima de $N_(f,*) = 56.69$ bajo $A_0^"MVS" = 0.75$, la economía pierde por completo el atractor superior próspero: ninguna dotación inicial de capital puede ya salvarla de la contracción hacia el origen.

#include "tables/table3_fragmentation_equivalence.typ"

// ============================================================================
// SECCIÓN 5: CERTIFICACIÓN CONTINUA CEGIS-LP
// ============================================================================
= Certificación Continua sobre Regiones Institucionales y Escala Empresarial

Mientras la VFI puntual arroja luz sobre la curvatura del umbral de Skiba, no demuestra formalmente qué ocurre en todo el continuo de parámetros ni certifica un tiempo máximo finito de escape garantizado para toda política óptima. Esta sección despliega el sintetizador *CEGIS-LP* (`log-PWL`) junto con el verificador continuo por intervalos libre de `libm`, multiplicando por más de cincuenta el dominio certificado de política institucional y trasladándolo de manera exacta a la escala empresarial.

== Barreras `log-PWL`, Elección de $M_"pol"$ y Transparencia Paramétrica

Dado un parámetro reducido fijo $(A_e, q, beta, eta)$ en el caso determinista ($g = 0$), el algoritmo CEGIS-LP busca simultáneamente sobre la región de tránsito $M = [b_m, h_m)$ y el corredor intermedio $H_1 = [h_m, 0.80]$ tres splines continuas por tramos en coordenada $log K$ —una barrera de Bellman de primer paso $B(K)$, un techo superior de Bellman $Psi(K)$ y un testigo factible inferior $W(K)$, extendiéndose $B(K') := B(h_m)$ de forma constante para todo $K' >= h_m$— que satisfagan:
1. $W(K) <= V(K) <= Psi(K)$ para todo $K in M union H_1$ (encapsulamiento riguroso de la función valor exacta).
2. En $M$, todo par admisible $(K, K', L) in M times [b_m, Y_"max"] times [0, 1)$ con consumo positivo $c = q K + F_(A_e)(K, L) - K' > 0$ que no pueda descartarse por suboptimalidad frente al testigo ($u(c, L) + beta Psi(K') >= W(K)$) verifica la desigualdad de barrera de permanencia (súper-solución restringida de Bellman):
   $ u(q K + F_(A_e)(K, L) - K', L) + beta B(K') <= B(K), #h(14pt) (K' >= h_m ==> B(K') := B(h_m)), $ <eq:cegis_det_stay>
   junto con las cotas analíticas de salida hacia $H_2 = (0.80, oo)$ verificadas en aritmética de intervalos IEEE-754 libre de `libm`.

Como los márgenes positivos de salida inferior ($Delta_"exit"^M > 0$) garantizan que ningún óptimo abandona $M$ por debajo de $b_m$ ($K' >= b_m$), iterar @eq:cegis_det_stay sobre cualquier trayectoria óptima que permanezca en $M$ durante $T$ períodos consecutivos y acotar $m_"inf" := inf_(K in M) (W(K) - B(K)) > 0$ junto con $d_"stay" := sup_(K in M) (Psi(K) - B(K))$ rinde $W(K_0) <= V(K_0) <= B(K_0) + beta_+^T d_"stay"$. Por consiguiente, ninguna trayectoria óptima $pi^*(K)$ puede permanecer en $M$ al cumplirse $beta_+^T d_"stay" < m_"inf"$, certificando de forma constructiva el plazo finito exacto $T_"cert" = min { T >= 1 : beta_+^T d_"stay" < m_"inf" }$.

#obs_box([Observación 2 (Transparencia formal sobre $M_"pol"$ y la parametrización fija del atlas)])[
  Para garantizar total rigor comparativo respecto del benchmark MVS de Milei y Reidel (2026), explicitamos dos definiciones estructurales del diseño experimental:
  1. *Justificación económica de $M_"pol" = [0.10, 0.18)$ frente a $M = [0.10, 0.28)$:* En los módulos de extensión institucional (`barro_Ae_atlas`), volatilidad política (`political_markov`) y frontera tecnológica (`red_queen_markov`), evaluamos el escape en tiempo finito sobre la región de tránsito de política $M_"pol" = [0.10, 0.18)$. La razón económica es precisa: cuando las distorsiones institucionales o las olas tecnológicas reducen $A_e$ hacia $0.385$ o $tilde(A)_omega$ hacia $0.36$, el atractor superior $K^*$ desciende significativamente y el umbral $h_m = 0.28$ del caso puro $A = 0.75$ queda demasiado próximo —o incluso por encima— de la zona de desaceleración en economías muy distorsionadas. En contraste, $h_"pol" = 0.18$ captura exactamente la *puerta de salida post-Skiba*: toda trayectoria que supera $K = 0.18$ en el interior del atlas se encuentra más de diez veces por encima del umbral de Skiba más adverso ($S <= 0.014$) y dentro de la cuenca de convergencia monótona hacia su estado estacionario alto. A la vez, el módulo `mvs_canonical` conserva intacta la caja original $M = [0.10, 0.28)$ ($T_"cert" = 5$).
  2. *Dimensiones fijas en el Atlas de $63$ bandas vs. caja 4D completa:* Mientras el certificado maestro `mvs_canonical` audita simultáneamente la caja paramétrica cuadridimensional completa $(A, q, beta, eta) in [0.749, 0.751] times [0.9199, 0.9201] times [0.9699, 0.9701] times [0.6999, 0.7001]$, el atlas continuo de $63$ bandas (`barro_Ae_atlas`) certifica sin huecos sobre todo el espectro $A_e in [0.385, 0.780]$ fijando los parámetros estructurales en sus valores estándar $(q, beta, eta) = (0.92, 0.97, 0.70)$ (tratados como intervalos degenerados exactos en el verificador). Ello permite aislar sin distorsiones el impacto de la tríada institucional $(tau_p, tau_u, N_f)$ sobre todo el continuo viable.
]

== Expansión $53.9 times$ en el Plano Institucional $(tau_p, tau_u)$

Dividiendo adaptativamente el intervalo de productividad $A_e in [0.385, 0.780]$ hasta lograr márgenes positivos en las ocho condiciones de verificación por intervalos (permanencia $Psi$, testigo $W$, descenso de barrera $B$, salida $M$, salidas $H_1\/H_2$ y derivadas de concavidad en nodos), el motor CEGIS-LP produce una partición contigua exacta de $63$ bandas cerradas cuya unión cubre sin fisuras $[0.385, 0.780]$.

#cert_box("Proposición 2 (Atlas Continuo en el Plano de Políticas y Expansión 53.9x)")[
  Fijados $(q, beta, eta) = (0.92, 0.97, 0.70)$ sobre la región de tránsito $M_"pol" = [0.10, 0.18)$:
  1. Las $63$ bandas contiguas sintetizadas por CEGIS-LP satisfacen $100%$ de verificación continua por intervalos IEEE-754 sin `libm` ($union.big_(i=1)^(63) [A_(e,i)^-, A_(e,i)^+] = [0.385, 0.780]$, cero huecos), acotando el plazo determinista de escape en $T_"cert" in {4, 5, 6, 7}$ períodos: exactamente $24$ bandas certifican en $T_"cert" = 4$ (dentro de $A_e in [0.550, 0.780]$), $21$ bandas en $T_"cert" = 5$, $15$ bandas en $T_"cert" = 6$ y $3$ bandas terminales junto al borde $A_e = 0.385$ en $T_"cert" = 7$.
  2. Proyectando la condición $A_e (tau_p, tau_u, 1) in [0.385, 0.780]$ sobre el simplex fiscal $tau_p > 0, tau_u >= 0, tau_p + tau_u < 1$, el área institucional certificada asciende a $"Área"_"CEGIS" = 0.185793$, frente a $"Área"_"MVS" = 0.003445$ de la banda antigua $A_e >= 0.749$ —una expansión de **$53.93 times$**.
  3. En burocracia cero ($tau_u = 0$), el rango fiscal certificado se extiende desde $tau_p = 0.005072$ hasta $tau_p = 0.710831$ (frente a $[0.117245, 0.304799]$ en $A_e >= 0.749$). En la infraestructura óptima $tau_p = 0.20$, la economía tolera una burocracia improductiva certificada de hasta $tau_u^"max" = 0.402959$ (más de $14.6 times$ el máximo $tau_u^"MVS" = 0.02758$ de la isla clásica).
]

La Figura 1 contrasta gráficamente esta expansión masiva. En el Panel B, la antigua región MVS ocupa apenas un pequeño lóbulo verde en la base del plano fiscal; en cambio, el atlas de $63$ bandas cubre todo el dominio institucional empíricamente relevante, dejando por debajo solamente los entornos cercanos al colapso silla-nodo ($A_"SN" = 0.0995$) y al repulsor ($A_"rep" = 0.0735$).

#figure(
  image("figures/fig1_u_curve_and_policy_plane.pdf", width: 100%),
  caption: [Curva en U institucional y plano de políticas certificado. *Panel A:* umbral de Skiba VFI $S_"VFI" (tau_p; tau_u)$ para $tau_u in {0, 0.15, 0.30}$ junto con la envolvente analítica inferior $S_"env"$ ($tau_u = 0$), contrastando la estrecha isla MVS clásica con la cobertura del atlas CEGIS-LP. *Panel B:* curvas de nivel de productividad efectiva $A_e (tau_p, tau_u)$ mostrando la expansión de $53.9 times$ en área del plano $(tau_p, tau_u)$ hasta el borde certificado $A_e = 0.385$ ($tau_u^"max" = 0.403$) frente a las fronteras silla-nodo ($A_"SN"$) y repulsor ($A_"rep"$).],
) <fig:u_curve_plane>

== Transferencia al Atlas de Fragmentación Industrial ($N_f$)

Por el isomorfismo exacto de la Proposición 1, el mismo archivo certificado de $63$ bandas proporciona de inmediato una garantía continua sobre la fragmentación empresarial cuando la política fiscal se fija en el óptimo $tau_p = 0.20, tau_u = 0$ mediante la relación biyectiva $N_f (A_e) = (A_e^"pico" \/ A_e)^2$:

#cert_box([Proposición 3 (Atlas Continuo en Fragmentación Empresarial $N_f$)])[
  En $(tau_p, tau_u) = (0.20, 0)$ ($A_e^"pico" = 0.775739$), las $63$ bandas certificadas cubren sin interrupciones toda estructura industrial desde la firma integrada ($N_f = 1.00$) hasta la fragmentación crítica certificada:
  $ N_f^("max,cert") = ( 0.775739 / 0.385 )^2 = 4.059846, $
  asegurando el escape de $M_"pol" = [0.10, 0.18)$ en un plazo determinista $T_"cert" in {4, 5, 6, 7}$ períodos. Si la productividad base sin distorsiones fuese $A_0^"MVS" = 0.75$, el borde certificado se situaría en $N_f^"max" (0.75) = 3.794906$.
]

La Figura 2 visualiza tanto la equivalencia hiperbólica entre $N_f$ y $tau_u^"eq"$ hasta la bifurcación silla-nodo (Panel A) como la anatomía detallada de las $63$ bandas sobre $N_f in [1.00, 4.060]$ (Panel B). Nótese que los saltos discretos en el margen mínimo de salida en $M_"pol"$ (curva negra, eje derecho) señalan los puntos donde CEGIS-LP incrementa el horizonte $T_"cert"$ de $4$ a $5$, $6$ y $7$ para sostener una barrera estrictamente decreciente con margen de intervalo positivo.

#figure(
  image("figures/fig2_fragmentation_equivalence.pdf", width: 100%),
  caption: [Distorsión de tamaño empresarial y certificación continua. *Panel A:* caída hiperbólica de $A_e (N_f)$ y correspondencia exacta con la burocracia improductiva $tau_u^"eq" (N_f)$ en $tau_p = 0.20$ (marcando $N_f = 4 <==> tau_u^"eq" = 0.40$ y la extinción silla-nodo $N_(f,*) = 56.69$). *Panel B:* plazo certificado $T_"cert" in {4, 5, 6, 7}$ y margen mínimo de salida por intervalos en $M_"pol"$ a través de las $63$ bandas contiguas sobre $N_f in [1.00, 4.060]$.],
) <fig:frag_equiv>

// ============================================================================
// SECCIÓN 6: VOLATILIDAD POLÍTICO-FISCAL
// ============================================================================
= Volatilidad Político-Fiscal: Regresión de Reformas y Trampas Estocásticas

Incluso cuando una economía adopta instituciones fiscales y regulatorias óptimas hoy, las empresas e inversores evalúan la probabilidad de una reversión política futura hacia un régimen burocrático o extractivo. Modelamos esta alternancia político-fiscal mediante una cadena de Markov de dos estados $Omega = {G, B}$ y demostramos tanto el acoplamiento estocástico de Doob como un marcado efecto de *huida precautoria hacia la seguridad* en la solución óptima.

== Formulación Markoviana Bilateral $(G, B)$ y Barreras de Permanencia de Doob

Mantenemos constante la frontera tecnológica mundial ($g_G = g_B = 0$) y definimos dos regímenes institucionales con parámetros estructurales $(q, beta, eta) = (0.92, 0.97, 0.70)$:
- *Régimen $G$ (Reformista):* $(tau_p, tau_u, N_f) = (0.20, 0, 1)$, generando $A_G = 0.775739$.
- *Régimen $B$ (Reversión):* deterioro institucional que reduce la productividad efectiva hasta $A_B = 0.45$ (equivalente a una carga burocrática improductiva $tau_u = 0.3359$ en $tau_p = 0.20$ o a una fragmentación $N_f = 2.97$).

Las transiciones entre ambos regímenes obedecen a la matriz estocástica:
$ P = mat(1 - p_"rev", p_"rev"; p_"ref", 1 - p_"ref"), $
donde $p_"rev" in [0.02, 0.18]$ mide la probabilidad anual de reversión ($G -> B$) y $p_"ref" in {0.25, 1\/3, 0.50}$ mide la tasa de recuperación reformista ($B -> G$, implicando una duración esperada de la fase adversa entre $2$ y $4$ períodos).

En entornos estocásticos ya no existe un horizonte determinista máximo finito, pues una cadena arbitrariamente larga de realizaciones $B$ podría retrasar la acumulación. En su lugar, aplicando el *teorema converso estocástico de Doob acoplado a selección óptima* (Segura, 2026), sintetizamos mediante CEGIS-LP una pareja acoplada de barreras de permanencia (súper-soluciones restringidas de Bellman) $(B_G, B_B)$, techos $(Psi_G, Psi_B)$ y testigos $(W_G, W_B)$ tales que, extendiendo constantemente $B_(omega') (K') := B_(omega') (h_"pol")$ para toda salida $K' >= h_"pol" = 0.18$, todo régimen $omega in {G, B}$, todo $K in M_"pol" = [0.10, 0.18)$ y toda decisión admisible $(K', L)$ compatible con $W_omega (K)$ satisfacen la desigualdad de barrera de permanencia acoplada:
$ u(q K + F_(A_omega)(K, L) - K', L) + beta sum_(omega' in {G, B}) p_(omega omega') B_(omega') (K') <= B_omega (K). $ <eq:doob_markov>
Definiendo los márgenes uniformes $m_"inf" := min_omega inf_(M_"pol") (W_omega - B_omega) > 0$, $d_"stay" := max_omega sup_(M_"pol") (Psi_omega - B_omega)$ y el exceso máximo de salida $d_"exit" := max_omega (Psi_omega (Y_"max") - B_omega (h_"pol")) > 0$, la aplicación del Teorema de Parada Opcional de Doob sobre la supermartingala descontada de Bellman detenida en $tau_"exit" and T_0$ (Apéndice A.3) arroja la cota inferior uniforme de probabilidad de escape en $T_0$ pasos:
$ epsilon.alt_0 (T_0) = (m_"inf" - beta_+^(T_0) d_"stay") / (beta_+ d_"exit" - beta_+^(T_0) d_"stay") > 0, #h(14pt) sup_((K_0, omega_0) in M_"pol" times {G, B}) E_(K_0, omega_0) [ tau_"exit" ] <= (T_0^"opt") / (epsilon.alt_0^"opt") =: E_tau^"opt". $ <eq:doob_bound>

== Curvas Iso-Skiba y Regímenes Extremos ($A_B = 0.35, 0.095$)

La iteración continua de función valor (VFI) estocástica permite examinar en primer lugar cómo el riesgo de reversión distorsiona la ubicación del punto de Skiba $S_G (p_"rev", tau_(u,G))$ incluso antes de que ocurra el choque adverso. La Figura 3A grafica las *curvas iso-Skiba* calculadas mediante VFI localmente refinada para $tau_(u,G) in {0.00, 0.05, 0.10, 0.15, 0.20, 0.25}$: al incrementarse $p_"rev"$ de $0%$ a $25%$, el umbral mínimo de despegue en el régimen bueno se eleva progresivamente en cada nivel de burocracia. Económica e institucionalmente, una mayor incertidumbre política exige un acervo inicial mayor de capital para garantizar el escape, actuando como un sustituto directo de la ineficiencia burocrática presente.

Asimismo, comparamos en VFI la severidad del régimen adverso $B$ evaluando dos escenarios extremos adicionales: un deterioro moderado-severo ($A_B = 0.35$, fuera de la banda certificada estática $0.385$) y un colapso institucional ($A_B = 0.095 < A_"SN" = 0.0995$, donde el régimen $B$ carece de estado estacionario alto propio). En $A_B = 0.35$ con $p_"ref" = 1\/3$, el umbral de cruce de la recta de $45 degree$ en el régimen adverso $K_B^*$ (donde $K'_B (K) = K$, distinto del punto de quiebre de Skiba $S_("B,kink")$ en $V_B$ caracterizado en Segura, 2026) salta a `0.009697` (casi el doble que bajo $A_B = 0.45$, donde $K_B^* = 0.005102$) y el salto de inversión $Delta K'_G$ en $M$ alcanza `+0.00950` a medida que sube $p_"rev"$; cuando $A_B = 0.095$, la política en $B$ contrae el capital en toda la región baja y el impulso precautorio máximo en $G$ salta hasta `+0.03792` ($p_"rev" = 15%, p_"ref" = 10%$), confirmando que los regímenes adversos terminales destruyen la separabilidad lineal de las barreras en $M_"pol"$ mientras $A_B = 0.45$ provee un laboratorio completo donde ambos estados permanecen certificables (véase la Tabla A.2 en el Apéndice para las $12$ configuraciones completas de $A_B in {0.35, 0.095}$).

== Huida Precautoria hacia la Seguridad: Análisis VFI y Riesgo Endógeno

Un resultado central de este artículo emerge al comparar la estática comparativa de la cota certificada de Doob frente al tiempo esperado exacto de salida bajo la política óptima VFI cuando aumenta la probabilidad de reversión $p_"rev"$.

Podría pensarse intuitivamente que elevar la probabilidad anual de sufrir una reversión anti-reforma desde $2%$ hasta $18%$ empeora los incentivos de inversión y alarga invariablemente el tiempo necesario para escapar de la región vulnerable $M_"pol"$. Sin embargo, nuestros cálculos muestran una bifurcación cualitativa notable (Tabla 4 y Figura 3B): mientras que la cota certificada constructiva $sup E[tau]_"CEGIS"$ asciende monotónicamente de `22.94` períodos ($p_"rev" = 2%$) a `24.05` períodos ($p_"rev" = 18%$) reflejando la mayor exposición al estado lento $B$, el **máximo esperado exacto en VFI, $max_(M_"pol" times Omega) E_"VFI" [tau_H]$ (alcanzado en $(K_0 = 0.10, omega_0 = B)$ y estabilizado cerca de $p_"rev" = 18%$ por la competencia entre mayor ahorro precautorio en $G$ y retornos más frecuentes hacia el régimen lento $B$), desciende de `3.483` a `3.444` períodos cuando $p_"rev"$ sube de $2%$ a $18%$** (con $p_"ref" = 1\/3$).

Este acortamiento del horizonte óptimo es la firma inequívoca de una *huida precautoria hacia la seguridad* (*precautionary flight-to-safety*), que en $M_"pol"$ combina dos canales complementarios: (i) el motivo estándar de ahorro precautorio ante un mayor valor marginal futuro en el régimen adverso ($V'_B (K') > V'_G (K')$ en la ecuación de Euler), y (ii) el motivo no convexo de alejarse de la cuenca de colapso (que domina drásticamente cuando $A_B = 0.095$ o bajo ruina endógena). Mientras la economía se encuentra todavía en el régimen reformista $G$, cruzar rápidamente la frontera $h_"pol" = 0.18$ actúa como un seguro real contra futuras reversiones políticas, pues una vez superada la zona de peligro, un choque temporal $B$ ya no amenaza con devolver al país debajo del punto de Skiba. Por ello, ante mayor riesgo de reversión ($p_"rev"$ creciente), el planificador sacrifica consumo corriente en $G$ para acelerar la acumulación de capital y reducir la exposición en tiempo esperado. El mismo mecanismo aparece cuando el riesgo de reversión es endógeno al tamaño de la economía ($p_"rev" (K) = p bold(1)_(K < 0.18)$): en $p = 12%$ y $p = 20%$, la duración máxima en $G$ baja de $4$ a $3$ períodos ($Delta K'_"endo-exo" = +0.00068$ en $p = 12%$).

== Certificación Acoplada de Doob ($7\/7$ Combinaciones)

El siguiente resultado certifica formalmente el escape casi seguro de la región vulnerable en todas las combinaciones evaluadas del modelo político Markoviano.

#cert_box("Proposición 4 (Certificación Estocástica de Doob bajo Alternancia Política)")[
  Para el sistema Markoviano $(A_G = 0.775739, A_B = 0.45)$ sobre $M_"pol" = [0.10, 0.18)$ con $(q, beta, eta) = (0.92, 0.97, 0.70)$:
  1. Todas las $7\/7$ configuraciones evaluadas —$p_"rev" in {0.02, 0.05, 0.08, 0.12, 0.18}$ con $p_"ref" = 1\/3$, más la sensibilidad a persistencia en $p_"rev" = 0.08$ con $p_"ref" in {0.25, 0.50}$— poseen parejas acopladas certificadas $(B_G, B_B)$ en CEGIS-LP con verificación IEEE-754 libre de `libm`, brechas estrictas $epsilon.alt_0^"opt" in [0.4159, 0.4361]$ y tiempos esperados garantizados $sup E[tau] in [20.82, 25.52]$ períodos ($T_0^"opt" in {9, 10, 11}$).
  2. Al reducirse la probabilidad de retorno reformista $p_"ref"$ desde $0.50$ hasta $0.25$ (duplicando la duración media del régimen burocrático de $2$ a $4$ años en $p_"rev" = 8%$), la cota certificada crece monotónicamente de $20.82$ a $25.52$ períodos en concordancia con la subida del umbral VFI $S_G^"VFI"$ desde `0.001616` hasta `0.001668`.
]

La Tabla 4 reporta simultáneamente la malla certificada completa, los umbrales $S_G^"VFI"$ y los cruces de $45 degree$ en el régimen adverso $K_B^*$ computados mediante VFI localmente refinada sobre las vecindades de $[0.0012, 0.0022]$ y $[0.0046, 0.0056]$ (eliminando los saltos discretos de grilla gruesa) y el contraste entre $max E_"VFI" [tau_H]$ y $sup E[tau]_"CEGIS"$.

#include "tables/table4_political_markov.typ"

#figure(
  image("figures/fig3_political_volatility.pdf", width: 100%),
  caption: [Volatilidad político-fiscal y huida precautoria. *Panel A:* curvas iso-Skiba $S_G^"VFI" (p_"rev", tau_(u,G))$ mostrando cómo la amenaza futura de reversión eleva el umbral crítico aun estando hoy en el régimen favorable (el tramo plano en $tau_(u,G) = 0$ entre $p_"rev" = 18%$ y $25%$ refleja la resolución discreta de la malla de controles VFI). *Panel B:* evolución opuesta de la cota certificada de Doob CEGIS-LP ($sup E[tau]$ de `22.94` a `24.05`, redondeada hacia $+oo$) frente al máximo esperado VFI ($max E_"VFI" [tau_H]$ cayendo de `3.483` a `3.444` por huida precautoria hacia la seguridad).],
) <fig:political_markov>

// ============================================================================
// SECCIÓN 7: DINÁMICA RED QUEEN ESTOCÁSTICA
// ============================================================================
= Dinámica «Red Queen» Estocástica: Olas Tecnológicas y Divergencia Institucional

En las secciones anteriores asumimos una frontera tecnológica estacionaria ($E_t equiv 1$). Sin embargo, en la economía global la frontera productiva avanza de manera irregular mediante olas de innovación de propósito general. Demostramos aquí que instituciones burocráticas tolerables bajo crecimiento global lento pueden desencadenar un colapso irreversible en unidades de eficiencia en cuanto irrumpe una ola tecnológica acelerada.

== Teorema de Invarianza Homotética en Unidades de Eficiencia

Formalizamos el colapso dimensional exacto desde el espacio de estados bidimensional $(K_t, E_t)$ más régimen $omega_t in Omega = {L, H}$ hacia el programa Markoviano unidimensional en capital por unidad de eficiencia $hat(K)_t = K_t \/ E_t$.

#thm_box("Teorema 2 (Reducción Exacta Homotética en Dinámica Red Queen)")[
  Consideremos una economía con preferencias logarítmicas @eq:prefs y frontera tecnológica exógena Markoviana $E_(t+1) = (1 + g_(omega_t)) E_t$ con tecnología agregada homogénea reescalada por la frontera $Y_t = E_t F_(A_(e,omega)) (K_t \/ E_t, L_t)$ y restricciones de factibilidad $c_t + K_(t+1) = q K_t + Y_t$:
  1. Para todo $(K, E, omega) in (0, oo)^2 times Omega$, la función valor óptima bidimensional $V(K, E, omega)$ admite la descomposición aditiva exacta:
     $ V(K, E, omega) = hat(V)(K / E, omega) + phi_omega + (eta / (1 - beta)) log E, $ <eq:rq_decomp>
     donde $hat(V)(hat(K), omega)$ resuelve exactamente la ecuación de Bellman unidimensional reducida @eq:master_bellman con parámetros efectivos $(tilde(A)_omega, tilde(q)_omega) = (A_(e,omega)\/(1 + g_omega), q\/(1 + g_omega))$, y el vector de desplazamiento $phi = (phi_omega)_(omega in Omega)$ constituye la solución única del sistema lineal:
     $ (I - beta P) phi = (eta / (1 - beta)) log(1 + g), #h(12pt) "es decir, " phi_omega = (eta / (1 - beta)) log(1 + g_omega) + beta sum_(omega' in Omega) p_(omega omega') phi_(omega'). $
  2. La política óptima satisface la invariancia homotética exacta: $K'(K, E, omega) = (1 + g_omega) E thin hat(K)'(K \/ E, omega)$ y $L(K, E, omega) = hat(L)(K \/ E, omega)$.
  3. Verificando numéricamente la identidad @eq:rq_decomp en la parametrización de referencia ($g_L = 0.02, g_H = 0.05, p_"wave" = 0.10, p_"end" = 0.25, tau_u = 0$), el desplazamiento exacto vale $phi = [21.3207, 23.1512]$ y el error máximo residual del operador de Bellman sobre toda la malla alcanza únicamente $5.684 times 10^(-14)$ (precisión de máquina IEEE-754).
]

#proof_block[
  Sustituimos la forma separable @eq:rq_decomp en el segundo miembro de la Bellman bidimensional:
  $ cal(T) V(K, E, omega) &= max_(hat(K)' > 0, L in [0, 1)) { eta log c + (1 - eta) log(1 - L) \ &+ beta sum_(omega') p_(omega omega') [ hat(V)(K' / ((1 + g_omega) E), omega') + phi_(omega') + (eta / (1 - beta)) log((1 + g_omega) E) ] }. $
  Realizando el cambio de variables exacto $hat(K) = K \/ E$, $hat(K)' = K' \/ [(1 + g_omega) E]$ y $tilde(c) = c \/ [(1 + g_omega) E]$, la restricción presupuestaria divide limpiamente por $(1 + g_omega) E$ para convertirse en @eq:eff_budget: $tilde(c) + hat(K)' = tilde(q)_omega hat(K) + tilde(A)_omega F_1 (hat(K), L)$. A su vez, utilizando $eta log c = eta log tilde(c) + eta log(1 + g_omega) + eta log E$, el término proporcional a $log E$ fuera del máximo agrupa $eta + beta (eta \/ (1 - beta)) = eta \/ (1 - beta)$, igualando idénticamente el término final de @eq:rq_decomp en el lado izquierdo. De forma análoga, $eta log(1 + g_omega) + beta (eta \/ (1 - beta)) log(1 + g_omega) = (eta \/ (1 - beta)) log(1 + g_omega)$, cuya suma junto con $beta sum_(omega') p_(omega omega') phi_(omega')$ cancela exactamente $phi_omega$ gracias al sistema lineal $(I - beta P)phi = (eta\/(1-beta))log(1 + g)$. Esto reduce la maximización sobre $(hat(K)', L)$ a @eq:master_bellman y demuestra simultáneamente la homogeneidad lineal exacta de $K'$ respecto de $E$.
]

El Teorema 2 revela de inmediato la aritmética cruel de la dinámica *Red Queen*: una ola de innovación global ($g_H > g_L$) actúa simultáneamente sobre el denominador tanto de la productividad efectiva ($tilde(A)_H = A_e \/ (1 + g_H)$) como de la tasa efectiva de preservación del capital ($tilde(q)_H = q \/ (1 + g_H)$). Por lo tanto, el umbral normalizado de reversión de deriva de $45 degree$ durante una ola tecnológica ($hat(K)'_H (hat(K)) = hat(K)$) se ubica estrictamente por encima del umbral lento ($hat(K)_H^* > hat(S)_L$), abriendo una franja de vulnerabilidad $(hat(S)_L, hat(K)_H^*)$ inexistente en el modelo estático.

== La Paradoja «Red Queen» Pura: Contrafactual vs. Ola Tecnológica

Para visualizar la trampa *Red Queen* en su forma más pura —separándola de una recesión autárquica ordinaria—, mantenemos fija la infraestructura óptima ($tau_p = 0.20, N_f = 1$) y comparamos dos economías que arrancan con idéntica dotación inicial en unidades de eficiencia $hat(K)_0 = 0.03400$:
- *Economía burocrática ($tau_u = 0.55$):* padece una pesada carga burocrática ($A_e = 0.24242$) que, sin embargo, sigue siendo viable cuando la frontera avanza lentamente a tasa $g_L = 2%$. Sus umbrales críticos en el modelo estocástico ($g_H = 5%, p_"wave" = 10%, p_"end" = 25%$) se ubican en $hat(S)_L = 0.02731$ (régimen lento) y $hat(K)_H^* = 0.04987$ (umbral de reversión de deriva durante la ola tecnológica). Crucialmente, $hat(K)_0 = 0.03400$ se encuentra **estrictamente dentro de la ventana crítica $(hat(S)_L, hat(K)_H^*)$**.
- *Economía reformada ($tau_u = 0.00$):* elimina la burocracia improductiva ($A_e = 0.77574$), reduciendo sus umbrales críticos hasta $hat(S)_L = 0.00240$ y $hat(K)_H^* = 0.00392$ (casi diez veces por debajo de $hat(K)_0$).

Simulamos el horizonte $T_"sim" = 45$ períodos bajo una ola tecnológica temprana ($g_H = 5%$ durante $t in [1, 16)$) contrastando la trayectoria con el contrafactual sin ola ($g_t equiv g_L = 2%$):

1. *Contrafactual burocrático SIN ola tecnológica ($g_t equiv g_L = 2%$):* al mantenerse por encima del umbral lento ($hat(K)_0 = 0.03400 > hat(S)_L = 0.02731$), el país burocrático **sobrevive** y acumula lentamente en unidades de eficiencia, alcanzando $hat(K)_(45) = 0.1231$ (y $K_(45) = 0.3001$ en niveles absolutos). Incluso bajo expectativas estocásticas de ola ($p_"wave" = 10%$) pero sin que la ola llegue a materializarse, el ahorro precautorio lo eleva hasta $hat(K)_(45) = 0.1602$.
2. *País burocrático golpeado por la ola tecnológica ($g_H = 5%$ en $t in [1, 16)$):* en $t = 1$ estalla la aceleración de la frontera global y el umbral de reversión de deriva salta por encima de la dotación de capital existente ($hat(K)_H^* = 0.04987 > hat(K)_0$). Incapaz de acumular tan rápido como avanza $E_t$, la economía se desliza hacia abajo durante la ola y cae por debajo de $hat(S)_L$ antes de $t = 16$; cuando la ola concluye, el país ya quedó atrapado irreversiblemente debajo de la escala mínima viable y se contrae hasta $hat(K)_(45) = 0.01099$.
3. *País reformado ($tau_u = 0.00$) frente a la misma ola:* libre de lastres improductivos, cruza la ventana $t in [1, 16)$ sin sufrir desaceleración alguna y describe un despegue clásico en «palo de hockey» hasta $hat(K)_(45) = 2.4507$ (un acervo de capital real multiplicado hasta $K_(45) = 9.2287$).

La Figura 4A ilustra este resultado medular: el país burocrático no colapsó porque su política interna empeorara repentinamente, sino porque su burocracia de $55%$ lo mantenía apenas por encima del agua en un mundo lento ($hat(S)_L$) y lo dejó indefenso ante la aceleración externa de la frontera ($hat(K)_H^*$).

#figure(
  image("figures/fig4_red_queen_dynamics.pdf", width: 100%),
  caption: [Dinámica «Red Queen» estocástica. *Panel A:* trayectorias simuladas ($T=45$) desde $hat(K)_0 = 0.03400 in (hat(S)_L = 0.02731, hat(K)_H^* = 0.04987)$ bajo ola tecnológica temprana $t in [1, 16)$: el país burocrático ($tau_u = 0.55$) sobrevive en el contrafactual sin ola ($hat(K)_(45) = 0.1231$) pero colapsa cuando la ola eleva el umbral de deriva ($hat(K)_(45) = 0.01099$), mientras el reformado ($tau_u = 0$) despega en palo de hockey ($hat(K)_(45) = 2.4507$). *Panel B:* superficie certificada Doob CEGIS-LP $sup E[tau]$ sobre $(g_H, tau_u)$, verificada `9/9` hasta $tau_u^"max" = 0.30$ con frontera de certificabilidad en $tau_u = 0.40$.],
) <fig:red_queen>

== Superficie Certificada Doob en $(g_H, tau_u)$

Completamos el análisis *Red Queen* evaluando la síntesis certificada CEGIS-LP sobre el plano bidimensional de aceleración tecnológica $g_H in {3%, 5%, 7%}$ ($g_L = 2%, p_"wave" = 10%, p_"end" = 25%$) frente a burocracia creciente $tau_u in {0.00, 0.15, 0.30, 0.40}$ en el corredor $M_"pol" = [0.10, 0.18)$.

#cert_box("Proposición 5 (Superficie Certificada Red Queen 9/9 y Techo de Burocracia)")[
  En la Bellman reducida Markoviana @eq:master_bellman con infraestructura óptima $tau_p = 0.20, N_f = 1$:
  1. Las $9\/9$ configuraciones interiores $(g_H, tau_u) in {3%, 5%, 7%} times {0.00, 0.15, 0.30}$ quedan certificadas mediante parejas acopladas de Doob CEGIS-LP $(B_L, B_H)$ y auditadas por intervalos libres de `libm`, con tiempos esperados de escape uniformes $sup E[tau] in [15.26, 31.84]$ períodos ($T_0^"opt" in [6, 13]$).
  2. La cota certificada crece estrictamente tanto con la carga burocrática $tau_u$ como con la intensidad de la ola tecnológica $g_H$: en $tau_u = 0.30$, acelerar $g_H$ de $3%$ a $7%$ eleva $sup E[tau]$ de `26.99` a `31.84` períodos (en sintonía con el aumento en VFI de `4.000` a `4.483` períodos).
  3. En $tau_u = 0.40$ ($A_e = 0.3879$, ya inmediato al borde inferior $0.385$ del atlas estático), la deflación combinada $(tilde(A)_H, tilde(q)_H) = (0.3879\/(1 + g_H), 0.92\/(1 + g_H))$ durante la ola empuja $tilde(A)_H$ por debajo de $0.377$, estrechando el margen de salida en $M_"pol"$ más allá de la separabilidad lineal de splines `log-PWL` y fijando en $tau_u^"max" = 0.30$ el techo certificable de la superficie.
]

La Tabla 5 y la Figura 4B consignan todos los umbrales VFI $(hat(S)_L, hat(K)_H^*)$, los tiempos óptimos $max E_"VFI"$ y las cotas certificadas $sup E[tau]_"CEGIS"$ a través de los doce puntos de la grilla.

#include "tables/table5_red_queen_markov.typ"

// ============================================================================
// SECCIÓN 8: ARQUITECTURA COMPUTACIONAL cegis-bellman v0.1
// ============================================================================
= Arquitectura Computacional: De un Script Ad-Hoc a `cegis-bellman` v0.1

Además de sus teoremas económicos, este proyecto convierte el flujo numérico de verificación en un motor reutilizable y auditable de ingeniería matemática (`cegis-bellman` v0.1), diseñado explícitamente para ser extendido a nuevos modelos económicos unidimensionales sin reescribir ni la aritmética de intervalos ni el sintetizador LP.

== Separación de Responsabilidades: `core/` vs. `models/` vs. `paper/`

El repositorio sigue una arquitectura limpia en tres módulos desacoplados:

- *Núcleo agnóstico (`core/`):* encapsula toda la matemática certificada independiente de la economía particular. `interval_arith.py` provee aritmética IEEE-754 de redondeo dirigido y envolturas `Decimal` de $50$ dígitos sin `libm`; `model_api.py` define las interfaces abstractas `ParamBox`, `RegimeSpec`, `Economy1D` y `MarkovEconomy1D` junto con el solucionador VFI de alta precisión; `cegis_lp.py` implementa la síntesis determinista y Markoviana `log-PWL` sobre HiGHS (SciPy); `box_partition.py` ejecuta la bisección adaptativa de atlas 1D (`barro_Ae_atlas`); y `audit_standalone.py` ofrece un verificador terminal autocontenido sin dependencias numéricas externas (`numpy`, `scipy`, `highs`).
- *Modelos económicos enchufables (`models/`):* `mvs_canonical.py`, `barro_u_frag.py`, `political_markov.py` y `red_queen_markov.py` mapean las instituciones y los choques macroeconómicos exclusivamente a instancias de `ParamBox` y matrices de transición $P$, invocando al núcleo común.
- *Canal editorial reproducible (`paper/`):* `compute_paper_extras.py`, `generate_figures.py` y `generate_tables.py` consumen únicamente las salidas congeladas (`certificates/vfi_results.json`) para regenerar automáticamente las $4$ figuras vectoriales, las $6$ tablas principales más $2$ tablas de apéndice en Typst y el manuscrito final `paper/main.pdf`.

#alg_box("Algoritmo 1: Flujo de Síntesis Desacoplado Proposer–Verifier en cegis-bellman v0.1")[
  1. *Especificación:* el modelo económico define una lista de `RegimeSpec` (`ParamBox` en coordenadas reducidas $(A, q, beta, eta)$), la matriz $P$, el corredor $M = [b_m, h_m)$ y las tolerancias de malla B&B.
  2. *Proposer (CEGIS-LP):* inicializa los nodos `log-PWL` en $M$ y $H_1 = [h_m, 0.80]$; resuelve un LP disperso optimizando las barreras de Bellman $(B_omega, Psi_omega, W_omega)$ sujeto a las desigualdades FPBB @eq:cegis_det_stay o @eq:doob_markov sobre las tuplas activas; consulta al oráculo continuo de contraejemplos e inserta los peores nudos violadores durante hasta $28$–$32$ rondas hasta eliminar toda violación puntual, calculando $T_"cert"$ o $(T_0^"opt", epsilon.alt_0^"opt")$.
  3. *Verifier Terminal sin `libm`:* serializa $(B_omega, Psi_omega, W_omega)$ como arreglos puros y verifica cada celda mediante Branch-and-Bound continuo en el núcleo compilado *Rust* (`cegis_bellman_verifier.dll`) o en modo `--pure-python` (`Decimal` $50$ dígitos + intervalos IEEE-754).
  4. *Archivo congelado:* persiste todos los certificados aprobados en `certificates/cegis_certificates.json.xz` con verificación de huella criptográfica SHA-256.
]

== Verificador Rust Libre de `libm` y Auditoría `80/80`

Para blindar la reproducibilidad entre sistemas operativos y compiladores —eliminando cualquier divergencia oculta de funciones trascendentes `libm` como `f64::ln`—, `core/rust_verifier/src/lib.rs` está escrito íntegramente en Rust estándar *sin dependencias de crates externos* ni llamadas a `libm`. Cada logaritmo de intervalo `[x_lo, x_hi]` se acota descomponiendo por potencias de dos hacia $[1, 2)$, aplicando cuatro reducciones exactas por raíz cuadrada encajonada y evaluando la serie de potencias de términos positivos de $2 "atanh"((z - 1)\/(z + 1))$ con cota geométrica explícita de residuo y ajuste bit a bit de ULP dirigido hacia $-oo$ y $+oo$.

La Tabla 6 resume la verificación integral ejecutada sobre el archivo maestro congelado `certificates/cegis_certificates.json.xz` ($376,368$ bytes, `sha256` comenzando en `a2f9707b1c7b2ed8`):
- La auditoría integral (`python -u verify_all.py --audit-only`) valida **`80/80` certificados (`PASS`)** en `882.32` segundos ($1$ caja 4D `mvs_canonical`, $63$ bandas `barro_Ae_atlas`, $7$ parejas `political_markov` y $9$ parejas `red_queen_markov`).
- La auditoría minimalista en Python puro sin extensiones compiladas (`python -u core/audit_standalone.py certificates/cegis_certificates.json.xz --pure-python --model mvs_canonical`) valida independientemente la caja canónica 4D en `6.06` segundos.
- La batería completa de pruebas automatizadas (`python -m pytest -v tests/test_core_intervals.py tests/test_models_analytics.py tests/test_mvs_regression.py`) aprueba **`7/7` tests** en `123.73` segundos, corroborando todas las cotas de intervalos, fórmulas analíticas de Barro/$N_f$ y la regresión exacta sobre el modelo MVS original ($T_"cert" = 5$, $S_"VFI" (0.75) = 0.001589$, frente a `0.001588` en la malla refinada de Segura, 2026).

#include "tables/table6_audit_summary.typ"

// ============================================================================
// SECCIÓN 9: CONCLUSIONES Y AGENDA EMPÍRICA
// ============================================================================
= Conclusiones y Agenda Empírica ($d >= 2$)

Este artículo ha integrado en un marco analítico y computacional unificado cuatro determinantes centrales de las trampas de pobreza bajo rendimientos crecientes: la provisión óptima de infraestructura pública ($tau_p$), el peso de la burocracia improductiva ($tau_u$), la fragmentación regulatoria del tamaño empresarial ($N_f$) y el doble riesgo dinámico derivado de la reversión política y la aceleración de la frontera tecnológica mundial (*Red Queen*). A través de la ecuación maestra institucional @eq:master_Ae y del colapso homotético en unidades de eficiencia @eq:master_markov, los cuatro bloques convergen exactamente a un único programa dinámico Markoviano unidimensional certificado en tiempo finito.

Tres conclusiones de política económica emergen con nitidez de la evidencia analítica y de nuestros `80/80` certificados deterministas:

1. *Integralidad de reformas frente a ajustes parciales:* optimizar una única dimensión fiscal es insuficiente si persisten exacciones burocráticas o trabas regulatorias que fragmentan el tamaño de firma. Como demuestra la Proposición 1, forzar la atomización productiva en $N_f = 4$ fragmentos destruye exactamente la misma capacidad de despegue que apropiarse del $40%$ del ingreso en burocracia improductiva ($tau_u^"eq" = 0.40$), y el atlas CEGIS-LP expandido $53.9 times$ fija en $N_f^("max,cert") = 4.060$ el techo certificado de fragmentación compatible con el escape en $M_"pol"$.

2. *Estabilidad política e incentivos precautorios:* la sola probabilidad de reversión política eleva el punto de Skiba $S_G$ aun bajo políticas presentes limpias (curvas iso-Skiba), pero cuando el régimen adverso es recuperable los agentes privados ejecutan una *huida precautoria hacia la seguridad*: al elevarse el riesgo de reversión $p_"rev"$ de $2%$ a $18%$, $max E_"VFI"[tau_H]$ desciende de `3.483` a `3.444` períodos porque acelerar el cruce de $h_"pol" = 0.18$ blinda a la economía frente a choques futuros.

3. *Urgencia temporal bajo dinámica «Red Queen»:* en presencia de olas tecnológicas globales ($g_H in [3%, 7%]$), tolerar distorsiones internas aparentemente sostenibles en épocas de calma ($tau_u = 0.55$, viable bajo $g_L = 2%$) condena a la economía a quedar atrapada y divergir en cuanto irrumpe una ola innovadora que eleva el umbral crítico normalizado por encima de su acervo inicial ($hat(K)_0 = 0.034 in (hat(S)_L, hat(K)_H^*)$).

Finalmente, la consolidación de `cegis-bellman` v0.1 ($d = 1$) sienta las bases directas para una agenda en múltiples dimensiones continuas ($d >= 2$). Entre las extensiones empíricas prioritarias para la versión `v0.2` destacan: (i) introducir un segundo stock continuo de *capital público acumulado* $K_(g,t)$ con tasa propia de depreciación y rezagos de maduración de infraestructura; (ii) modelar economías abiertas con *deuda soberana endógena y primas de riesgo país* $(K_t, B_t)$ donde la reversión política dispare cesaciones de pagos; y (iii) extender la síntesis `log-PWL` CEGIS-LP hacia triangulaciones simpliciales adaptativas y verificadores B&B bidimensionales libres de `libm`.

// ============================================================================
// REFERENCIAS BIBLIOGRÁFICAS
// ============================================================================
#v(0.8em)
#heading(numbering: none)[Referencias]
#set text(size: 9.2pt)

- Abate, A., Ahmed, D., Giacobbe, M., & Peruffo, A. (2021). Formal synthesis of Lyapunov neural networks. _IEEE Control Systems Letters_, 5(3), 773--778.
- Acemoglu, D. (2005). Politics and economics in weak and strong states. _Journal of Monetary Economics_, 52(7), 1199--1226.
- Acemoglu, D. (2009). _Introduction to Modern Economic Growth_. Princeton University Press.
- Akao, K., Ishii, H., Kamihigashi, T., & Nishimura, K. (2022). Existence of an optimal path in a continuous-time nonconcave Ramsey model. _Pure and Applied Functional Analysis_, 7(6), 1939--1952.
- Akao, K., Kamihigashi, T., & Nishimura, K. (2011). Monotonicity and continuity of the critical capital stock in the Dechert--Nishimura model. _Journal of Mathematical Economics_, 47(6), 677--682.
- Alesina, A., & Tabellini, G. (1991). A positive theory of fiscal deficits and government debt. _Review of Economic Studies_, 57(3), 403--414.
- Barro, R. J. (1990). Government spending in a simple model of endogenous growth. _Journal of Political Economy_, 98(5, Part 2), S103--S125.
- Dechert, W. D., & Nishimura, K. (1983). A complete characterization of optimal growth paths in an aggregated model with a non-concave production function. _Journal of Economic Theory_, 31(2), 332--354.
- Devarajan, S., Swaroop, V., & Zou, H. (1996). The composition of public expenditure and economic growth. _Journal of Monetary Economics_, 37(2), 313--344.
- Doob, J. L. (1953). _Stochastic Processes_. Wiley.
- Futagami, K., Morita, Y., & Shibata, A. (1993). Dynamic analysis of an endogenous growth model with public capital. _Scandinavian Journal of Economics_, 95(4), 607--625.
- Garicano, L., Lelarge, C., & Van Reenen, J. (2016). Firm size distortions and the productivity distribution: Evidence from France. _American Economic Review_, 106(11), 3439--3479.
- Glomm, G., & Ravikumar, B. (1994). Public investment in infrastructure in a simple growth model. _Journal of Economic Dynamics and Control_, 18(6), 1173--1187.
- Guner, N., Ventura, G., & Xu, Y. (2008). Macroeconomic implications of size-dependent policies. _Review of Economic Dynamics_, 11(4), 721--744.
- Hernández-Lerma, O., & Lasserre, J. B. (1996). _Discrete-Time Markov Control Processes: Basic Optimality Criteria_. Springer.
- Howitt, P. (2000). Endogenous growth and cross-country income differences. _American Economic Review_, 90(4), 829--846.
- Hsieh, C.-T., & Klenow, P. J. (2009). Misallocation and manufacturing TFP in China and India. _Quarterly Journal of Economics_, 124(4), 1403--1448.
- Huangfu, Q., & Hall, J. A. J. (2018). Parallelizing the dual revised simplex method. _Mathematical Programming Computation_, 10, 119--142.
- Kamihigashi, T., & Roy, S. (2007). A nonsmooth, nonconvex model of optimal growth. _Journal of Economic Theory_, 132(1), 435--460.
- Kraay, A., & McKenzie, D. (2014). Do poverty traps exist? Assessing the evidence. _Journal of Economic Perspectives_, 28(3), 127--148.
- Kushner, H. J. (1967). _Stochastic Stability and Control_. Academic Press.
- Majumdar, M., & Mitra, T. (1982). Intertemporal allocation with a non-convex technology: The aggregative framework. _Journal of Economic Theory_, 27(1), 101--136.
- Meyn, S. P., & Tweedie, R. L. (2009). _Markov Chains and Stochastic Stability_ (2.ª ed.). Cambridge University Press.
- Milei, J., & Reidel, D. (2026). _Minimum Viable Scale: Bellman Barriers and the Economics of Survival_ (edición de octubre de 2026). Manuscrito de trabajo (`minscale.org/paper/mvs.pdf`).
- Moore, R. E., Kearfott, R. B., & Cloud, M. J. (2009). _Introduction to Interval Analysis_. SIAM.
- Prajna, S., Jadbabaie, A., & Pappas, G. J. (2007). A framework for worst-case and stochastic safety verification using barrier certificates. _IEEE Transactions on Automatic Control_, 52(8), 1415--1428.
- Ravanbakhsh, H., & Sankaranarayanan, S. (2019). Learning control Lyapunov functions from counterexamples and demonstrations. _Autonomous Robots_, 43, 275--307.
- Restuccia, D., & Rogerson, R. (2008). Policy distortions and aggregate productivity with heterogeneous establishments. _Review of Economic Dynamics_, 11(4), 707--720.
- Rodrik, D. (1991). Policy uncertainty and private investment in developing countries. _Journal of Development Economics_, 36(2), 229--242.
- Segura, M. (2026). _Barreras de Bellman Afiladas, Equivalencia Asintótica y Supervivencia Estocástica Certificada bajo Rendimientos Crecientes_. Noviembre de 2026, DOI: `10.5281/zenodo.24464158`.
- Skiba, A. K. (1978). Optimal growth with a convex-concave production function. _Econometrica_, 46(3), 527--539.
- Solar-Lezama, A. (2008). _Program Synthesis by Sketching_. Tesis doctoral, UC Berkeley.
- Tucker, W. (2011). _Validated Numerics: A Short Introduction to Rigorous Computations_. Princeton University Press.
- Van Valen, L. (1973). A new evolutionary law. _Evolutionary Theory_, 1, 1--30.
- Wagener, F. O. O. (2003). Skiba points and heteroclinic bifurcations, with applications to the shallow lake system. _Journal of Economic Dynamics and Control_, 27(9), 1533--1561.

// ============================================================================
// APÉNDICE TÉCNICO
// ============================================================================
#pagebreak()
#set heading(numbering: "A.1.")
#counter(heading).update(0)
#counter(figure.where(kind: table)).update(0)
#show figure.where(kind: table): set figure(numbering: n => "A." + str(n))
#set text(size: 9.0pt)
#set par(leading: 0.46em, spacing: 0.46em)
#show heading.where(level: 2): set block(above: 0.58em, below: 0.28em)
#show math.equation: set block(above: 0.36em, below: 0.36em)

= Apéndice Técnico

== Lemas de Homogenización CES y Derivadas del Punto Silla-Nodo

Verificamos explícitamente la equivalencia entre la tecnología bruta con gasto productivo de Barro (1990) y la forma reducida de @eq:master_Ae, así como las condiciones analíticas exactas empleadas en el Teorema 1 para calcular $A_"rep"$, $A_"SN"$, $A_*$ y $A_"cross"$.

Sea $F_1 (K, L) = [ (1\/2) K^(-1) + (1\/2) L^(-1) ]^(-3\/2) = (2 K L \/ (K + L))^(3\/2)$. Para todo escalar positivo $lambda > 0$, la homogeneidad de grado $theta = 3\/2$ garantiza $F_1 (lambda K, lambda L) = lambda^(3\/2) F_1 (K, L)$. Cuando regulaciones de tamaño atomizan los insumos agregados en $N_f >= 1$ establecimientos simétricos de tamaño $(K\/N_f, L\/N_f)$, cada unidad produce $F_1 (K\/N_f, L\/N_f) = N_f^(-3\/2) F_1 (K, L)$, y la suma sobre los $N_f$ fragmentos arroja exactamente $N_f dot N_f^(-3\/2) F_1 (K, L) = N_f^(-1\/2) F_1 (K, L)$.

Las derivadas parciales de $F_(A_e) (K, L) = A_e F_1 (K, L)$ respecto del capital y del trabajo toman las expresiones cerradas:
$ partial_K F_(A_e) (K, L) = 3 A_e sqrt(2) (K^(1\/2) L^(5\/2)) / (K + L)^(5\/2), #h(16pt) partial_L F_(A_e) (K, L) = 3 A_e sqrt(2) (L^(1\/2) K^(5\/2)) / (K + L)^(5\/2). $
Todo estado estacionario interior $(K^*, L^*) in (0, oo) times (0, 1)$ con consumo estacionario $c^* = (q - 1) K^* + F_(A_e) (K^*, L^*) > 0$ satisface simultáneamente la ecuación de Euler intertemporal $q + partial_K F_(A_e) (K^*, L^*) = 1\/beta$ y la relación marginal intratemporal entre ocio y consumo $((1 - eta) \/ eta) c^* \/ (1 - L^*) = partial_L F_(A_e) (K^*, L^*)$. La bifurcación silla-nodo local (ya incorporando trabajo elástico $L^*$) ocurre exactamente en $A_"SN" = 0.099524495$. Ligeramente por encima, en el umbral global de Skiba/Maxwell $A_* = 0.099611121$, el valor estacionario del equilibrio alto $V_H^*(A_*)$ iguala por primera vez al de la rama contractiva $V_"contract" (K_H^*; A_*)$, mientras que $A_"cross" = 0.110400460$ identifica la intersección numérica donde el umbral $S_"VFI" (A)$ cruza la envolvente de producto medio $s_"medio" \/ A^2$ ($s_"medio" = ((1\/beta - q)\/2^(3\/2))^2 = 0.001538$, frente a la raíz estacionaria marginal de Euler $(D\/(theta c_K))^2 = 0.000684 < s_oo^* = 0.000800$ bajo paciencia local $beta(q + theta delta) = 1.0088 > 1$).

== Isomorfismo, Síntesis CEGIS-LP, Cotas de Salida y Verificador sin `libm`

Las tripletas `log-PWL` $(B_omega, Psi_omega, W_omega)$ certificadas en las Proposiciones 2--5 parametrizan splines continuas afines por tramos en coordenada $log K$ con dominios diferenciados en `core/cegis_lp.py`: la barrera $B_omega$ se define sobre la región de tránsito $M_"pol" = [0.10, 0.18]$ con extensión constante en la cola superior ($s_"hi" = 0$ para $K >= 0.18$); el testigo inferior $W_omega$ cubre $[0.10, 5.5]$ con cola plana ($s_"hi" = 0$); y el techo superior $Psi_omega$ cubre $[10^(-4), 90.0]$ acoplado a la cola analítica logarítmica con pendiente exacta $s_"hi" = eta\/(1 - beta) = 23.333dots$:
- *Encapsulamiento del valor $(W_omega, Psi_omega)$:* certifica globalmente $W_omega (K) <= V_omega (K) <= Psi_omega (K)$ sobre $M_"pol" = [0.10, 0.18)$ y la zona intermedia de salida $H_1 = [0.18, 0.80]$, mediante evaluación por intervalos de la desigualdad de Bellman sobre cada celda $(K_j, K'_m, L_n)$ refinada por Branch-and-Bound hasta tolerancia $10^(-7)$. En la banda superior $H_2 = (0.80, oo)$ se emplea la cota analítica explícita de testigo estacionario y convexidad asintótica.
- *Permanencia acoplada y eliminación por testigo:* dentro de $M_"pol"$, toda celda candidata con acción $(K', L) in [b_m, Y_"max"] times [0, 1)$ solo requiere verificación de barrera si su envolvente superior de utilidad futura no queda estrictamente dominada por el testigo inferior: $overline(u)(K, K', L) + beta sum_(omega') p_(omega omega') overline(Psi)_(omega') (K') >= underline(W)_omega (K)$. Sobre el conjunto de celdas potencialmente óptimas sobrevivientes, el verificador exige simultáneamente que la barrera de permanencia satisfaga la cota superior estricta $overline(u)(K, K', L) + beta sum_(omega') p_(omega omega') overline(B)_(omega') (K') - underline(B)_omega (K) < 0$ (con extensión constante $B_(omega')(K') := B_(omega')(h_"pol")$ para $K' >= h_"pol"$), garantizando márgenes positivos en todo el continuo.
- *Aritmética libre de `libm` (`iv_ln_pt`):* tanto el módulo Python de $50$ dígitos (`core/interval_arith.py`) como el núcleo compilado Rust (`core/rust_verifier/src/lib.rs`) reducen cualquier argumento positivo $x = 2^m dot y$ con $y in [1, 2)$, aplican cuatro pasos sucesivos de raíz cuadrada encajonada hasta $z in [1, 2^(1\/16))$ y evalúan la serie truncada $2 sum_(k=0)^5 s^(2k+1) \/ (2k+1)$ en $s = (z - 1)\/(z + 1)$ sumando explícitamente la cota geométrica de residuo:
  $ sum_(k=6)^oo (2 s^(2k+1)) / (2k + 1) <= (2 s^(13)) / (13 (1 - s^2)), #h(14pt) s <= (2^(1\/16) - 1) / (2^(1\/16) + 1) < 0.02167, $
  garantizando un error de truncamiento estrictamente menor que $10^(-22)$ antes del ajuste ULP IEEE-754 dirigido hacia $-oo$ en extremos inferiores y hacia $+oo$ en extremos superiores. En la caja canónica 4D `mvs_canonical`, todos los márgenes de verificación superan estrictamente las tolerancias: descenso del techo $d_"ub"^Psi = -6.89 times 10^(-5)$, holgura de testigo $d_"ub"^W = -1.49 times 10^(-6)$, residuo de barrera FPBB $d_"ub"^B = -2.00 times 10^(-4)$, márgenes de salida $Delta_"exit"^M = 0.7623$, $Delta_"exit"^(H_1) = 0.2379$, $Delta_"exit"^(H_2) = 2.7731$ y holguras de derivada en los bordes $b = 0.10$ y $h = 0.28$ ($62.73$ y $12.76$).

La Tabla A.1 desglosa las $63$ bandas contiguas del atlas `barro_Ae_atlas` agrupadas por horizonte certificado $T_"cert" in {4, 5, 6, 7}$, detallando sus rangos equivalentes de fragmentación $N_f$ y peores márgenes de intervalo verificados.

#include "tables/tableA1_atlas_tiers.typ"

== Cota de Parada Opcional de Doob Acoplada a Selección Óptima

Para todo par inicial $(K_0, omega_0) in M_"pol" times Omega$, sea $tau_"exit" := inf {t >= 0 : K_t >= h_"pol"}$ el primer instante de salida bajo cualquier política estocástica admisible óptima $pi^*$ (nótese que $K_0 < h_"pol"$ implica estrictamente $tau_"exit" >= 1$). Bajo la condición certificada de ausencia casi segura de salida inferior ($K_t >= b_m$ para $0 <= t < tau_"exit"$ y $K_(tau_"exit") >= h_"pol"$, garantizada por los márgenes positivos $Delta_"exit"^M > 0$ frente a $E^+$ y asumiendo $Psi_omega$ no decreciente en $[h_"pol", Y_"max"]$), introducimos el proceso detenido descontado de Bellman $Z_t := sum_(s=0)^(t-1) beta^s u(c_s, L_s) + beta^t B_(omega_t) (K_t)$ en $t <= tau_"exit"$ (manteniendo la extensión constante $B_(omega')(K') := B_(omega')(h_"pol")$ para $K' >= h_"pol"$). Por la desigualdad acoplada @eq:doob_markov verificada en CEGIS-LP, para todo $t < tau_"exit"$ se cumple:
$ E [ Z_(t+1) | cal(F)_t ] = sum_(s=0)^t beta^s u(c_s, L_s) + beta^(t+1) sum_(omega') p_(omega_t omega') B_(omega') (K_(t+1)) <= sum_(s=0)^(t-1) beta^s u(c_s, L_s) + beta^t B_(omega_t) (K_t) = Z_t, $
probando que ${Z_(t and tau_"exit")}_(t >= 0)$ es una supermartingala discreta. Aplicando el Teorema de Parada Opcional de Doob al tiempo acotado $tau_"exit" and T_0$, y descomponiendo el resto descontado entre trayectorias que salen en algún instante $1 <= tau_"exit" <= T_0$ (probabilidad $p_(T_0) := P_(K_0, omega_0)(tau_"exit" <= T_0)$, cuyo primer factor de descuento satisface $beta^(tau_"exit") <= beta_+$ precisamente por ser $tau_"exit" >= 1$, acotando el exceso de techo por $beta_+ d_"exit"$ tras @eq:doob_bound) frente a las que permanecen hasta $T_0$ (exceso acotado por $beta_+^(T_0) d_"stay"$), el encapsulamiento $W <= V <= Psi$ rinde:
$ W_(omega_0)(K_0) <= V_(omega_0)(K_0) <= B_(omega_0)(K_0) + p_(T_0) beta_+ d_"exit" + (1 - p_(T_0)) beta_+^(T_0) d_"stay". $
Restando $B_(omega_0)(K_0)$ y acotando inferiormente $W_(omega_0)(K_0) - B_(omega_0)(K_0) >= m_"inf" > 0$ se despeja uniformemente $p_(T_0) >= epsilon.alt_0 (T_0) = (m_"inf" - beta_+^(T_0) d_"stay") \/ (beta_+ d_"exit" - beta_+^(T_0) d_"stay") > 0$. Por la propiedad fuerte de Markov, el número de bloques sucesivos de $T_0$ períodos antes de escapar queda dominado estocásticamente por una variable geométrica de parámetro $epsilon.alt_0 (T_0)$, lo cual implica $tau_"exit" < oo$ casi seguramente y establece exactamente la cota reportada en las Tablas 4 y 5:
$ sup_((K_0, omega_0) in M_"pol" times Omega) E_(K_0, omega_0) [ tau_"exit" ] <= (T_0^"opt") / (epsilon.alt_0^"opt"). $

Como complemento cuantitativo de la Sección 6.2, la Tabla A.2 reúne las $12$ mediciones de VFI continua sobre regímenes adversos extremos ($A_B in {0.35, 0.095}$), cuantificando el incremento precautorio de inversión $Delta K'_G$ en $M$.

#include "tables/tableA2_flight_to_safety.typ"

== Verificación Numérica del Teorema 2 e Independencia del Desplazamiento $phi$

Para corroborar independientemente la reducción homotética exacta establecida en el Teorema 2, evaluamos el operador original de Bellman bidimensional sobre tres niveles distintos de la frontera tecnológica inicial $E in {1.0, 2.5, 10.0}$ manteniendo la malla normalizada $hat(K) = K \/ E in [10^(-4), 50.0]$ en la parametrización estocástica de referencia ($g_L = 0.02, g_H = 0.05, p_"wave" = 0.10, p_"end" = 0.25, tau_u = 0$). Al resolver el sistema lineal $(I - beta P)phi = (eta\/(1 - beta))log(1 + g)$ se obtiene exactamente $phi_L = 21.320704$ y $phi_H = 23.151232$. Evaluando luego un paso del operador de Bellman original sobre $V(K, E, omega) := hat(V)(K\/E, omega) + phi_omega + (eta\/(1 - beta))log E$, la diferencia máxima absoluta entre $V(K, E, omega)$ y $(cal(T) V)(K, E, omega)$ en todos los nodos de la malla y para todos los $E$ evaluados asciende a $5.68434 times 10^(-14)$, coincidiendo exactamente con el épsilon de máquina IEEE-754 de doble precisión y confirmando la invarianza perfecta de las políticas normalizadas $(hat(K)', L)$.

== Protocolo de Reproducción Integral y Verificación Automatizada

Todos los certificados, cifras numéricas, tablas y figuras del presente manuscrito se reproducen deterministamente desde la raíz del repositorio `cegis-bellman` (#link("https://github.com/lordtiva/cegis-bellman")[`github.com/lordtiva/cegis-bellman`], archivo permanente en Zenodo con Concept DOI #link("https://doi.org/10.5281/zenodo.24536780")[`10.5281/zenodo.24536780`]) sin alterar el archivo congelado `certificates/cegis_certificates.json.xz` ($376,368$ bytes, SHA-256 `a2f9707b1c7b2ed8...`):

1. *Auditoría independiente de los $80\/80$ certificados congelados (Rust sin `libm` + VFI):*
   ```
   python -u verify_all.py --audit-only
   ```
2. *Auditoría minimalista en Python puro (cero dependencias externas, caja 4D MVS):*
   ```
   python -u core/audit_standalone.py certificates/cegis_certificates.json.xz --pure-python --model mvs_canonical
   ```
3. *Batería completa de pruebas unitarias, analíticas y de regresión (`7/7` tests):*
   ```
   python -m pytest -v tests/test_core_intervals.py tests/test_models_analytics.py tests/test_mvs_regression.py
   ```
4. *Regeneración de refinamientos VFI, $4$ figuras, $6$ tablas principales más $2$ de apéndice y compilación Typst:*
   ```
   python -u paper/compute_paper_extras.py
   python -u paper/generate_figures.py
   python -u paper/generate_tables.py
   python -c "import typst; typst.compile('paper/main.typ', output='paper/main.pdf')"
   ```
