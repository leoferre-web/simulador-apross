from __future__ import annotations
import pandas as pd
from core.rules import (
    SimulationOutput, presentacion_key, band_for_group, is_eligible,
    second_highest_pvp, consumption_block, annual_billing
)

class SimulationService:
    def __init__(self, troqueles: pd.DataFrame, convenio: pd.DataFrame, liquidaciones: pd.DataFrame):
        self.troqueles = troqueles.copy()
        self.convenio = convenio.copy()
        self.liquidaciones = liquidaciones.copy()
        if not self.troqueles.empty:
            self.troqueles['presentacion_equivalente'] = self.troqueles.apply(presentacion_key, axis=1)

    def active_convenio_codes(self) -> list[str]:
        if self.convenio.empty:
            return []
        df = self.convenio[self.convenio['fecha_baja_convenio'].isna()]
        return df['codigo_troquel'].astype(str).tolist()

    def current_group(self, troquel: dict) -> pd.DataFrame:
        return self.troqueles[
            (self.troqueles['estado'] == 'activa') &
            (self.troqueles['monodroga'] == troquel['monodroga']) &
            (self.troqueles['presentacion_equivalente'] == presentacion_key(troquel))
        ].copy()

    def simulate_alta(self, codigo_troquel: str, months_window: int = 6) -> SimulationOutput:
        row = self.troqueles[self.troqueles['codigo_troquel'].astype(str) == str(codigo_troquel)]
        troquel = row.iloc[0].to_dict() if not row.empty else None
        ok, msg = is_eligible(troquel, months_window)
        if not ok:
            return self._basic('A', codigo_troquel, False, msg, troquel)

        if codigo_troquel in self.active_convenio_codes():
            return self._basic('A', codigo_troquel, False, 'No aplica alta: el troquel ya está convenido.', troquel)

        current = self.current_group(troquel)
        current_convenio = current[current['codigo_troquel'].isin(self.active_convenio_codes())]
        hypo = pd.concat([current_convenio, pd.DataFrame([troquel])], ignore_index=True).drop_duplicates('codigo_troquel')
        band_current = band_for_group(current_convenio)
        band_hypo = band_for_group(hypo)
        improves_band = band_hypo['porcentaje_descuento'] > band_current['porcentaje_descuento']

        mono = self.troqueles[self.troqueles['monodroga'] == troquel['monodroga']]
        second_pvp = second_highest_pvp(mono)
        pvp_ok = second_pvp is not None and float(troquel['pvp']) <= second_pvp
        recommend = improves_band and pvp_ok
        motivo = []
        motivo.append(f"Banda actual {band_current['porcentaje_descuento']:.0%}; banda hipotética {band_hypo['porcentaje_descuento']:.0%}.")
        motivo.append(f"PVP candidato ${float(troquel['pvp']):,.0f}; segundo más caro ${second_pvp:,.0f}." if second_pvp is not None else 'No hay universo suficiente para segundo PVP más caro.')
        motivo.append('Recomendar alta.' if recommend else 'No recomendar alta: no cumple todas las condiciones.')
        current_codes = self.active_convenio_codes()
        projected_codes = list(set(current_codes + [codigo_troquel])) if recommend else current_codes
        return self._full('A', codigo_troquel, recommend, ' '.join(motivo), troquel, current_codes, projected_codes)

    def simulate_baja(self, codigo_troquel: str, months_window: int = 6) -> SimulationOutput:
        row = self.troqueles[self.troqueles['codigo_troquel'].astype(str) == str(codigo_troquel)]
        troquel = row.iloc[0].to_dict() if not row.empty else None
        ok, msg = is_eligible(troquel, months_window)
        if not ok:
            return self._basic('B', codigo_troquel, False, msg, troquel)
        if codigo_troquel not in self.active_convenio_codes():
            return self._basic('B', codigo_troquel, False, 'No aplica baja: el troquel no está convenido.', troquel)

        group = self.current_group(troquel)
        current_convenio = group[group['codigo_troquel'].isin(self.active_convenio_codes())]
        hypo = current_convenio[current_convenio['codigo_troquel'] != codigo_troquel]
        band_current = band_for_group(current_convenio)
        band_hypo = band_for_group(hypo)
        worsens_band = band_hypo['porcentaje_descuento'] < band_current['porcentaje_descuento']
        mono_remaining = self.troqueles[(self.troqueles['monodroga'] == troquel['monodroga']) & (self.troqueles['codigo_troquel'] != codigo_troquel)]
        second_pvp = second_highest_pvp(mono_remaining)
        pvp_low = second_pvp is not None and float(troquel['pvp']) < second_pvp
        recommend_baja = not (worsens_band and pvp_low)
        motivo = []
        motivo.append(f"Banda actual {band_current['porcentaje_descuento']:.0%}; banda sin troquel {band_hypo['porcentaje_descuento']:.0%}.")
        motivo.append(f"PVP a excluir ${float(troquel['pvp']):,.0f}; segundo más caro restante ${second_pvp:,.0f}." if second_pvp is not None else 'No hay universo suficiente para segundo PVP más caro.')
        motivo.append('Recomendar baja.' if recommend_baja else 'No recomendar baja: empeora banda y el PVP a sacar es bajo.')
        current_codes = self.active_convenio_codes()
        projected_codes = [c for c in current_codes if c != codigo_troquel] if recommend_baja else current_codes
        return self._full('B', codigo_troquel, recommend_baja, ' '.join(motivo), troquel, current_codes, projected_codes)

    def _basic(self, tipo: str, codigo: str, rec: bool, motivo: str, troquel: dict | None) -> SimulationOutput:
        return self._full(tipo, codigo, rec, motivo, troquel or {}, self.active_convenio_codes(), self.active_convenio_codes())

    def _full(self, tipo: str, codigo: str, rec: bool, motivo: str, troquel: dict, current_codes: list[str], projected_codes: list[str]) -> SimulationOutput:
        detalle = consumption_block(self.liquidaciones, self.troqueles, troquel.get('monodroga',''), troquel.get('potencia')) if troquel else {}
        return SimulationOutput(
            tipo_caso=tipo,
            codigo_troquel=codigo,
            recomendacion=bool(rec),
            motivo=motivo,
            facturacion_actual_anual=annual_billing(self.liquidaciones, current_codes),
            facturacion_proyectada_anual=annual_billing(self.liquidaciones, projected_codes),
            detalle_consumo=detalle
        )
