# Dutch Railway OLAP Project

This project loads the dutch_railway.cv into a datawarehouse which in turn gets queried to form an OLAP Report displayed on a streamlit webapp.

## Pre-requisites
1. Clone repository
2. Download Dutch Railway Dataset through https://duckdb.org/docs/lts/guides/snippets/dutch_railway_datasets. 
> *This project was made with the 2025 dataset in mind. Use a different year at your own risk.*
3. Open the project in your own editor
4. Through a terminal, install all the requirements.
```cmd
    pip install -r requiremnts.txt
```
5. Optionally, you can also run the program in a virtual environment.
- Create a venv folder
```cmd
python -m venv venv
```


## How to run the program
## 
1. Run virtual environemnt

- Windows (cmd.exe)
```cmd
venv/Scripts/Activate
```

- Windows (PowerShell): 
```Powershell
venv\Scripts\Activate.ps1
```

- Linux and macOS:
```Linux and MacOs
 source venv/bin/activate
```
2. Create a copy of secrets.toml.example in streamlit/secrets.toml and replace the appropriate values with your own credentials

3. Run ETL script 
```cmd
 python run etl/pipeline.py
```
4. Run the webpage
```cmd
streamlit run main.py

5. Congratulations! your webapp hould be visible on your browser. 


## Using nGrok
- This project was initially deployed in an nGrok server.
To do so follow the insructions at https://ngrok.com/
and replace the localhost port where your local build of streamlit is being ran.