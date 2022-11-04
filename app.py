#imports
import st_connection
import st_connection.snowflake

import streamlit as st
import pandas as pd

from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid import GridUpdateMode, DataReturnMode
from openpyxl import load_workbook

# Use wide layout
st.set_page_config(page_icon="🚀", page_title="SnowTransport: Load file into Snowflake", layout="wide", initial_sidebar_state="expanded")

#login form and Snowflake connection
session = st.connection.snowflake.login({'account': 'ORGNAME-ACCOUNTNAME', 'user': '', 'password': ''
                                        }, {'warehouse': '','database': '', 'schema': ''}, 'Snowflake Login')

@st.cache
def get_avail_roles():
        user = pd.DataFrame(session.sql('select current_user() as cuser').collect())
        user = user.CUSER.values[0]
        #collect roles granted to the user and assign to var
        rolesp = pd.DataFrame(session.sql('SHOW GRANTS TO USER ' + user).collect())
        # remove all but "role" axis (column)
        rolesp = rolesp[['role']]
        # rename axis (column) from role to name for dataframe concat later
        rolesp.rename(columns={"role": "name"}, inplace=True)
        # collect roles and return only roles inherited, default, or current
        rolesi = pd.DataFrame(session.sql('SHOW ROLES').collect())
        rolesi = rolesi[(rolesi['is_inherited'] == 'Y') | (
        rolesi['is_default'] == 'Y') | (rolesi['is_current'] == 'Y')]
        # remove all axis except name
        rolesi = rolesi[["name"]]
        # concat (union) dataframes and set list
        roles = pd.concat([rolesp, rolesi])
        return roles

with st.sidebar:
        roles = get_avail_roles()
        default_role = session.get_current_role().replace('"','')
        idx = int(roles[roles['name']==default_role].index[0])
        with st.form("role"):
            try:
                role = st.selectbox("role:", roles['name'], help='💡 Choose from your available roles. Tip: It is best practice to not use accountadmin', index=idx)
                role_button = st.form_submit_button("Set Role")
            except:
                role = st.selectbox("role:", roles['name'], help='💡 Choose from your available roles. Tip: It is best practice to not use accountadmin')
                role_button = st.form_submit_button("Set Role")
        if role_button:
            session.use_role(role)
        warehouses = pd.DataFrame(session.sql('SHOW WAREHOUSES').collect())[['name']]
        warehouse = st.selectbox("warehouse:",pd.unique(warehouses['name']),help='💡 Warehouse list depends on privlages of Role')
        if(warehouse):
            session.use_warehouse(warehouse)

        databases = pd.DataFrame(session.sql('SHOW DATABASES').collect())
        databases = databases[databases['origin'] == '']
        database=st.selectbox("database:",pd.unique(databases['name']))
        if(database):
            session.use_database(database)

        schemas = pd.DataFrame(session.sql('SHOW SCHEMAS').collect())
        schemas = schemas[schemas['name'] != 'INFORMATION_SCHEMA']
        schema=st.selectbox("schema:",pd.unique(schemas['name']))
        if(schema):
            session.use_schema(schema)
        
def read_sheet(uploaded_file, file_type='xlsx', str_sheetname="", col_list=None, date_col_list=False):
    dataframe = ""
    try:
        if uploaded_file is not None:
            if file_type == 'csv':
                dataframe = pd.read_csv(uploaded_file, usecols=col_list, parse_dates=date_col_list).applymap(
                    lambda s: s.upper() if type(s) == str else s).fillna('')
            else:
                dataframe = pd.read_excel(uploaded_file, sheet_name=str_sheetname, usecols=col_list, parse_dates=date_col_list).applymap(
                    lambda s: s.upper() if type(s) == str else s).fillna('')
        else:
            dataframe = "Empty - Upload a file first"
            st.warning(dataframe)
    except ValueError as e:
        st.error("Problem: " + e.args[0])
    finally:
        return dataframe


def get_sheetnames(upload_file):
    wb = load_workbook(upload_file, read_only=True, keep_links=False)
    return wb.sheetnames

############## custom animated background style ###########################
st.write("""
<style>
[class*="block-container css-18e3th9 egzxvld2"]  {
	background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
	background-size: 400% 400%;
	animation: gradient 15s ease infinite;
	height: 200vh;
}

@keyframes gradient {
	0% {
		background-position: 0% 50%;
	}
	50% {
		background-position: 100% 50%;
	}
	100% {
		background-position: 0% 50%;
	}
}
</style>
""", unsafe_allow_html=True)

############## logo ###########################
st.image(
    "rocket2.png",
    width=400
)


uploaded_file = st.file_uploader(
    "",
    key="1",
    help="Choose a 'csv','xlsx','xls' file",
    type=['csv', 'xlsx', 'xls']
)


if uploaded_file is not None:
    if uploaded_file.type == 'text/csv':
        shows = read_sheet(uploaded_file, 'csv')
    else:
        excel_sheets = get_sheetnames(uploaded_file)
        excel_sheets_mod = ("Select Sheet", *excel_sheets)
        sheet = st.selectbox("Select a Workbook Sheet",
                             excel_sheets_mod, help="Select a sheet from this list")
        if sheet != "Select Sheet":
            shows = read_sheet(uploaded_file, 'xls', sheet)
        else:
            st.stop()  # this makes streamlit wait until user selects a worksheet
else:
    st.info(
        f"""
            👆 Upload a csv, xlsx, or xls file from your local system.
            """
    )
    st.stop()
        
# setup AG Grid

gb = GridOptionsBuilder.from_dataframe(shows)
gb.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True, editable=True, groupable=True)
gb.configure_side_bar()
gb.configure_pagination(
    enabled=True, paginationAutoPageSize=False, paginationPageSize=20)
gridOptions = gb.build()

response = AgGrid(
    shows,
    gridOptions=gridOptions,
    enable_enterprise_modules=False,
    editable=True,
    update_mode=GridUpdateMode.MODEL_CHANGED,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    fit_columns_on_grid_load=False,
    theme='balham'
)
df = pd.DataFrame(response["data"])

with st.form('my_form'):
    st.subheader('Load as a table in Snowflake')
    tablname = st.text_input('Enter the table name')
    submitted = st.form_submit_button('create table')
    if submitted and tablname:
        done = False
        with st.spinner(text="Creating Table in Snowflake..."):
            try:
                # st.info("Session information:")
                # st.info(session.sql("select current_warehouse(), current_database(), current_schema()").collect())
                snowpark_df = session.write_pandas(df, tablname.upper(), auto_create_table=True)
                st.success("TABLE CREATED!", icon="✅")
                desc = snowpark_df.describe()
                if desc:
                    with st.spinner(text="Gathering Summary Stats..."):
                        st.dataframe(desc)
                        st.success("Summary Stats complete!", icon="✅")
                        st.snow()
            except:
                st.error("⚠️ It looks like you don't have privlages to create or overwite a table in this schema. Check your role and try again.")
            


          
