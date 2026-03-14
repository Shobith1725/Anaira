-- ============================================================
-- ANAIRA Complete Database Schema
-- Paste entire file into Supabase SQL Editor → Run
-- Builds ALL tables + seeds all demo data in one shot
-- ============================================================


-- ── 1. CALLERS ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS callers (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name           text NOT NULL DEFAULT 'Unknown',
    phone_hash     text UNIQUE,
    preferred_lang text DEFAULT 'en',
    created_at     timestamptz DEFAULT now()
);

-- ── 2. DRIVERS ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drivers (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_code    text UNIQUE NOT NULL,
    vehicle_type   text DEFAULT 'bike',
    caller_id      uuid REFERENCES callers(id),
    active_shift   boolean DEFAULT false,
    created_at     timestamptz DEFAULT now()
);

-- ── 3. SHIPMENTS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shipments (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tracking_number  text UNIQUE NOT NULL,
    driver_id        uuid REFERENCES drivers(id),
    status           text DEFAULT 'pending',
    destination      text,
    recipient_name   text,
    priority_flag    boolean DEFAULT false,
    cargo_type       text DEFAULT 'General',
    delivered_at     timestamptz,
    created_at       timestamptz DEFAULT now()
);

-- ── 4. ROUTES ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS routes (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    route_code         text UNIQUE NOT NULL,
    assigned_driver_id uuid REFERENCES drivers(id),
    waypoints          jsonb DEFAULT '[]',
    status             text DEFAULT 'active',
    created_at         timestamptz DEFAULT now()
);

-- ── 5. LOGISTICS EVENTS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS logistics_events (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id  text,
    event_type   text NOT NULL,
    payload      text,
    created_at   timestamptz DEFAULT now()
);

-- ── 6. APPOINTMENTS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id  text NOT NULL,
    caller_id    uuid REFERENCES callers(id),
    slot_time    text NOT NULL,
    status       text DEFAULT 'available',
    notes        text DEFAULT '',
    created_at   timestamptz DEFAULT now()
);

-- ── 7. INTERACTIONS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interactions (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   text,
    caller_id    uuid REFERENCES callers(id),
    driver_id    uuid REFERENCES drivers(id),
    mode         text DEFAULT 'logistics',
    outcome      text,
    duration_ms  integer,
    created_at   timestamptz DEFAULT now()
);

-- ── 8. WAREHOUSES ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warehouses (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_code   text UNIQUE NOT NULL,
    name             text NOT NULL,
    address          text NOT NULL,
    city             text DEFAULT 'Bengaluru',
    phone            text,
    manager_name     text,
    capacity_units   integer,
    created_at       timestamptz DEFAULT now()
);

-- ── 9. PRODUCTS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text UNIQUE NOT NULL,
    category    text,
    unit        text DEFAULT 'units',
    created_at  timestamptz DEFAULT now()
);

-- ── 10. INVENTORY ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_code   text NOT NULL REFERENCES warehouses(warehouse_code),
    product_id       uuid NOT NULL REFERENCES products(id),
    quantity         integer NOT NULL DEFAULT 0,
    unit             text DEFAULT 'units',
    updated_at       timestamptz DEFAULT now(),
    UNIQUE(warehouse_code, product_id)
);

-- ── 11. DELIVERY ORDERS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS delivery_orders (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id            text UNIQUE NOT NULL,
    product_name        text NOT NULL,
    quantity            integer NOT NULL,
    unit                text DEFAULT 'units',
    from_warehouse_code text NOT NULL REFERENCES warehouses(warehouse_code),
    destination_address text NOT NULL,
    destination_city    text,
    assigned_driver_id  uuid,        -- no FK to avoid dependency issues
    priority            text DEFAULT 'normal',
    special_notes       text DEFAULT '',
    status              text DEFAULT 'pending',
    created_at          timestamptz DEFAULT now()
);


-- ============================================================
-- SEED DATA
-- ============================================================

-- Callers
INSERT INTO callers (id, name, phone_hash, preferred_lang) VALUES
  ('a1000000-0000-0000-0000-000000000001', 'Ravi Kumar',   'hash_ravi',   'en'),
  ('a1000000-0000-0000-0000-000000000002', 'Suresh Naik',  'hash_suresh', 'en'),
  ('a1000000-0000-0000-0000-000000000003', 'Priya Sharma', 'hash_priya',  'en'),
  ('a1000000-0000-0000-0000-000000000004', 'Arjun Mehta',  'hash_arjun',  'en')
ON CONFLICT (id) DO NOTHING;

