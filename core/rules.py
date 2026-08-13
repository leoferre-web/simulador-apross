# ============================================================
# BLOQUE 01 — Imports
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta


# ============================================================
# BLOQUE 02 — Modelos de salida
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


@dataclass
class AltaRuleResult:
    """
    Resultado interno de la regla de negocio
    Caso A — Alta de troquel.
    """

    aplica: bool
    estado: str

    recomendacion: bool
    motivo: str

    elegible: bool
    ya_en_convenio: bool

    banda_actual: float
    banda_hipotetica: float

    laboratorios_actuales: int
    laboratorios_hipoteticos: int

    mejora_banda: bool

    pvp_candidato: float
    segundo_pvp_mas_alto: float | None
    cumple_pvp: bool


# ============================================================
# BLOQUE 03 — Elegibilidad del troquel
# ============================================================

def is_eligible(
    troquel: dict | None,
    months_window: int = 6,
) -> tuple[bool, str]:
    """
    Precondición de elegibilidad del Caso A.

    El troquel es elegible únicamente si:

    1. Existe en ALB.
    2. baja = 0.
    3. La fecha de vigencia del precio
       no supera la ventana definida.

    Default: 6 meses.
    """

    if not troquel:
        return (
            False,
            "Presentación no elegible: troquel inexistente en ALB.",
        )

    # --------------------------------------------------------
    # Validar estado
    # --------------------------------------------------------

    baja = pd.to_numeric(
        pd.Series([troquel.get("baja")]),
        errors="coerce",
    ).iloc[0]

    if pd.isna(baja):
        return (
            False,
            "Presentación no elegible: no fue posible determinar el estado de baja.",
        )

    if int(baja) != 0:
        return (
            False,
            "Presentación no elegible: la presentación se encuentra dada de baja.",
        )

    # --------------------------------------------------------
    # Validar fecha de vigencia
    # --------------------------------------------------------

    fecha_vigencia = troquel.get("fecha")

    if fecha_vigencia is None or pd.isna(fecha_vigencia):
        return (
            False,
            "Presentación no elegible: no posee fecha de vigencia de precio.",
        )

    try:
        fecha_vigencia = pd.to_datetime(
            fecha_vigencia,
            errors="raise",
        ).date()

    except Exception:
        return (
            False,
            "Presentación no elegible: fecha de vigencia de precio inválida.",
        )

    fecha_limite = (
        date.today()
        - relativedelta(months=months_window)
    )

    if fecha_vigencia < fecha_limite:
        return (
            False,
            (
                "Presentación no elegible: "
                f"la vigencia del precio supera los {months_window} meses."
            ),
        )

    return (
        True,
        "Presentación elegible.",
    )


# ============================================================
# BLOQUE 04 — Regla de negocio Caso A — Alta
# ============================================================

