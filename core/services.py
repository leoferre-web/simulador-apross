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
# BLOQUE 03 — Normalización de códigos
# ============================================================

    def _normalize_code(
        self,
        value,
    ) -> str:
        """
        Normaliza códigos como:

        12345
        12345.0
        "12345"
        "12345.0"

        a:

        "12345"
        """

        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

        try:
            return str(
                int(
                    float(value)
                )
            )

        except Exception:
            return str(
                value
            ).strip()


# ============================================================
# BLOQUE 04 — Vista vigente del ALB
# ============================================================

    def _build_current_alb(
        self,
    ) -> pd.DataFrame:
        """
        Para cada troquel:

        1. toma la fecha de precio más reciente;
        2. si hay empate, toma el ID más alto.
        """

        if self.troqueles_raw.empty:
            return self.troqueles_raw.copy()

        df = self.troqueles_raw.copy()

        if "tronquel" not in df.columns:
            return df

        df["_troquel_normalizado"] = (
            df["tronquel"]
            .apply(
                self._normalize_code
            )
        )

        if "fecha" in df.columns:

            df["_fecha_orden"] = (
                pd.to_datetime(
                    df["fecha"],
                    errors="coerce",
                )
            )

        else:

            df["_fecha_orden"] = pd.NaT

        if "id" in df.columns:

            df["_id_orden"] = (
                pd.to_numeric(
                    df["id"],
                    errors="coerce",
                )
                .fillna(0)
            )

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
            subset=[
                "_troquel_normalizado"
            ],
            keep="first",
        )

        df["tronquel"] = (
            df["_troquel_normalizado"]
        )

        df = df.drop(
            columns=[
                "_troquel_normalizado",
                "_fecha_orden",
                "_id_orden",
            ],
            errors="ignore",
        )

        return df.reset_index(
            drop=True
        )


# ============================================================
# BLOQUE 05 — Obtener troquel candidato
# ============================================================

    def get_troquel(
        self,
        codigo_troquel: str,
    ) -> dict | None:

        if (
            self.troqueles.empty
            or "tronquel"
            not in self.troqueles.columns
        ):

            return None

        codigo = (
            self._normalize_code(
                codigo_troquel
            )
        )

        row = self.troqueles[
            self.troqueles[
                "tronquel"
            ]
            .apply(
                self._normalize_code
            )
            == codigo
        ]

        if row.empty:
            return None

        return (
            row
            .iloc[0]
            .to_dict()
        )


# ============================================================
# BLOQUE 06 — Troqueles en convenio
# ============================================================

    def active_convenio_codes(
        self,
    ) -> list[str]:
        """
        Si figura en src_convenio_oyte,
        se considera conveniado.

        No se utiliza Estado.
        """

        if (
            self.convenio.empty
            or "troquel"
            not in self.convenio.columns
        ):

            return []

        codigos = (
            self.convenio[
                "troquel"
            ]
            .dropna()
            .apply(
                self._normalize_code
            )
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

        codigo = (
            self._normalize_code(
                codigo_troquel
            )
        )

        return (
            codigo
            in set(
                self.active_convenio_codes()
            )
        )


# ============================================================
# BLOQUE 08 — Universo para banda
# ============================================================

    def equivalent_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        UNIVERSO DE BANDA.

        Se utiliza únicamente:

            cod_monodroga

        No intervienen:
        - formas
        - potencia
        - unidad_potencia
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
                [
                    troquel.get(
                        "cod_monodroga"
                    )
                ]
            ),
            errors="coerce",
        ).iloc[0]

        if pd.isna(
            cod_monodroga
        ):

            return pd.DataFrame()

        df = self.troqueles.copy()

        df[
            "_cod_monodroga_num"
        ] = pd.to_numeric(
            df[
                "cod_monodroga"
            ],
            errors="coerce",
        )

        grupo = df[
            df[
                "_cod_monodroga_num"
            ]
            == cod_monodroga
        ].copy()

        return grupo.drop(
            columns=[
                "_cod_monodroga_num"
            ],
            errors="ignore",
        )


