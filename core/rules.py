# ============================================================
# BLOQUE 01 — Imports
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
import pandas as pd


# ============================================================
# BLOQUE 02 — Resultado principal de simulación
# ============================================================

@dataclass
class SimulationOutput:

    tipo_caso: str

    codigo_troquel: str

    recomendacion: bool

    motivo: str

    facturacion_actual_anual: float

    facturacion_proyectada_anual: float

    detalle_consumo: dict


# ============================================================
# BLOQUE 03 — Resultado interno de reglas
# ============================================================

@dataclass
class RuleResult:

    aplica: bool

    estado: str

    elegible: bool

    ya_en_convenio: bool

    recomendacion: bool

    motivo: str

    banda_actual: float

    banda_hipotetica: float

    laboratorios_actuales: int

    laboratorios_hipoteticos: int

    mejora_banda: bool

    pvp_candidato: float

    segundo_pvp_mas_alto: float | None

    cumple_pvp: bool


# ============================================================
# BLOQUE 04 — Funciones auxiliares
# ============================================================

def normalize_code(value) -> str:
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
# BLOQUE 05 — Elegibilidad del candidato
# ============================================================

def is_eligible(
    troquel: dict,
    months_window: int = 6,
) -> tuple[bool, str]:
    """
    Precondición de elegibilidad Caso A.

    ALB se utiliza para verificar:

    1. presentación activa;
    2. vigencia del precio dentro de la ventana configurable.

    Default:
        6 meses.
    """

    if not troquel:

        return (
            False,
            "Presentación no elegible: troquel inexistente."
        )

    # --------------------------------------------------------
    # 1. Estado activo
    # --------------------------------------------------------

    baja = troquel.get(
        "baja"
    )

    try:

        baja_num = int(
            float(
                baja
            )
        )

    except Exception:

        baja_num = None

    if baja_num != 0:

        return (
            False,
            (
                "Presentación no elegible: "
                "la presentación se encuentra dada de baja."
            )
        )

    # --------------------------------------------------------
    # 2. Fecha de vigencia del precio
    # --------------------------------------------------------

    fecha_precio = pd.to_datetime(
        troquel.get(
            "fecha"
        ),
        errors="coerce",
    )

    if pd.isna(
        fecha_precio
    ):

        return (
            False,
            (
                "Presentación no elegible: "
                "no posee una fecha de vigencia de precio válida."
            )
        )

    fecha_limite = (
        date.today()
        - relativedelta(
            months=months_window
        )
    )

    if (
        fecha_precio.date()
        < fecha_limite
    ):

        return (
            False,
            (
                "Presentación no elegible: "
                f"el precio tiene una vigencia mayor "
                f"a {months_window} meses."
            )
        )

    return (
        True,
        "Presentación elegible."
    )


# ============================================================
# BLOQUE 06 — Motor de reglas Caso A
# ============================================================