def evaluate_case_a(
    troquel: dict,
    ya_en_convenio: bool,
    banda_actual: dict,
    banda_hipotetica: dict,
    segundo_pvp: float | None,
    months_window: int = 6,
) -> AltaRuleResult:
    """
    Ejecuta la regla completa del Caso A.

    Flujo:

    1. Validar elegibilidad.
    2. Verificar si el troquel ya está convenido.
    3. Evaluar mejora de banda.
    4. Evaluar PVP candidato.
    5. Recomendar solamente si ambas condiciones se cumplen.
    """

    # --------------------------------------------------------
    # Datos básicos
    # --------------------------------------------------------

    pvp_candidato = pd.to_numeric(
        pd.Series([troquel.get("precio")]),
        errors="coerce",
    ).iloc[0]

    if pd.isna(pvp_candidato):
        pvp_candidato = 0.0

    pvp_candidato = float(pvp_candidato)

    banda_actual_pct = float(
        banda_actual.get(
            "porcentaje_descuento",
            0,
        )
        or 0
    )

    banda_hipotetica_pct = float(
        banda_hipotetica.get(
            "porcentaje_descuento",
            0,
        )
        or 0
    )

    laboratorios_actuales = int(
        banda_actual.get(
            "cantidad_laboratorios",
            0,
        )
        or 0
    )

    laboratorios_hipoteticos = int(
        banda_hipotetica.get(
            "cantidad_laboratorios",
            0,
        )
        or 0
    )

    # --------------------------------------------------------
    # PASO 1 — Elegibilidad
    # --------------------------------------------------------

    elegible, motivo_elegibilidad = is_eligible(
        troquel,
        months_window,
    )

    if not elegible:
        return AltaRuleResult(
            aplica=False,
            estado="NO_ELEGIBLE",
            recomendacion=False,
            motivo=motivo_elegibilidad,
            elegible=False,
            ya_en_convenio=False,
            banda_actual=banda_actual_pct,
            banda_hipotetica=banda_hipotetica_pct,
            laboratorios_actuales=laboratorios_actuales,
            laboratorios_hipoteticos=laboratorios_hipoteticos,
            mejora_banda=False,
            pvp_candidato=pvp_candidato,
            segundo_pvp_mas_alto=segundo_pvp,
            cumple_pvp=False,
        )

    # --------------------------------------------------------
    # PASO 2 — Ya está en convenio
    # --------------------------------------------------------

    if ya_en_convenio:
        return AltaRuleResult(
            aplica=False,
            estado="YA_CONVENIDO",
            recomendacion=False,
            motivo=(
                "El troquel ya se encuentra incluido en el "
                "Convenio APROSS OYTE. "
                "No corresponde ejecutar un análisis de incorporación."
            ),
            elegible=True,
            ya_en_convenio=True,
            banda_actual=banda_actual_pct,
            banda_hipotetica=banda_actual_pct,
            laboratorios_actuales=laboratorios_actuales,
            laboratorios_hipoteticos=laboratorios_actuales,
            mejora_banda=False,
            pvp_candidato=pvp_candidato,
            segundo_pvp_mas_alto=segundo_pvp,
            cumple_pvp=False,
        )

    # --------------------------------------------------------
    # PASO 3 — Condición 1: mejora de banda
    # --------------------------------------------------------

    mejora_banda = (
        banda_hipotetica_pct
        > banda_actual_pct
    )

    # --------------------------------------------------------
    # PASO 4 — Condición 2: segundo PVP más alto
    # --------------------------------------------------------

    if segundo_pvp is None:
        cumple_pvp = False

    else:
        cumple_pvp = (
            pvp_candidato
            <= float(segundo_pvp)
        )

    # --------------------------------------------------------
    # PASO 5 — Recomendación
    # --------------------------------------------------------

    if mejora_banda and cumple_pvp:

        recomendacion = True
        estado = "RECOMENDAR_ALTA"

        motivo = (
            "Recomendar incorporación. "
            f"La banda mejora de "
            f"{banda_actual_pct:.0%} a "
            f"{banda_hipotetica_pct:.0%} "
            f"y el PVP candidato "
            f"(${pvp_candidato:,.2f}) "
            f"es menor o igual al segundo PVP "
            f"más alto de la monodroga "
            f"(${float(segundo_pvp):,.2f})."
        )

    else:

        recomendacion = False
        estado = "NO_RECOMENDAR"

        motivos = []

        if not mejora_banda:
            motivos.append(
                (
                    "la incorporación no mejora la banda "
                    f"({banda_actual_pct:.0%} → "
                    f"{banda_hipotetica_pct:.0%})"
                )
            )

        if segundo_pvp is None:
            motivos.append(
                (
                    "no fue posible determinar "
                    "el segundo PVP más alto de la monodroga"
                )
            )

        elif not cumple_pvp:
            motivos.append(
                (
                    f"el PVP candidato "
                    f"(${pvp_candidato:,.2f}) "
                    f"supera el segundo PVP más alto "
                    f"(${float(segundo_pvp):,.2f})"
                )
            )

        motivo = (
            "No recomendar incorporación: "
            + " y ".join(motivos)
            + "."
        )

    return AltaRuleResult(
        aplica=True,
        estado=estado,
        recomendacion=recomendacion,
        motivo=motivo,
        elegible=True,
        ya_en_convenio=False,
        banda_actual=banda_actual_pct,
        banda_hipotetica=banda_hipotetica_pct,
        laboratorios_actuales=laboratorios_actuales,
        laboratorios_hipoteticos=laboratorios_hipoteticos,
        mejora_banda=mejora_banda,
        pvp_candidato=pvp_candidato,
        segundo_pvp_mas_alto=segundo_pvp,
        cumple_pvp=cumple_pvp,
    )