-- Drivers
INSERT INTO drivers (id, driver_code, vehicle_type, caller_id, active_shift) VALUES
  ('b2000000-0000-0000-0000-000000000001', 'DRV-001', 'bike',  'a1000000-0000-0000-0000-000000000001', true),
  ('b2000000-0000-0000-0000-000000000002', 'DRV-002', 'van',   'a1000000-0000-0000-0000-000000000002', true),
  ('b2000000-0000-0000-0000-000000000003', 'DRV-003', 'truck', 'a1000000-0000-0000-0000-000000000003', true),
  ('b2000000-0000-0000-0000-000000000004', 'DRV-004', 'bike',  'a1000000-0000-0000-0000-000000000004', false)
ON CONFLICT (id) DO NOTHING;

-- Shipments
INSERT INTO shipments (id, tracking_number, driver_id, status, destination, recipient_name, priority_flag, cargo_type) VALUES
  ('c3000000-0000-0000-0000-000000000001', 'TRK-101', 'b2000000-0000-0000-0000-000000000001', 'in_transit',       '14 MG Road, Indiranagar',       'Anita Rao',    false, 'General'),
  ('c3000000-0000-0000-0000-000000000002', 'TRK-102', 'b2000000-0000-0000-0000-000000000001', 'out_for_delivery', '7 Koramangala 5th Block',       'Vijay Singh',  true,  'Medical'),
  ('c3000000-0000-0000-0000-000000000003', 'TRK-103', 'b2000000-0000-0000-0000-000000000002', 'pending',          '22 Whitefield Main Road',       'Deepa Nair',   false, 'General'),
  ('c3000000-0000-0000-0000-000000000004', 'TRK-104', 'b2000000-0000-0000-0000-000000000002', 'in_transit',       '3 HSR Layout Sector 4',         'Kiran Patil',  true,  'Medical'),
  ('c3000000-0000-0000-0000-000000000005', 'TRK-105', 'b2000000-0000-0000-0000-000000000003', 'pending',          '55 Jayanagar 4th T Block',      'Meena Iyer',   false, 'General'),
  ('c3000000-0000-0000-0000-000000000006', 'TRK-106', 'b2000000-0000-0000-0000-000000000003', 'out_for_delivery', '10 Rajajinagar Industrial Area', 'Sanjay Gupta', false, 'General')
ON CONFLICT (id) DO NOTHING;

-- Routes (waypoints stored as JSONB)
INSERT INTO routes (route_code, assigned_driver_id, status, waypoints) VALUES
  ('RTE-001', 'b2000000-0000-0000-0000-000000000001', 'active', '[
    {"stop": 1, "address": "12 Industrial Layout, Peenya",        "type": "pickup",   "shipment": "TRK-101"},
    {"stop": 2, "address": "14 MG Road, Indiranagar",             "type": "delivery", "shipment": "TRK-101"},
    {"stop": 3, "address": "7 Koramangala 5th Block",             "type": "delivery", "shipment": "TRK-102"}
  ]'),
  ('RTE-002', 'b2000000-0000-0000-0000-000000000002', 'active', '[
    {"stop": 1, "address": "45 Hebbal Ring Road, Hebbal",         "type": "pickup",   "shipment": "TRK-103"},
    {"stop": 2, "address": "22 Whitefield Main Road",             "type": "delivery", "shipment": "TRK-103"},
    {"stop": 3, "address": "3 HSR Layout Sector 4",               "type": "delivery", "shipment": "TRK-104"}
  ]'),
  ('RTE-003', 'b2000000-0000-0000-0000-000000000003', 'active', '[
    {"stop": 1, "address": "8 Bannerghatta Road, JP Nagar",       "type": "pickup",   "shipment": "TRK-105"},
    {"stop": 2, "address": "55 Jayanagar 4th T Block",            "type": "delivery", "shipment": "TRK-105"},
    {"stop": 3, "address": "10 Rajajinagar Industrial Area",      "type": "delivery", "shipment": "TRK-106"}
  ]')
ON CONFLICT (route_code) DO NOTHING;

-- Appointments (receptionist mode demo)
INSERT INTO appointments (business_id, slot_time, status) VALUES
  ('BIZ-001', '2026-03-16 09:00:00', 'available'),
  ('BIZ-001', '2026-03-16 10:00:00', 'available'),
  ('BIZ-001', '2026-03-16 11:00:00', 'available'),
  ('BIZ-001', '2026-03-16 14:00:00', 'available'),
  ('BIZ-001', '2026-03-16 15:00:00', 'available')
ON CONFLICT DO NOTHING;

-- Warehouses
INSERT INTO warehouses (warehouse_code, name, address, city, phone, manager_name, capacity_units) VALUES
  ('WH-01', 'Central Depot',       '12, Industrial Layout, Peenya',  'Bengaluru', '+91-80-2222-0101', 'Ramesh Kumar', 5000),
  ('WH-02', 'North Bengaluru Hub', '45, Hebbal Ring Road, Hebbal',   'Bengaluru', '+91-80-2222-0202', 'Suresh Naik',  3000),
  ('WH-03', 'South Bengaluru Hub', '8, Bannerghatta Road, JP Nagar', 'Bengaluru', '+91-80-2222-0303', 'Priya Sharma', 4000)
