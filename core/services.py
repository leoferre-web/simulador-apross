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
    projected_billing_by_band,
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
            [
                "tronquel",
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
            subset=["tronquel"],
            keep="first",
        )

        df = df.drop(
            columns=[
                "_fecha_orden",
                "_id_orden",
            ],
            errors="ignore",
        )

        return df.reset_index(
            drop=True
        )


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
            self.troqueles[
                "tronquel"
            ].astype(str)
            == str(codigo_troquel)
        ]

        if row.empty:
            return None

        return row.iloc[0].to_dict()


# ============================================================
# BLOQUE 05 — Troqueles en convenio
# ============================================================

    def active_convenio_codes(
        self,
    ) -> list[str]:
        """
        Si el troquel figura en src_convenio_oyte,
        se considera conveniado.

        El atributo Estado no interviene.
        """

        if (
            self.convenio.empty
            or "troquel" not in self.convenio.columns
        ):
            return []

        return (
            self.convenio[
                "troquel"
            ]
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

        return (
            str(codigo_troquel)
            in set(
                self.active_convenio_codes()
            )
        )


# ============================================================
# BLOQUE 07 — Universo para cálculo de banda
# ============================================================

    def equivalent_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        UNIVERSO PARA LA BANDA.

        Para calcular la banda actual NO utilizamos
        forma + potencia + unidad.

        Se utiliza únicamente:

            cod_monodroga

        Por lo tanto, todos los laboratorios conveniados
        pertenecientes a esa monodroga participan del
        cálculo de banda.
        """

        if (
            not troquel
            or self.troqueles.empty
            or "cod_monodroga"
            not in self.troqueles.columns
        ):

            return pd.DataFrame()

        cod_monodroga = (
            troquel.get(
                "cod_monodroga"
            )
        )

        return self.troqueles[
            self.troqueles[
                "cod_monodroga"
            ].astype(str)
            == str(
                cod_monodroga
            )
        ].copy()


# ============================================================
# BLOQUE 08 — Monodroga actualmente conveniada
# ============================================================

    def current_convenio_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        Toma todos los troqueles de la misma monodroga
        y conserva solamente los que figuran en
        Convenio OYTE.

        Este universo se utiliza para la banda.
        """

        grupo = self.equivalent_group(
            troquel
        )

        if grupo.empty:
            return grupo

        convenio_codes = set(
            self.active_convenio_codes()
        )

        return grupo[
            grupo[
                "tronquel"
            ]
            .astype(str)
            .isin(
                convenio_codes
            )
        ].copy()


# ============================================================
# BLOQUE 09 — Cantidad de laboratorios
# ============================================================

    def count_laboratories(
        self,
        grupo: pd.DataFrame,
    ) -> int:
        """
        Cuenta laboratorios diferentes.

        El atributo utilizado es:
            desc_laboratorio
        """

        if (
            grupo.empty
            or "desc_laboratorio"
            not in grupo.columns
        ):

            return 0

        labs = (
            grupo[
                "desc_laboratorio"
            ]
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
        """
        Consulta la banda correspondiente en
        src_bandas_descuento.
        """

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

        df[
            "cantidad_laboratorios"
        ] = pd.to_numeric(
            df[
                "cantidad_laboratorios"
            ],
            errors="coerce",
        )

        fila = df[
            df[
                "cantidad_laboratorios"
            ]
            == cantidad_laboratorios
        ]

        # Si la cantidad supera el máximo de la tabla,
        # se utiliza la última banda definida.
        if fila.empty:

            max_labs = df[
                "cantidad_laboratorios"
            ].max()

            fila = df[
                df[
                    "cantidad_laboratorios"
                ]
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
        """
        Banda actual:

        1. misma cod_monodroga;
        2. solamente troqueles conveniados;
        3. contar desc_laboratorio distintos;
        4. consultar src_bandas_descuento.
        """

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
# BLOQUE 12 — Banda hipotética con incorporación
# ============================================================

    def hypothetical_band(
        self,
        troquel: dict,
    ) -> dict:
        """
        Simula la incorporación del laboratorio candidato.

        El universo es toda la monodroga.

        Solo suma +1 laboratorio si el laboratorio
        candidato todavía no se encuentra representado
        entre los conveniados de esa monodroga.
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

            hipotetico = (
                actual + 1
            )

        else:

            hipotetico = actual

        return self.get_band(
            hipotetico
        )


# ============================================================
# BLOQUE 13 — Universo para comparación de PVP
# ============================================================

    def monodroga_universe(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        UNIVERSO PARA EL SEGUNDO PVP.

        A diferencia de la banda, acá sí utilizamos
        la presentación equivalente completa:

            cod_monodroga
            + formas
            + potencia
            + unidad_potencia

        Luego se conservan solamente los troqueles
        que figuran en Convenio OYTE.

        El PVP se obtiene del ALB vigente.
        """

        if not troquel or self.troqueles.empty:

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

        cod_monodroga = (
            troquel.get(
                "cod_monodroga"
            )
        )

        forma = str(
            troquel.get(
                "formas",
                "",
            )
            or ""
        )

        potencia = str(
            troquel.get(
                "potencia",
                "",
            )
            or ""
        )

        unidad_potencia = str(
            troquel.get(
                "unidad_potencia",
                "",
            )
            or ""
        )

        convenio_codes = set(
            self.active_convenio_codes()
        )

        universo = self.troqueles[
            (
                self.troqueles[
                    "cod_monodroga"
                ].astype(str)
                == str(
                    cod_monodroga
                )
            )
            &
            (
                self.troqueles[
                    "formas"
                ]
                .fillna("")
                .astype(str)
                == forma
            )
            &
            (
                self.troqueles[
                    "potencia"
                ]
                .fillna("")
                .astype(str)
                == potencia
            )
            &
            (
                self.troqueles[
                    "unidad_potencia"
                ]
                .fillna("")
                .astype(str)
                == unidad_potencia
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
# BLOQUE 14 — Segundo PVP más alto
# ============================================================

    def second_highest_price(
        self,
        troquel: dict,
    ) -> float | None:
        """
        Calcula el segundo PVP más alto entre:

        - misma cod_monodroga;
        - misma forma;
        - misma potencia;
        - misma unidad_potencia;
        - solamente troqueles conveniados.

        Los precios provienen del ALB vigente.
        """

        universo = (
            self.monodroga_universe(
                troquel
            )
        )

        if (
            universo.empty
            or "precio"
            not in universo.columns
        ):

            return None

        valores = pd.to_numeric(
            universo[
                "precio"
            ],
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
# BLOQUE 15 — Simulación Caso A
# ============================================================

    def simulate_alta(
        self,
        codigo_troquel: str,
        months_window: int = 6,
    ) -> SimulationOutput:
        """
        Ejecuta el Caso A completo.
        """

        # ----------------------------------------------------
        # 1. Obtener candidato desde ALB
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
        # 2. Verificar si ya está en convenio
        # ----------------------------------------------------

        ya_convenido = (
            self.is_in_convenio(
                codigo_troquel
            )
        )


        # ----------------------------------------------------
        # 3. Banda actual
        #
        # SOLO cod_monodroga
        # ----------------------------------------------------

        banda_actual = (
            self.current_band(
                troquel
            )
        )


        # ----------------------------------------------------
        # 4. Banda hipotética
        #
        # SOLO cod_monodroga
        # + laboratorio candidato
        # ----------------------------------------------------

        banda_hipotetica = (
            self.hypothetical_band(
                troquel
            )
        )


        # ----------------------------------------------------
        # 5. Segundo PVP
        #
        # cod_monodroga
        # + formas
        # + potencia
        # + unidad_potencia
        # + solo conveniados
        # ----------------------------------------------------

        segundo_pvp = (
            self.second_highest_price(
                troquel
            )
        )


        # ----------------------------------------------------
        # 6. Regla de negocio
        # ----------------------------------------------------

        rule_result = (
            evaluate_case_a(
                troquel=troquel,

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
        )


        # ----------------------------------------------------
        # 7. No elegible / ya conveniado
        # ----------------------------------------------------

        if not rule_result.aplica:

            detalle = {

                "estado":
                    rule_result.estado,

                "elegible":
                    rule_result.elegible,

                "ya_en_convenio":
                    rule_result
                    .ya_en_convenio,

                "banda_actual":
                    rule_result
                    .banda_actual,

                "banda_hipotetica":
                    rule_result
                    .banda_hipotetica,

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

                motivo=
                    rule_result.motivo,

                facturacion_actual_anual=0,

                facturacion_proyectada_anual=0,

                detalle_consumo=
                    detalle,
            )


        # ----------------------------------------------------
        # 8. Consumo histórico
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
        # 9. Agregar detalle de reglas
        # ----------------------------------------------------

        detalle_consumo.update(
            {

                "estado":
                    rule_result.estado,

                "elegible":
                    rule_result.elegible,

                "ya_en_convenio":
                    rule_result
                    .ya_en_convenio,

                "banda_actual":
                    rule_result
                    .banda_actual,

                "banda_hipotetica":
                    rule_result
                    .banda_hipotetica,

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
        # 10. Facturación actual total
        # ----------------------------------------------------

        current_codes = (
            self.active_convenio_codes()
        )

        facturacion_actual_total = (
            annual_billing(
                self.liquidaciones,
                current_codes,
            )
        )


        # ----------------------------------------------------
        # 11. Simulación económica
        # ----------------------------------------------------

        simulacion_economica = (
            projected_billing_by_band(

                liq_df=
                    self.liquidaciones,

                troqueles_df=
                    self.troqueles,

                troquel_candidato=
                    troquel,

                banda_actual=
                    rule_result
                    .banda_actual,

                banda_proyectada=
                    rule_result
                    .banda_hipotetica,
            )
        )


        facturacion_actual_grupo = float(
            simulacion_economica.get(
                "facturacion_actual_grupo_anual",
                0,
            )
            or 0
        )


        facturacion_proyectada_grupo = float(
            simulacion_economica.get(
                "facturacion_proyectada_grupo_anual",
                0,
            )
            or 0
        )


        # ----------------------------------------------------
        # 11.1 Escenario proyectado total
        # ----------------------------------------------------

        if rule_result.recomendacion:

            facturacion_proyectada_total = (

                facturacion_actual_total

                - facturacion_actual_grupo

                + facturacion_proyectada_grupo
            )

        else:

            facturacion_proyectada_total = (
                facturacion_actual_total
            )


        # ----------------------------------------------------
        # 11.2 Detalle económico
        # ----------------------------------------------------

        detalle_consumo.update(
            {

                "facturacion_actual_grupo_anual":
                    simulacion_economica.get(
                        "facturacion_actual_grupo_anual",
                        0,
                    ),

                "facturacion_proyectada_grupo_anual":
                    simulacion_economica.get(
                        "facturacion_proyectada_grupo_anual",
                        0,
                    ),

                "impacto_grupo_anual":
                    simulacion_economica.get(
                        "impacto_grupo_anual",
                        0,
                    ),

                "ahorro_grupo_anual":
                    simulacion_economica.get(
                        "ahorro_grupo_anual",
                        0,
                    ),

                "ahorro_porcentual":
                    simulacion_economica.get(
                        "ahorro_porcentual",
                        0,
                    ),

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
            }
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
                rule_result.recomendacion
            ),

            motivo=
                rule_result.motivo,

            facturacion_actual_anual=(
                facturacion_actual_total
            ),

            facturacion_proyectada_anual=(
                facturacion_proyectada_total
            ),

            detalle_consumo=(
                detalle_consumo
            ),
        )