# ============================================================
# BLOQUE 05 — Bloque vacío de consumo
# ============================================================

def empty_consumption_block() -> dict:
    return {
        "afiliados_monodroga": 0,
        "costo_anual_monodroga": 0.0,
        "afiliados_misma_potencia": 0,
        "costo_anual_misma_potencia": 0.0,
        "promedio_mensual_cajas_por_afiliado": 0.0,
        "tasa_uso_potencia": 0.0,
        "consumo_promedio_mensual_producto": [],
    }


# ============================================================
# BLOQUE 06 — Información de consumo
# ============================================================

def consumption_block(
    liq_df: pd.DataFrame,
    troqueles_df: pd.DataFrame,
    cod_monodroga,
    potencia=None,
) -> dict:
    """
    Obtiene la información de consumo histórico
    correspondiente a una monodroga.

    Precio utilizado:
        pconv_fecha_remito

    Cantidad:
        unidades

    Afiliado:
        nro_afiliado
    """

    if liq_df.empty or troqueles_df.empty:
        return empty_consumption_block()

    required_troquel = {
        "tronquel",
        "cod_monodroga",
        "potencia",
    }

    required_liq = {
        "troquel",
        "periodo",
        "unidades",
        "pconv_fecha_remito",
        "nro_afiliado",
    }

    if not required_troquel.issubset(
        troqueles_df.columns
    ):
        return empty_consumption_block()

    if not required_liq.issubset(
        liq_df.columns
    ):
        return empty_consumption_block()

    # --------------------------------------------------------
    # Buscar troqueles de la misma monodroga
    # --------------------------------------------------------

    mono = troqueles_df[
        troqueles_df[
            "cod_monodroga"
        ].astype(str)
        == str(cod_monodroga)
    ].copy()

    if mono.empty:
        return empty_consumption_block()

    mono_codes = (
        mono["tronquel"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    # --------------------------------------------------------
    # Liquidaciones de la monodroga
    # --------------------------------------------------------

    liq = liq_df.copy()

    liq["_troquel_str"] = (
        liq["troquel"]
        .astype(str)
    )

    liq_mono = liq[
        liq["_troquel_str"].isin(
            mono_codes
        )
    ].copy()

    if liq_mono.empty:
        return empty_consumption_block()

    # --------------------------------------------------------
    # Normalizar valores
    # --------------------------------------------------------

    liq_mono["unidades"] = pd.to_numeric(
        liq_mono["unidades"],
        errors="coerce",
    ).fillna(0)

    liq_mono[
        "pconv_fecha_remito"
    ] = pd.to_numeric(
        liq_mono[
            "pconv_fecha_remito"
        ],
        errors="coerce",
    ).fillna(0)

    # Importe histórico definido con negocio
    liq_mono["importe"] = (
        liq_mono["unidades"]
        * liq_mono[
            "pconv_fecha_remito"
        ]
    )

    # --------------------------------------------------------
    # Agregar atributos ALB
    # --------------------------------------------------------

    mono_aux = mono[
        [
            "tronquel",
            "cod_monodroga",
            "potencia",
        ]
    ].copy()

    mono_aux["_troquel_str"] = (
        mono_aux["tronquel"]
        .astype(str)
    )

    joined = liq_mono.merge(
        mono_aux[
            [
                "_troquel_str",
                "cod_monodroga",
                "potencia",
            ]
        ],
        on="_troquel_str",
        how="left",
    )

    # --------------------------------------------------------
    # Meses disponibles
    # --------------------------------------------------------

    months = max(
        joined["periodo"]
        .dropna()
        .nunique(),
        1,
    )

    # --------------------------------------------------------
    # Consumo promedio por producto
    # --------------------------------------------------------

    by_product = (
        joined.groupby(
            "_troquel_str"
        )
        .agg(
            cajas_promedio_mensual=(
                "unidades",
                lambda s:
                    float(s.sum())
                    / months,
            ),
            pxq_promedio_mensual=(
                "importe",
                lambda s:
                    float(s.sum())
                    / months,
            ),
        )
        .reset_index()
        .rename(
            columns={
                "_troquel_str":
                    "codigo_troquel"
            }
        )
        .to_dict("records")
    )

    # --------------------------------------------------------
    # Afiliados monodroga
    # --------------------------------------------------------

    afiliados_monodroga = (
        joined["nro_afiliado"]
        .dropna()
        .nunique()
    )

    # --------------------------------------------------------
    # Misma potencia
    # --------------------------------------------------------

    if potencia is not None:

        misma_potencia = joined[
            joined["potencia"]
            .astype(str)
            == str(potencia)
        ].copy()

    else:
        misma_potencia = (
            joined.iloc[0:0]
        )

    afiliados_potencia = (
        misma_potencia[
            "nro_afiliado"
        ]
        .dropna()
        .nunique()
    )

    # --------------------------------------------------------
    # Promedio mensual por afiliado
    # --------------------------------------------------------

    promedio_cajas = (
        float(
            joined[
                "unidades"
            ].sum()
        )
        / months
        / max(
            afiliados_monodroga,
            1,
        )
    )

    # --------------------------------------------------------
    # Costos anualizados
    # --------------------------------------------------------

    costo_anual_monodroga = (
        float(
            joined[
                "importe"
            ].sum()
        )
        / months
        * 12
    )

    costo_anual_potencia = (
        float(
            misma_potencia[
                "importe"
            ].sum()
        )
        / months
        * 12
        if not misma_potencia.empty
        else 0.0
    )

    # --------------------------------------------------------
    # Tasa uso potencia
    # --------------------------------------------------------

    tasa_uso = (
        float(
            afiliados_potencia
            / afiliados_monodroga
        )
        if afiliados_monodroga
        else 0.0
    )

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
            by_product,
    }


# ============================================================
# BLOQUE 07 — Facturación anual y simulación económica
# ============================================================

def annual_billing(
    liq_df: pd.DataFrame,
    convenio_codes: list[str],
) -> float:
    """
    Calcula la facturación anual actual de los troqueles
    indicados utilizando el precio convenido histórico:

        Unidades × PConv Fecha Remito

    El resultado se anualiza según la cantidad de períodos
    disponibles en Liquidaciones.
    """

    if liq_df.empty:
        return 0.0

    if (
        "troquel" not in liq_df.columns
        or "unidades" not in liq_df.columns
        or "pconv_fecha_remito" not in liq_df.columns
    ):
        return 0.0

    df = liq_df.copy()

    df["_troquel_str"] = (
        df["troquel"]
        .astype(str)
    )

    codigos = set(
        str(c)
        for c in convenio_codes
    )

    df = df[
        df["_troquel_str"].isin(
            codigos
        )
    ].copy()

    if df.empty:
        return 0.0

    df["unidades"] = pd.to_numeric(
        df["unidades"],
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

    df["importe_actual"] = (
        df["unidades"]
        *
        df["pconv_fecha_remito"]
    )

    if "periodo" in df.columns:

        meses = max(
            df["periodo"]
            .dropna()
            .nunique(),
            1,
        )

    else:

        meses = 1

    facturacion_anual = (
        float(
            df[
                "importe_actual"
            ].sum()
        )
        / meses
        * 12
    )

    return float(
        facturacion_anual
    )


# ============================================================
# BLOQUE 07.1 — Simulación económica por cambio de banda
# ============================================================

def projected_billing_by_band(
    liq_df: pd.DataFrame,
    troqueles_df: pd.DataFrame,
    troquel_candidato: dict,
    banda_actual: float,
    banda_proyectada: float,
) -> dict:
    """
    Simula el impacto económico de incorporar el troquel
    candidato cuando dicha incorporación modifica la banda.

    PRESENTACIÓN EQUIVALENTE:

        cod_monodroga
        + formas
        + potencia
        + unidad_potencia

    ESCENARIO ACTUAL:

        Unidades × PConv Fecha Remito

    ESCENARIO PROYECTADO:

        Unidades × PVP Fecha Remito
                 × (1 - banda proyectada)

    Se mantiene exactamente el mismo consumo histórico.

    No se supone consumo para el troquel candidato.
    El efecto económico proviene del cambio de banda sobre
    el consumo histórico de la presentación equivalente.
    """

    resultado_vacio = {

        "facturacion_actual_grupo_anual":
            0.0,

        "facturacion_proyectada_grupo_anual":
            0.0,

        "impacto_grupo_anual":
            0.0,

        "ahorro_grupo_anual":
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
    # 1. Validaciones generales
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
        "formas",
        "potencia",
        "unidad_potencia",
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
    # 2. Obtener presentación equivalente del candidato
    # --------------------------------------------------------

    cod_monodroga = (
        troquel_candidato.get(
            "cod_monodroga"
        )
    )

    forma = str(
        troquel_candidato.get(
            "formas",
            "",
        )
        or ""
    )

    potencia = str(
        troquel_candidato.get(
            "potencia",
            "",
        )
        or ""
    )

    unidad_potencia = str(
        troquel_candidato.get(
            "unidad_potencia",
            "",
        )
        or ""
    )

    # --------------------------------------------------------
    # 3. Buscar troqueles de la presentación equivalente
    # --------------------------------------------------------

    grupo = troqueles_df[
        (
            troqueles_df[
                "cod_monodroga"
            ].astype(str)
            == str(
                cod_monodroga
            )
        )
        &
        (
            troqueles_df[
                "formas"
            ]
            .fillna("")
            .astype(str)
            == forma
        )
        &
        (
            troqueles_df[
                "potencia"
            ]
            .fillna("")
            .astype(str)
            == potencia
        )
        &
        (
            troqueles_df[
                "unidad_potencia"
            ]
            .fillna("")
            .astype(str)
            == unidad_potencia
        )
    ].copy()

    if grupo.empty:
        return resultado_vacio

    codigos_grupo = (
        grupo["tronquel"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    # --------------------------------------------------------
    # 4. Obtener liquidaciones históricas del grupo
    # --------------------------------------------------------

    liquidaciones = (
        liq_df.copy()
    )

    liquidaciones[
        "_troquel_str"
    ] = (
        liquidaciones[
            "troquel"
        ]
        .astype(str)
    )

    liquidaciones = liquidaciones[
        liquidaciones[
            "_troquel_str"
        ].isin(
            codigos_grupo
        )
    ].copy()

    if liquidaciones.empty:
        return resultado_vacio

    # --------------------------------------------------------
    # 5. Normalizar campos económicos
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
    # 6. Escenario actual
    #
    # Unidades × precio convenido histórico
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
    # 7. Escenario proyectado
    #
    # PVP histórico × (1 - nueva banda)
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
    # 8. Determinar meses observados
    # --------------------------------------------------------

    if "periodo" in liquidaciones.columns:

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
    # 9. Anualizar escenario actual
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

    # --------------------------------------------------------
    # 10. Anualizar escenario proyectado
    # --------------------------------------------------------

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
    # 11. Calcular impacto económico
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

        "facturacion_actual_grupo_anual":
            float(
                actual_anual
            ),

        "facturacion_proyectada_grupo_anual":
            float(
                proyectado_anual
            ),

        "impacto_grupo_anual":
            float(
                impacto
            ),

        "ahorro_grupo_anual":
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
