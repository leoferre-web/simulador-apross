from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

DISCOUNT_RULES = [(1, 1, 0.44), (2, 5, 0.57), (6, 8, 0.72), (9, 10**9, 0.81)]

@dataclass
class SimulationOutput:
    tipo_caso: str
    codigo_troquel: str
    recomendacion: bool
    motivo: str
    facturacion_actual_anual: float
    facturacion_proyectada_anual: float
    detalle_consumo: dict


def presentacion_key(row: dict | pd.Series) -> str:
    return f"{row.get('potencia','')}|{row.get('forma_farmacologica','')}".strip('|')


def descuento_por_labs(cantidad_labs: int) -> float:
    if cantidad_labs <= 0:
        return 0.0
    for low, high, discount in DISCOUNT_RULES:
        if low <= cantidad_labs <= high:
            return discount
    return 0.81


def band_for_group(troqueles_df: pd.DataFrame) -> dict:
    if troqueles_df.empty:
        labs = 0
    else:
        labs = troqueles_df['laboratorio'].dropna().nunique()
    descuento = descuento_por_labs(labs)
    return {'cantidad_laboratorios': int(labs), 'porcentaje_descuento': descuento}


def is_eligible(troquel: dict, months_window: int = 6) -> tuple[bool, str]:
    if not troquel:
        return False, 'Troquel inexistente.'
    if troquel.get('estado') != 'activa':
        return False, 'Presentación no elegible: estado no activo.'
    fv = pd.to_datetime(troquel.get('fecha_vigencia_precio')).date()
    if fv < (date.today() - relativedelta(months=months_window)):
        return False, f'Presentación no elegible: precio con vigencia mayor a {months_window} meses.'
    return True, 'Elegible.'


def second_highest_pvp(monodroga_df: pd.DataFrame) -> float | None:
    vals = sorted(monodroga_df['pvp'].dropna().astype(float).unique(), reverse=True)
    if len(vals) >= 2:
        return vals[1]
    if len(vals) == 1:
        return vals[0]
    return None


def consumption_block(liq_df: pd.DataFrame, troqueles_df: pd.DataFrame, monodroga: str, potencia: str | None = None) -> dict:
    mono_codes = troqueles_df.loc[troqueles_df['monodroga'] == monodroga, 'codigo_troquel'].tolist()
    liq_mono = liq_df[liq_df['codigo_troquel'].isin(mono_codes)].copy()
    if liq_mono.empty:
        return {
            'afiliados_monodroga': 0, 'costo_anual_monodroga': 0,
            'afiliados_misma_potencia': 0, 'costo_anual_misma_potencia': 0,
            'promedio_mensual_cajas_por_afiliado': 0, 'tasa_uso_potencia': 0,
            'consumo_promedio_mensual_producto': []
        }
    joined = liq_mono.merge(troqueles_df[['codigo_troquel','monodroga','potencia']], on='codigo_troquel', how='left')
    joined['importe'] = joined['cantidad_cajas'].astype(float) * joined['pvp_descuento'].astype(float)
    months = max(joined['periodo'].nunique(), 1)
    by_product = joined.groupby('codigo_troquel').agg(
        cajas_promedio_mensual=('cantidad_cajas', lambda s: float(s.sum())/months),
        pxq_promedio_mensual=('importe', lambda s: float(s.sum())/months)
    ).reset_index().to_dict('records')
    aff_mono = joined['afiliado_id'].nunique()
    same_pot = joined[joined['potencia'].astype(str) == str(potencia)] if potencia is not None else joined.iloc[0:0]
    aff_pot = same_pot['afiliado_id'].nunique()
    avg_boxes = float(joined['cantidad_cajas'].sum()) / months / max(aff_mono, 1)
    return {
        'afiliados_monodroga': int(aff_mono),
        'costo_anual_monodroga': float(joined['importe'].sum()) / months * 12,
        'afiliados_misma_potencia': int(aff_pot),
        'costo_anual_misma_potencia': float(same_pot['importe'].sum()) / months * 12 if not same_pot.empty else 0,
        'promedio_mensual_cajas_por_afiliado': avg_boxes,
        'tasa_uso_potencia': float(aff_pot / aff_mono) if aff_mono else 0,
        'consumo_promedio_mensual_producto': by_product
    }


def annual_billing(liq_df: pd.DataFrame, convenio_codes: list[str]) -> float:
    df = liq_df[liq_df['codigo_troquel'].isin(convenio_codes)].copy()
    if df.empty:
        return 0.0
    df['importe'] = df['cantidad_cajas'].astype(float) * df['pvp_descuento'].astype(float)
    return float(df['importe'].sum()) / max(df['periodo'].nunique(), 1) * 12