def evaluate_case_a(
    troquel: dict,
    ya_en_convenio: bool,
    banda_actual: dict,
    banda_hipotetica: dict,
    segundo_pvp: float | None,
    months_window: int = 6,
) -> RuleResult:
    """
    Caso A — Alta de troquel.

    Regla:

    PRECONDICIÓN
        presentación activa
        + precio vigente dentro de la ventana.

    SI YA ESTÁ CONVENIADO
        no aplica análisis de incorporación.

    SI NO ESTÁ CONVENIADO

        Condición 1:
            banda hipotética > banda actual.

        Condición 2:
            PVP candidato <= segundo PVP más alto
            del universo comparable definido en services.py.

    Ambas deben cumplirse para recomendar.
    """

    # --------------------------------------------------------
    # 1. Elegibilidad
    # --------------------------------------------------------

    elegible, motivo_elegibilidad = (
        is_eligible(
            troquel,
            months_window,
        )
    )

    porcentaje_actual = float(
        banda_actual.get(
            "porcentaje_descuento",
            0,
        )
        or 0
    )

    porcentaje_hipotetico = float(
        banda_hipotetica.get(
            "porcentaje_descuento",
            0,
        )
        or 0
    )

    labs_actuales = int(
        banda_actual.get(
            "cantidad_laboratorios",
            0,
        )
        or 0
    )

    labs_hipoteticos = int(
        banda_hipotetica.get(
            "cantidad_laboratorios",
            0,
        )
        or 0
    )

    try:

        pvp_candidato = float(
            troquel.get(
                "precio",
                0,
            )
            or 0
        )

    except Exception:

        pvp_candidato = 0.0

    # --------------------------------------------------------
    # No elegible
    # --------------------------------------------------------

    if not elegible:

        return RuleResult(

            aplica=False,

            estado="NO_ELEGIBLE",

            elegible=False,

            ya_en_convenio=bool(
                ya_en_convenio
            ),

            recomendacion=False,

            motivo=
                motivo_elegibilidad,

            banda_actual=
                porcentaje_actual,

            banda_hipotetica=
                porcentaje_hipotetico,

            laboratorios_actuales=
                labs_actuales,

            laboratorios_hipoteticos=
                labs_hipoteticos,

            mejora_banda=False,

            pvp_candidato=
                pvp_candidato,

            segundo_pvp_mas_alto=
                segundo_pvp,

            cumple_pvp=False,
        )

    # --------------------------------------------------------
    # 2. Ya está conveniado
    # --------------------------------------------------------

    if ya_en_convenio:

        return RuleResult(

            aplica=False,

            estado="YA_CONVENIDO",

            elegible=True,

            ya_en_convenio=True,

            recomendacion=False,

            motivo=(
                "El troquel ya se encuentra en Convenio OYTE. "
                "No aplica análisis de incorporación."
            ),

            banda_actual=
                porcentaje_actual,

            banda_hipotetica=
                porcentaje_hipotetico,

            laboratorios_actuales=
                labs_actuales,

            laboratorios_hipoteticos=
                labs_hipoteticos,

            mejora_banda=False,

            pvp_candidato=
                pvp_candidato,

            segundo_pvp_mas_alto=
                segundo_pvp,

            cumple_pvp=False,
        )

    # --------------------------------------------------------
    # 3. Condición 1 — Mejora de banda
    # --------------------------------------------------------

    mejora_banda = (
        porcentaje_hipotetico
        >
        porcentaje_actual
    )

    # --------------------------------------------------------
    # 4. Condición 2 — Segundo PVP
    # --------------------------------------------------------

    cumple_pvp = (
        segundo_pvp is not None
        and pvp_candidato
        <= float(
            segundo_pvp
        )
    )

    # --------------------------------------------------------
    # 5. Recomendación
    # --------------------------------------------------------

    recomendacion = (
        mejora_banda
        and cumple_pvp
    )

    # --------------------------------------------------------
    # 6. Motivo
    # --------------------------------------------------------

    if recomendacion:

        motivo = (
            "Recomendar incorporación. "
            f"La banda mejora de "
            f"{porcentaje_actual:.0%} a "
            f"{porcentaje_hipotetico:.0%} "
            f"y el PVP candidato "
            f"(${pvp_candidato:,.2f}) "
            f"es menor o igual al segundo PVP "
            f"más alto del grupo comparable "
            f"(${float(segundo_pvp):,.2f})."
        )

    else:

        motivos_falla = []

        if not mejora_banda:

            motivos_falla.append(
                (
                    "la incorporación no mejora la banda "
                    f"({porcentaje_actual:.0%} → "
                    f"{porcentaje_hipotetico:.0%})"
                )
            )

        if segundo_pvp is None:

            motivos_falla.append(
                (
                    "no existe un universo suficiente "
                    "para determinar el segundo PVP más alto"
                )
            )

        elif not cumple_pvp:

            motivos_falla.append(
                (
                    f"el PVP candidato "
                    f"(${pvp_candidato:,.2f}) "
                    f"supera el segundo PVP más alto "
                    f"(${float(segundo_pvp):,.2f})"
                )
            )

        motivo = (
            "No recomendar incorporación: "
            + " y ".join(
                motivos_falla
            )
            + "."
        )

    return RuleResult(

        aplica=True,

        estado=(
            "RECOMENDADO"
            if recomendacion
            else "NO_RECOMENDADO"
        ),

        elegible=True,

        ya_en_convenio=False,

        recomendacion=bool(
            recomendacion
        ),

        motivo=
            motivo,

        banda_actual=
            porcentaje_actual,

        banda_hipotetica=
            porcentaje_hipotetico,

        laboratorios_actuales=
            labs_actuales,

        laboratorios_hipoteticos=
            labs_hipoteticos,

        mejora_banda=bool(
            mejora_banda
        ),

        pvp_candidato=
            pvp_candidato,

        segundo_pvp_mas_alto=(
            float(
                segundo_pvp
            )
            if segundo_pvp is not None
            else None
        ),

        cumple_pvp=bool(
            cumple_pvp
        ),
    )


