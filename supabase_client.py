import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get('SUPABASE_URL')
    key = st.secrets.get('SUPABASE_KEY')
    if not url or not key:
        st.error('Faltan SUPABASE_URL y/o SUPABASE_KEY en .streamlit/secrets.toml')
        st.stop()
    return create_client(url, key)
