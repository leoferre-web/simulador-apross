# ============================================================
# BLOQUE 01 — Imports
# ============================================================

from __future__ import annotations

import pandas as pd

from core.rules import (
    SimulationOutput,
    evaluate_case_a,
    consumption_block,
    projected_billing_by_band,
)


# ============================================================
# BLOQUE 02 — Servicio principal
# ============================================================

class SimulationService:

    def __init__(
        self,
        troqueles: pd.DataFrame,
        convenio: pd.DataFrame,
        bandas: pd.DataFrame,
        liquidaciones: pd.DataFrame,
    ):
        """
        Servicio Caso A — Alta de troquel.
        """

        self.troqueles_raw = troqueles.copy()
        self.convenio = convenio.copy()
        self.bandas = bandas.copy()
        self.liquidaciones = liquidaciones.copy()

        self.troqueles = self._build_current_alb()


# ============================================================
# BLOQUE 03 — Normalización de códigos
# ============================================================

    def _normalize_code(self, value) -> str:

        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

        try:
            return str(int(float(value)))
        except Exception:
            return str(value).strip()


# ============================================================
# BLOQUE 04 — Vista vigente del ALB
# ============================================================

    def _build_current_alb(self) -> pd.DataFrame:

        if self.troqueles_raw.empty:
            return self.troqueles_raw.copy()

        df = self.troqueles_raw.copy()

        if "tronquel" not in df.columns:
            return df

        df["_troquel_normalizado"] = (
            df["tronquel"]
            .apply(self._normalize_code)
        )

        if "fecha" in df.columns:
            df["_fecha_orden"] = pd.to_datetime(
                df["fecha"],
                errors="coerce",
            )
        else:
            df["_fecha_orden"] = pd.NaT

        if "id" in df.columns:
            df["_id_orden"] = pd.to_numeric(
                df["id"],
                errors="coerce",
            ).fillna(0)
        else:
            df["_id_orden"] = 0

        df = df.sort_values(
            [
                "_troquel_normalizado",
                "_fecha_orden",
                "_id_orden",
            ],
            ascending=[
                True,
                False,
                False,
            ],
        )

        df = df.drop_duplicates(
            subset=["_troquel_normalizado"],
            keep="first",
        )

        df["tronquel"] = df["_troquel_normalizado"]

        df = df.drop(
            columns=[
                "_troquel_normalizado",
                "_fecha_orden",
                "_id_orden",
            ],
            errors="ignore",
        )

        return df.reset_index(drop=True)


# ============================================================
# BLOQUE 05 — Obtener candidato
# ============================================================

    def get_troquel(
        self,
        codigo_troquel: str,
    ) -> dict | None:

        if (
            self.troqueles.empty
            or "tronquel" not in self.troqueles.columns
        ):
            return None

        codigo = self._normalize_code(
            codigo_troquel
        )

        row = self.troqueles[
            self.troqueles["tronquel"]
            .apply(self._normalize_code)
            == codigo
        ]

        if row.empty:
            return None

        return row.iloc[0].to_dict()


# ============================================================
# BLOQUE 06 — Troqueles en convenio
# ============================================================

    def active_convenio_codes(
        self,
    ) -> list[str]:

        if (
            self.convenio.empty
            or "troquel" not in self.convenio.columns
        ):
            return []

        codigos = (
            self.convenio["troquel"]
            .dropna()
            .apply(self._normalize_code)
        )

        codigos = codigos[
            codigos != ""
        ]

        return (
            codigos
            .unique()
            .tolist()
        )


# ============================================================
# BLOQUE 07 — Verificar convenio
# ============================================================

    def is_in_convenio(
        self,
        codigo_troquel: str,
    ) -> bool:

        codigo = self._normalize_code(
            codigo_troquel
        )

        return codigo in set(
            self.active_convenio_codes()
        )