# ============================================================
# BLOQUE 07 — Consumo histórico de la monodroga
# ============================================================

def consumption_block(
    liq_df: pd.DataFrame,
    troqueles_df: pd.DataFrame,
    cod_monodroga,
    potencia=None,
) -> dict:
    """
    Información histórica de consumo.

    UNIVERSO PRINCIPAL:
        toda la cod_monodroga.

    Se utiliza potencia únicamente para mostrar
    indicadores adicionales:

        afiliados de la misma potencia
        tasa de uso de la potencia

    No afecta banda ni facturación.
    """

    resultado_vacio = {

        "afiliados_monodroga":
            0,

        "costo_anual_monodroga":
            0.0,

        "afiliados_misma_potencia":
            0,

        "costo_anual_misma_potencia":
            0.0,

        "promedio_mensual_cajas_por_afiliado":
            0.0,

        "tasa_uso_potencia":
            0.0,

        "consumo_promedio_mensual_producto":
            [],
    }

    if (
        liq_df.empty
        or troqueles_df.empty
    ):

        return resultado_vacio

    if (
        "tronquel"
        not in troqueles_df.columns
        or "cod_monodroga"
        not in troqueles_df.columns
        or "troquel"
        not in liq_df.columns
    ):

        return resultado_vacio

    # --------------------------------------------------------
    # 1. Troqueles de la monodroga
    # --------------------------------------------------------

    cod_mono_num = pd.to_numeric(
        pd.Series(
            [cod_monodroga]
        ),
        errors="coerce",
    ).iloc[0]

    if pd.isna(
        cod_mono_num
    ):

        return resultado_vacio

    alb = troqueles_df.copy()

    alb[
        "_cod_monodroga_num"
    ] = pd.to_numeric(
        alb[
            "cod_monodroga"
        ],
        errors="coerce",
    )

    alb[
        "_troquel_normalizado"
    ] = (
        alb[
            "tronquel"
        ]
        .apply(
            normalize_code
        )
    )

    grupo = alb[
        alb[
            "_cod_monodroga_num"
        ]
        == cod_mono_num
    ].copy()

    if grupo.empty:

        return resultado_vacio

    codigos_monodroga = set(
        grupo[
            "_troquel_normalizado"
        ]
        .dropna()
        .tolist()
    )

    # --------------------------------------------------------
    # 2. Liquidaciones de la monodroga
    # --------------------------------------------------------

    liq = (
        liq_df.copy()
    )

    liq[
        "_troquel_normalizado"
    ] = (
        liq[
            "troquel"
        ]
        .apply(
            normalize_code
        )
    )

    liq = liq[
        liq[
            "_troquel_normalizado"
        ]
        .isin(
            codigos_monodroga
        )
    ].copy()

    if liq.empty:

        return resultado_vacio

    # --------------------------------------------------------
    # 3. Normalización
    # --------------------------------------------------------

    if "unidades" in liq.columns:

        liq[
            "unidades"
        ] = pd.to_numeric(
            liq[
                "unidades"
            ],
            errors="coerce",
        ).fillna(0)

    else:

        liq[
            "unidades"
        ] = 0.0

    if (
        "pconv_fecha_remito"
        in liq.columns
    ):

        liq[
            "pconv_fecha_remito"
        ] = pd.to_numeric(
            liq[
                "pconv_fecha_remito"
            ],
            errors="coerce",
        ).fillna(0)

    else:

        liq[
            "pconv_fecha_remito"
        ] = 0.0

    liq[
        "importe"
    ] = (
        liq[
            "unidades"
        ]
        *
        liq[
            "pconv_fecha_remito"
        ]
    )

    # --------------------------------------------------------
    # 4. Meses observados
    # --------------------------------------------------------

    if "periodo" in liq.columns:

        meses = max(
            liq[
                "periodo"
            ]
            .dropna()
            .nunique(),
            1,
        )

    else:

        meses = 1

    # --------------------------------------------------------
    # 5. Afiliados
    # --------------------------------------------------------

    afiliado_col = None

    for possible_col in [
        "afiliado_id",
        "nro_afiliado",
        "afiliado",
    ]:

        if possible_col in liq.columns:

            afiliado_col = (
                possible_col
            )

            break

    if afiliado_col:

        afiliados_monodroga = (
            liq[
                afiliado_col
            ]
            .dropna()
            .nunique()
        )

    else:

        afiliados_monodroga = 0

    # --------------------------------------------------------
    # 6. Incorporar potencia desde ALB
    # --------------------------------------------------------

    mismo_potencia = (
        pd.DataFrame()
    )

    afiliados_potencia = 0

    if (
        potencia is not None
        and "potencia"
        in grupo.columns
    ):

        mapa_potencia = (
            grupo[
                [
                    "_troquel_normalizado",
                    "potencia",
                ]
            ]
            .drop_duplicates(
                "_troquel_normalizado"
            )
        )

        liq = liq.merge(
            mapa_potencia,
            on="_troquel_normalizado",
            how="left",
        )

        mismo_potencia = liq[
            liq[
                "potencia"
            ]
            .fillna("")
            .astype(str)
            ==
            str(
                potencia
            )
        ].copy()

        if (
            afiliado_col
            and not mismo_potencia.empty
        ):

            afiliados_potencia = (
                mismo_potencia[
                    afiliado_col
                ]
                .dropna()
                .nunique()
            )

    # --------------------------------------------------------
    # 7. Promedio mensual de cajas por afiliado
    # --------------------------------------------------------

    if afiliados_monodroga > 0:

        promedio_cajas = (
            float(
                liq[
                    "unidades"
                ].sum()
            )
            / meses
            / afiliados_monodroga
        )

    else:

        promedio_cajas = 0.0

    # --------------------------------------------------------
    # 8. Tasa de uso de potencia
    # --------------------------------------------------------

    tasa_uso = (
        float(
            afiliados_potencia
            / afiliados_monodroga
        )
        if afiliados_monodroga
        else 0.0
    )

    # --------------------------------------------------------
    # 9. Consumo promedio por producto
    # --------------------------------------------------------

    consumo_producto = []

    if not liq.empty:

        consumo_producto = (
            liq.groupby(
                "_troquel_normalizado"
            )
            .agg(
                cajas_promedio_mensual=(
                    "unidades",
                    lambda s:
                        float(
                            s.sum()
                        )
                        / meses
                ),
                pxq_promedio_mensual=(
                    "importe",
                    lambda s:
                        float(
                            s.sum()
                        )
                        / meses
                ),
            )
            .reset_index()
            .rename(
                columns={
                    "_troquel_normalizado":
                        "troquel"
                }
            )
            .to_dict(
                "records"
            )
        )

    # --------------------------------------------------------
    # 10. Costos anualizados
    # --------------------------------------------------------

    costo_anual_monodroga = (
        float(
            liq[
                "importe"
            ].sum()
        )
        / meses
        * 12
    )

    if (
        not mismo_potencia.empty
    ):

        costo_anual_potencia = (
            float(
                mismo_potencia[
                    "importe"
                ].sum()
            )
            / meses
            * 12
        )

    else:

        costo_anual_potencia = 0.0

    return {

        "afiliados_monodroga":
            int(
                afiliados_monodroga
            ),

        "costo_anual_monodroga":
            float(
                costo_anual_monodroga
            ),

        "afiliados_misma_potencia":
            int(
                afiliados_potencia
            ),

        "costo_anual_misma_potencia":
            float(
                costo_anual_potencia
            ),

        "promedio_mensual_cajas_por_afiliado":
            float(
                promedio_cajas
            ),

        "tasa_uso_potencia":
            float(
                tasa_uso
            ),

        "consumo_promedio_mensual_producto":
            consumo_producto,
    }


