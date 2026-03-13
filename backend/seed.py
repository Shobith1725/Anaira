"""
Run this ONCE after setting up Supabase to populate demo data.
Usage: python seed.py
"""

import asyncio
from services.supabase_client import _db


def seed():
    db = _db()

    print("Seeding warehouses...")
    db.table("businesses").upsert([
        {"id": "a1000000-0000-0000-0000-000000000001",
         "name": "Central Depot", "location": "Whitefield, Bengaluru",
         "warehouse_code": "WH-01", "speciality": "General cargo"},
        {"id": "a1000000-0000-0000-0000-000000000002",
         "name": "Cold Chain Facility", "location": "Peenya, Bengaluru",
         "warehouse_code": "WH-02", "speciality": "Perishables and pharma"},
        {"id": "a1000000-0000-0000-0000-000000000003",
         "name": "Electronics Hub", "location": "Electronic City, Bengaluru",
         "warehouse_code": "WH-03", "speciality": "High-value fragile items"},
    ]).execute()

    print("Seeding callers...")
    db.table("callers").upsert([
        {"id": "b1000000-0000-0000-0000-000000000001",
         "phone_hash": "hash_ramesh", "name": "Ramesh Kumar", "preferred_lang": "en"},
        {"id": "b1000000-0000-0000-0000-000000000002",
         "phone_hash": "hash_priya", "name": "Priya Sharma", "preferred_lang": "en"},
        {"id": "b1000000-0000-0000-0000-000000000003",
         "phone_hash": "hash_arjun", "name": "Arjun Nair", "preferred_lang": "en"},
        {"id": "b1000000-0000-0000-0000-000000000004",
         "phone_hash": "hash_sunita", "name": "Sunita Das", "preferred_lang": "en"},
    ]).execute()

    print("Seeding drivers...")
    db.table("drivers").upsert([
        {"id": "c1000000-0000-0000-0000-000000000001",
         "caller_id": "b1000000-0000-0000-0000-000000000001",
         "driver_code": "DRV-01", "vehicle_type": "Tata Ace Van",
         "license_plate": "KA-01-AB-1234", "active_shift": True,
         "warehouse_id": "a1000000-0000-0000-0000-000000000001"},
        {"id": "c1000000-0000-0000-0000-000000000002",
         "caller_id": "b1000000-0000-0000-0000-000000000002",
         "driver_code": "DRV-02", "vehicle_type": "Mahindra Truck",
         "license_plate": "KA-02-CD-5678", "active_shift": True,
         "warehouse_id": "a1000000-0000-0000-0000-000000000002"},
        {"id": "c1000000-0000-0000-0000-000000000003",
         "caller_id": "b1000000-0000-0000-0000-000000000003",
         "driver_code": "DRV-03", "vehicle_type": "Hero Bike",
         "license_plate": "KA-03-EF-9012", "active_shift": True,
         "warehouse_id": "a1000000-0000-0000-0000-000000000003"},
        {"id": "c1000000-0000-0000-0000-000000000004",
         "caller_id": "b1000000-0000-0000-0000-000000000004",
         "driver_code": "DRV-04", "vehicle_type": "Tata Ace Van",
         "license_plate": "KA-04-GH-3456", "active_shift": True,
         "warehouse_id": "a1000000-0000-0000-0000-000000000001"},
    ]).execute()

    print("Seeding routes...")
    db.table("routes").upsert([
        {"id": "d1000000-0000-0000-0000-000000000001",
         "route_code": "RTE-A",
         "assigned_driver_id": "c1000000-0000-0000-0000-000000000001",
         "warehouse_id": "a1000000-0000-0000-0000-000000000001",
         "status": "active",
         "waypoints": [
             {"stop": 1, "address": "WH-01 Whitefield Depot", "type": "pickup"},
             {"stop": 2, "address": "14 Brigade Road, Koramangala", "type": "delivery", "shipment": "TRK-124"},
             {"stop": 3, "address": "Hebbal Flyover Junction", "type": "delivery", "shipment": "TRK-088"},
         ]},
        {"id": "d1000000-0000-0000-0000-000000000002",
         "route_code": "RTE-B",
         "assigned_driver_id": "c1000000-0000-0000-0000-000000000002",
         "warehouse_id": "a1000000-0000-0000-0000-000000000002",
         "status": "active",
         "waypoints": [
             {"stop": 1, "address": "WH-02 Peenya Cold Facility", "type": "pickup"},
             {"stop": 2, "address": "Indiranagar 100ft Road", "type": "delivery", "shipment": "TRK-207"},
             {"stop": 3, "address": "Jayanagar 4th Block", "type": "delivery", "shipment": "TRK-055"},
         ]},
        {"id": "d1000000-0000-0000-0000-000000000003",
         "route_code": "RTE-C",
         "assigned_driver_id": "c1000000-0000-0000-0000-000000000003",
         "warehouse_id": "a1000000-0000-0000-0000-000000000003",
         "status": "active",
         "waypoints": [
             {"stop": 1, "address": "WH-03 Electronic City Hub", "type": "pickup"},
             {"stop": 2, "address": "MG Road, Commercial Street", "type": "delivery", "shipment": "TRK-301"},
         ]},
        {"id": "d1000000-0000-0000-0000-000000000004",
         "route_code": "RTE-D",
         "assigned_driver_id": "c1000000-0000-0000-0000-000000000004",
         "warehouse_id": "a1000000-0000-0000-0000-000000000001",
         "status": "active",
         "waypoints": [
             {"stop": 1, "address": "WH-01 Whitefield Depot", "type": "pickup"},
             {"stop": 2, "address": "ITPL Road, Whitefield", "type": "delivery", "shipment": "TRK-412"},
             {"stop": 3, "address": "HSR Layout Sector 2", "type": "delivery", "shipment": "TRK-199"},
         ]},
    ]).execute()

    print("Seeding shipments...")
    db.table("shipments").upsert([
        {"tracking_number": "TRK-124",
         "driver_id": "c1000000-0000-0000-0000-000000000001",
         "route_id": "d1000000-0000-0000-0000-000000000001",
         "warehouse_id": "a1000000-0000-0000-0000-000000000001",
         "origin": "WH-01 Whitefield", "destination": "14 Brigade Road, Koramangala",
         "recipient_name": "Arun Mehta", "cargo_type": "General goods",
         "priority_flag": False, "status": "in_transit"},
        {"tracking_number": "TRK-088",
         "driver_id": "c1000000-0000-0000-0000-000000000001",
         "route_id": "d1000000-0000-0000-0000-000000000001",
         "warehouse_id": "a1000000-0000-0000-0000-000000000001",
         "origin": "WH-01 Whitefield", "destination": "Hebbal Flyover Junction",
         "recipient_name": "Deepa Rao", "cargo_type": "General goods",
         "priority_flag": False, "status": "in_transit"},
        {"tracking_number": "TRK-207",
         "driver_id": "c1000000-0000-0000-0000-000000000002",
         "route_id": "d1000000-0000-0000-0000-000000000002",
         "warehouse_id": "a1000000-0000-0000-0000-000000000002",
         "origin": "WH-02 Peenya", "destination": "Indiranagar 100ft Road",
         "recipient_name": "City Hospital", "cargo_type": "Pharma cold chain",
         "priority_flag": True, "status": "in_transit"},
        {"tracking_number": "TRK-055",
         "driver_id": "c1000000-0000-0000-0000-000000000002",
         "route_id": "d1000000-0000-0000-0000-000000000002",
         "warehouse_id": "a1000000-0000-0000-0000-000000000002",
         "origin": "WH-02 Peenya", "destination": "Jayanagar 4th Block",
         "recipient_name": "Fresh Mart Store", "cargo_type": "Perishables",
         "priority_flag": False, "status": "in_transit"},
        {"tracking_number": "TRK-301",
         "driver_id": "c1000000-0000-0000-0000-000000000003",
         "route_id": "d1000000-0000-0000-0000-000000000003",
         "warehouse_id": "a1000000-0000-0000-0000-000000000003",
         "origin": "WH-03 Electronic City", "destination": "MG Road Commercial Street",
         "recipient_name": "TechZone Retail", "cargo_type": "Electronics",
         "priority_flag": True, "status": "pending"},
        {"tracking_number": "TRK-412",
         "driver_id": "c1000000-0000-0000-0000-000000000004",
         "route_id": "d1000000-0000-0000-0000-000000000004",
         "warehouse_id": "a1000000-0000-0000-0000-000000000001",
         "origin": "WH-01 Whitefield", "destination": "ITPL Road, Whitefield",
         "recipient_name": "Kavya Singh", "cargo_type": "General goods",
         "priority_flag": False, "status": "out_for_delivery"},
        {"tracking_number": "TRK-199",
         "driver_id": "c1000000-0000-0000-0000-000000000004",
         "route_id": "d1000000-0000-0000-0000-000000000004",
         "warehouse_id": "a1000000-0000-0000-0000-000000000003",
         "origin": "WH-03 Electronic City", "destination": "HSR Layout Sector 2",
         "recipient_name": "Rohan Verma", "cargo_type": "Electronics",
         "priority_flag": True, "status": "pending"},
    ]).execute()

    print("Seed complete. All demo data loaded.")


if __name__ == "__main__":
    seed()