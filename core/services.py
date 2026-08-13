# ============================================================
# BLOQUE 01 — Imports
# ============================================================

from __future__ import annotations

import pandas as pd

from core.rules import (
    SimulationOutput,
    evaluate_case_a,
    consumption_block,
    annual_billing,
)


# ============================================================
# BLOQUE 02 — Servicio principal de simulación
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
        Servicio exclusivo para Caso A — Alta de troquel.

        Fuentes:
        - src_troqueles_alb
        - src_convenio_oyte
        - src_bandas_descuento
        - src_liquidaciones
        """

        self.troqueles_raw = troqueles.copy()
        self.convenio = convenio.copy()
        self.bandas = bandas.copy()
        self.liquidaciones = liquidaciones.copy()

        self.troqueles = self._build_current_alb()


# ============================================================
# BLOQUE 03 — Vista vigente del ALB
# ============================================================

    def _build_current_alb(self) -> pd.DataFrame:
        """
        Para cada tronquel:
        1. toma la fecha de precio más reciente;
        2. si hay empate, toma el ID más alto de Supabase.
        """

        if self.troqueles_raw.empty:
            return self.troqueles_raw.copy()

        df = self.troqueles_raw.copy()

        if "tronquel" not in df.columns:
            return df

        df["tronquel"] = df["tronquel"].astype(str)

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
            ["tronquel", "_fecha_orden", "_id_orden"],
            ascending=[True, False, False],
        )

        df = df.drop_duplicates(
            subset=["tronquel"],
            keep="first",
        )

        df = df.drop(
            columns=["_fecha_orden", "_id_orden"],
            errors="ignore",
        )

        return df.reset_index(drop=True)


# ============================================================
# BLOQUE 04 — Obtener troquel candidato
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

        row = self.troqueles[
            self.troqueles["tronquel"].astype(str)
            == str(codigo_troquel)
        ]

        if row.empty:
            return None

        return row.iloc[0].to_dict()


# ============================================================
# BLOQUE 05 — Troqueles en convenio
# ============================================================

    def active_convenio_codes(self) -> list[str]:
        """
        Si figura en src_convenio_oyte,
        se considera convenido.

        El estado no interviene.
        """

        if (
            self.convenio.empty
            or "troquel" not in self.convenio.columns
        ):
            return []

        return (
            self.convenio["troquel"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )


# ============================================================
# BLOQUE 06 — Verificar si está en convenio
# ============================================================

    def is_in_convenio(
        self,
        codigo_troquel: str,
    ) -> bool:

        return str(codigo_troquel) in set(
            self.active_convenio_codes()
        )


# ============================================================
# BLOQUE 07 — Grupo de presentación equivalente
# ============================================================

    def equivalent_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        Presentación equivalente confirmada:

        cod_monodroga
        + formas
        + potencia
        + unidad_potencia
        """

        if not troquel or self.troqueles.empty:
            return pd.DataFrame()

        required = [
            "cod_monodroga",
            "formas",
            "potencia",
            "unidad_potencia",
        ]

        for col in required:
            if col not in self.troqueles.columns:
                return pd.DataFrame()

        cod_monodroga = troquel.get(
            "cod_monodroga"
        )

        forma = troquel.get(
            "formas"
        )

        potencia = troquel.get(
            "potencia"
        )

        unidad = troquel.get(
            "unidad_potencia"
        )

        return self.troqueles[
            (
                self.troqueles[
                    "cod_monodroga"
                ].astype(str)
                == str(cod_monodroga)
            )
            &
            (
                self.troqueles[
                    "formas"
                ]
                .fillna("")
                .astype(str)
                == str(forma or "")
            )
            &
            (
                self.troqueles[
                    "potencia"
                ]
                .fillna("")
                .astype(str)
                == str(potencia or "")
            )
            &
            (
                self.troqueles[
                    "unidad_potencia"
                ]
                .fillna("")
                .astype(str)
                == str(unidad or "")
            )
        ].copy()


# ============================================================
# BLOQUE 08 — Grupo equivalente actualmente convenido
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

        return grupo[
            grupo["tronquel"]
            .astype(str)
            .isin(convenio_codes)
        ].copy()