# ============================================================
# BLOQUE 09 — Monodroga actualmente conveniada
# ============================================================

    def current_convenio_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        Universo utilizado para banda:

        misma cod_monodroga
        + solamente troqueles conveniados.
        """

        grupo = (
            self.equivalent_group(
                troquel
            )
        )

        if grupo.empty:
            return grupo

        convenio_codes = set(
            self.active_convenio_codes()
        )

        grupo = grupo.copy()

        grupo[
            "_troquel_normalizado"
        ] = (
            grupo[
                "tronquel"
            ]
            .apply(
                self._normalize_code
            )
        )

        grupo = grupo[
            grupo[
                "_troquel_normalizado"
            ]
            .isin(
                convenio_codes
            )
        ].copy()

        return grupo.drop(
            columns=[
                "_troquel_normalizado"
            ],
            errors="ignore",
        )


# ============================================================
# BLOQUE 10 — Cantidad de laboratorios
# ============================================================

    def count_laboratories(
        self,
        grupo: pd.DataFrame,
    ) -> int:
        """
        Cuenta laboratorios distintos por desc_laboratorio.
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
# BLOQUE 11 — Obtener banda
# ============================================================

    def get_band(
        self,
        cantidad_laboratorios: int,
    ) -> dict:

        if cantidad_laboratorios <= 0:

            return {
                "cantidad_laboratorios":
                    0,

                "porcentaje_descuento":
                    0.0,

                "banda_texto":
                    "Sin banda",
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

        # Si supera el máximo configurado,
        # utiliza la última banda.
        if fila.empty:

            max_labs = (
                df[
                    "cantidad_laboratorios"
                ]
                .max()
            )

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
                int(
                    cantidad_laboratorios
                ),

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
        """
        Banda actual:

        misma cod_monodroga
        → solo conveniados
        → laboratorios únicos
        → banda.
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
# BLOQUE 13 — Banda hipotética
# ============================================================

    def hypothetical_band(
        self,
        troquel: dict,
    ) -> dict:
        """
        Agrega el laboratorio candidato solamente si
        todavía no está representado entre los conveniados
        de esa monodroga.
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

            cantidad_hipotetica = (
                actual + 1
            )

        else:

            cantidad_hipotetica = (
                actual
            )

        return self.get_band(
            cantidad_hipotetica
        )


# ============================================================
# BLOQUE 14 — Universo para segundo PVP
# ============================================================

    def monodroga_universe(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        UNIVERSO DEL SEGUNDO PVP.

        Se utiliza:

            cod_monodroga
            + formas
            + potencia
            + unidad_potencia

        Luego:
            solo troqueles conveniados.

        El precio se obtiene del ALB vigente.
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
                [
                    troquel.get(
                        "cod_monodroga"
                    )
                ]
            ),
            errors="coerce",
        ).iloc[0]

        if pd.isna(
            cod_monodroga
        ):

            return pd.DataFrame()

        forma = str(
            troquel.get(
                "formas",
                "",
            )
            or ""
        ).strip()

        potencia = str(
            troquel.get(
                "potencia",
                "",
            )
            or ""
        ).strip()

        unidad_potencia = str(
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

        df[
            "_cod_monodroga_num"
        ] = pd.to_numeric(
            df[
                "cod_monodroga"
            ],
            errors="coerce",
        )

        df[
            "_troquel_normalizado"
        ] = (
            df[
                "tronquel"
            ]
            .apply(
                self._normalize_code
            )
        )

        df[
            "_formas_normalizado"
        ] = (
            df[
                "formas"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df[
            "_potencia_normalizado"
        ] = (
            df[
                "potencia"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df[
            "_unidad_normalizado"
        ] = (
            df[
                "unidad_potencia"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        universo = df[
            (
                df[
                    "_cod_monodroga_num"
                ]
                == cod_monodroga
            )
            &
            (
                df[
                    "_formas_normalizado"
                ]
                == forma
            )
            &
            (
                df[
                    "_potencia_normalizado"
                ]
                == potencia
            )
            &
            (
                df[
                    "_unidad_normalizado"
                ]
                == unidad_potencia
            )
            &
            (
                df[
                    "_troquel_normalizado"
                ]
                .isin(
                    convenio_codes
                )
            )
        ].copy()

        return universo.drop(
            columns=[
                "_cod_monodroga_num",
                "_troquel_normalizado",
                "_formas_normalizado",
                "_potencia_normalizado",
                "_unidad_normalizado",
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
        # 1. Obtener candidato
        # ----------------------------------------------------

        troquel = (
            self.get_troquel(
                codigo_troquel
            )
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

                facturacion_actual_anual=
                    0,

                facturacion_proyectada_anual=
                    0,

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
        # 5. Segundo PVP
        # ----------------------------------------------------

        segundo_pvp = (
            self.second_highest_price(
                troquel
            )
        )

        # ----------------------------------------------------
        # 6. Evaluar reglas
        # ----------------------------------------------------

        rule_result = (
            evaluate_case_a(

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

                codigo_troquel=
                    codigo_troquel,

                recomendacion=False,

                motivo=
                    rule_result.motivo,

                facturacion_actual_anual=
                    0,

                facturacion_proyectada_anual=
                    0,

                detalle_consumo=
                    detalle,
            )

        # ----------------------------------------------------
        # 8. Información de consumo
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
        # 10. Universo conveniado
        # ----------------------------------------------------

        current_codes = (
            self.active_convenio_codes()
        )

        # ----------------------------------------------------
        # 11. Simulación económica de la monodroga
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
                    rule_result
                    .banda_actual,

                banda_proyectada=
                    rule_result
                    .banda_hipotetica,
            )
        )

        # ----------------------------------------------------
        # 11.1 Facturación actual anual
        #
        # SOLO monodroga analizada
        # ----------------------------------------------------

        facturacion_actual_monodroga = float(
            simulacion_economica.get(
                "facturacion_actual_monodroga_anual",
                0,
            )
            or 0
        )

        # ----------------------------------------------------
        # 11.2 Facturación proyectada anual
        #
        # SOLO monodroga analizada
        # ----------------------------------------------------

        facturacion_proyectada_calculada = float(
            simulacion_economica.get(
                "facturacion_proyectada_monodroga_anual",
                0,
            )
            or 0
        )

        # Solo aplicamos el escenario proyectado
        # si la incorporación fue recomendada.
        if rule_result.recomendacion:

            facturacion_proyectada_monodroga = (
                facturacion_proyectada_calculada
            )

        else:

            facturacion_proyectada_monodroga = (
                facturacion_actual_monodroga
            )

        # ----------------------------------------------------
        # 11.3 Impacto anual
        # ----------------------------------------------------

        impacto_anual = (
            facturacion_proyectada_monodroga
            - facturacion_actual_monodroga
        )

        ahorro_anual = (
            facturacion_actual_monodroga
            - facturacion_proyectada_monodroga
        )

        if (
            facturacion_actual_monodroga
            > 0
        ):

            ahorro_porcentual = (
                ahorro_anual
                / facturacion_actual_monodroga
            )

        else:

            ahorro_porcentual = 0.0

        # ----------------------------------------------------
        # 11.4 Detalle económico
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
        # 12. Resultado final
        # ----------------------------------------------------

        return SimulationOutput(

            tipo_caso="A",

            codigo_troquel=
                codigo_troquel,

            recomendacion=bool(
                rule_result
                .recomendacion
            ),

            motivo=
                rule_result.motivo,

            # IMPORTANTE:
            # estas dos cifras corresponden únicamente
            # a la monodroga analizada.
            facturacion_actual_anual=(
                facturacion_actual_monodroga
            ),

            facturacion_proyectada_anual=(
                facturacion_proyectada_monodroga
            ),

            detalle_consumo=(
                detalle_consumo
            ),
        )
