from __future__ import annotations
from typing import Any
import pandas as pd
from db.supabase_client import get_supabase

class Repo:
    def __init__(self):
        self.sb = get_supabase()

    def table_df(self, table: str, limit: int = 10000) -> pd.DataFrame:
        data = self.sb.table(table).select('*').limit(limit).execute().data
        return pd.DataFrame(data or [])

    def get_troquel(self, codigo: str) -> dict[str, Any] | None:
        data = self.sb.table('troqueles').select('*').eq('codigo_troquel', codigo).limit(1).execute().data
        return data[0] if data else None

    def is_in_convenio(self, codigo: str) -> bool:
        data = self.sb.table('convenio_oyte').select('codigo_troquel,fecha_baja_convenio').eq('codigo_troquel', codigo).limit(1).execute().data
        return bool(data and data[0].get('fecha_baja_convenio') is None)

    def save_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return self.sb.table('simulacion_resultados').insert(result).execute().data[0]
