import os
import folium
import numpy as np
import pandas as pd

from sklearn.cluster import DBSCAN 
from shapely.geometry import MultiPoint

def find_anchorages(df, approach='naive'):
    """
    Main function to detect anchorage areas from AIS data
    """
    if approach == 'optimized':
        result = optimized_anchorage_detection(df)
    elif approach == 'cluster_sampling':
        result = cluster_sampling_detection(df)
    else:
        dbscan_kwargs={'eps': 0.003, 'min_samples': 30}
        result = naive_detection(df, **dbscan_kwargs)

    # extract polygon for visualise
    polygons = extract_polygon(result, 'cluster')

    return result, polygons


def visualize_anchorages(df, clustered_data, polygons, data_path, output_path):
    m = folium.Map(location=[df.latitude.mean(), df.longitude.mean()], zoom_start=12)

    # for _, row in df.iterrows():
    #     folium.CircleMarker([row['latitude'], row['longitude']], radius=0.5).add_to(m)
    
    visual_data = df[['latitude', 'longitude']].sample(n=20000, random_state=42).to_numpy()
    for latitude, longitude in visual_data:
        folium.CircleMarker([latitude, longitude], radius=0.5).add_to(m)

    # for _, row in clustered_data.iterrows(): 
    #     folium.CircleMarker([row['latitude'], row['longitude']], radius=0.5, color='yellow',fill=True, fill_opacity=0.7).add_to(m)

    for hull in polygons:
        x, y = hull.exterior.xy
        hull_coord = np.vstack((x,y)).transpose()
        folium.Polygon(
            locations=hull_coord,
            color='red',
            tooltip = "waiting zone"
        ).add_to(m)

    unlocode = data_path.split('/')[-1].split('.')[0]
    output_name = os.path.join(output_path, f"{unlocode}.html")
    m.save(output_name)
    
def extract_polygon(df, column="cluster"):
    data = df[['latitude', 'longitude']].values
    labels = df[column].values

    polygons = []

    for label in set(labels):
        if label == -1: # Skip noise
            continue

        cluster_pts = data[labels == label]
        mp = MultiPoint(cluster_pts)

        hull = mp.convex_hull
        polygons.append(hull)

    return polygons 

def naive_detection(df, **dbscan_kwargs):
    df_sample = df.sample(n=20000, random_state=42)
    coords = df_sample[['latitude', 'longitude']].to_numpy()

    clusters = DBSCAN(**dbscan_kwargs).fit_predict(coords)
    df_sample['cluster'] = clusters

    return df_sample

def cluster_sampling_detection(df, coarse_sample=10000, fine_eps=0.002):
    # Stage 1: Coarse sampling and clustering to find potential anchorage regions
    df_coarse = anchorage_focused_sampling(df, coarse_sample)
    
    coords_coarse = df_coarse[['latitude', 'longitude']].values
    coords_coarse_rad = np.radians(coords_coarse)

    # Coarse DBSCAN to find general areas
    dbscan_coarse = DBSCAN(
        eps=0.01,  # ~1km radius
        min_samples=10,
        metric='haversine',
        algorithm='ball_tree'
    )
    coarse_clusters = dbscan_coarse.fit_predict(coords_coarse_rad)
    df_coarse['coarse_cluster'] = coarse_clusters

    # Stage 2: Fine clustering within each coarse cluster
    final_results = []
    
    for cluster_id in np.unique(coarse_clusters):
        if cluster_id == -1:  
            continue
            
        cluster_data = df_coarse[df_coarse['coarse_cluster'] == cluster_id]
        
        # Get more data from this region
        center_lat = cluster_data['latitude'].mean()
        center_lon = cluster_data['longitude'].mean()
        radius = 0.02  # ~2km radius
        
        region_data = df[
            (df['latitude'].between(center_lat - radius, center_lat + radius)) &
            (df['longitude'].between(center_lon - radius, center_lon + radius)) &
            (df['speed'] < 2.0)
        ]
        
        if len(region_data) > 5:
            # Fine clustering within this region
            coords_fine = np.radians(region_data[['latitude', 'longitude']].values)
            
            dbscan_fine = DBSCAN(
                eps=fine_eps,  # ~200m radius
                min_samples=5,
                metric='haversine'
            )
            
            fine_clusters = dbscan_fine.fit_predict(coords_fine)
            region_data = region_data.copy()
            region_data['cluster'] = fine_clusters
            region_data['coarse_cluster'] = cluster_id
            
            final_results.append(region_data)
    
    return pd.concat(final_results) if final_results else pd.DataFrame()

