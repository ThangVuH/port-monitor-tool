from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import json
import fetch 
import process
import storage
import glob
import os
import csv
from typing import Dict, Any

app = FastAPI(
    title="Verify UN/LOCODE API",
    description="API for fetching, processing, and storing UN/LOCODE data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_FILE = r"/home/thang_sinay/port-editor-tool/code/config.json"

# Utility function
def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file '{config_path}' not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in '{config_path}'.")

# Load config at startup
config = load_config(CONFIG_FILE)

@app.get("/")
def read_root():
    return {"message": "port updatte tool"}

@app.get("/fetch_data/unlocode")
async def fetch_data():
    """Fetch UNLOCODE data and extract it."""
    try:
        downloader = fetch.fetch_UNLOCODE(config["UNLOCODE"])
        downloader.download_folder()
        downloader.extract_folder()
        return {"message": "Data fetch initiated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/fetch_data/shipnext")
async def fetch_shipnext():
    """Fetch Shipnext data and process it."""
    try:
        fetcher = fetch.fetch_Shipnext(config['Shipnext'])
        fetcher.fetch_cookies()
        api_url_list = fetcher.fetch_list_port()
        data = fetcher.extract_data()
        processer = process.extract_Shipnext(api_url_list, data)
        processer.export_to_json(config['Shipnext']['output_file'])
        return {"message": "Shipnext Data fetch initiated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/process_data")
async def process_data():
    """Process UNLOCODE data and return statistics."""
    data_folder = config["UNLOCODE"]["download_path"]
    output_file = config["UNLOCODE"]["output_file"]
    
    try:
        data_file_list = glob.glob(os.path.join(data_folder, "*.csv"))
        extractor = process.extract_UNLOCODE(data_file_list)
        df = extractor.extract_data()
        stats = extractor.get_statistics(df)
        ports_df, _ = extractor.filter_ports(df)
        extractor.export_to_csv(ports_df, output_file)

        return {
            "total_locations": stats['total_locations'], 
            "ports_only": stats['ports_only'], 
            "unique_locode_port": stats['unique_locode_port'], 
            "port_status_change": stats['port_status_change']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@app.get("/store_data")
async def store_data():
    """Store processed data in the database."""
    database_config = config["Database"]
    output_file = config["UNLOCODE"]["output_file"]
    input_file_shipnext = config['Shipnext']["output_file"]
    
    try:
        data = {}
        with open(output_file, newline='', encoding='latin-1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                loc = row['locode']
                date = row['date']
                if loc not in data or date > data[loc]['date']:
                    data[loc] = row

        db_manager = storage.Database_Manager(database_config)
        db_manager.create_tables()
        db_manager.insert_unlocode(data)
        db_manager.insert_shipnext(load_config(input_file_shipnext))

        return {"message": "Data store initiated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)