import os
import glob
import pandas as pd
import csv
import json
from typing import List, Dict, Optional

class extract_UNLOCODE:
    def __init__(self, csv_file_paths: List[str]):
        self.csv_file_paths = csv_file_paths if isinstance(csv_file_paths, list) else [csv_file_paths]
        self.data = []

    def extract_data(self):
        total_files = len(self.csv_file_paths)
        for file_idx, csv_file_path in enumerate(self.csv_file_paths):
            print(f"Processing file {file_idx + 1}/{total_files}: {csv_file_path}")
            
            with open(csv_file_path, 'r', encoding='latin-1', errors='ignore') as file:
                csv_reader = csv.reader(file)
                for row in csv_reader:
                    if len(row[2]) >= 3:
                        location_data = self._parse_location_row(row)
                        self.data.append(location_data)

        return pd.DataFrame(self.data)
    
    def _parse_location_row(self, row):
        """
        Parse location data row
        """
        try:
            while len(row) < 13:
                row.append('')
            location_data = {
                    'change_indicator':row[0],
                    'country_code': row[1].strip(),
                    'location_code': row[2].strip(),
                    'location_name': row[3].strip(),
                    'name_wo_diacritics': row[4].strip(),
                    'subdivision': row[5].strip(),
                    'function': row[6].strip(),
                    'status': row[7].strip(),
                    'date': row[8].strip(),
                    'iata': row[9].strip(),
                    'coordinates': row[10].strip(),
                    'remarks': row[11].strip() if len(row) > 10 else ''
                }
            location_data['locode'] = f"{location_data['country_code']}{location_data['location_code']}"
                
            return location_data
        except (IndexError, AttributeError):
            return None
        
    def filter_ports(self, df):
        """
        Filter data to include only ports and harbors
        Function codes: 1 = Port, 
                        2 = Rail terminal, 
                        3 = Road terminal, 
                        4 = Airport, 
                        5 = Postal exchange, 
                        6 = Inland clearance depot, 
                        7 = Fixed transport functions, 
                        B = Border crossing
        """
        # Filter for locations with port functions (function code contains '1')
        ports_df = df[df['function'].str.contains('1', na=False)]
        change_ports = ports_df[ports_df['change_indicator'].notna() & (ports_df['change_indicator'].str.strip() != '')]
        return ports_df, change_ports
    
    def export_to_csv(self, df, output_file):
        """
        Export cleaned data to CSV file
        """
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Data exported to {output_file}")

    
    def get_statistics(self, df):
        """
        Get basic statistics about the extracted data
        """
        ports_df, change_ports = self.filter_ports(df)
        stats = {
            'total_locations': len(df),
            'total_countries': df['country_code'].nunique(),
            'countries_list': sorted(df['country_code'].unique()),
            'ports_only': len(df[df['function'].str.contains('1', na=False)]) if not df.empty else 0,
            'unique_locode_port': ports_df['locode'].nunique(),
            'port_status_change':len(change_ports)
        }
        return stats
    
class extract_Shipnext:
    def __init__(self, api_url_list, data):
        self.api_url_list = api_url_list
        self.data = data

    def export_to_txt(self, output_file):
        df = pd.DataFrame(self.api_url_list, columns=['api_port_name'])
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved API URL to {output_file}")

    def export_to_json(self, output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        print(f"Saved to {output_file}")

    