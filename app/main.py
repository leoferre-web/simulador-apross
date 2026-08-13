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
from core.rules import is_eligible


# ============================================================
# BLOQUE 02 — Configuración
# ============================================================

st.set_page_config(
    page_title="Simulador APROSS OYTE",
    layout="wide",
)


# ============================================================
# BLOQUE 03 — Render HTML seguro
# ============================================================

def html_block(html: str):
    """
    Elimina la sangría inicial de cada línea para evitar
    que Markdown interprete HTML anidado como código.
    """

    clean_html = "\n".join(
        line.lstrip()
        for line in html.splitlines()
    )

    st.markdown(
        clean_html,
        unsafe_allow_html=True,
    )


# ============================================================
# BLOQUE 04 — CSS
# ============================================================

html_block("""
<style>

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1180px;
}

div[data-testid="stAppViewContainer"] {
    background: #ffffff;
}

.top-bar {
    height: 42px;
    background: #f4f1ea;
    border-bottom: 1px solid #e2ded4;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    margin-bottom: 34px;
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

.red {
    background: #e86b5c;
}

.yellow {
    background: #e8bf4f;
}

.green {
    background: #52b788;
}

.url-pill {
    background: #ffffff;
    border: 1px solid #ddd8ce;
    border-radius: 999px;
    padding: 5px 80px;
    color: #999999;
    font-size: 11px;
}

.kicker {
    color: #8f8a80;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 5px;
}

.main-title {
    font-size: 26px;
    font-weight: 800;
    color: #2b2b2b;
    margin: 0 0 12px 0;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
    margin-top: 28px;
    margin-bottom: 20px;
}

.metric-card {
    background: #f5f2ec;
    border-radius: 12px;
    padding: 20px 22px;
    min-height: 95px;
}

.metric-label {
    color: #716c64;
    font-size: 12px;
    margin-bottom: 8px;
}

.metric-value {
    color: #2c2c2c;
    font-size: 24px;
    font-weight: 800;
}

.metric-sub {
    color: #9b958b;
    font-size: 11px;
    margin-top: 5px;
}

.green-value {
    color: #08765f;
}

.red-value {
    color: #a33d2c;
}

.section-title {
    margin-top: 22px;
    margin-bottom: 10px;
    color: #6f6a62;
    font-size: 14px;
}

.bar-row {
    display: grid;
    grid-template-columns: 90px 1fr 120px;
    align-items: center;
    gap: 18px;
    margin: 12px 0;
    font-size: 12px;
    color: #777169;
}

.bar-bg {
    height: 17px;
    background: #dfddd5;
    border-radius: 999px;
    overflow: hidden;
}

.bar-fill {
    height: 17px;
    background: #0d765f;
    border-radius: 999px;
}

.validation-card {
    background: #f5f2ec;
    border-radius: 12px;
    padding: 22px;
}

.validation-title {
    font-weight: 800;
    color: #333333;
    margin-bottom: 14px;
    font-size: 14px;
}

.validation-row {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 7px 0;
    font-size: 12px;
    border-bottom: 1px solid #e5e0d6;
    color: #5f5a53;
}

.validation-row:last-child {
    border-bottom: none;
}

.validation-row strong {
    color: #2d2d2d;
    text-align: right;
}

.check-ok {
    color: #08765f !important;
    font-weight: 800;
}

.check-no {
    color: #a33d2c !important;
    font-weight: 800;
}

.result-placeholder {
    margin-top: 40px;
    border: 2px dashed #ddd6c9;
    border-radius: 14px;
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #aaa39a;
    font-size: 13px;
    font-style: italic;
}

.result-box {
    margin-top: 30px;
    border: 1px solid #e5dfd3;
    border-radius: 14px;
    padding: 22px;
    background: #ffffff;
}

.result-ok {
    background: #d9f1e9;
    color: #0e6d5e;
    padding: 7px 14px;
    border-radius: 999px;
    display: inline-block;
    font-weight: 700;
    font-size: 12px;
}

.result-no {
    background: #f8e3db;
    color: #924126;
    padding: 7px 14px;
    border-radius: 999px;
    display: inline-block;
    font-weight: 700;
    font-size: 12px;
}

.footer-note {
    color: #9d978d;
    font-size: 11px;
    margin-top: 16px;
}

button[kind="primary"] {
    background: #1f5b6b !important;
    border-radius: 8px !important;
    border: none !important;
}

div[data-testid="stMetric"] {
    background: #f5f2ec;
    border-radius: 12px;
    padding: 14px;
}

@media(max-width:850px) {

    .metric-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .url-pill {
        padding: 5px 30px;
    }
}

</style>
""")


