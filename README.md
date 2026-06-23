# Simulador Troqueles APROSS OYTE

App en Streamlit + Supabase para simular altas/bajas de troqueles del convenio APROSS OYTE.

## Instalación
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app/main.py
```

## Variables
En Streamlit Cloud cargar:
- SUPABASE_URL
- SUPABASE_KEY

## Orden recomendado
1. Ejecutar `db/schema.sql` en Supabase.
2. Cargar datos de prueba con `scripts/seed_demo.py`.
3. Correr `streamlit run app/main.py`.
