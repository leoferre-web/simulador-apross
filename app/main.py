# ============================================================
# BLOQUE 01 — Imports
# ============================================================

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.repositories import Repo
from core.services import SimulationService


# ============================================================
# BLOQUE 02 — Configuración de página
# ============================================================

st.set_page_config(
    page_title="Simulador APROSS OYTE",
    layout="wide",
)


# ============================================================
# BLOQUE 03 — Estilos CSS
# ============================================================

st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1180px;
}

.app-window {
    background: #ffffff;
    border: 1px solid #dedbd2;
    border-radius: 18px;
    padding: 0;
    box-shadow: 0 8px 24px rgba(0,0,0,.08);
    overflow: hidden;
}

.top-bar {
    height: 42px;
    background: #f4f1ea;
    border-bottom: 1px solid #e2ded4;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.dots {
    position: absolute;
    left: 18px;
    display: flex;
    gap: 7px;
}

.dot {
    width: 11px;
    height: 11px;
    border-radius: 50%;
}

.red { background:#e86b5c; }
.yellow { background:#e8bf4f; }
.green { background:#52b788; }

.url-pill {
    background: #fff;
    border: 1px solid #ddd8ce;
    border-radius: 999px;
    padding: 5px 90px;
    color: #999;
    font-size: 12px;
}

.inner {
    padding: 36px 44px;
}

.kicker {
    color:#8f8a80;
    font-size:12px;
    text-transform:uppercase;
    letter-spacing:.04em;
    margin-bottom:3px;
}

.main-title {
    font-size:26px;
    font-weight:800;
    color:#2b2b2b;
    margin:0;
}

.metric-grid {
    display:grid;
    grid-template-columns:repeat(4, 1fr);
    gap:20px;
    margin-top:32px;
}

.metric-card {
    background:#f5f2ec;
    border-radius:12px;
    padding:20px 22px;
    min-height:92px;
}

.metric-label {
    color:#716c64;
    font-size:13px;
    margin-bottom:8px;
}

.metric-value {
    color:#2c2c2c;
    font-size:25px;
    font-weight:800;
}

.metric-sub {
    color:#9b958b;
    font-size:12px;
    margin-top:4px;
}

.green-value {
    color:#08765f;
}

.red-value {
    color:#a33d2c;
}

.section-title {
    margin-top:22px;
    margin-bottom:10px;
    color:#6f6a62;
    font-size:15px;
}

.bar-row {
    display:grid;
    grid-template-columns:90px 1fr 110px;
    align-items:center;
    gap:18px;
    margin:12px 0;
    font-size:13px;
    color:#777169;
}

.bar-bg {
    height:18px;
    background:#dfddd5;
    border-radius:999px;
    overflow:hidden;
}

.bar-fill {
    height:18px;
    background:#0d765f;
    border-radius:999px;
}

.validation-card {
    background:#f5f2ec;
    border-radius:12px;
    padding:22px;
}

.validation-title {
    font-weight:800;
    color:#333;
    margin-bottom:14px;
}

.validation-row {
    display:flex;
    justify-content:space-between;
    gap:20px;
    padding:7px 0;
    font-size:13px;
    border-bottom:1px solid #e5e0d6;
    color:#5f5a53;
}

.validation-row:last-child {
    border-bottom:none;
}

.validation-row strong {
    color:#2d2d2d;
    text-align:right;
}

.check-ok {
    color:#08765f;
    font-weight:800;
}

.check-no {
    color:#a33d2c;
    font-weight:800;
}

.result-placeholder {
    margin-top:40px;
    border:2px dashed #ddd6c9;
    border-radius:14px;
    min-height:120px;
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    color:#aaa39a;
    font-style:italic;
}

.result-box {
    margin-top:32px;
    border:1px solid #e5dfd3;
    border-radius:14px;
    padding:22px;
    background:#fff;
}

.result-ok {
    background:#d9f1e9;
    color:#0e6d5e;
    padding:7px 14px;
    border-radius:999px;
    display:inline-block;
    font-weight:700;
    font-size:13px;
}

.result-no {
    background:#f8e3db;
    color:#924126;
    padding:7px 14px;
    border-radius:999px;
    display:inline-block;
    font-weight:700;
    font-size:13px;
}

.footer-note {
    color:#9d978d;
    font-size:11px;
    margin-top:16px;
}

button[kind="primary"] {
    background:#1f5b6b !important;
    border-radius:8px !important;
}

@media(max-width:850px) {

    .metric-grid {
        grid-template-columns:repeat(2,1fr);
    }

    .url-pill {
        padding:5px 30px;
    }
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# BLOQUE 04 — Funciones auxiliares
# ============================================================

def money(value):

    try:
        value = float(value or 0)
    except Exception:
        value = 0

    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:,.1f}M"

    return f"{sign}${value:,.2f}"


def percentage(value):

    try:
        return f"{float(value):.0%}"
    except Exception:
        return "-"


def normalize_code(value):
    """
    Evita códigos visualmente como 123456.0.
    """

    if pd.isna(value):
        return ""

    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


def render_browser_header(
    path="simulador-convenio.aprossoyte.local"
):

    st.markdown(
        f"""
        <div class="top-bar">

            <div class="dots">
                <span class="dot red"></span>
                <span class="dot yellow"></span>
                <span class="dot green"></span>
            </div>

            <div class="url-pill">
                {path}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# BLOQUE 05 — Carga de datos desde Supabase
# ============================================================

@st.cache_data(ttl=300)
def load_data():

    repo = Repo()

    troqueles = repo.table_df(
        "src_troqueles_alb"
    )

    convenio = repo.table_df(
        "src_convenio_oyte"
    )

    bandas = repo.table_df(
        "src_bandas_descuento"
    )

    liquidaciones = repo.table_df(
        "src_liquidaciones"
    )

    return (
        troqueles,
        convenio,
        bandas,
        liquidaciones,
    )


try:

    (
        troqueles,
        convenio,
        bandas,
        liquidaciones,
    ) = load_data()

except Exception as e:

    st.error(
        f"No se pudieron cargar los datos desde Supabase: {e}"
    )

    st.stop()


# ============================================================
# BLOQUE 06 — Servicios
# ============================================================

repo = Repo()

svc = SimulationService(
    troqueles=troqueles,
    convenio=convenio,
    bandas=bandas,
    liquidaciones=liquidaciones,
)


# ============================================================
# BLOQUE 07 — Navegación
# ============================================================

if "view" not in st.session_state:
    st.session_state.view = "panel"

view = st.session_state.view


# ============================================================
# BLOQUE 08 — PANEL FINANCIERO
# ============================================================

if view == "panel":

    st.markdown(
        '<div class="app-window">',
        unsafe_allow_html=True,
    )

    render_browser_header()

    st.markdown(
        '<div class="inner">',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="kicker">
            Simulador de convenio
        </div>

        <h1 class="main-title">
            APROSS OYTE — Panel financiero
        </h1>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Historial
    # --------------------------------------------------------

    try:

        hist = repo.table_df(
            "simulacion_resultados",
            limit=500,
        )

    except Exception:

        hist = pd.DataFrame()

    # Solo Caso A
    if (
        not hist.empty
        and "tipo_caso" in hist.columns
    ):

        hist = hist[
            hist["tipo_caso"] == "A"
        ].copy()

    # --------------------------------------------------------
    # Métricas
    # --------------------------------------------------------

    cantidad_simulaciones = len(hist)

    recomendadas = 0
    no_recomendadas = 0

    if (
        not hist.empty
        and "recomendacion" in hist.columns
    ):

        recomendadas = int(
            hist["recomendacion"]
            .fillna(False)
            .astype(bool)
            .sum()
        )

        no_recomendadas = (
            cantidad_simulaciones
            - recomendadas
        )

    fact_actual = 0
    fact_proyectada = 0

    if not hist.empty:

        hist_ordenado = hist.copy()

        if "fecha_corrida" in hist_ordenado.columns:

            hist_ordenado[
                "fecha_corrida"
            ] = pd.to_datetime(
                hist_ordenado[
                    "fecha_corrida"
                ],
                errors="coerce",
            )

            hist_ordenado = (
                hist_ordenado.sort_values(
                    "fecha_corrida",
                    ascending=False,
                )
            )

        if not hist_ordenado.empty:

            ultima = hist_ordenado.iloc[0]

            fact_actual = float(
                ultima.get(
                    "facturacion_actual_anual",
                    0,
                )
                or 0
            )

            fact_proyectada = float(
                ultima.get(
                    "facturacion_proyectada_anual",
                    0,
                )
                or 0
            )

    impacto = (
        fact_proyectada
        - fact_actual
    )

    st.markdown(
        f"""
        <div class="metric-grid">

            <div class="metric-card">
                <div class="metric-label">
                    Facturación actual anual
                </div>
                <div class="metric-value">
                    {money(fact_actual)}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">
                    Facturación proyectada
                </div>
                <div class="metric-value">
                    {money(fact_proyectada)}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">
                    Impacto neto estimado
                </div>
                <div class="metric-value {'green-value' if impacto <= 0 else 'red-value'}">
                    {money(impacto)}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">
                    Troqueles evaluados
                </div>

                <div class="metric-value">
                    {cantidad_simulaciones}
                </div>

                <div class="metric-sub">
                    {recomendadas} recomendados ·
                    {no_recomendadas} no recomendados
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Comparación financiera
    # --------------------------------------------------------

    max_bar = max(
        fact_actual,
        fact_proyectada,
        1,
    )

    actual_pct = min(
        100,
        fact_actual / max_bar * 100,
    )

    proyectada_pct = min(
        100,
        fact_proyectada / max_bar * 100,
    )

    st.markdown(
        f"""
        <div class="section-title">
            Facturación anual: actual vs. proyectada
        </div>

        <div class="bar-row">

            <div>Actual</div>

            <div class="bar-bg">
                <div
                    class="bar-fill"
                    style="
                        width:{actual_pct}%;
                        background:#d8d5cc;
                    ">
                </div>
            </div>

            <strong>
                {money(fact_actual)}
            </strong>

        </div>

        <div class="bar-row">

            <div>Proyectada</div>

            <div class="bar-bg">

                <div
                    class="bar-fill"
                    style="
                        width:{proyectada_pct}%;
                    ">
                </div>

            </div>

            <strong>
                {money(fact_proyectada)}
            </strong>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Historial reciente
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Evaluaciones recientes de incorporación</div>',
        unsafe_allow_html=True,
    )

    rows_html = ""

    if not hist.empty:

        data = hist.copy()

        if "fecha_corrida" in data.columns:

            data["fecha_corrida"] = (
                pd.to_datetime(
                    data["fecha_corrida"],
                    errors="coerce",
                )
            )

            data = data.sort_values(
                "fecha_corrida",
                ascending=False,
            )

        data = data.head(10)

        for _, r in data.iterrows():

            codigo = normalize_code(
                r.get("codigo_troquel")
            )

            recomendacion = bool(
                r.get("recomendacion")
            )

            badge = (
                "Recomendado"
                if recomendacion
                else "No recomendado"
            )

            badge_class = (
                "badge-ok"
                if recomendacion
                else "badge-no"
            )

            monodroga = ""

            # Buscar descripción en ALB vigente
            candidato = svc.get_troquel(
                codigo
            )

            if candidato:
                monodroga = str(
                    candidato.get(
                        "monodro",
                        "",
                    )
                    or ""
                )

            fa = float(
                r.get(
                    "facturacion_actual_anual",
                    0,
                )
                or 0
            )

            fp = float(
                r.get(
                    "facturacion_proyectada_anual",
                    0,
                )
                or 0
            )

            imp = fp - fa

            imp_class = (
                "positive"
                if imp < 0
                else
                "negative"
                if imp > 0
                else
                "muted"
            )

            rows_html += f"""
            <tr>

                <td>{codigo}</td>

                <td>
                    {monodroga}
                </td>

                <td>
                    <span class="badge {badge_class}">
                        {badge}
                    </span>
                </td>

                <td
                    class="{imp_class}"
                    style="text-align:right;"
                >
                    {money(imp)}
                </td>

            </tr>
            """

    else:

        rows_html = """
        <tr>
            <td
                colspan="4"
                style="
                    text-align:center;
                    color:#999;
                    padding:20px;
                "
            >
                Todavía no hay simulaciones realizadas.
            </td>
        </tr>
        """

    components.html(
        f"""
        <style>

        .reco-table {{
            width:100%;
            border-collapse:collapse;
            font-family:Arial, sans-serif;
            font-size:14px;
        }}

        .reco-table th {{
            background:#1f5b6b;
            color:white;
            padding:10px 13px;
            text-align:left;
        }}

        .reco-table td {{
            padding:10px 13px;
            border-bottom:1px solid #eeeae2;
            color:#333;
        }}

        .reco-table tr:nth-child(even) {{
            background:#f6f3ed;
        }}

        .badge {{
            display:inline-block;
            border-radius:999px;
            padding:4px 18px;
            font-size:12px;
        }}

        .badge-ok {{
            background:#d9f1e9;
            color:#0e6d5e;
        }}

        .badge-no {{
            background:#f8e3db;
            color:#924126;
        }}

        .positive {{
            color:#08765f;
            font-weight:800;
        }}

        .negative {{
            color:#a33d2c;
            font-weight:800;
        }}

        .muted {{
            color:#99948b;
            font-weight:700;
        }}

        </style>

        <table class="reco-table">

            <thead>

                <tr>
                    <th>Troquel</th>
                    <th>Monodroga</th>
                    <th>Recomendación</th>
                    <th style="text-align:right;">
                        Impacto anual
                    </th>
                </tr>

            </thead>

            <tbody>
                {rows_html}
            </tbody>

        </table>
        """,
        height=430,
        scrolling=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(
        "Nueva simulación",
        type="primary",
    ):

        st.session_state.view = (
            "simular"
        )

        st.rerun()

    st.markdown(
        "</div></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# BLOQUE 09 — NUEVA SIMULACIÓN — CASO A
# ============================================================

else:

    st.markdown(
        '<div class="app-window">',
        unsafe_allow_html=True,
    )

    render_browser_header(
        "simulador-convenio.aprossoyte.local/nueva-simulacion"
    )

    st.markdown(
        '<div class="inner">',
        unsafe_allow_html=True,
    )

    if st.button(
        "← Volver al panel"
    ):

        st.session_state.view = "panel"

        st.rerun()

    st.markdown(
        """
        <div class="kicker">
            Simulador de convenio
        </div>

        <h1 class="main-title">
            Nueva simulación — Alta de troquel
        </h1>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Lista de troqueles vigentes
    # --------------------------------------------------------

    if (
        not svc.troqueles.empty
        and "tronquel" in svc.troqueles.columns
    ):

        opciones = (
            svc.troqueles[
                "tronquel"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        opciones = sorted(
            opciones
        )

    else:

        opciones = []

    left, right = st.columns(
        [1.15, 0.95]
    )

    # ========================================================
    # FORMULARIO
    # ========================================================

    with left:

        if opciones:

            codigo = st.selectbox(
                "Código de troquel",
                opciones,
            )

        else:

            codigo = st.text_input(
                "Código de troquel"
            )

        months_window = st.slider(
            "Vigencia máxima del precio en meses",
            min_value=1,
            max_value=12,
            value=6,
        )

        ejecutar = st.button(
            "Ejecutar simulación",
            type="primary",
        )

    # ========================================================
    # VALIDACIÓN PREVIA
    # ========================================================

    candidato = (
        svc.get_troquel(codigo)
        if codigo
        else None
    )

    with right:

        if candidato:

            monodroga = (
                candidato.get(
                    "monodro",
                    "",
                )
                or ""
            )

            forma = (
                candidato.get(
                    "formas",
                    "",
                )
                or ""
            )

            potencia = (
                candidato.get(
                    "potencia",
                    "",
                )
                or ""
            )

            unidad = (
                candidato.get(
                    "unidad_potencia",
                    "",
                )
                or ""
            )

            laboratorio = (
                candidato.get(
                    "desc_laboratorio",
                    "",
                )
                or ""
            )

            pvp = (
                candidato.get(
                    "precio",
                    0,
                )
                or 0
            )

            fecha = candidato.get(
                "fecha"
            )

            baja = candidato.get(
                "baja"
            )

            en_convenio = (
                svc.is_in_convenio(
                    codigo
                )
            )

            banda_actual = (
                svc.current_band(
                    candidato
                )
            )

            banda_hipotetica = (
                svc.hypothetical_band(
                    candidato
                )
            )

            segundo_pvp = (
                svc.second_highest_price(
                    candidato
                )
            )

            mejora_banda = (
                banda_hipotetica.get(
                    "porcentaje_descuento",
                    0,
                )
                >
                banda_actual.get(
                    "porcentaje_descuento",
                    0,
                )
            )

            cumple_pvp = (
                segundo_pvp is not None
                and float(pvp)
                <= float(segundo_pvp)
            )

            try:
                baja_num = int(
                    float(baja)
                )
            except Exception:
                baja_num = None

            activo = (
                baja_num == 0
            )

            st.markdown(
                f"""
                <div class="validation-card">

                    <div class="validation-title">
                        Validación previa
                    </div>

                    <div class="validation-row">
                        <span>Presentación activa</span>
                        <strong class="{'check-ok' if activo else 'check-no'}">
                            {'Sí' if activo else 'No'}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Fecha vigencia PVP</span>
                        <strong>
                            {fecha if fecha else '-'}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Actualmente en convenio</span>
                        <strong class="{'check-no' if en_convenio else 'check-ok'}">
                            {'Sí' if en_convenio else 'No'}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Monodroga</span>
                        <strong>{monodroga}</strong>
                    </div>

                    <div class="validation-row">
                        <span>Presentación equivalente</span>
                        <strong>
                            {forma} · {potencia} {unidad}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Laboratorio</span>
                        <strong>{laboratorio}</strong>
                    </div>

                    <div class="validation-row">
                        <span>PVP candidato</span>
                        <strong>{money(pvp)}</strong>
                    </div>

                    <div class="validation-row">
                        <span>Banda actual</span>
                        <strong>
                            {percentage(
                                banda_actual.get(
                                    "porcentaje_descuento",
                                    0
                                )
                            )}
                            ·
                            {banda_actual.get(
                                "cantidad_laboratorios",
                                0
                            )}
                            lab.
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Banda hipotética</span>
                        <strong>
                            {percentage(
                                banda_hipotetica.get(
                                    "porcentaje_descuento",
                                    0
                                )
                            )}
                            ·
                            {banda_hipotetica.get(
                                "cantidad_laboratorios",
                                0
                            )}
                            lab.
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Mejora de banda</span>
                        <strong class="{'check-ok' if mejora_banda else 'check-no'}">
                            {'Sí' if mejora_banda else 'No'}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Segundo PVP más alto</span>
                        <strong>
                            {money(segundo_pvp) if segundo_pvp is not None else '-'}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Cumple criterio de PVP</span>
                        <strong class="{'check-ok' if cumple_pvp else 'check-no'}">
                            {'Sí' if cumple_pvp else 'No'}
                        </strong>
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.info(
                "Seleccione un troquel."
            )

    # ========================================================
    # EJECUCIÓN
    # ========================================================

    if ejecutar and codigo:

        try:

            result = svc.simulate_alta(
                codigo,
                months_window,
            )

            # ------------------------------------------------
            # Persistir resultado
            # ------------------------------------------------

            try:

                saved = repo.save_result(
                    result.__dict__
                )

                saved_msg = (
                    "Simulación guardada correctamente."
                )

            except Exception as e:

                saved_msg = (
                    "La simulación fue calculada, "
                    f"pero no pudo guardarse: {e}"
                )

            # ------------------------------------------------
            # Resultado
            # ------------------------------------------------

            impacto = (
                result.facturacion_proyectada_anual
                - result.facturacion_actual_anual
            )

            estado = (
                result.detalle_consumo.get(
                    "estado",
                    "",
                )
                if result.detalle_consumo
                else ""
            )

            if result.recomendacion:

                badge_resultado = (
                    '<span class="result-ok">'
                    'RECOMENDAR INCORPORACIÓN'
                    '</span>'
                )

            elif estado == "NO_ELEGIBLE":

                badge_resultado = (
                    '<span class="result-no">'
                    'PRESENTACIÓN NO ELEGIBLE'
                    '</span>'
                )

            elif estado == "YA_CONVENIDO":

                badge_resultado = (
                    '<span class="result-no">'
                    'TROQUEL YA CONVENIDO'
                    '</span>'
                )

            else:

                badge_resultado = (
                    '<span class="result-no">'
                    'NO RECOMENDAR INCORPORACIÓN'
                    '</span>'
                )

            st.markdown(
                f"""
                <div class="result-box">

                    <h3>
                        Resultado de simulación
                    </h3>

                    <p>
                        {badge_resultado}
                    </p>

                    <p>
                        <strong>Motivo:</strong>
                        {result.motivo}
                    </p>

                    <div
                        class="metric-grid"
                        style="
                            grid-template-columns:
                            repeat(3,1fr);
                        "
                    >

                        <div class="metric-card">

                            <div class="metric-label">
                                Facturación actual anual
                            </div>

                            <div class="metric-value">
                                {money(
                                    result.facturacion_actual_anual
                                )}
                            </div>

                        </div>

                        <div class="metric-card">

                            <div class="metric-label">
                                Facturación proyectada anual
                            </div>

                            <div class="metric-value">
                                {money(
                                    result.facturacion_proyectada_anual
                                )}
                            </div>

                        </div>

                        <div class="metric-card">

                            <div class="metric-label">
                                Impacto anual
                            </div>

                            <div class="metric-value {'green-value' if impacto <= 0 else 'red-value'}">
                                {money(impacto)}
                            </div>

                        </div>

                    </div>

                    <p class="footer-note">
                        {saved_msg}
                    </p>

                </div>
                """,
                unsafe_allow_html=True,
            )

                # ------------------------------------------------
            # Información de consumo
            # ------------------------------------------------

            if result.detalle_consumo:

                detalle = result.detalle_consumo

                st.markdown(
                    '<div class="section-title">Información de consumo</div>',
                    unsafe_allow_html=True,
                )

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "Afiliados monodroga",
                    detalle.get(
                        "afiliados_monodroga",
                        0,
                    ),
                )

                c2.metric(
                    "Afiliados misma potencia",
                    detalle.get(
                        "afiliados_misma_potencia",
                        0,
                    ),
                )

                promedio_cajas = detalle.get(
                    "promedio_mensual_cajas_por_afiliado",
                    0,
                ) or 0

                tasa_uso = detalle.get(
                    "tasa_uso_potencia",
                    0,
                ) or 0

                c3.metric(
                    "Cajas mensuales / afiliado",
                    f"{float(promedio_cajas):,.2f}",
                )

                c4.metric(
                    "Tasa uso potencia",
                    f"{float(tasa_uso):.1%}",
                )

                with st.expander(
                    "Ver detalle completo del cálculo"
                ):

                    st.json(
                        detalle
                    )

        except Exception as e:

            st.error(
                f"No se pudo ejecutar la simulación: {e}"
            )

    else:

        st.markdown(
            """
            <div class="result-placeholder">

                <div>

                    <strong>
                        El resultado de la simulación aparecerá aquí
                    </strong>

                    <br>

                    Se evaluará elegibilidad, banda,
                    PVP, consumo e impacto económico.

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "</div></div>",
        unsafe_allow_html=True,
    )
