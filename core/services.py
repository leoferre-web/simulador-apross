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

        # Vista vigente del ALB:
        # una sola fila vigente por troquel.
        self.troqueles = self._build_current_alb()


# ============================================================
# BLOQUE 03 — Normalización de códigos
# ============================================================

    def _normalize_code(
        self,
        value,
    ) -> str:
        """
        Normaliza códigos para evitar diferencias como:

            12345
            12345.0
            "12345"
            "12345.0"

        Todos pasan a:

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
        Para cada tronquel:

        1. toma la fecha de precio más reciente;
        2. ante igualdad de fecha, toma el ID más alto.

        La tabla original no se modifica.
        """

        if self.troqueles_raw.empty:
            return self.troqueles_raw.copy()

        df = self.troqueles_raw.copy()

        if "tronquel" not in df.columns:
            return df

        # Normalizar código.
        df["_troquel_normalizado"] = (
            df["tronquel"]
            .apply(
                self._normalize_code
            )
        )

        # Fecha para ordenar.
        if "fecha" in df.columns:

            df["_fecha_orden"] = (
                pd.to_datetime(
                    df["fecha"],
                    errors="coerce",
                )
            )

        else:

            df["_fecha_orden"] = (
                pd.NaT
            )

        # ID para desempate.
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

        # Registro más nuevo primero.
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

        # Una sola fila por troquel.
        df = df.drop_duplicates(
            subset=[
                "_troquel_normalizado"
            ],
            keep="first",
        )

        # Guardamos el código normalizado en tronquel
        # para que todos los cruces posteriores sean consistentes.
        df["tronquel"] = (
            df[
                "_troquel_normalizado"
            ]
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
        """
        Busca el registro vigente del candidato en ALB.
        """

        if (
            self.troqueles.empty
            or "tronquel"
            not in self.troqueles.columns
        ):

            return None

        codigo_normalizado = (
            self._normalize_code(
                codigo_troquel
            )
        )

        row = self.troqueles[
            self.troqueles[
                "tronquel"
            ].apply(
                self._normalize_code
            )
            == codigo_normalizado
        ]

        if row.empty:
            return None

        return (
            row
            .iloc[0]
            .to_dict()
        )


# ============================================================
# BLOQUE 06 — Troqueles actualmente en convenio
# ============================================================

    def active_convenio_codes(
        self,
    ) -> list[str]:
        """
        Regla confirmada:

        Si un troquel figura en src_convenio_oyte,
        se considera conveniado.

        No se utiliza el campo Estado.
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

        codigos = (
            codigos[
                codigos != ""
            ]
        )

        return (
            codigos
            .unique()
            .tolist()
        )


# ============================================================
# BLOQUE 07 — Verificar si está en convenio
# ============================================================

    def is_in_convenio(
        self,
        codigo_troquel: str,
    ) -> bool:

        codigo_normalizado = (
            self._normalize_code(
                codigo_troquel
            )
        )

        return (
            codigo_normalizado
            in set(
                self.active_convenio_codes()
            )
        )


# ============================================================
# BLOQUE 08 — Universo para cálculo de banda
# ============================================================

    def equivalent_group(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        UNIVERSO PARA CALCULAR LA BANDA.

        Regla confirmada:

        Se utiliza únicamente:

            cod_monodroga

        NO se utilizan:
        - formas
        - potencia
        - unidad_potencia

        Por lo tanto, participan todos los troqueles
        correspondientes a la misma monodroga.
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
        Universo utilizado para calcular la banda actual:

        1. misma cod_monodroga;
        2. únicamente troqueles presentes en Convenio OYTE.

        Los códigos son normalizados antes de cruzarlos.
        """

        grupo = (
            self.equivalent_group(
                troquel
            )
        )

        if grupo.empty:

            return grupo

        if (
            "tronquel"
            not in grupo.columns
        ):

            return pd.DataFrame()

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
            ].isin(
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
        Cuenta laboratorios distintos.

        Campo utilizado:
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
# BLOQUE 11 — Obtener banda
# ============================================================

    def get_band(
        self,
        cantidad_laboratorios: int,
    ) -> dict:
        """
        Obtiene la banda correspondiente desde:

            src_bandas_descuento
        """

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

        df = (
            self.bandas.copy()
        )

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

        # Si supera el máximo disponible,
        # utilizamos la última banda definida.
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

        1. identificar cod_monodroga;
        2. buscar todos los troqueles de esa monodroga;
        3. quedarse solo con conveniados;
        4. contar laboratorios distintos;
        5. consultar banda.
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
# BLOQUE 13 — Banda hipotética con incorporación
# ============================================================

    def hypothetical_band(
        self,
        troquel: dict,
    ) -> dict:
        """
        Calcula la banda si el candidato ingresara.

        Si el laboratorio candidato ya está representado
        dentro de los conveniados de esa monodroga,
        la cantidad de laboratorios no cambia.

        Si no está representado:
            cantidad actual + 1
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
# BLOQUE 14 — Universo para cálculo del segundo PVP
# ============================================================

    def monodroga_universe(
        self,
        troquel: dict,
    ) -> pd.DataFrame:
        """
        UNIVERSO PARA SEGUNDO PVP.

        Se utiliza:

            cod_monodroga
            + formas
            + potencia
            + unidad_potencia

        Luego se conservan únicamente los troqueles
        que figuran en Convenio OYTE.

        Los precios se obtienen del ALB vigente.
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

        # ----------------------------------------------------
        # Datos del candidato
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Preparar ALB
        # ----------------------------------------------------

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

        convenio_codes = set(
            self.active_convenio_codes()
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
        """
        Busca los PVP de:

        misma cod_monodroga
        + misma forma
        + misma potencia
        + misma unidad_potencia
        + únicamente conveniados.

        Ordena PVP únicos de mayor a menor
        y toma el segundo.
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
# BLOQUE 16 — Simulación Caso A
# ============================================================

    def simulate_alta(
        self,
        codigo_troquel: str,
        months_window: int = 6,
    ) -> SimulationOutput:
        """
        Ejecuta Caso A — Alta de troquel.
        """

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
        # 2. Verificar convenio
        # ----------------------------------------------------

        ya_convenido = (
            self.is_in_convenio(
                codigo_troquel
            )
        )

        # ----------------------------------------------------
        # 3. Banda actual
        #
        # Universo:
        # SOLO cod_monodroga
        # + conveniados
        # ----------------------------------------------------

        banda_actual = (
            self.current_band(
                troquel
            )
        )

        # ----------------------------------------------------
        # 4. Banda hipotética
        #
        # Misma monodroga
        # + candidato
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
        # + conveniados
        # ----------------------------------------------------

        segundo_pvp = (
            self.second_highest_price(
                troquel
            )
        )

        # ----------------------------------------------------
        # 6. Motor de reglas
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
        # 9. Agregar resultado de reglas
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
        # 11.1 Facturación proyectada total
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

            codigo_troquel=
                codigo_troquel,

            recomendacion=bool(
                rule_result
                .recomendacion
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
