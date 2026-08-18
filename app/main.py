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

                    # ========================================
                    # Datos base para el detalle
                    # ========================================

                    banda_actual_det = float(
                        detalle.get(
                            "banda_actual",
                            0,
                        )
                        or 0
                    )

                    banda_hipotetica_det = float(
                        detalle.get(
                            "banda_hipotetica",
                            0,
                        )
                        or 0
                    )

                    labs_actuales = int(
                        detalle.get(
                            "laboratorios_actuales",
                            0,
                        )
                        or 0
                    )

                    labs_hipoteticos = int(
                        detalle.get(
                            "laboratorios_hipoteticos",
                            0,
                        )
                        or 0
                    )

                    pvp_candidato_det = float(
                        detalle.get(
                            "pvp_candidato",
                            0,
                        )
                        or 0
                    )

                    segundo_pvp_det = detalle.get(
                        "segundo_pvp_mas_alto"
                    )

                    afiliados_monodroga_det = int(
                        detalle.get(
                            "afiliados_monodroga",
                            0,
                        )
                        or 0
                    )

                    costo_anual_monodroga_det = float(
                        detalle.get(
                            "costo_anual_monodroga",
                            0,
                        )
                        or 0
                    )

                    afiliados_potencia_det = int(
                        detalle.get(
                            "afiliados_misma_potencia",
                            0,
                        )
                        or 0
                    )

                    costo_anual_potencia_det = float(
                        detalle.get(
                            "costo_anual_misma_potencia",
                            0,
                        )
                        or 0
                    )

                    promedio_cajas_det = float(
                        detalle.get(
                            "promedio_mensual_cajas_por_afiliado",
                            0,
                        )
                        or 0
                    )

                    tasa_uso_det = float(
                        detalle.get(
                            "tasa_uso_potencia",
                            0,
                        )
                        or 0
                    )

                    fact_actual_det = float(
                        detalle.get(
                            "facturacion_actual_monodroga_anual",
                            0,
                        )
                        or 0
                    )

                    fact_proyectada_det = float(
                        detalle.get(
                            "facturacion_proyectada_monodroga_anual",
                            0,
                        )
                        or 0
                    )

                    impacto_det = float(
                        detalle.get(
                            "impacto_anual",
                            0,
                        )
                        or 0
                    )

                    ahorro_det = float(
                        detalle.get(
                            "ahorro_anual",
                            0,
                        )
                        or 0
                    )

                    ahorro_pct_det = float(
                        detalle.get(
                            "ahorro_porcentual",
                            0,
                        )
                        or 0
                    )

                    liquidaciones_det = int(
                        detalle.get(
                            "cantidad_liquidaciones_afectadas",
                            0,
                        )
                        or 0
                    )

                    unidades_det = float(
                        detalle.get(
                            "unidades_historicas_afectadas",
                            0,
                        )
                        or 0
                    )

                    meses_det = int(
                        detalle.get(
                            "meses_observados",
                            0,
                        )
                        or 0
                    )

                    banda_economica_actual_det = float(
                        detalle.get(
                            "banda_economica_actual",
                            0,
                        )
                        or 0
                    )

                    banda_economica_proyectada_det = float(
                        detalle.get(
                            "banda_economica_proyectada",
                            0,
                        )
                        or 0
                    )

                    consumo_producto = detalle.get(
                        "consumo_promedio_mensual_producto",
                        [],
                    ) or []

                    troqueles_afectados = detalle.get(
                        "troqueles_afectados",
                        [],
                    ) or []

                    # ========================================
                    # Laboratorios que conforman banda actual
                    # ========================================

                    nombres_laboratorios_actuales = []

                    try:

                        grupo_banda_actual = (
                            svc.current_convenio_group(
                                candidato
                            )
                        )

                        if (
                            not grupo_banda_actual.empty
                            and "desc_laboratorio"
                            in grupo_banda_actual.columns
                        ):

                            nombres_laboratorios_actuales = sorted(
                                grupo_banda_actual[
                                    "desc_laboratorio"
                                ]
                                .dropna()
                                .astype(str)
                                .str.strip()
                                .loc[
                                    lambda s: s != ""
                                ]
                                .unique()
                                .tolist()
                            )

                    except Exception:

                        nombres_laboratorios_actuales = []

                    laboratorio_candidato_det = str(
                        candidato.get(
                            "desc_laboratorio",
                            "",
                        )
                        or ""
                    ).strip()

                    # ========================================
                    # 1. Estado general
                    # ========================================

                    st.markdown("### 1. Estado general de la simulación")

                    st.markdown(
                        f"""
**Estado del análisis:** {detalle.get("estado", "-")}  
**Presentación elegible:** {"Sí" if detalle.get("elegible", False) else "No"}  
**Troquel actualmente en convenio:** {"Sí" if detalle.get("ya_en_convenio", False) else "No"}  
**Mejora de banda:** {"Sí" if detalle.get("mejora_banda", False) else "No"}  
**Cumple criterio de PVP:** {"Sí" if detalle.get("cumple_pvp", False) else "No"}  
                        """
                    )

                    st.markdown("---")

                    # ========================================
                    # 2. Banda actual y proyectada
                    # ========================================

                    st.markdown("### 2. Análisis de banda")

                    st.markdown(
                        f"""
La banda se determina considerando todos los troqueles actualmente conveniados que pertenecen a la misma monodroga del producto candidato.

**Cantidad de laboratorios actuales:** {labs_actuales}  
**Banda actual:** {banda_actual_det:.0%}  
**Laboratorio candidato:** {laboratorio_candidato_det if laboratorio_candidato_det else "-"}  
**Cantidad de laboratorios con la incorporación:** {labs_hipoteticos}  
**Banda con incorporación:** {banda_hipotetica_det:.0%}  
**Resultado de la comparación:** {"La incorporación mejora la banda." if detalle.get("mejora_banda", False) else "La incorporación no mejora la banda."}
                        """
                    )

                    st.markdown("**Laboratorios que conforman la banda actual:**")

                    if nombres_laboratorios_actuales:

                        for lab in nombres_laboratorios_actuales:

                            st.markdown(
                                f"- **{lab}**"
                            )

                    else:

                        st.markdown(
                            "No se pudieron identificar los nombres de los laboratorios que conforman la banda actual."
                        )

                    st.markdown("---")

                    # ========================================
                    # 3. Comparación PVP
                    # ========================================

                    st.markdown("### 3. Análisis de PVP")

                    segundo_pvp_texto = (
                        money(segundo_pvp_det)
                        if segundo_pvp_det is not None
                        else "-"
                    )

                    st.markdown(
                        f"""
Para el criterio de PVP se consideran los troqueles conveniados de la misma monodroga, misma potencia y misma forma farmacológica que el candidato.

**PVP candidato:** {money(pvp_candidato_det)}  
**Segundo PVP más alto del grupo comparable:** {segundo_pvp_texto}  
**Resultado:** {"El PVP candidato cumple el criterio definido." if detalle.get("cumple_pvp", False) else "El PVP candidato no cumple el criterio definido."}
                        """
                    )

                    st.markdown("---")

                    # ========================================
                    # 4. Consumo histórico
                    # ========================================

                    st.markdown("### 4. Consumo histórico de la monodroga")

                    st.markdown(
                        f"""
**Afiliados con consumo de la monodroga:** {afiliados_monodroga_det:,}  
**Costo anual de la monodroga:** {money(costo_anual_monodroga_det)}  
**Afiliados con consumo de la misma potencia:** {afiliados_potencia_det:,}  
**Costo anual de la misma potencia:** {money(costo_anual_potencia_det)}  
**Promedio mensual de cajas por afiliado:** {promedio_cajas_det:,.2f}  
**Tasa de uso de la potencia:** {tasa_uso_det:.1%}
                        """
                    )

                    st.markdown("---")

                    # ========================================
                    # 5. Consumo promedio mensual por troquel
                    # ========================================

                    st.markdown("### 5. Consumo promedio mensual por troquel")

                    if consumo_producto:

                        for item in consumo_producto:

                            codigo_item = item.get(
                                "troquel",
                                item.get(
                                    "codigo_troquel",
                                    "-"
                                )
                            )

                            cajas_item = float(
                                item.get(
                                    "cajas_promedio_mensual",
                                    0,
                                )
                                or 0
                            )

                            importe_item = float(
                                item.get(
                                    "pxq_promedio_mensual",
                                    0,
                                )
                                or 0
                            )

                            st.markdown(
                                f"""
**Troquel {codigo_item}**  
Cajas promedio mensuales: **{cajas_item:,.2f}**  
Importe promedio mensual: **{money(importe_item)}**
                                """
                            )

                    else:

                        st.markdown(
                            "No existen registros de consumo promedio mensual por troquel."
                        )

                    st.markdown("---")

                    # ========================================
                    # 6. Facturación actual
                    # ========================================

                    st.markdown("### 6. Facturación actual anual")

                    st.markdown(
                        f"""
La facturación actual corresponde exclusivamente a los troqueles conveniados de la monodroga analizada.

Se calcula a partir de las liquidaciones históricas utilizando:

**Unidades × PConv Fecha Remito**

Luego, el valor observado se anualiza según la cantidad de meses disponibles.

**Meses observados:** {meses_det}  
**Liquidaciones utilizadas:** {liquidaciones_det:,}  
**Unidades históricas utilizadas:** {unidades_det:,.0f}  
**Facturación actual anual de la monodroga:** {money(fact_actual_det)}
                        """
                    )

                    st.markdown("---")

                    # ========================================
                    # 7. Facturación proyectada
                    # ========================================

                    st.markdown("### 7. Facturación proyectada anual")

                    st.markdown(
                        f"""
La proyección mantiene el mismo consumo histórico de la monodroga y modifica únicamente la condición económica resultante de la nueva banda.

Para cada liquidación se calcula:

**Unidades × PVP Fecha Remito × (1 - banda proyectada)**

**Banda económica actual:** {banda_economica_actual_det:.0%}  
**Banda económica proyectada:** {banda_economica_proyectada_det:.0%}  
**Facturación proyectada anual de la monodroga:** {money(fact_proyectada_det)}
                        """
                    )

                    st.markdown("---")

                    # ========================================
                    # 8. Impacto económico
                    # ========================================

                    st.markdown("### 8. Impacto económico")

                    st.markdown(
                        f"""
**Facturación actual anual:** {money(fact_actual_det)}  
**Facturación proyectada anual:** {money(fact_proyectada_det)}  
**Impacto anual:** {money(impacto_det)}  
**Ahorro anual estimado:** {money(ahorro_det)}  
**Ahorro porcentual estimado:** {ahorro_pct_det:.2%}
                        """
                    )

                    st.markdown("---")

                    # ========================================
                    # 9. Troqueles afectados
                    # ========================================

                    st.markdown("### 9. Troqueles afectados por el cambio de banda")

                    st.markdown(
                        f"""
Los siguientes troqueles pertenecen al universo económico de la monodroga considerado para la simulación.  
**Cantidad total de troqueles afectados:** {len(troqueles_afectados)}
                        """
                    )

                    if troqueles_afectados:

                        for codigo_afectado in troqueles_afectados:

                            st.markdown(
                                f"- Troquel **{codigo_afectado}**"
                            )

                    else:

                        st.markdown(
                            "No se identificaron troqueles afectados."
                        )

                    st.markdown("---")

                    # ========================================
                    # 10. Resumen técnico completo
                    # ========================================

                    st.markdown("### 10. Resumen técnico completo")

                    st.markdown(
                        f"""
**Estado:** {detalle.get("estado", "-")}  
**Elegible:** {detalle.get("elegible", False)}  
**Ya en convenio:** {detalle.get("ya_en_convenio", False)}  
**Banda actual:** {banda_actual_det:.0%}  
**Banda hipotética:** {banda_hipotetica_det:.0%}  
**Laboratorios actuales:** {labs_actuales}  
**Laboratorios hipotéticos:** {labs_hipoteticos}  
**Mejora de banda:** {detalle.get("mejora_banda", False)}  
**PVP candidato:** {money(pvp_candidato_det)}  
**Segundo PVP más alto:** {segundo_pvp_texto}  
**Cumple PVP:** {detalle.get("cumple_pvp", False)}  
**Afiliados monodroga:** {afiliados_monodroga_det:,}  
**Costo anual monodroga:** {money(costo_anual_monodroga_det)}  
**Afiliados misma potencia:** {afiliados_potencia_det:,}  
**Costo anual misma potencia:** {money(costo_anual_potencia_det)}  
**Promedio mensual cajas por afiliado:** {promedio_cajas_det:,.2f}  
**Tasa uso potencia:** {tasa_uso_det:.1%}  
**Facturación actual monodroga anual:** {money(fact_actual_det)}  
**Facturación proyectada monodroga anual:** {money(fact_proyectada_det)}  
**Impacto anual:** {money(impacto_det)}  
**Ahorro anual:** {money(ahorro_det)}  
**Ahorro porcentual:** {ahorro_pct_det:.2%}  
**Cantidad de liquidaciones afectadas:** {liquidaciones_det:,}  
**Unidades históricas afectadas:** {unidades_det:,.0f}  
**Meses observados:** {meses_det}  
**Banda económica actual:** {banda_economica_actual_det:.0%}  
**Banda económica proyectada:** {banda_economica_proyectada_det:.0%}  
                        """
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