# ============================================================
# BLOQUE 05 — Funciones auxiliares
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

    if value >= 1_000:
        return f"{sign}${value:,.0f}"

    return f"{sign}${value:,.2f}"


def percentage(value):

    try:
        return f"{float(value):.0%}"
    except Exception:
        return "-"


def normalize_code(value):

    if value is None or pd.isna(value):
        return ""

    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


def render_browser_header(
    path="simulador-convenio.aprossoyte.local",
):

    html_block(
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
        """
    )


# ============================================================
# BLOQUE 06 — Carga de datos
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
# BLOQUE 07 — Servicios
# ============================================================

repo = Repo()

svc = SimulationService(
    troqueles=troqueles,
    convenio=convenio,
    bandas=bandas,
    liquidaciones=liquidaciones,
)
st.write("DEBUG troqueles recibidos:", len(troqueles))
st.write("DEBUG columnas:", list(troqueles.columns))
st.write("DEBUG troqueles vigentes:", len(svc.troqueles))

# ============================================================
# BLOQUE 08 — Navegación
# ============================================================

if "view" not in st.session_state:
    st.session_state.view = "panel"

view = st.session_state.view


# ============================================================
# BLOQUE 09 — PANEL FINANCIERO
# ============================================================

if view == "panel":

    render_browser_header()

    html_block(
        """
        <div class="kicker">
            Simulador de convenio
        </div>
        <h1 class="main-title">
            APROSS OYTE — Panel financiero
        </h1>
        """
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

    if (
        not hist.empty
        and "tipo_caso" in hist.columns
    ):

        hist = hist[
            hist["tipo_caso"] == "A"
        ].copy()

    # --------------------------------------------------------
    # Indicadores
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

    fact_actual = 0.0
    fact_proyectada = 0.0

    if not hist.empty:

        hist_ordenado = hist.copy()

        if "fecha_corrida" in hist_ordenado.columns:

            hist_ordenado["fecha_corrida"] = (
                pd.to_datetime(
                    hist_ordenado["fecha_corrida"],
                    errors="coerce",
                )
            )

            hist_ordenado = (
                hist_ordenado.sort_values(
                    "fecha_corrida",
                    ascending=False,
                )
            )

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

    html_block(
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
        """
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

    html_block(
        f"""
        <div class="section-title">
            Facturación anual: actual vs. proyectada
        </div>

        <div class="bar-row">
            <div>Actual</div>
            <div class="bar-bg">
                <div
                    class="bar-fill"
                    style="width:{actual_pct}%; background:#d8d5cc;">
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
                    style="width:{proyectada_pct}%;">
                </div>
            </div>
            <strong>
                {money(fact_proyectada)}
            </strong>
        </div>
        """
    )

    # --------------------------------------------------------
    # Evaluaciones recientes
    # --------------------------------------------------------

    html_block(
        """
        <div class="section-title">
            Evaluaciones recientes de incorporación
        </div>
        """
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

        for _, row_hist in data.iterrows():

            codigo = normalize_code(
                row_hist.get(
                    "codigo_troquel"
                )
            )

            recomendacion = bool(
                row_hist.get(
                    "recomendacion"
                )
            )

            candidato_hist = svc.get_troquel(
                codigo
            )

            monodroga = ""

            if candidato_hist:

                monodroga = str(
                    candidato_hist.get(
                        "monodro",
                        "",
                    )
                    or ""
                )

            if recomendacion:

                badge_html = (
                    '<span class="badge badge-ok">'
                    'Recomendado'
                    '</span>'
                )

            else:

                badge_html = (
                    '<span class="badge badge-no">'
                    'No recomendado'
                    '</span>'
                )

            fa = float(
                row_hist.get(
                    "facturacion_actual_anual",
                    0,
                )
                or 0
            )

            fp = float(
                row_hist.get(
                    "facturacion_proyectada_anual",
                    0,
                )
                or 0
            )

            impacto_fila = fp - fa

            if impacto_fila < 0:
                impacto_class = "positive"

            elif impacto_fila > 0:
                impacto_class = "negative"

            else:
                impacto_class = "muted"

            rows_html += (
                f"<tr>"
                f"<td>{codigo}</td>"
                f"<td>{monodroga}</td>"
                f"<td>{badge_html}</td>"
                f'<td class="{impacto_class}">{money(impacto_fila)}</td>'
                f"</tr>"
            )

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

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
        }}

        .reco-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .reco-table th {{
            background: #1f5b6b;
            color: #ffffff;
            padding: 10px 13px;
            text-align: left;
        }}

        .reco-table td {{
            padding: 10px 13px;
            border-bottom: 1px solid #eeeae2;
            color: #333333;
        }}

        .reco-table tr:nth-child(even) {{
            background: #f6f3ed;
        }}

        .badge {{
            display: inline-block;
            border-radius: 999px;
            padding: 4px 18px;
            font-size: 11px;
        }}

        .badge-ok {{
            background: #d9f1e9;
            color: #0e6d5e;
        }}

        .badge-no {{
            background: #f8e3db;
            color: #924126;
        }}

        .positive {{
            color: #08765f !important;
            font-weight: 800;
            text-align: right;
        }}

        .negative {{
            color: #a33d2c !important;
            font-weight: 800;
            text-align: right;
        }}

        .muted {{
            color: #99948b !important;
            font-weight: 700;
            text-align: right;
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
        height=410,
        scrolling=True,
    )

    st.markdown("")

    if st.button(
        "Nueva simulación",
        type="primary",
    ):

        st.session_state.view = "simular"

        st.rerun()


# ============================================================
# BLOQUE 10 — NUEVA SIMULACIÓN — CASO A
# ============================================================

else:

    render_browser_header(
        "simulador-convenio.aprossoyte.local/nueva-simulacion"
    )

    if st.button(
        "← Volver al panel"
    ):

        st.session_state.view = "panel"

        st.rerun()

    html_block(
        """
        <div class="kicker">
            Simulador de convenio
        </div>
        <h1 class="main-title">
            Nueva simulación — Alta de troquel
        </h1>
        """
    )

    # --------------------------------------------------------
    # Troqueles disponibles
    # --------------------------------------------------------

    if (
        not svc.troqueles.empty
        and "tronquel" in svc.troqueles.columns
    ):

        opciones = (
            svc.troqueles["tronquel"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        try:

            opciones = sorted(
                opciones,
                key=lambda x: int(float(x)),
            )

        except Exception:

            opciones = sorted(
                opciones
            )

    else:

        opciones = []

    left, right = st.columns(
        [1.10, 0.90]
    )

    # --------------------------------------------------------
    # Formulario
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Candidato
    # --------------------------------------------------------

    candidato = (
        svc.get_troquel(codigo)
        if codigo
        else None
    )

    # --------------------------------------------------------
    # Validación previa
    # --------------------------------------------------------

    with right:

        if candidato:

            monodroga = str(
                candidato.get(
                    "monodro",
                    "",
                )
                or ""
            )

            forma = str(
                candidato.get(
                    "formas",
                    "",
                )
                or ""
            )

            potencia = candidato.get(
                "potencia",
                ""
            )

            unidad = str(
                candidato.get(
                    "unidad_potencia",
                    "",
                )
                or ""
            )

            laboratorio = str(
                candidato.get(
                    "desc_laboratorio",
                    "",
                )
                or ""
            )

            pvp = candidato.get(
                "precio",
                0
            ) or 0

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
                float(
                    banda_hipotetica.get(
                        "porcentaje_descuento",
                        0,
                    )
                    or 0
                )
                >
                float(
                    banda_actual.get(
                        "porcentaje_descuento",
                        0,
                    )
                    or 0
                )
            )

            try:

                cumple_pvp = (
                    segundo_pvp is not None
                    and float(pvp)
                    <= float(segundo_pvp)
                )

            except Exception:

                cumple_pvp = False

            elegible, motivo_elegibilidad = (
                is_eligible(
                    candidato,
                    months_window,
                )
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

            fecha_texto = "-"

            if (
                fecha is not None
                and not pd.isna(fecha)
            ):

                try:

                    fecha_texto = (
                        pd.to_datetime(fecha)
                        .strftime("%d/%m/%Y")
                    )

                except Exception:

                    fecha_texto = str(fecha)

            html_block(
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
                        <span>
                            Precio vigente ≤ {months_window} meses
                        </span>
                        <strong class="{'check-ok' if elegible else 'check-no'}">
                            {'Sí' if elegible else 'No'}
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Fecha vigencia PVP</span>
                        <strong>{fecha_texto}</strong>
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
                                    0,
                                )
                            )}
                            ·
                            {banda_actual.get(
                                "cantidad_laboratorios",
                                0,
                            )}
                            lab.
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Banda con incorporación</span>
                        <strong>
                            {percentage(
                                banda_hipotetica.get(
                                    "porcentaje_descuento",
                                    0,
                                )
                            )}
                            ·
                            {banda_hipotetica.get(
                                "cantidad_laboratorios",
                                0,
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
                            {
                                money(segundo_pvp)
                                if segundo_pvp is not None
                                else "-"
                            }
                        </strong>
                    </div>

                    <div class="validation-row">
                        <span>Cumple criterio de PVP</span>
                        <strong class="{'check-ok' if cumple_pvp else 'check-no'}">
                            {'Sí' if cumple_pvp else 'No'}
                        </strong>
                    </div>

                </div>
                """
            )

            if not elegible:

                st.caption(
                    motivo_elegibilidad
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
            # Persistencia
            # ------------------------------------------------

            try:

                repo.save_result(
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

            impacto_resultado = (
                result.facturacion_proyectada_anual
                - result.facturacion_actual_anual
            )

            detalle = (
                result.detalle_consumo
                if result.detalle_consumo
                else {}
            )

            estado_resultado = detalle.get(
                "estado",
                "",
            )

            if result.recomendacion:

                resultado_html = (
                    '<span class="result-ok">'
                    'RECOMENDAR INCORPORACIÓN'
                    '</span>'
                )

            elif estado_resultado == "NO_ELEGIBLE":

                resultado_html = (
                    '<span class="result-no">'
                    'PRESENTACIÓN NO ELEGIBLE'
                    '</span>'
                )

            elif estado_resultado == "YA_CONVENIDO":

                resultado_html = (
                    '<span class="result-no">'
                    'TROQUEL YA CONVENIDO'
                    '</span>'
                )

            else:

                resultado_html = (
                    '<span class="result-no">'
                    'NO RECOMENDAR INCORPORACIÓN'
                    '</span>'
                )

            html_block(
                f"""
                <div class="result-box">
                    <h3>
                        Resultado de simulación
                    </h3>

                    <p>
                        {resultado_html}
                    </p>

                    <p>
                        <strong>Motivo:</strong>
                        {result.motivo}
                    </p>
                </div>
                """
            )

            html_block(
                f"""
                <div
                    class="metric-grid"
                    style="grid-template-columns:repeat(3,1fr);"
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
                        <div class="metric-value {'green-value' if impacto_resultado <= 0 else 'red-value'}">
                            {money(
                                impacto_resultado
                            )}
                        </div>
                    </div>

                </div>
                """
            )

            st.caption(
                saved_msg
            )

            # ------------------------------------------------
            # Información de consumo
            # ------------------------------------------------

            if detalle:

                html_block(
                    """
                    <div class="section-title">
                        Información de consumo
                    </div>
                    """
                )

                c1, c2, c3, c4 = st.columns(4)

                afiliados_mono = detalle.get(
                    "afiliados_monodroga",
                    0,
                ) or 0

                afiliados_potencia = detalle.get(
                    "afiliados_misma_potencia",
                    0,
                ) or 0

                promedio_cajas = detalle.get(
                    "promedio_mensual_cajas_por_afiliado",
                    0,
                ) or 0

                tasa_uso = detalle.get(
                    "tasa_uso_potencia",
                    0,
                ) or 0

                c1.metric(
                    "Afiliados monodroga",
                    int(afiliados_mono),
                )

                c2.metric(
                    "Afiliados misma potencia",
                    int(afiliados_potencia),
                )

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

        html_block(
            """
            <div class="result-placeholder">
                <div>
                    <strong>
                        El resultado de la simulación aparecerá aquí
                    </strong>
                    <br><br>
                    Se evaluará elegibilidad, banda,
                    PVP, consumo e impacto económico.
                </div>
            </div>
            """
        )