# ============================================================
# BLOQUE 08 — Facturación anual genérica
# ============================================================

def annual_billing(
    liq_df: pd.DataFrame,
    convenio_codes: list[str],
) -> float:
    """
    Función genérica que calcula facturación anual
    para una lista determinada de troqueles.

    Fórmula:

        Unidades × PConv Fecha Remito

    Actualmente se mantiene por compatibilidad con
    otros componentes del servicio.
    """

    if liq_df.empty:
        return 0.0

    required = {
        "troquel",
        "unidades",
        "pconv_fecha_remito",
    }

    if not required.issubset(
        liq_df.columns
    ):

        return 0.0

    codigos = set(
        normalize_code(
            c
        )
        for c in convenio_codes
        if normalize_code(
            c
        ) != ""
    )

    df = (
        liq_df.copy()
    )

    df[
        "_troquel_normalizado"
    ] = (
        df[
            "troquel"
        ]
        .apply(
            normalize_code
        )
    )

    df = df[
        df[
            "_troquel_normalizado"
        ]
        .isin(
            codigos
        )
    ].copy()

    if df.empty:

        return 0.0

    df[
        "unidades"
    ] = pd.to_numeric(
        df[
            "unidades"
        ],
        errors="coerce",
    ).fillna(0)

    df[
        "pconv_fecha_remito"
    ] = pd.to_numeric(
        df[
            "pconv_fecha_remito"
        ],
        errors="coerce",
    ).fillna(0)

    df[
        "importe_actual"
    ] = (
        df[
            "unidades"
        ]
        *
        df[
            "pconv_fecha_remito"
        ]
    )

    if "periodo" in df.columns:

        meses = max(
            df[
                "periodo"
            ]
            .dropna()
            .nunique(),
            1,
        )

    else:

        meses = 1

    return (
        float(
            df[
                "importe_actual"
            ].sum()
        )
        / meses
        * 12
    )


