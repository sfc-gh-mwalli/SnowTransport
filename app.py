import streamlit as st
import pandas as pd

from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid import GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode

import numpy as np
import re
from openpyxl import load_workbook

import st_connection
import st_connection.snowflake

# Use wide layout
st.set_page_config(page_icon="🚀", page_title="Table Loader", layout="wide")

session = st.connection.snowflake.login({'account': '', 'user': '', 'password': '', 'database': '', 'schema': 'PUBLIC'}, {'warehouse': ''}, 'Snowflake Login')

def read_sheet(uploaded_file,file_type='xlsx',str_sheetname="",col_list=None, date_col_list=False):
    dataframe=""    
    try:
        if uploaded_file is not None:
            if file_type == 'csv':
                dataframe = pd.read_csv(uploaded_file, usecols=col_list, parse_dates = date_col_list).applymap(lambda s: s.upper() if type(s) == str else s).fillna('')
            else:
                dataframe = pd.read_excel(uploaded_file,sheet_name = str_sheetname, usecols=col_list, parse_dates = date_col_list).applymap(lambda s: s.upper() if type(s) == str else s).fillna('')
        else:
            dataframe="Empty - Upload a file first"
            st.warning(dataframe)			
    except ValueError as e:
        st.error("Problem: "+ e.args[0])
    finally:
        return dataframe

def get_sheetnames(upload_file):
    wb = load_workbook(upload_file, read_only=True, keep_links=False)
    return wb.sheetnames


def _max_width_():
    max_width_str = f"max-width: 1800px;"
    st.markdown(
        f"""
    <style>
    .reportview-container .main .block-container{{
        {max_width_str}
    }}
    </style>    
    """,
        unsafe_allow_html=True,
    )

st.image(
    "rocket.png",
    width=700,
)


uploaded_file = st.file_uploader(
    "",
    key="1",
    help="Choose a 'csv','xlsx','xls' file",
    type=['csv','xlsx','xls']
)


if uploaded_file is not None:
    #file_container = st.expander("Check your uploaded file")
    
    if uploaded_file.type == 'text/csv':
        shows=read_sheet(uploaded_file,'csv')
    else :
        excel_sheets = get_sheetnames(uploaded_file)
        excel_sheets_mod = ("Select Sheet",*excel_sheets)
        sheet = st.selectbox("Select a Workbook Sheet",excel_sheets_mod, help = "Select a sheet from this list")
        if sheet != "Select Sheet":
            shows = read_sheet(uploaded_file,'xls',sheet)
        else:
            st.stop() # this makes streamlit wait until user selects a worksheet
else:
    st.info(
        f"""
            👆 Upload a csv, xlsx, or xls file from your local system.)
            """
    )
    st.stop()
        
# setup AG Grid

gb = GridOptionsBuilder.from_dataframe(shows)
gb.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True, editable=True, groupable=True)
gb.configure_side_bar()
gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=20)
gridOptions = gb.build()

response = AgGrid(
    shows,
    gridOptions=gridOptions,
    enable_enterprise_modules=True,
    update_mode=GridUpdateMode.MODEL_CHANGED,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    fit_columns_on_grid_load=False,
)

df = pd.DataFrame(response["data"])  # retrieve all rows

with st.form('my_form'):
        st.write('Load as a table in Snowflake')
        tabname = st.text_input('input table name')
        submitted = st.form_submit_button('create table')
        if submitted and tabname:
            done=False
            st.info("CREATING SNOWFLAKE TABLE...")
            st.info("Session information:")
            st.info(session.sql("select current_warehouse(), current_database(), current_schema()").collect())
            snowpark_df = session.write_pandas(df, tabname.upper(), auto_create_table=True)
            if done:
                st.info("DONE")

            desc=snowpark_df.describe().sort("SUMMARY").collect()
            if desc:
                st.info("Done!")
                st.table(desc)
                #st.line_chart(snowpark_df.to_pandas())
          
