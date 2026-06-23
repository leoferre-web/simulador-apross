import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import plotly.express as px
from core.repositories import Repo
from core.services import SimulationService

st.set_page_config(page_title='Simulador APROSS OYTE', layout='wide')

st.markdown('''
<style>
.metric-card {background:#f7f5ef;border-radius:14px;padding:18px;border:1px solid #ebe7dc;}
.status-ok {background:#e2f3ed;color:#0f6b5f;padding:4px 10px;border-radius:999px;font-weight:600;}
.status-no {background:#f8e8e2;color:#8a3b25;padding:4px 10px;border-radius:999px;font-weight:600;}
</style>
''', unsafe_allow_html=True)

st.title('Simulador Troqueles APROSS OYTE')
st.caption('Motor de reglas para altas, bajas, análisis paralelo y simulación de impacto económico')

@st.cache_data(ttl=60)
def load_data():
    repo = Repo()
    return repo.table_df('troqueles'), repo.table_df('convenio_oyte'), repo.table_df('liquidaciones')

try:
    troqueles, convenio, liquidaciones = load_data()
except Exception as e:
    st.error(f'No se pudieron cargar datos desde Supabase: {e}')
    st.stop()

svc = SimulationService(troqueles, convenio, liquidaciones)
repo = Repo()

tab_panel, tab_simular, tab_historial, tab_datos = st.tabs(['Panel financiero', 'Nueva simulación', 'Historial', 'Datos'])

with tab_panel:
    convenio_codes = svc.active_convenio_codes()
    if troqueles.empty or liquidaciones.empty:
    fact_actual = 0
else:
    fact_actual = svc._full('A','',False,'', {'monodroga':'','potencia':''}, convenio_codes, convenio_codes).facturacion_actual_anual
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Facturación actual anual', f'${fact_actual:,.0f}')
    c2.metric('Troqueles convenidos', len(convenio_codes))
    c3.metric('Troqueles ALB', len(troqueles))
    c4.metric('Liquidaciones', len(liquidaciones))

    st.subheader('Troqueles por monodroga')
    if not troqueles.empty:
        count = troqueles.groupby('monodroga', as_index=False).size().sort_values('size', ascending=False).head(15)
        fig = px.bar(count, x='monodroga', y='size', labels={'size':'Cantidad', 'monodroga':'Monodroga'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Sin datos de troqueles.')

with tab_simular:
    st.subheader('Nueva simulación')
    col_form, col_prev = st.columns([1.2, 1])
    with col_form:
        codigos = troqueles['codigo_troquel'].astype(str).tolist() if not troqueles.empty else []
        codigo = st.selectbox('Código de troquel', codigos) if codigos else st.text_input('Código de troquel')
        tipo = st.radio('Tipo de análisis', ['Alta', 'Baja', 'Auto'], horizontal=True)
        months_window = st.slider('Vigencia máxima de precio en meses', 1, 24, 6)
        ejecutar = st.button('Ejecutar simulación', type='primary')
    with col_prev:
        st.markdown('#### Validación previa')
        if codigo and not troqueles.empty:
            row = troqueles[troqueles['codigo_troquel'].astype(str) == str(codigo)]
            if not row.empty:
                r = row.iloc[0]
                st.write(f"**Monodroga:** {r.get('monodroga','')}")
                st.write(f"**Potencia/Forma:** {r.get('potencia','')} / {r.get('forma_farmacologica','')}")
                st.write(f"**Laboratorio:** {r.get('laboratorio','')}")
                st.write(f"**PVP:** ${float(r.get('pvp',0)):,.0f}")
                st.write(f"**Estado:** {r.get('estado','')}")
                st.write(f"**En convenio:** {'Sí' if codigo in convenio_codes else 'No'}")
            else:
                st.warning('Código no encontrado.')

    if ejecutar and codigo:
        if tipo == 'Alta':
            result = svc.simulate_alta(codigo, months_window)
        elif tipo == 'Baja':
            result = svc.simulate_baja(codigo, months_window)
        else:
            result = svc.simulate_baja(codigo, months_window) if codigo in convenio_codes else svc.simulate_alta(codigo, months_window)
        data = result.__dict__
        try:
            saved = repo.save_result(data)
            st.success(f"Simulación guardada: {saved.get('id_simulacion')}")
        except Exception as e:
            st.warning(f'La simulación se calculó, pero no pudo guardarse: {e}')
        st.markdown('### Resultado')
        st.metric('Recomendación', 'Sí' if result.recomendacion else 'No')
        st.write(result.motivo)
        a, b, c = st.columns(3)
        a.metric('Facturación actual anual', f'${result.facturacion_actual_anual:,.0f}')
        b.metric('Facturación proyectada anual', f'${result.facturacion_proyectada_anual:,.0f}')
        c.metric('Impacto neto', f'${result.facturacion_proyectada_anual - result.facturacion_actual_anual:,.0f}')
        st.json(result.detalle_consumo)

with tab_historial:
    st.subheader('Historial de simulaciones')
    try:
        hist = repo.table_df('simulacion_resultados', limit=500)
        if not hist.empty:
            st.dataframe(hist.sort_values('fecha_corrida', ascending=False), use_container_width=True)
        else:
            st.info('Todavía no hay simulaciones guardadas.')
    except Exception as e:
        st.warning(f'No se pudo leer historial: {e}')

with tab_datos:
    st.subheader('Datos cargados')
    st.write('Troqueles')
    st.dataframe(troqueles, use_container_width=True)
    st.write('Convenio OYTE')
    st.dataframe(convenio, use_container_width=True)
    st.write('Liquidaciones')
    st.dataframe(liquidaciones, use_container_width=True)
