import streamlit as st
from etl.pipeline import run_etl_pipeline

st.set_page_config(
    page_title="Dutch Railway OLAP Dashboard",
    layout="wide",
)

st.title("Dutch Railway Analytics Dashboard")