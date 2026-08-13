from __future__ import annotations

from typing import Any
import pandas as pd

from db.supabase_client import get_supabase


class Repo:

    def __init__(self):
        self.sb = get_supabase()


    # ========================================================
    # LECTURA DE TABLAS
    # ========================================================

    def table_df(
        self,
        table: str,
        limit: int | None = None,
        page_size: int = 1000,
    ) -> pd.DataFrame:

        """
        Lee una tabla de Supabase por páginas.

        Si limit=None, intenta traer toda la tabla.
        Si limit tiene un valor, trae como máximo esa cantidad.
        """

        rows = []
        start = 0

        while True:

            if limit is not None:

                remaining = limit - len(rows)

                if remaining <= 0:
                    break

                current_size = min(
                    page_size,
                    remaining,
                )

            else:

                current_size = page_size

            end = (
                start
                + current_size
                - 1
            )

            response = (
                self.sb
                .table(table)
                .select("*")
                .range(start, end)
                .execute()
            )

            batch = (
                response.data
                if response.data
                else []
            )

            if not batch:
                break

            rows.extend(batch)

            if len(batch) < current_size:
                break

            start += current_size

        return pd.DataFrame(rows)


    # ========================================================
    # BUSCAR TROQUEL
    # ========================================================

    def get_troquel(
        self,
        codigo: str,
    ) -> dict[str, Any] | None:

        data = (
            self.sb
            .table("src_troqueles_alb")
            .select("*")
            .eq(
                "tronquel",
                codigo,
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


    # ========================================================
    # VERIFICAR CONVENIO
    # ========================================================

    def is_in_convenio(
        self,
        codigo: str,
    ) -> bool:

        data = (
            self.sb
            .table("src_convenio_oyte")
            .select("*")
            .eq(
                "troquel",
                codigo,
            )
            .limit(1)
            .execute()
            .data
        )

        # Regla definida:
        # si figura en la lista de convenio,
        # se considera convenido.
        return bool(data)


    # ========================================================
    # GUARDAR SIMULACIÓN
    # ========================================================

    def save_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:

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
