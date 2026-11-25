# La Curva en U Institucional, Volatilidad Política y Dinámica «Red Queen»: Supervivencia Económica Certificada bajo Rendimientos Crecientes

[![Verify CEGIS-Bellman Certificates](https://github.com/lordtiva/cegis-bellman/actions/workflows/verify.yml/badge.svg)](https://github.com/lordtiva/cegis-bellman/actions/workflows/verify.yml)

Motor modular **CEGIS-LP** (`cegis-bellman` v0.1, $d=1$) para síntesis determinista de **Barreras de Bellman de Primer Paso** y auditoría continua por intervalos libre de `libm` (en Rust y `Decimal` de 50 dígitos), archivo congelado de **`80/80` certificados** (`certificates/cegis_certificates.json.xz`), `4` figuras, `8` tablas en Typst y manuscrito reproducible ([`paper/main.typ`](paper/main.typ) / [`paper/main.pdf`](paper/main.pdf)), construido sobre *Minimum Viable Scale* de Milei y Reidel (2026) y la arquitectura de Segura (2026, Paper 1: [`10.5281/zenodo.24464158`](https://doi.org/10.5281/zenodo.24464158)).

---

## Resultados principales certificados

1. **Curva en U Institucional e Isomorfismo Burocracia–Fragmentación (Sección 4):**
   - **Ecuación maestra de productividad efectiva:** unifica gasto público productivo ($`\tau_p`$), burocracia improductiva ($`\tau_u`$) y fragmentación regulatoria ($`N_f`$) en el escalar exacto $`A_e(\tau_p, \tau_u, N_f) = A_0 \tau_p^\alpha (1 - \tau_p - \tau_u) N_f^{-(\theta - 1)}`$ bajo tecnología CES armónica con rendimientos crecientes ($\theta = 3/2$).
   - **Teorema 1 (Curva en U institucional):** prueba un único máximo productivo en $`\tau_p^*(\tau_u) = \gamma(1 - \tau_u)`$ ($`\tau_p^*(0) = 0.20`$, $`A_e^{\text{pico}} = 0.775739`$) y caracteriza exactamente el repulsor físico ($`A_{\text{rep}} = 0.073485`$), la bifurcación silla-nodo ($`A_{\text{SN}} = 0.099524`$), el umbral global de Skiba/Maxwell ($`A_* = 0.099611`$) y el cruce con la envolvente de Euler ($`A_{\text{cross}} = 0.110400`$).
   - **Proposición 1 (isomorfismo burocracia–fragmentación):** $`\tau_u^{\text{eq}}(N_f; \tau_p) = (1 - \tau_p)(1 - N_f^{-(\theta - 1)})`$. En $`\tau_p = 0.20`$, fragmentar una empresa en $`N_f = 4`$ unidades equivale exactamente a una extracción burocrática del $40\%$ ($`\tau_u^{\text{eq}} = 0.40`$), mientras la existencia del equilibrio próspero colapsa en $`N_{f,*} = 56.69 < N_{f,\text{SN}} = 56.79`$.

2. **Expansión $53.9\times$ del Espacio Institucional Certificado (Sección 5):**
   - **Proposición 2 (atlas continuo `barro_Ae_atlas`):** `63` bandas contiguas sin huecos sobre $`A_e \in [0.385, 0.780]`$ fijando $(q, \beta, \eta) = (0.92, 0.97, 0.70)$, ampliando en un factor **$53.93\times$** el área certificada del plano $`(\tau_p, \tau_u)`$ (de `0.003445` a `0.18579`) y extendiendo la banda viable hasta $`\tau_p \in [0.00507, 0.71083]`$ con burocracia tolerable hasta $`\tau_u^{\max} = 0.4030`$.
   - **Proposición 3 (corredor de fragmentación):** transfiere la certificación determinista a todo el corredor $`N_f \in [1.00, 4.060]`$ con plazos certificados $`T_{\text{cert}} \in [4, 7]`$.

3. **Volatilidad Político-Fiscal y Huida Precautoria Certificada (Sección 6):**
   - **Proposición 4 (`political_markov`):** certifica **`7/7` parejas acopladas de súper-barreras de Doob** sobre $`M_{\text{pol}} = [0.10, 0.18)`$ entre el régimen reformista $G$ ($`A_G = 0.775739`$) y el régimen adverso $B$ ($`A_B = 0.45`$) para $`p_{\text{rev}} \in [2\%, 18\%]`$ y $`p_{\text{ref}} \in \{0.25, 1/3, 0.50\}`$, con cotas de tiempo esperado $`\sup \mathbb{E}[\tau] \in [20.81, 25.51]`$ períodos.
   - **Huida precautoria hacia la seguridad (VFI continua):** al elevarse el riesgo de reversión $`p_{\text{rev}}`$ de $2\%$ a $18\%$ ($`p_{\text{ref}} = 1/3`$), el máximo esperado VFI del tiempo de permanencia $`\max_{M_{\text{pol}} \times \Omega} \mathbb{E}_{\text{VFI}}[\tau_H]`$ **desciende de `3.483` a `3.444` períodos**.

4. **Dinámica «Red Queen» Estocástica y Motor Modular `cegis-bellman` v0.1 (Secciones 7 y 8):**
   - **Teorema 2 (colapso homotético exacto):** bajo crecimiento estocástico de la frontera $`E_{t+1} = (1 + g_\omega) E_t`$, la dinámica bidimensional colapsa exactamente hacia $`\hat{K}_t = K_t / E_t`$ con parámetros dependientes del régimen $`\tilde{A}_\omega = A_{e,\omega}/(1 + g_\omega)`$ y $`\tilde{q}_\omega = q/(1 + g_\omega)`$ (desplazamiento $\phi = [21.3207, 23.1512]$, error máximo de Bellman $`5.68 \times 10^{-14}`$).
   - **Proposición 5 (`red_queen_markov`):** verifica la paradoja *Red Queen* pura desde $`\hat{K}_0 = 0.034 \in (\hat{S}_L, \hat{S}_H)`$ en $`\tau_u = 0.55`$, y certifica **`9/9` configuraciones** $`(g_H, \tau_u)`$ hasta $`\tau_u^{\max} = 0.30`$ con cotas de Doob entre `15.25` y `31.84` períodos.
   - **Archivo congelado verificado (`80/80` `PASS`):** `certificates/cegis_certificates.json.xz` (`376,368` bytes, SHA-256 `a2f9707b1c7b2ed8...`) aprobado íntegramente por el núcleo nativo en Rust sin `libm` (`882.32 s`) y por el auditor independiente en Python puro.

---

## Estructura del repositorio

```text
cegis-bellman/
├── .github/workflows/verify.yml    # CI en GitHub Actions (compila Rust, pytest y audita 80/80)
├── pyproject.toml                  # Paquete importable cegis_bellman
├── README.md
├── LICENSE                         # Licencia MIT
├── .zenodo.json                    # Metadatos para archivo permanente en Zenodo
├── verify_all.py                   # Orquestador completo (síntesis, VFI y auditoría)
├── core/                           # Motor genérico 1D (reutilizable)
│   ├── model_api.py                # ParamBox, Economy1D, MarkovEconomy1D, solvers VFI
│   ├── interval_arith.py           # Intervalos Decimal 50 dígitos (sin libm) + mappers
│   ├── pwl_basis.py                # Splines log-PWL exactos + operadores CSR para HiGHS
│   ├── verifier_bridge.py          # Puente ctypes a Rust + auditoría de colas y Doob eps_0
│   ├── cegis_lp.py                 # Proposer-Verifier CEGIS-LP (estático y acoplado Markov)
│   ├── box_partition.py            # Partición adaptativa 1D/2D sobre cajas de política
│   ├── cert_schema.py              # Esquema JSON.xz v1.0 con integridad SHA-256
│   ├── audit_standalone.py         # Auditor minimalista (stdlib + Rust opcional / --pure-python)
│   └── rust_verifier/              # Verificador B&B nativo en Rust puro sin crates ni libm
│       ├── build.py
│       └── src/lib.rs
├── models/                         # Modelos económicos sobre la interfaz core/
│   ├── mvs_canonical.py            # Benchmark canónico de regresión (Paper 1)
│   ├── barro_u_frag.py             # Curva en U Barro–CES + fragmentación N_f
│   ├── political_markov.py         # Alternancia fiscal G <-> B y riesgo político endógeno
│   └── red_queen_markov.py         # Olas tecnológicas estocásticas g_L <-> g_H
├── certificates/                   # Certificados exportados (.json.xz) y resultados VFI
│   ├── cegis_certificates.json.xz  # Archivo congelado de 80/80 certificados (376,368 B)
│   └── vfi_results.json
├── tests/                          # Suite pytest (intervalos, regresión, analítica, E2E)
└── paper/                          # Figuras, tablas, scripts extras y manuscrito Typst -> PDF
    ├── compute_paper_extras.py
    ├── generate_figures.py
    ├── generate_tables.py
    ├── figures/
    ├── tables/
    ├── main.typ
    └── main.pdf
```

---

## Instalación y reproducibilidad

```bash
pip install -e ".[dev]"
python core/rust_verifier/build.py

# Auditoría independiente de los 80/80 certificados congelados (Rust sin libm + VFI):
python -u verify_all.py --audit-only

# Auditoría standalone (80/80 en Rust; o 100% Python puro en caja 4D MVS):
python -u core/audit_standalone.py certificates/cegis_certificates.json.xz
python -u core/audit_standalone.py certificates/cegis_certificates.json.xz --pure-python --model mvs_canonical

# Suite de pruebas unitarias, analíticas y de regresión:
python -m pytest -v tests/test_core_intervals.py tests/test_models_analytics.py tests/test_mvs_regression.py

# Regenerar figuras, tablas y compilar el manuscrito PDF:
python -u paper/compute_paper_extras.py
python -u paper/generate_figures.py
python -u paper/generate_tables.py
python -c "import typst; typst.compile('paper/main.typ', output='paper/main.pdf')"
```

---

## Licencia

Distribuido bajo licencia MIT ([LICENSE](LICENSE)).
