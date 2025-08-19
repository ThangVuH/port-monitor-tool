# Run the application:  

`uv run main.py` or `uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000`

you can easily find the API docs in `127.0.0.1:8000/docs` but here are the pipeline also: 

1. to fetch data:
`127.0.0.1:8000/fetch_data`

2. to process data:
- UNLOCODE: `127.0.0.1:8000/fetch_data/unlocode`
- Shipnext.com: `127.0.0.1:8000/fetch_data/shipnext`

3. to store data:
`127.0.0.1:8000/fetch_data/store_data`


# **note to improve**: 

    - refactor `main.py` to use FastAPI instead of Flask
    - re-design a way to manage database instead of use only `storage.py`
    - "unece.org" have just add CAPTCHA to detect bot so need to update `fetch/fetch_UNLOCODE` with Playwright instead of using Selenium

# Cluster analysis:

check `cluster_vessel.ipynb` for more information
