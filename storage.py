import json
import csv
from typing import Dict
from collections import defaultdict
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from contextlib import contextmanager

Base = declarative_base()

class Database_Config:
    def __init__(self, config):
        self.config = config
        self.database_uri = self._get_database_uri()

    def _get_database_uri(self):
        if 'URI' in self.config:
            return self.config['URI']
        
        # Construct URI from individual components
        dbname = self.config.get('dbname', 'test0')
        user = self.config.get('user', 'postgres')
        password = self.config.get('password', '1234')
        host = self.config.get('host', '10.255.255.254')
        port = self.config.get('port', '5432')
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
class UNlocode(Base):
    __tablename__ = "unlocode_ports"
    locode = Column(String, primary_key=True)
    change_indicator = Column(String)
    location_name = Column(String)
    name_wo_diacritics = Column(String)
    subdivision = Column(String)
    function = Column(String)
    status = Column(String)
    date = Column(String(4))
    coordinates = Column(String)
    remarks = Column(Text)

    ship_next = relationship("Shipnext", back_populates='unLoCode')

class Shipnext(Base):
    __tablename__ = "shipnext_data"
    id = Column(String, primary_key=True)
    name = Column(String)
    country_id = Column(String)
    country_name = Column(String)
    longitude = Column(Float)
    latitude = Column(Float)
    site = Column(String)
    description = Column(Text)

    unLoCode_id = Column(String, ForeignKey('unlocode_ports.locode'), nullable=True)

    unLoCode = relationship("UNlocode", back_populates='ship_next')
    lifts_cranes = relationship('Lifts_Cranes', back_populates='port', cascade='all, delete-orphan')
    port_limitations = relationship('Port_Limitation', back_populates='port', cascade='all, delete-orphan')
    facilities = relationship('Facility', back_populates='port', cascade='all, delete-orphan')
    warehouse = relationship('Warehouse', back_populates='port', cascade='all, delete-orphan')
    geo_feature = relationship('GeoFeature', back_populates='port', cascade='all, delete-orphan')
    service_provider = relationship('Service_Provider', back_populates='port', cascade='all, delete-orphan')

class Lifts_Cranes(Base):
    __tablename__ = "lifts_cranes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(String, ForeignKey('shipnext_data.id'), nullable=False)
    range_label = Column(String)  # e.g. "0-24", "25-49"
    checked = Column(Boolean)
    details = Column(JSONB)  # Store details as JSON array

    port = relationship("Shipnext", back_populates="lifts_cranes")

class Port_Limitation(Base):
    __tablename__ = "port_limitations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(String, ForeignKey('shipnext_data.id'), nullable=False)
    max_type = Column(String)
    details = Column(Float)

    port = relationship("Shipnext", back_populates="port_limitations")

class Facility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(String, ForeignKey('shipnext_data.id'), nullable=False)
    type = Column(String) # e.g. dryBulk, container, shipyard
    available = Column(Boolean, default=False)

    port = relationship("Shipnext", back_populates="facilities")

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(String, ForeignKey('shipnext_data.id'), nullable=False)
    wh_type = Column(String)
    available = Column(Boolean, default=False)

    port = relationship("Shipnext", back_populates="warehouse")

class GeoFeature(Base):
    __tablename__ = "geo_feature"
    id = Column(String, primary_key=True)  # Use _id from your data
    port_id = Column(String, ForeignKey('shipnext_data.id'), nullable=False)
    name = Column(String)
    feature_type = Column(String)  # e.g. "Feature"
    geometry_type = Column(String)  # e.g. "Polygon"
    coordinates = Column(JSONB)  # Store raw coordinates as JSON
    entity_type = Column(String)  # e.g. "Port", "Terminal", "Berth"
    terminal_id = Column(String, nullable=True)
    berth_id = Column(String, nullable=True)

    port = relationship("Shipnext", back_populates="geo_feature")

class Service_Provider(Base):
    __tablename__ = "service_provider"
    id = Column(String, primary_key=True)
    port_id = Column(String, ForeignKey('shipnext_data.id'), nullable=False)
    name = Column(String)
    email = Column(JSONB)

    port = relationship("Shipnext", back_populates="service_provider")