ON CONFLICT (warehouse_code) DO NOTHING;

-- Products
INSERT INTO products (name, category, unit) VALUES
  ('Paracetamol',            'Medicine',       'boxes'),
  ('Insulin',                'Medicine',       'vials'),
  ('Bandages',               'Medical Supply', 'rolls'),
  ('Surgical Gloves',        'Medical Supply', 'boxes'),
  ('IV Fluids',              'Medicine',       'bags'),
  ('Amoxicillin',            'Medicine',       'strips'),
  ('Blood Pressure Monitor', 'Equipment',      'units'),
  ('Syringes',               'Medical Supply', 'boxes'),
  ('Oxygen Cylinders',       'Equipment',      'cylinders'),
  ('Sanitizer',              'Hygiene',        'bottles')
ON CONFLICT (name) DO NOTHING;

-- Inventory (WH-01)
INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-01', id, 500, 'boxes'  FROM products WHERE name = 'Paracetamol'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-01', id, 120, 'vials'  FROM products WHERE name = 'Insulin'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-01', id, 300, 'rolls'  FROM products WHERE name = 'Bandages'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-01', id, 80,  'boxes'  FROM products WHERE name = 'Surgical Gloves'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-01', id, 40,  'bags'   FROM products WHERE name = 'IV Fluids'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

-- Inventory (WH-02)
INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-02', id, 200, 'boxes'      FROM products WHERE name = 'Paracetamol'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-02', id, 30,  'vials'      FROM products WHERE name = 'Insulin'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-02', id, 150, 'strips'     FROM products WHERE name = 'Amoxicillin'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-02', id, 60,  'units'      FROM products WHERE name = 'Blood Pressure Monitor'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-02', id, 25,  'cylinders'  FROM products WHERE name = 'Oxygen Cylinders'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

-- Inventory (WH-03)
INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-03', id, 400, 'boxes'    FROM products WHERE name = 'Paracetamol'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-03', id, 200, 'boxes'    FROM products WHERE name = 'Surgical Gloves'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-03', id, 500, 'boxes'    FROM products WHERE name = 'Syringes'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-03', id, 350, 'bottles'  FROM products WHERE name = 'Sanitizer'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

INSERT INTO inventory (warehouse_code, product_id, quantity, unit)
SELECT 'WH-03', id, 20,  'bags'     FROM products WHERE name = 'IV Fluids'
ON CONFLICT (warehouse_code, product_id) DO NOTHING;

-- Delivery Orders
INSERT INTO delivery_orders (order_id, product_name, quantity, unit, from_warehouse_code, destination_address, destination_city, assigned_driver_id, priority, special_notes, status) VALUES
  ('ORD-001', 'Paracetamol',     200, 'boxes',     'WH-01', '14, MG Road, Indiranagar',         'Bengaluru', 'b2000000-0000-0000-0000-000000000001', 'high',   'Handle with care. Deliver before noon.', 'pending'),
  ('ORD-002', 'Insulin',          50, 'vials',     'WH-01', '7, Koramangala 5th Block',         'Bengaluru', 'b2000000-0000-0000-0000-000000000001', 'urgent', 'Cold chain required. Keep below 8C.',   'pending'),
  ('ORD-003', 'Surgical Gloves', 100, 'boxes',     'WH-02', '22, Whitefield Main Road',         'Bengaluru', 'b2000000-0000-0000-0000-000000000002', 'normal', '',                                      'pending'),
  ('ORD-004', 'Amoxicillin',      80, 'strips',    'WH-02', '3, HSR Layout, Sector 4',          'Bengaluru', 'b2000000-0000-0000-0000-000000000002', 'normal', 'Signature required on delivery.',       'pending'),
  ('ORD-005', 'IV Fluids',        30, 'bags',      'WH-03', '55, Jayanagar 4th T Block',        'Bengaluru', 'b2000000-0000-0000-0000-000000000003', 'high',   'Fragile. Do not stack.',                'pending'),
  ('ORD-006', 'Syringes',        200, 'boxes',     'WH-03', '10, Rajajinagar Industrial Area',  'Bengaluru', 'b2000000-0000-0000-0000-000000000003', 'normal', '',                                      'pending'),
  ('ORD-007', 'Oxygen Cylinders', 10, 'cylinders', 'WH-02', '1, Hennur Road, Kalyan Nagar',     'Bengaluru', 'b2000000-0000-0000-0000-000000000002', 'urgent', 'Extremely fragile. Use padded vehicle.','pending')
ON CONFLICT (order_id) DO NOTHING;