# ============================================================
# BLOQUE 08 — Universo para banda
# ============================================================

    def equivalent_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        Para banda se utiliza únicamente cod_monodroga.
        """

        if (
            not troquel
            or self.troqueles.empty
            or "cod_monodroga"
            not in self.troqueles.columns
        ):
            return pd.DataFrame()

        cod_monodroga = pd.to_numeric(
            pd.Series(
                [troquel.get("cod_monodroga")]
            ),
            errors="coerce",
        ).iloc[0]

        if pd.isna(cod_monodroga):
            return pd.DataFrame()

        df = self.troqueles.copy()

        df["_cod_monodroga_num"] = (
            pd.to_numeric(
                df["cod_monodroga"],
                errors="coerce",
            )
        )

        grupo = df[
            df["_cod_monodroga_num"]
            == cod_monodroga
        ].copy()

        return grupo.drop(
            columns=["_cod_monodroga_num"],
            errors="ignore",
        )


# ============================================================
# BLOQUE 09 — Monodroga conveniada
# ============================================================

    def current_convenio_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:

        grupo = self.equivalent_group(
            troquel
        )

        if grupo.empty:
            return grupo

        convenio_codes = set(
            self.active_convenio_codes()
        )

        grupo = grupo.copy()

        grupo["_troquel_normalizado"] = (
            grupo["tronquel"]
            .apply(self._normalize_code)
        )

        grupo = grupo[
            grupo["_troquel_normalizado"]
            .isin(convenio_codes)
        ].copy()

        return grupo.drop(
            columns=["_troquel_normalizado"],
            errors="ignore",
        )


# ============================================================
# BLOQUE 10 — Contar laboratorios
# ============================================================

    def count_laboratories(
        self,
        grupo: pd.DataFrame,
    ) -> int:

        if (
            grupo.empty
            or "desc_laboratorio" not in grupo.columns
        ):
            return 0

        labs = (
            grupo["desc_laboratorio"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        labs = labs[
            labs != ""
        ]

        return int(labs.nunique())


# ============================================================
# BLOQUE 11 — Obtener banda
# ============================================================

    def get_band(
        self,
        cantidad_laboratorios: int,
    ) -> dict:

        if cantidad_laboratorios <= 0:
            return {
                "cantidad_laboratorios": 0,
                "porcentaje_descuento": 0.0,
                "banda_texto": "Sin banda",
            }

        if self.bandas.empty:
            return {
                "cantidad_laboratorios":
                    cantidad_laboratorios,
                "porcentaje_descuento": 0.0,
                "banda_texto": "",
            }

        df = self.bandas.copy()

        df["cantidad_laboratorios"] = (
            pd.to_numeric(
                df["cantidad_laboratorios"],
                errors="coerce",
            )
        )

        fila = df[
            df["cantidad_laboratorios"]
            == cantidad_laboratorios
        ]

        if fila.empty:

            max_labs = (
                df["cantidad_laboratorios"]
                .max()
            )

            fila = df[
                df["cantidad_laboratorios"]
                == max_labs
            ]

        if fila.empty:
            return {
                "cantidad_laboratorios":
                    cantidad_laboratorios,
                "porcentaje_descuento": 0.0,
                "banda_texto": "",
            }

        r = fila.iloc[0]

        return {
            "cantidad_laboratorios":
                int(cantidad_laboratorios),

            "porcentaje_descuento":
                float(
                    r.get(
                        "descuento",
                        0,
                    )
                    or 0
                ),

            "banda_texto":
                str(
                    r.get(
                        "banda_texto",
                        "",
                    )
                    or ""
                ),
        }


# ============================================================
# BLOQUE 12 — Banda actual
# ============================================================

    def current_band(
        self,
        troquel: dict,
    ) -> dict:

        grupo = self.current_convenio_group(
            troquel
        )

        cantidad = self.count_laboratories(
            grupo
        )

        return self.get_band(
            cantidad
        )


# ============================================================
# BLOQUE 13 — Banda hipotética
# ============================================================

    def hypothetical_band(
        self,
        troquel: dict,
    ) -> dict:

        grupo = self.current_convenio_group(
            troquel
        )

        actual = self.count_laboratories(
            grupo
        )

        laboratorio_candidato = str(
            troquel.get(
                "desc_laboratorio",
                "",
            )
            or ""
        ).strip()

        laboratorios_actuales = set()

        if (
            not grupo.empty
            and "desc_laboratorio" in grupo.columns
        ):

            laboratorios_actuales = set(
                grupo["desc_laboratorio"]
                .dropna()
                .astype(str)
                .str.strip()
            )

        if (
            laboratorio_candidato
            and laboratorio_candidato
            not in laboratorios_actuales
        ):

            cantidad_hipotetica = (
                actual + 1
            )

        else:

            cantidad_hipotetica = actual

        return self.get_band(
            cantidad_hipotetica
        )


# ============================================================
# BLOQUE 14 — Universo segundo PVP
# ============================================================

    def monodroga_universe(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        Segundo PVP:

        cod_monodroga
        + formas
        + potencia
        + unidad_potencia
        + solo conveniados
        """

        if (
            not troquel
            or self.troqueles.empty
        ):
            return pd.DataFrame()

        required = [
            "tronquel",
            "cod_monodroga",
            "formas",
            "potencia",
            "unidad_potencia",
            "precio",
        ]

        for col in required:
            if col not in self.troqueles.columns:
                return pd.DataFrame()

        cod_monodroga = pd.to_numeric(
            pd.Series(
                [troquel.get("cod_monodroga")]
            ),
            errors="coerce",
        ).iloc[0]

        if pd.isna(cod_monodroga):
            return pd.DataFrame()

        forma = str(
            troquel.get("formas", "")
            or ""
        ).strip()

        potencia = str(
            troquel.get("potencia", "")
            or ""
        ).strip()

        unidad = str(
            troquel.get(
                "unidad_potencia",
                "",
            )
            or ""
        ).strip()

        convenio_codes = set(
            self.active_convenio_codes()
        )

        df = self.troqueles.copy()

        df["_cod_mono"] = pd.to_numeric(
            df["cod_monodroga"],
            errors="coerce",
        )

        df["_troquel"] = (
            df["tronquel"]
            .apply(self._normalize_code)
        )

        df["_forma"] = (
            df["formas"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["_potencia"] = (
            df["potencia"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["_unidad"] = (
            df["unidad_potencia"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        universo = df[
            (df["_cod_mono"] == cod_monodroga)
            &
            (df["_forma"] == forma)
            &
            (df["_potencia"] == potencia)
            &
            (df["_unidad"] == unidad)
            &
            (df["_troquel"].isin(convenio_codes))
        ].copy()

        return universo.drop(
            columns=[
                "_cod_mono",
                "_troquel",
                "_forma",
                "_potencia",
                "_unidad",
            ],
            errors="ignore",
        )


# ============================================================
# BLOQUE 15 — Segundo PVP más alto
# ============================================================

    def second_highest_price(
        self,
        troquel: dict,
    ) -> float | None:

        universo = self.monodroga_universe(
            troquel
        )

        if (
            universo.empty
            or "precio" not in universo.columns
        ):
            return None

        valores = pd.to_numeric(
            universo["precio"],
            errors="coerce",
        ).dropna()

        valores = valores[
            valores > 0
        ]

        valores = sorted(
            valores.unique(),
            reverse=True,
        )

        if len(valores) >= 2:
            return float(
                valores[1]
            )

        if len(valores) == 1:
            return float(
                valores[0]
            )

        return None


# ============================================================
# BLOQUE 16 — Simulación Caso A
# ============================================================

    def simulate_alta(
        self,
        codigo_troquel: str,
        months_window: int = 6,
    ) -> SimulationOutput:

        codigo_troquel = (
            self._normalize_code(
                codigo_troquel
            )
        )

        # ----------------------------------------------------
        # 1. Candidato
        # ----------------------------------------------------

        troquel = self.get_troquel(
            codigo_troquel
        )

        if not troquel:

            return SimulationOutput(
                tipo_caso="A",
                codigo_troquel=
                    codigo_troquel,
                recomendacion=False,
                motivo=(
                    "Presentación no elegible: "
                    "troquel inexistente en ALB."
                ),
                facturacion_actual_anual=0,
                facturacion_proyectada_anual=0,
                detalle_consumo={},
            )

        # ----------------------------------------------------
        # 2. Convenio
        # ----------------------------------------------------

        ya_convenido = (
            self.is_in_convenio(
                codigo_troquel
            )
        )

        # ----------------------------------------------------
        # 3. Bandas
        # ----------------------------------------------------

        banda_actual = (
            self.current_band(
                troquel
            )
        )

        banda_hipotetica = (
            self.hypothetical_band(
                troquel
            )
        )

        # ----------------------------------------------------
        # 4. Segundo PVP
        # ----------------------------------------------------

        segundo_pvp = (
            self.second_highest_price(
                troquel
            )
        )

        # ----------------------------------------------------
        # 5. Motor de reglas
        # ----------------------------------------------------

        rule_result = evaluate_case_a(

            troquel=
                troquel,

            ya_en_convenio=
                ya_convenido,

            banda_actual=
                banda_actual,

            banda_hipotetica=
                banda_hipotetica,

            segundo_pvp=
                segundo_pvp,

            months_window=
                months_window,
        )

        # ----------------------------------------------------
        # 6. No elegible / ya conveniado
        # ----------------------------------------------------

        if not rule_result.aplica:

            detalle = {
                "estado":
                    rule_result.estado,

                "elegible":
                    rule_result.elegible,

                "ya_en_convenio":
                    rule_result.ya_en_convenio,

                "banda_actual":
                    rule_result.banda_actual,

                "banda_hipotetica":
                    rule_result.banda_hipotetica,

                "laboratorios_actuales":
                    rule_result.laboratorios_actuales,

                "laboratorios_hipoteticos":
                    rule_result.laboratorios_hipoteticos,

                "pvp_candidato":
                    rule_result.pvp_candidato,

                "segundo_pvp_mas_alto":
                    rule_result.segundo_pvp_mas_alto,
            }

            return SimulationOutput(
                tipo_caso="A",
                codigo_troquel=
                    codigo_troquel,
                recomendacion=False,
                motivo=
                    rule_result.motivo,
                facturacion_actual_anual=0,
                facturacion_proyectada_anual=0,
                detalle_consumo=
                    detalle,
            )

        # ----------------------------------------------------
        # 7. Consumo histórico
        # ----------------------------------------------------

        detalle_consumo = (
            consumption_block(

                liq_df=
                    self.liquidaciones,

                troqueles_df=
                    self.troqueles,

                cod_monodroga=
                    troquel.get(
                        "cod_monodroga"
                    ),

                potencia=
                    troquel.get(
                        "potencia"
                    ),
            )
        )

        # ----------------------------------------------------
        # 8. Detalle de reglas
        # ----------------------------------------------------

        detalle_consumo.update(
            {
                "estado":
                    rule_result.estado,

                "elegible":
                    rule_result.elegible,

                "ya_en_convenio":
                    rule_result.ya_en_convenio,

                "banda_actual":
                    rule_result.banda_actual,

                "banda_hipotetica":
                    rule_result.banda_hipotetica,

                "laboratorios_actuales":
                    rule_result.laboratorios_actuales,

                "laboratorios_hipoteticos":
                    rule_result.laboratorios_hipoteticos,

                "mejora_banda":
                    rule_result.mejora_banda,

                "pvp_candidato":
                    rule_result.pvp_candidato,

                "segundo_pvp_mas_alto":
                    rule_result.segundo_pvp_mas_alto,

                "cumple_pvp":
                    rule_result.cumple_pvp,
            }
        )

        # ----------------------------------------------------
        # 9. Códigos conveniados
        # ----------------------------------------------------

        current_codes = (
            self.active_convenio_codes()
        )

        # ----------------------------------------------------
        # 10. Simulación económica
        #
        # IMPORTANTE:
        # devuelve únicamente valores de la monodroga.
        # ----------------------------------------------------

        simulacion_economica = (
            projected_billing_by_band(

                liq_df=
                    self.liquidaciones,

                troqueles_df=
                    self.troqueles,

                convenio_codes=
                    current_codes,

                troquel_candidato=
                    troquel,

                banda_actual=
                    rule_result.banda_actual,

                banda_proyectada=
                    rule_result.banda_hipotetica,
            )
        )

        # ----------------------------------------------------
        # 11. FACTURACIÓN ACTUAL DE LA MONODROGA
        # ----------------------------------------------------

        facturacion_actual_monodroga = float(
            simulacion_economica.get(
                "facturacion_actual_monodroga_anual",
                0,
            )
            or 0
        )

        # ----------------------------------------------------
        # 12. FACTURACIÓN PROYECTADA DE LA MONODROGA
        # ----------------------------------------------------

        facturacion_proyectada_calculada = float(
            simulacion_economica.get(
                "facturacion_proyectada_monodroga_anual",
                0,
            )
            or 0
        )

        if rule_result.recomendacion:

            facturacion_proyectada_monodroga = (
                facturacion_proyectada_calculada
            )

        else:

            # Si no se recomienda incorporar,
            # no se aplica el cambio de banda.
            facturacion_proyectada_monodroga = (
                facturacion_actual_monodroga
            )

        # ----------------------------------------------------
        # 13. Impacto
        # ----------------------------------------------------

        impacto_anual = (
            facturacion_proyectada_monodroga
            - facturacion_actual_monodroga
        )

        ahorro_anual = (
            facturacion_actual_monodroga
            - facturacion_proyectada_monodroga
        )

        ahorro_porcentual = (
            ahorro_anual
            / facturacion_actual_monodroga
            if facturacion_actual_monodroga > 0
            else 0.0
        )

        # ----------------------------------------------------
        # 14. Detalle económico
        # ----------------------------------------------------

        detalle_consumo.update(
            {
                "facturacion_actual_monodroga_anual":
                    facturacion_actual_monodroga,

                "facturacion_proyectada_monodroga_anual":
                    facturacion_proyectada_monodroga,

                "impacto_anual":
                    impacto_anual,

                "ahorro_anual":
                    ahorro_anual,

                "ahorro_porcentual":
                    ahorro_porcentual,

                "cantidad_liquidaciones_afectadas":
                    simulacion_economica.get(
                        "cantidad_liquidaciones",
                        0,
                    ),

                "unidades_historicas_afectadas":
                    simulacion_economica.get(
                        "unidades_historicas",
                        0,
                    ),

                "meses_observados":
                    simulacion_economica.get(
                        "meses_observados",
                        0,
                    ),

                "troqueles_afectados":
                    simulacion_economica.get(
                        "troqueles_afectados",
                        [],
                    ),

                "banda_economica_actual":
                    simulacion_economica.get(
                        "banda_actual",
                        0,
                    ),

                "banda_economica_proyectada":
                    simulacion_economica.get(
                        "banda_proyectada",
                        0,
                    ),
            }
        )

        # ----------------------------------------------------
        # 15. Resultado final
        #
        # ESTOS SON LOS VALORES QUE MAIN.PY
        # MOSTRARÁ EN LAS TRES TARJETAS.
        # ----------------------------------------------------

        return SimulationOutput(

            tipo_caso="A",

            codigo_troquel=
                codigo_troquel,

            recomendacion=bool(
                rule_result.recomendacion
            ),

            motivo=
                rule_result.motivo,

            # SOLO MONODROGA
            facturacion_actual_anual=(
                facturacion_actual_monodroga
            ),

            # SOLO MONODROGA
            facturacion_proyectada_anual=(
                facturacion_proyectada_monodroga
            ),

            detalle_consumo=(
                detalle_consumo
            ),
        )
