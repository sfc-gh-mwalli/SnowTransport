# SnowTransport

CSV and Excel File uploader for Snowflake

## To Install

### Faster Solver
Use libmamba for a much faster solver

First, make sure you are running conda 4.12.0 or higher:
```
conda update -n base conda
```

Then install conda-libmamba-solver:
```
conda install -n base conda-libmamba-solver
```

Use the following command to always use libmamba as your default solver:

```
conda config --set experimental_solver libmamba
```


Use these commands to create and activate the conda environment based on the specifications in the Yaml file:
```
conda env create --file snowtransport_env.yml
conda activate snowtransport_env
```
To run this streamlit app
```
streamlit run app.py
```
Use this command to list the environments you have:
```
conda info --envs
```

Use this command to remove the environment:
```
conda env remove --name snowtransport_env
```