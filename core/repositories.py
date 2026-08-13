
# ============================================================
# BLOQUE 01 — Imports
# ============================================================

from __future__ import annotations

from typing import Any

import pandas as pd

from db.supabase_client import get_supabase


# ============================================================
# BLOQUE 02 — Repositorio principal
# ============================================================

class Repo:

    def __init__(self):
        self.sb = get_supabase()


# ============================================================
# BLOQUE 03 — Lectura completa de tablas con paginación
# ============================================================

    def table_df(
        self,
        table: str,
        limit: int | None = None,
        page_size: int = 1000,
    ) -> pd.DataFrame:
        """
        Lee una tabla completa de Supabase mediante paginación.

        Supabase limita la cantidad de filas devueltas por
        consulta, por lo que se realizan consultas sucesivas
        usando range().

        Parámetros
        ----------
        table:
            Nombre de la tabla.

        limit:
            Si se informa, devuelve como máximo esa cantidad.
            Si es None, intenta leer la tabla completa.

        page_size:
            Cantidad de registros por consulta.
            Default: 1000.
        """

        all_rows = []
        start = 0

        while True:

            # ------------------------------------------------
            # Determinar final del bloque
            # ------------------------------------------------

            if limit is not None:

                remaining = limit - len(all_rows)

                if remaining <= 0:
                    break

                current_page_size = min(
                    page_size,
                    remaining,
                )

            else:
                current_page_size = page_size

            end = (
                start
                + current_page_size
                - 1
            )

            # ------------------------------------------------
            # Consulta paginada
            # ------------------------------------------------

            response = (
                self.sb
                .table(table)
                .select("*")
                .range(start, end)
                .execute()
            )

            rows = response.data or []

            if not rows:
                break

            all_rows.extend(rows)

            # ------------------------------------------------
            # Si llegaron menos filas que las solicitadas,
            # llegamos al final de la tabla.
            # ------------------------------------------------

            if len(rows) < current_page_size:
                break

            start += current_page_size

        return pd.DataFrame(all_rows)


# ============================================================
# BLOQUE 04 — Obtener troquel vigente desde ALB
# ============================================================

    def get_troquel(
        self,
        codigo: str,
    ) -> dict[str, Any] | None:
        """
        Busca un troquel en src_troqueles_alb.

        Si existen varias versiones del mismo troquel,
        devuelve la de fecha más reciente.
        Ante empate, utiliza el ID más alto.
        """

        data = (
            self.sb
            .table("src_troqueles_alb")
            .select("*")
            .eq("tronquel", codigo)
            .order(
                "fecha",
                desc=True,
            )
            .order(
                "id",
                desc=True,
            )
            .limit(1)
            .execute()
            .data
        )

        return (
            data[0]
            if data
            else None
        )


# ============================================================
# BLOQUE 05 — Verificar pertenencia al convenio
# ============================================================

    def is_in_convenio(
        self,
        codigo: str,
    ) -> bool:
        """
        Regla definida:

        Si el troquel figura en src_convenio_oyte,
        se considera convenido.

        El atributo Estado no interviene.
        """

        data = (
            self.sb
            .table("src_convenio_oyte")
            .select("troquel")
            .eq(
                "troquel",
                codigo,
            )
            .limit(1)
            .execute()
            .data
        )

        return bool(data)


# ============================================================
# BLOQUE 06 — Guardar resultado de simulación
# ============================================================

    def save_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Persiste el resultado de una simulación
        en simulacion_resultados.
        """

        data = (
            self.sb
            .table("simulacion_resultados")
            .insert(result)
            .execute()
            .data
        )

        return (
            data[0]
            if data
            else {}
        )