# ============================================================
# BLOQUE 09 — Simulación económica de la monodroga
# ============================================================

def projected_billing_by_band(
    liq_df: pd.DataFrame,
    troqueles_df: pd.DataFrame,
    convenio_codes: list[str],
    troquel_candidato: dict,
    banda_actual: float,
    banda_proyectada: float,
) -> dict:
    """
    Calcula la facturación actual y proyectada
    EXCLUSIVAMENTE de la monodroga del candidato.

    UNIVERSO ECONÓMICO:

        misma cod_monodroga
        +
        solamente troqueles conveniados

    NO intervienen:

        formas
        potencia
        unidad_potencia

    ESCENARIO ACTUAL:

        Unidades × PConv Fecha Remito

    ESCENARIO PROYECTADO:

        Unidades
        × PVP Fecha Remito
        × (1 - banda proyectada)

    El consumo histórico permanece constante.
    """

    resultado_vacio = {

        "facturacion_actual_monodroga_anual":
            0.0,

        "facturacion_proyectada_monodroga_anual":
            0.0,

        "impacto_anual":
            0.0,

        "ahorro_anual":
            0.0,

        "ahorro_porcentual":
            0.0,

        "cantidad_liquidaciones":
            0,

        "unidades_historicas":
            0.0,

        "meses_observados":
            0,

        "banda_actual":
            float(
                banda_actual or 0
            ),

        "banda_proyectada":
            float(
                banda_proyectada or 0
            ),

        "troqueles_afectados":
            [],
    }

    # --------------------------------------------------------
    # 1. Validaciones
    # --------------------------------------------------------

    if (
        liq_df.empty
        or troqueles_df.empty
        or not troquel_candidato
    ):

        return resultado_vacio

    required_alb = {
        "tronquel",
        "cod_monodroga",
    }

    required_liq = {
        "troquel",
        "unidades",
        "pvp_fecha_remito",
        "pconv_fecha_remito",
    }

    if not required_alb.issubset(
        troqueles_df.columns
    ):

        return resultado_vacio

    if not required_liq.issubset(
        liq_df.columns
    ):

        return resultado_vacio

    # --------------------------------------------------------
    # 2. cod_monodroga del candidato
    # --------------------------------------------------------

    cod_monodroga = pd.to_numeric(
        pd.Series(
            [
                troquel_candidato.get(
                    "cod_monodroga"
                )
            ]
        ),
        errors="coerce",
    ).iloc[0]

    if pd.isna(
        cod_monodroga
    ):

        return resultado_vacio

    # --------------------------------------------------------
    # 3. Normalizar convenio
    # --------------------------------------------------------

    convenio_normalizado = set(
        normalize_code(
            codigo
        )
        for codigo in convenio_codes
        if normalize_code(
            codigo
        ) != ""
    )

    # --------------------------------------------------------
    # 4. Troqueles conveniados de la monodroga
    # --------------------------------------------------------

    alb = (
        troqueles_df.copy()
    )

    alb[
        "_cod_monodroga_num"
    ] = pd.to_numeric(
        alb[
            "cod_monodroga"
        ],
        errors="coerce",
    )

    alb[
        "_troquel_normalizado"
    ] = (
        alb[
            "tronquel"
        ]
        .apply(
            normalize_code
        )
    )

    grupo = alb[
        (
            alb[
                "_cod_monodroga_num"
            ]
            == cod_monodroga
        )
        &
        (
            alb[
                "_troquel_normalizado"
            ]
            .isin(
                convenio_normalizado
            )
        )
    ].copy()

    if grupo.empty:

        return resultado_vacio

    codigos_grupo = (
        grupo[
            "_troquel_normalizado"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    # --------------------------------------------------------
    # 5. Liquidaciones de esos troqueles
    # --------------------------------------------------------

    liquidaciones = (
        liq_df.copy()
    )

    liquidaciones[
        "_troquel_normalizado"
    ] = (
        liquidaciones[
            "troquel"
        ]
        .apply(
            normalize_code
        )
    )

    liquidaciones = (
        liquidaciones[
            liquidaciones[
                "_troquel_normalizado"
            ]
            .isin(
                codigos_grupo
            )
        ]
        .copy()
    )

    if liquidaciones.empty:

        return resultado_vacio

    # --------------------------------------------------------
    # 6. Normalización económica
    # --------------------------------------------------------

    liquidaciones[
        "unidades"
    ] = pd.to_numeric(
        liquidaciones[
            "unidades"
        ],
        errors="coerce",
    ).fillna(0)

    liquidaciones[
        "pvp_fecha_remito"
    ] = pd.to_numeric(
        liquidaciones[
            "pvp_fecha_remito"
        ],
        errors="coerce",
    ).fillna(0)

    liquidaciones[
        "pconv_fecha_remito"
    ] = pd.to_numeric(
        liquidaciones[
            "pconv_fecha_remito"
        ],
        errors="coerce",
    ).fillna(0)

    # --------------------------------------------------------
    # 7. Escenario actual
    # --------------------------------------------------------

    liquidaciones[
        "importe_actual"
    ] = (
        liquidaciones[
            "unidades"
        ]
        *
        liquidaciones[
            "pconv_fecha_remito"
        ]
    )

    # --------------------------------------------------------
    # 8. Escenario proyectado
    # --------------------------------------------------------

    liquidaciones[
        "precio_proyectado"
    ] = (
        liquidaciones[
            "pvp_fecha_remito"
        ]
        *
        (
            1
            - float(
                banda_proyectada
                or 0
            )
        )
    )

    liquidaciones[
        "importe_proyectado"
    ] = (
        liquidaciones[
            "unidades"
        ]
        *
        liquidaciones[
            "precio_proyectado"
        ]
    )

    # --------------------------------------------------------
    # 9. Meses observados
    # --------------------------------------------------------

    if (
        "periodo"
        in liquidaciones.columns
    ):

        meses = max(
            liquidaciones[
                "periodo"
            ]
            .dropna()
            .nunique(),
            1,
        )

    else:

        meses = 1

    # --------------------------------------------------------
    # 10. Anualización
    # --------------------------------------------------------

    actual_anual = (
        float(
            liquidaciones[
                "importe_actual"
            ].sum()
        )
        / meses
        * 12
    )

    proyectado_anual = (
        float(
            liquidaciones[
                "importe_proyectado"
            ].sum()
        )
        / meses
        * 12
    )

    # --------------------------------------------------------
    # 11. Impacto
    # --------------------------------------------------------

    impacto = (
        proyectado_anual
        - actual_anual
    )

    ahorro = (
        actual_anual
        - proyectado_anual
    )

    if actual_anual > 0:

        ahorro_porcentual = (
            ahorro
            / actual_anual
        )

    else:

        ahorro_porcentual = 0.0

    # --------------------------------------------------------
    # 12. Resultado
    # --------------------------------------------------------

    return {

        "facturacion_actual_monodroga_anual":
            float(
                actual_anual
            ),

        "facturacion_proyectada_monodroga_anual":
            float(
                proyectado_anual
            ),

        "impacto_anual":
            float(
                impacto
            ),

        "ahorro_anual":
            float(
                ahorro
            ),

        "ahorro_porcentual":
            float(
                ahorro_porcentual
            ),

        "cantidad_liquidaciones":
            int(
                len(
                    liquidaciones
                )
            ),

        "unidades_historicas":
            float(
                liquidaciones[
                    "unidades"
                ].sum()
            ),

        "meses_observados":
            int(
                meses
            ),

        "banda_actual":
            float(
                banda_actual
                or 0
            ),

        "banda_proyectada":
            float(
                banda_proyectada
                or 0
            ),

        "troqueles_afectados":
            codigos_grupo,
    }