# ============================================================
# BLOQUE 09 — Cantidad de laboratorios
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

        return int(
            labs.nunique()
        )


# ============================================================
# BLOQUE 10 — Banda desde tabla real
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
                "porcentaje_descuento":
                    0.0,
                "banda_texto":
                    "",
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

        # Si supera el máximo disponible,
        # usamos la última banda definida.
        if fila.empty:

            max_labs = df[
                "cantidad_laboratorios"
            ].max()

            fila = df[
                df["cantidad_laboratorios"]
                == max_labs
            ]

        if fila.empty:
            return {
                "cantidad_laboratorios":
                    cantidad_laboratorios,
                "porcentaje_descuento":
                    0.0,
                "banda_texto":
                    "",
            }

        r = fila.iloc[0]

        return {
            "cantidad_laboratorios":
                cantidad_laboratorios,

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
# BLOQUE 11 — Banda actual
# ============================================================

    def current_band(
        self,
        troquel: dict,
    ) -> dict:

        current_group = (
            self.current_convenio_group(
                troquel
            )
        )

        cantidad = (
            self.count_laboratories(
                current_group
            )
        )

        return self.get_band(
            cantidad
        )


# ============================================================
# BLOQUE 12 — Banda hipotética
# ============================================================

    def hypothetical_band(
        self,
        troquel: dict,
    ) -> dict:
        """
        Solo suma un laboratorio si el laboratorio
        candidato todavía no está presente dentro
        de los conveniados equivalentes.
        """

        current_group = (
            self.current_convenio_group(
                troquel
            )
        )

        actual = (
            self.count_laboratories(
                current_group
            )
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
            not current_group.empty
            and "desc_laboratorio"
            in current_group.columns
        ):

            laboratorios_actuales = set(
                current_group[
                    "desc_laboratorio"
                ]
                .dropna()
                .astype(str)
                .str.strip()
            )

        if (
            laboratorio_candidato
            and laboratorio_candidato
            not in laboratorios_actuales
        ):

            hipotetico = actual + 1

        else:

            hipotetico = actual

        return self.get_band(
            hipotetico
        )


# ============================================================
# BLOQUE 13 — Universo conveniado de la monodroga
# ============================================================

    def monodroga_universe(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        Universo utilizado para calcular el segundo PVP:

        1. misma cod_monodroga que el candidato;
        2. solamente troqueles que figuran en Convenio OYTE.

        ALB aporta el PVP vigente.
        Convenio OYTE define qué productos forman parte
        del universo de comparación.
        """

        if (
            not troquel
            or self.troqueles.empty
            or "cod_monodroga"
            not in self.troqueles.columns
            or "tronquel"
            not in self.troqueles.columns
        ):

            return pd.DataFrame()

        cod_monodroga = troquel.get(
            "cod_monodroga"
        )

        convenio_codes = set(
            self.active_convenio_codes()
        )

        universo = self.troqueles[
            (
                self.troqueles[
                    "cod_monodroga"
                ].astype(str)
                == str(cod_monodroga)
            )
            &
            (
                self.troqueles[
                    "tronquel"
                ]
                .astype(str)
                .isin(
                    convenio_codes
                )
            )
        ].copy()

        return universo


# ============================================================
# BLOQUE 14 — Segundo PVP más alto de los conveniados
# ============================================================

    def second_highest_price(
        self,
        troquel: dict,
    ) -> float | None:
        """
        Obtiene el segundo PVP más alto entre los
        productos actualmente conveniados de la misma
        monodroga.

        Los PVP provienen del ALB vigente.

        Si existe un solo PVP conveniado válido,
        utiliza ese valor como referencia.

        Si no existen PVP válidos,
        devuelve None.
        """

        universo = (
            self.monodroga_universe(
                troquel
            )
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

        # Descartar precios nulos, negativos o cero.
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
# BLOQUE 15 — Simulación Caso A
# ============================================================

    def simulate_alta(
        self,
        codigo_troquel: str,
        months_window: int = 6,
    ) -> SimulationOutput:

        # ----------------------------------------------------
        # 1. Obtener candidato
        # ----------------------------------------------------

        troquel = self.get_troquel(
            codigo_troquel
        )

        if not troquel:

            return SimulationOutput(
                tipo_caso="A",
                codigo_troquel=str(
                    codigo_troquel
                ),
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
        # 2. ¿Ya está en convenio?
        # ----------------------------------------------------

        ya_convenido = (
            self.is_in_convenio(
                codigo_troquel
            )
        )

        # ----------------------------------------------------
        # 3. Banda actual
        # ----------------------------------------------------

        banda_actual = (
            self.current_band(
                troquel
            )
        )

        # ----------------------------------------------------
        # 4. Banda hipotética
        # ----------------------------------------------------

        banda_hipotetica = (
            self.hypothetical_band(
                troquel
            )
        )

        # ----------------------------------------------------
        # 5. Segundo PVP conveniado
        # ----------------------------------------------------

        segundo_pvp = (
            self.second_highest_price(
                troquel
            )
        )

        # ----------------------------------------------------
        # 6. Regla de negocio
        # ----------------------------------------------------

        rule_result = evaluate_case_a(
            troquel=troquel,
            ya_en_convenio=ya_convenido,
            banda_actual=banda_actual,
            banda_hipotetica=banda_hipotetica,
            segundo_pvp=segundo_pvp,
            months_window=months_window,
        )

        # ----------------------------------------------------
        # 7. No elegible / ya convenido
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
                    rule_result
                    .laboratorios_actuales,

                "laboratorios_hipoteticos":
                    rule_result
                    .laboratorios_hipoteticos,

                "pvp_candidato":
                    rule_result
                    .pvp_candidato,

                "segundo_pvp_mas_alto":
                    rule_result
                    .segundo_pvp_mas_alto,
            }

            return SimulationOutput(
                tipo_caso="A",
                codigo_troquel=str(
                    codigo_troquel
                ),
                recomendacion=False,
                motivo=rule_result.motivo,
                facturacion_actual_anual=0,
                facturacion_proyectada_anual=0,
                detalle_consumo=detalle,
            )

        # ----------------------------------------------------
        # 8. Consumo histórico
        # ----------------------------------------------------

        detalle_consumo = (
            consumption_block(
                liq_df=self.liquidaciones,
                troqueles_df=self.troqueles,
                cod_monodroga=troquel.get(
                    "cod_monodroga"
                ),
                potencia=troquel.get(
                    "potencia"
                ),
            )
        )

        # ----------------------------------------------------
        # 9. Agregar detalle de reglas
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
                    rule_result
                    .laboratorios_actuales,

                "laboratorios_hipoteticos":
                    rule_result
                    .laboratorios_hipoteticos,

                "mejora_banda":
                    rule_result
                    .mejora_banda,

                "pvp_candidato":
                    rule_result
                    .pvp_candidato,

                "segundo_pvp_mas_alto":
                    rule_result
                    .segundo_pvp_mas_alto,

                "cumple_pvp":
                    rule_result
                    .cumple_pvp,
            }
        )

        # ----------------------------------------------------
        # 10. Facturación actual
        # ----------------------------------------------------

        current_codes = (
            self.active_convenio_codes()
        )

        facturacion_actual = (
            annual_billing(
                self.liquidaciones,
                current_codes,
            )
        )

        # ----------------------------------------------------
        # 11. Escenario proyectado
        # ----------------------------------------------------

        if rule_result.recomendacion:

            projected_codes = list(
                set(
                    current_codes
                    + [
                        str(
                            codigo_troquel
                        )
                    ]
                )
            )

        else:

            projected_codes = (
                current_codes
            )

        facturacion_proyectada = (
            annual_billing(
                self.liquidaciones,
                projected_codes,
            )
        )

        # ----------------------------------------------------
        # 12. Resultado final
        # ----------------------------------------------------

        return SimulationOutput(
            tipo_caso="A",
            codigo_troquel=str(
                codigo_troquel
            ),
            recomendacion=bool(
                rule_result
                .recomendacion
            ),
            motivo=(
                rule_result.motivo
            ),
            facturacion_actual_anual=(
                facturacion_actual
            ),
            facturacion_proyectada_anual=(
                facturacion_proyectada
            ),
            detalle_consumo=(
                detalle_consumo
            ),
        )