def optimized_anchorage_detection(df):
    potential_anchors = df[
        (df['speed'] < 3.0)
    ].copy()

    if len(potential_anchors) > 100000:
        # Sample every nth record within geographic bins
        potential_anchors['lat_bin'] = pd.cut(potential_anchors['latitude'], bins=50)
        potential_anchors['lon_bin'] = pd.cut(potential_anchors['longitude'], bins=50)
        
        sampled_data = []
        target_per_bin = max(1, 100000 // 2500)  # 2500 = 50*50 bins
        
        for name, group in potential_anchors.groupby(['lat_bin', 'lon_bin'], observed=True):
            if len(group) > target_per_bin:
                # Take every nth record to maintain temporal distribution
                n = len(group) // target_per_bin
                sampled_data.append(group.iloc[::n][:target_per_bin])
            else:
                sampled_data.append(group)
        
        potential_anchors = pd.concat(sampled_data)
        print(f"Sampled down to {len(potential_anchors)} records")

    # Apply DBSCAN
    coords = np.radians(potential_anchors[['latitude', 'longitude']].values)
    
    dbscan = DBSCAN(
        eps=0.003,  # ~300m radius (adjust based on your region)
        min_samples=8,  # Minimum vessels to consider an anchorage
        metric='haversine',
        algorithm='ball_tree',
        n_jobs=-1
    )
    
    clusters = dbscan.fit_predict(coords)
    potential_anchors['cluster'] = clusters
    
    return potential_anchors

def grid_cluster_sampling(df, grid_size_km=5, samples_per_cell=1000):
    grid_size_deg = grid_size_km / 111.0  # 1 degree ≈ 111 km
    # Create grid cells
    df['lat_cell'] = (df['latitude'] / grid_size_deg).astype(int)
    df['lon_cell'] = (df['longitude'] / grid_size_deg).astype(int)
    df['cell_id'] = df['lat_cell'].astype(str) + '_' + df['lon_cell'].astype(str)

    cell_counts = df['cell_id'].value_counts()

    # Select cells with high vessel density (likely anchorage areas)
    high_density_cells = cell_counts[cell_counts >= 50].index  # Adjust threshold

    sampled_data = []
    for cell in high_density_cells:
        cell_data = df[df['cell_id'] == cell]
        if len(cell_data) > samples_per_cell:
            sampled_data.append(cell_data.sample(samples_per_cell))
        else:
            sampled_data.append(cell_data)
    
    return pd.concat(sampled_data).drop(['lat_cell', 'lon_cell', 'cell_id'], axis=1)

def anchorage_focused_sampling(df, max_samples=50000):
    anchoring_conditions = (
        (df['speed'] < 2.0) 
    )
    df_anchoring = df[anchoring_conditions].copy()
    
    if len(df_anchoring) <= max_samples:
        return df_anchoring
    
    return grid_cluster_sampling(df_anchoring, 
                                grid_size_km=3, 
                                samples_per_cell=min(1000, max_samples//50))


def main():
    data_path = r"/home/thang_sinay/unlocode/data/draft_data/ESMOT.csv"
    output_path = r"/home/thang_sinay/unlocode/data/draft_data"
    df = pd.read_csv(data_path, index_col=0)
    # clustered_data, polygons = find_anchorages(df,"cluster_sampling")
    clustered_data, polygons = find_anchorages(df)
    print(f"generate {len(polygons)} clusters")
    visualize_anchorages(df, clustered_data, polygons, data_path, output_path)
    print(f"find your port in html format in folder: {output_path}")


if __name__ == "__main__":
    main()
