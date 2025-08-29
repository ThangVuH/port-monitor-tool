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

check `cluster_vessel.ipynb` for experiment with generate vessel data

implement `cluster.py` with 3 algorithm based on DBSCAN:
    - "naive": (recommand to use for now, fine-tune with `eps` and `min_samples`)
        - random sampling: 20000
        - default DBSCAN
    - "cluster-sampling": (almost finish, need to fine-tune. Main idea is to reduce cluster parking in port and noise outside of coarse region)
        - cluster sampling
        - DBSCAN with 'distance' method is 'haversin' and 'find nearest neigboors' is 'Ball tree'
        - double cluster: first cluster sampling to take region close to coarse then continue cluster to find the waiting area
    - "optimized" (main idea is to reduce the cost of computation and memory so it can scale up with csv file > 1 millions)
        - work but still in experiment so not very result or efficient


# **note to improve**: 
    - merge the polygon cluster if it intersect with others
    - fine-tune "cluster-sampling"
    - try HDBSAN algorithm (less control parameter than DBSCAN but worth to try)
    - make user interface (eg. Strealit) for easy interact with map, chose method, parameter
    - manipulate with docker-compose for finish the tool.
    - try side-project with `pdf_reader.ipynb` which extract information about waiting zone from pdf file
