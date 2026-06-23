import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd

from core.repositories import Repo
from core.services import SimulationService


st.set_page_config(page_title="Simulador APROSS OYTE", layout="wide")


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
.dot { width: 11px; height: 11px; border-radius: 50%; }
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
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 3px;
}
.title-row {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:20px;
}
.main-title {
    font-size: 26px;
    font-weight: 800;
    color:#2b2b2b;
    margin:0;
}
.segment {
    display:flex;
    gap:10px;
}
.seg-btn {
    border:1px solid #d9d4ca;
    border-radius:999px;
    padding:8px 26px;
    font-size:13px;
    color:#706b63;
    background:#fff;
}
.seg-btn-active {
    background:#1f5b6b;
    color:#fff;
    border-color:#1f5b6b;
    font-weight:700;
}
.metric-grid {
    display:grid;
    grid-template-columns: repeat(4, 1fr);
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
.section-title {
    margin-top:18px;
    margin-bottom:10px;
    color:#6f6a62;
    font-size:15px;
}
.bar-row {
    display:grid;
    grid-template-columns: 90px 1fr 110px;
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
.reco-table {
    width:100%;
    border-collapse:collapse;
    overflow:hidden;
    font-size:14px;
}
.reco-table th {
    background:#1f5b6b;
    color:white;
    padding:10px 13px;
    text-align:left;
}
.reco-table td {
    padding:10px 13px;
    border-bottom:1px solid #eeeae2;
}
.reco-table tr:nth-child(even) {
    background:#f6f3ed;
}
.badge {
    display:inline-block;
    border-radius:999px;
    padding:4px 24px;
    font-size:12px;
}
.badge-neutral {
    background:#ebe8df;
    color:#6d665d;
}
.badge-ok {
    background:#d9f1e9;
    color:#0e6d5e;
}
.badge-no {
    background:#f8e3db;
    color:#924126;
}
.positive {
    color:#08765f;
    font-weight:800;
}
.negative {
    color:#a33d2c;
    font-weight:800;
}
.muted {
    color:#99948b;
    font-weight:700;
}
.footer-note {
    color:#9d978d;
    font-size:11px;
    margin-top:16px;
}
.form-grid {
    display:grid;
    grid-template-columns: 1.15fr .95fr;
    gap:38px;
    margin-top:26px;
}
.input-like {
    border:1px solid #d6d0c6;
    border-radius:9px;
    padding:12px 14px;
    color:#aaa;
    background:#fff;
    font-size:14px;
}
.stSelectbox label, .stTextInput label, .stRadio label, .stSlider label {
    color:#6f6a62 !important;
    font-size:13px !important;
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
.check {
    color:#0c7660;
    font-weight:700;
}
.validation-row {
    display:flex;
    justify-content:space-between;
    padding:6px 0;
    font-size:13px;
    color:#5f5a53;
}
.validation-row strong {
    color:#2d2d2d;
}
.result-placeholder {
    margin-top:70px;
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
    margin-top:42px;
    border:1px solid #e5dfd3;
    border-radius:14px;
    padding:22px;
    background:#fff;
}
.back-link {
    color:#1f5b6b;
    font-size:13px;
    margin-bottom:22px;
}
button[kind="primary"] {
    background:#1f5b6b !important;
    border-radius:8px !important;
}
@media(max-width: 850px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .form-grid { grid-template-columns: 1fr; }
    .title-row { flex-direction:column; align-items:flex-start; }
    .url-pill { padding:5px 30px; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    repo = Repo()
    return (
        repo.table_df("troqueles"),
        repo.table_df("convenio_oyte"),
        repo.table_df("liquidaciones"),
    )


def money(value):
    try:
        value = float(value or 0)
    except Exception:
        value = 0
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    return f"${value:,.0f}"


def render_browser_header(path="simulador-convenio.aprossoyte.local"):
    st.markdown(
        f"""
        <div class="top-bar">
            <div class="dots">
                <span class="dot red"></span>
                <span class="dot yellow"></span>
                <span class="dot green"></span>
            </div>
            <div class="url-pill">{path}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


try:
    troqueles, convenio, liquidaciones = load_data()
except Exception as e:
    st.error(f"No se pudieron cargar datos desde Supabase: {e}")
    st.stop()


svc = SimulationService(troqueles, convenio, liquidaciones)
repo = Repo()

view = st.query_params.get("view", "panel")
if isinstance(view, list):
    view = view[0]

convenio_codes = svc.active_convenio_codes()

if troqueles.empty or liquidaciones.empty:
    fact_actual = 0
else:
    try:
        fact_actual = svc._full(
            "A",
            "",
            False,
            "",
            {"monodroga": "", "potencia": ""},
            convenio_codes,
            convenio_codes,
        ).facturacion_actual_anual
    except Exception:
        fact_actual = 0


# =========================
# PANEL FINANCIERO
# =========================

if view == "panel":
    st.markdown('<div class="app-window">', unsafe_allow_html=True)
    render_browser_header()

    st.markdown('<div class="inner">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="title-row">
            <div>
                <div class="kicker">Simulador de convenio</div>
                <h1 class="main-title">APROSS OYTE — Panel financiero</h1>
            </div>
            <div class="segment">
                <span class="seg-btn seg-btn-active">Todas</span>
                <span class="seg-btn">Altas</span>
                <span class="seg-btn">Bajas</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fact_proyectada = fact_actual
    impacto = 0

    try:
        hist = repo.table_df("simulacion_resultados", limit=500)
    except Exception:
        hist = pd.DataFrame()

    if not hist.empty:
        if "facturacion_actual_anual" in hist.columns:
            fact_actual_hist = pd.to_numeric(hist["facturacion_actual_anual"], errors="coerce").fillna(0)
            fact_proy_hist = pd.to_numeric(hist["facturacion_proyectada_anual"], errors="coerce").fillna(0)
            if fact_actual_hist.sum() > 0:
                fact_actual = fact_actual_hist.sum()
                fact_proyectada = fact_proy_hist.sum()
                impacto = fact_actual - fact_proyectada

    troq_eval = len(hist) if not hist.empty else 0
    altas = len(hist[hist["tipo_caso"] == "A"]) if not hist.empty and "tipo_caso" in hist.columns else 0
    bajas = len(hist[hist["tipo_caso"] == "B"]) if not hist.empty and "tipo_caso" in hist.columns else 0

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Facturación actual anual</div>
                <div class="metric-value">{money(fact_actual)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Facturación proyectada</div>
                <div class="metric-value">{money(fact_proyectada)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Impacto neto estimado</div>
                <div class="metric-value green-value">▼ {money(abs(impacto))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Troqueles evaluados</div>
                <div class="metric-value">{troq_eval}</div>
                <div class="metric-sub">{altas} altas · {bajas} bajas</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    max_bar = max(fact_actual, fact_proyectada, 1)
    actual_pct = min(100, fact_actual / max_bar * 100)
    proy_pct = min(100, fact_proyectada / max_bar * 100)

    st.markdown(
        f"""
        <div class="section-title">Facturación anual: actual vs. proyectada</div>
        <div class="bar-row">
            <div>Actual</div>
            <div class="bar-bg"><div class="bar-fill" style="width:{actual_pct}%; background:#d8d5cc;"></div></div>
            <strong>{money(fact_actual)}</strong>
        </div>
        <div class="bar-row">
            <div>Proyectada</div>
            <div class="bar-bg"><div class="bar-fill" style="width:{proy_pct}%;"></div></div>
            <strong>{money(fact_proyectada)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Recomendaciones recientes</div>', unsafe_allow_html=True)

    rows_html = ""

    if not hist.empty:
        data = hist.copy()
        if "fecha_corrida" in data.columns:
            data = data.sort_values("fecha_corrida", ascending=False)
        data = data.head(8)

        for _, r in data.iterrows():
            codigo = r.get("codigo_troquel", "")
            caso = "Alta" if r.get("tipo_caso") == "A" else "Baja"
            reco = bool(r.get("recomendacion"))
            badge = "Recomendado" if reco else "No recomendado"
            badge_class = "badge-ok" if reco else "badge-no"

            monodroga = ""
            banda = "-"
            if not troqueles.empty and "codigo_troquel" in troqueles.columns:
                tr = troqueles[troqueles["codigo_troquel"].astype(str) == str(codigo)]
                if not tr.empty:
                    monodroga = tr.iloc[0].get("monodroga", "")
                    try:
                        banda = f"{svc.discount_for_count(1) if hasattr(svc, 'discount_for_count') else ''}"
                    except Exception:
                        banda = "-"

            fa = float(r.get("facturacion_actual_anual") or 0)
            fp = float(r.get("facturacion_proyectada_anual") or 0)
            imp = fp - fa
            imp_class = "positive" if imp < 0 else "negative" if imp > 0 else "muted"

            rows_html += f"""
            <tr>
                <td>{codigo}</td>
                <td>{monodroga}</td>
                <td><span class="badge badge-neutral">{caso}</span></td>
                <td>{banda}</td>
                <td><span class="badge {badge_class}">{badge}</span></td>
                <td class="{imp_class}" style="text-align:right;">{money(imp)}</td>
            </tr>
            """
    else:
        rows_html = """
        <tr>
            <td colspan="6" style="text-align:center; color:#999; padding:20px;">
                Todavía no hay simulaciones guardadas.
            </td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="reco-table">
            <thead>
                <tr>
                    <th>Troquel</th>
                    <th>Monodroga</th>
                    <th>Caso</th>
                    <th>Banda</th>
                    <th>Recomendación</th>
                    <th style="text-align:right;">Impacto anual</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <div class="footer-note">Datos ilustrativos o calculados desde Supabase. Fuentes: ALB, Convenio APROSS OYTE, Liquidación.</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Nueva simulación", type="primary"):
        st.query_params["view"] = "simular"
        st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


# =========================
# NUEVA SIMULACIÓN
# =========================

else:
    st.markdown('<div class="app-window">', unsafe_allow_html=True)
    render_browser_header("simulador-convenio.aprossoyte.local/nueva-simulacion")
    st.markdown('<div class="inner">', unsafe_allow_html=True)

    if st.button("← Volver al panel"):
        st.query_params["view"] = "panel"
        st.rerun()

    st.markdown(
        """
        <div class="kicker">Simulador de convenio</div>
        <h1 class="main-title">Nueva simulación</h1>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="form-grid">', unsafe_allow_html=True)

    left, right = st.columns([1.15, 0.95])

    with left:
        if not troqueles.empty and "codigo_troquel" in troqueles.columns:
            codigos = troqueles["codigo_troquel"].astype(str).tolist()
            codigo = st.selectbox("Código de troquel", codigos)
        else:
            codigo = st.text_input("Código de troquel", placeholder="Ej: TRQ-10532, o buscar por monodroga")

        tipo = st.radio(
            "Tipo de análisis",
            ["Alta", "Baja", "Detectar automáticamente"],
            horizontal=True,
        )

        st.caption('"Detectar automáticamente" corre el Caso A o el Caso B según corresponda.')

        months_window = st.slider("Vigencia máxima de precio en meses", 1, 24, 6)

        ejecutar = st.button("Ejecutar simulación", type="primary")

    with right:
        monodroga = ""
        potencia = ""
        forma = ""
        laboratorio = ""
        pvp = 0
        estado = ""
        en_convenio = False

        if codigo and not troqueles.empty and "codigo_troquel" in troqueles.columns:
            row = troqueles[troqueles["codigo_troquel"].astype(str) == str(codigo)]
            if not row.empty:
                r = row.iloc[0]
                monodroga = r.get("monodroga", "")
                potencia = r.get("potencia", "")
                forma = r.get("forma_farmacologica", "")
                laboratorio = r.get("laboratorio", "")
                estado = r.get("estado", "")
                en_convenio = codigo in convenio_codes
                try:
                    pvp = float(r.get("pvp", 0) or 0)
                except Exception:
                    pvp = 0

        st.markdown(
            f"""
            <div class="validation-card">
                <div class="validation-title">Validación previa</div>
                <div><span class="check">✓</span> Presentación {'activa' if estado == 'activa' else estado or 'sin dato'}</div>
                <div style="margin-top:8px;"><span class="check">✓</span> Vigencia de precio: ventana {months_window} meses</div>
                <hr style="border:none; border-top:1px solid #ddd6c9; margin:14px 0;">
                <div class="validation-row"><span>Monodroga</span><strong>{monodroga or '-'}</strong></div>
                <div class="validation-row"><span>Potencia/Forma</span><strong>{potencia or '-'} / {forma or '-'}</strong></div>
                <div class="validation-row"><span>Laboratorio</span><strong>{laboratorio or '-'}</strong></div>
                <div class="validation-row"><span>PVP vigente</span><strong>{money(pvp)}</strong></div>
                <div class="validation-row"><span>En convenio</span><strong>{'Sí' if en_convenio else 'No'}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if ejecutar and codigo:
        try:
            if tipo == "Alta":
                result = svc.simulate_alta(codigo, months_window)
            elif tipo == "Baja":
                result = svc.simulate_baja(codigo, months_window)
            else:
                result = (
                    svc.simulate_baja(codigo, months_window)
                    if codigo in convenio_codes
                    else svc.simulate_alta(codigo, months_window)
                )

            try:
                saved = repo.save_result(result.__dict__)
                saved_msg = f"Simulación guardada: {saved.get('id_simulacion')}"
            except Exception as e:
                saved_msg = f"La simulación se calculó, pero no pudo guardarse: {e}"

            impacto = result.facturacion_proyectada_anual - result.facturacion_actual_anual

            reco_badge = (
                '<span class="badge badge-ok">Recomendado</span>'
                if result.recomendacion
                else '<span class="badge badge-no">No recomendado</span>'
            )

            st.markdown(
                f"""
                <div class="result-box">
                    <h3 style="margin-top:0;">Resultado de simulación</h3>
                    <p>{reco_badge}</p>
                    <p><strong>Motivo:</strong> {result.motivo}</p>
                    <div class="metric-grid" style="grid-template-columns: repeat(3, 1fr); margin-top:20px;">
                        <div class="metric-card">
                            <div class="metric-label">Facturación actual anual</div>
                            <div class="metric-value">{money(result.facturacion_actual_anual)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Facturación proyectada anual</div>
                            <div class="metric-value">{money(result.facturacion_proyectada_anual)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Impacto neto</div>
                            <div class="metric-value {'green-value' if impacto < 0 else ''}">{money(impacto)}</div>
                        </div>
                    </div>
                    <p class="footer-note">{saved_msg}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("Ver detalle de consumo"):
                st.json(result.detalle_consumo)

        except Exception as e:
            st.error(f"No se pudo ejecutar la simulación: {e}")
    else:
        st.markdown(
            """
            <div class="result-placeholder">
                <div>
                    <strong>El resultado de la simulación aparecerá aquí</strong><br>
                    Incluye recomendación, motivo, info de consumo y simulación de facturación.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Datos cargados"):
        st.write("Troqueles")
        st.dataframe(troqueles, use_container_width=True)

        st.write("Convenio OYTE")
        st.dataframe(convenio, use_container_width=True)

        st.write("Liquidaciones")
        st.dataframe(liquidaciones, use_container_width=True)

    st.markdown("</div></div>", unsafe_allow_html=True)