class Database_Manager:
    def __init__(self, config):
        self.config = Database_Config(config)
        self.engine = None
        self.Session = None
        self._initialize_database()

    def _initialize_database(self):
        try:
            self.engine = create_engine(self.config.database_uri)
            self.Session = sessionmaker(bind=self.engine)
            print("Database engine initialized successfully")
        except Exception as e:
            raise Exception(f"Failed to initialize database: {e}")

    def create_tables(self):
        try:
            Base.metadata.create_all(self.engine)
            print("All tables created successfully")
        except Exception as e:
            raise Exception(f"Failed to create tables: {e}")
       
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Database session error: {e}")
        finally:
            session.close()

    def insert_unlocode(self, unlocode_records):
        try:
            with self.get_session() as session:
                for row in unlocode_records.values():
                    port = UNlocode(
                        locode=row['locode'],
                        change_indicator=row['change_indicator'],
                        location_name=row['location_name'],
                        name_wo_diacritics=row['name_wo_diacritics'],
                        subdivision=row['subdivision'],
                        function=row['function'],
                        status=row['status'],
                        date=row['date'],
                        coordinates=row['coordinates'],
                        remarks=row['remarks']
                    )
                    session.merge(port)
        except Exception as e:
            raise Exception(f"Error inserting UNLoCode data: {e}")
        
    def insert_shipnext(self,shipnext_records):
        try:
            with self.get_session() as session:
                for item in shipnext_records:
                    unlocode_value = item.get("unLoCode")
                    if not unlocode_value:
                        unlocode_value = None

                    port = Shipnext(
                        id = item['_id'],
                        name = item['name'],
                        country_id = item['country']['_id'],
                        country_name = item['country']['name'],
                        longitude = item['coordinates'][0], 
                        latitude = item['coordinates'][1],
                        site = item.get('site', ''),
                        description = item.get('additionalDescription', ''),
                        unLoCode_id = unlocode_value
                    )
                    if item.get('liftsCranes', ""):
                        self.insert_lift_crane(item['liftsCranes'], port)
                    if item.get('portLimitations', ""):
                        self.insert_port_limitation(item['portLimitations'], port)
                    if item.get('facilities', ""):
                        self.insert_facility(item['facilities'],port)
                    if item.get('warehouses', ""):
                        self.insert_warehouse(item['warehouses'],port)
                    if item.get('featureCollection', ""):
                        self.insert_geo_feature(item['featureCollection']['features'],port)
                    if item.get('serviceProviders', ""):
                        self.insert_service_provider(item['serviceProviders'],port)
                    
                    session.merge(port)
        except Exception as e:
            raise Exception(f"Error inserting Shipnext data: {e}")
    
    def insert_lift_crane(self,lifts_cranes_data, port):
        try:            
            for range_label, crane_data in lifts_cranes_data.items():
                crane = Lifts_Cranes(
                    range_label = range_label,
                    checked = crane_data['checked'],
                    details=crane_data['details'],
                    port=port
                )
                port.lifts_cranes.append(crane)
        except Exception as e:
            raise Exception(f"Error inserting lift crane Shipnext data: {e}")
    
    def insert_port_limitation(self,limitation_data, port):
        try:            
            for limit_type, detail in limitation_data.items():
                limitation = Port_Limitation(
                    max_type = limit_type,
                    details = detail,
                    port=port
                )
                port.port_limitations.append(limitation)
        except Exception as e:
            raise Exception(f"Error inserting limitation Shipnext data: {e}")
        
    def insert_facility(self, facility_data, port):
        try:
            for facility_type, detail in facility_data.items():
                facility = Facility(
                    type = facility_type,
                    available = detail,
                    port = port
                )
                port.facilities.append(facility)
        except Exception as e:
            raise Exception(f"Error inserting facility Shipnext data: {e}")

    def insert_warehouse(self, warehouse_data, port):
        try:
            for warehouse_type, detail in warehouse_data.items():
                warehouse = Warehouse(
                    wh_type = warehouse_type,
                    available = detail, 
                    port = port
                )
                port.warehouse.append(warehouse)
        except Exception as e:
            raise Exception(f"Error inserting warehouse Shipnext data: {e}")
    
    def insert_geo_feature(self, geo_feature_data, port):
        try:
            for item in geo_feature_data:
                geo_feature = GeoFeature(
                    id = item['_id'],
                    name = item['properties']['name'],
                    feature_type = item['type'],
                    geometry_type = item['geometry']['type'],
                    coordinates = item['geometry']['coordinates'],
                    entity_type = item['properties'].get('type', ""),
                    terminal_id = item['properties'].get('terminalID', ""),
                    berth_id = item['properties'].get('berthID', ""),

                    port = port
                )
                port.geo_feature.append(geo_feature)
        except Exception as e:
            raise Exception(f"Error inserting geo feature Shipnext data: {e}")
    
    def insert_service_provider(self,service_provider_data, port):
        try:            
            for item in service_provider_data:
                provider = Service_Provider(
                    id = item['_id'],
                    name = item.get('name', ""),
                    email = item.get('emails', ""),
                    port=port
                )
                port.service_provider.append(provider)
        except Exception as e:
            raise Exception(f"Error inserting service provider Shipnext data: {e}")
       