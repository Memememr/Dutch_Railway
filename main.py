import streamlit as st
from etl.pipeline import run_etl_pipeline



st.set_page_config(
    page_title="Dutch Railway OLAP Dashboard",
    layout="wide",
)

st.title("Dutch Railway Analytics Dashboard")

#Trigger run ETL
if st.button("Run ETL Pipeline"):
    with st.spinner("Processing data..."):
        run_etl_pipeline()
        st.cache_data.clear()
    st.success("Database populated!")
