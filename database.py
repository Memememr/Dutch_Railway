import time
import streamlit as st

def run_query(query:str, params: dict = None):
    conn = st.connection("mysql",type = "sql") 

    
    df = conn.query(query, params=params)

    return df
   