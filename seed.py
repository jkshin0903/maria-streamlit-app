# -*- coding: utf-8 -*-
"""
Schema extension + sample data seeding for the R&S Entertainment
Amusement Machine Asset Tracking & Management System.

Idempotent: adds missing columns / tables if absent, then truncates and
reloads deterministic sample data that matches the GP3 requirement scenario.
"""
import sys
import io
import random
from datetime import datetime, timedelta, date

import pymysql

from lib.db_config import get_connect_kwargs

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TODAY = date(2026, 5, 29)
random.seed(42)


def col_exists(cur, table, col):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name=%s AND column_name=%s",
        ("company", table, col))
    return cur.fetchone()[0] > 0


def table_exists(cur, table):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema=%s AND table_name=%s", ("company", table))
    return cur.fetchone()[0] > 0


def add_col(cur, table, col, ddl):
    if not col_exists(cur, table, col):
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN {ddl}")
        print(f"  + {table}.{col}")


def extend_schema(cur):
    print("Extending schema...")
    add_col(cur, "product", "manufacturer", "manufacturer VARCHAR(100) NULL")
    add_col(cur, "product", "machine_type", "machine_type VARCHAR(30) NULL")
    add_col(cur, "product", "list_price", "list_price DECIMAL(18,2) NULL")

    add_col(cur, "business_location", "manager_name", "manager_name VARCHAR(100) NULL")

    add_col(cur, "technician", "region", "region VARCHAR(50) NULL")
    add_col(cur, "technician", "phone", "phone VARCHAR(20) NULL")

    add_col(cur, "machine", "manufacturer", "manufacturer VARCHAR(100) NULL")
    add_col(cur, "machine", "machine_type", "machine_type VARCHAR(30) NULL")
    add_col(cur, "machine", "purchase_price", "purchase_price DECIMAL(18,2) NULL")
    add_col(cur, "machine", "purchase_date", "purchase_date DATETIME NULL")
    add_col(cur, "machine", "installation_date", "installation_date DATETIME NULL")
    add_col(cur, "machine", "disposal_date", "disposal_date DATETIME NULL")
    add_col(cur, "machine", "disposal_reason", "disposal_reason VARCHAR(100) NULL")

    add_col(cur, "contract", "revenue_share_pct", "revenue_share_pct DECIMAL(5,2) NULL")

    add_col(cur, "order", "scheduled_datetime", "scheduled_datetime DATETIME NULL")
    add_col(cur, "order", "signature", "signature VARCHAR(100) NULL")
    add_col(cur, "order", "notes", "notes VARCHAR(1000) NULL")
    add_col(cur, "order", "issuing_manager", "issuing_manager VARCHAR(100) NULL")

    if not table_exists(cur, "machine_repair"):
        cur.execute("""
            CREATE TABLE machine_repair (
                repair_id INT NOT NULL,
                serial_number INT NOT NULL,
                repair_date DATETIME NOT NULL,
                cost DECIMAL(18,2) NOT NULL,
                description VARCHAR(255) NULL,
                PRIMARY KEY (repair_id),
                KEY fk_machine_repair (serial_number),
                CONSTRAINT fk_machine_to_repair FOREIGN KEY (serial_number)
                    REFERENCES machine (serial_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        print("  + table machine_repair")

    if not table_exists(cur, "machine_revenue"):
        cur.execute("""
            CREATE TABLE machine_revenue (
                revenue_id INT NOT NULL,
                serial_number INT NOT NULL,
                revenue_month DATE NOT NULL,
                amount DECIMAL(18,2) NOT NULL,
                PRIMARY KEY (revenue_id),
                KEY fk_machine_revenue (serial_number),
                CONSTRAINT fk_machine_to_revenue FOREIGN KEY (serial_number)
                    REFERENCES machine (serial_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        print("  + table machine_revenue")

    if not table_exists(cur, "machine_location_hst"):
        cur.execute("""
            CREATE TABLE machine_location_hst (
                hst_id INT NOT NULL,
                serial_number INT NOT NULL,
                location_id INT NOT NULL,
                start_date DATETIME NOT NULL,
                end_date DATETIME NULL,
                performance_note VARCHAR(50) NULL,
                PRIMARY KEY (hst_id),
                KEY fk_mlh_machine (serial_number),
                KEY fk_mlh_loc (location_id),
                CONSTRAINT fk_mlh_to_machine FOREIGN KEY (serial_number)
                    REFERENCES machine (serial_number),
                CONSTRAINT fk_mlh_to_loc FOREIGN KEY (location_id)
                    REFERENCES business_location (location_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        print("  + table machine_location_hst")


def truncate_all(cur):
    print("Clearing existing data...")
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    for t in ["machine_revenue", "machine_repair", "machine_location_hst",
              "machine_contract_hst", "order", "machine", "invoice_item",
              "invoice", "purchase_order_item", "purchase_order",
              "purchase_request_item", "purchase_request", "contract",
              "vendor", "product", "technician", "business_location"]:
        cur.execute(f"TRUNCATE TABLE `{t}`")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")


# ---------------------------------------------------------------- data sets
VENDORS = [
    (1, "One Stop Amusement Distributing Company", "500 Industrial Pkwy, Chicago, IL 60607", "(312) 555-7100", "(312) 555-7101"),
    (2, "Midwest Coin Concepts Inc.", "84 Commerce Dr, Indianapolis, IN 46204", "(317) 555-3300", "(317) 555-3301"),
    (3, "Williams Electronics Distributing", "1200 Pinball Way, Chicago, IL 60618", "(312) 555-9200", "(312) 555-9201"),
    (4, "Rowe International Supply", "75 Jukebox Ln, Grand Rapids, MI 49503", "(616) 555-4400", "(616) 555-4401"),
]

PRODUCTS = [
    (101, "Jurassic Park Pinball", "Williams", "Pinball", 3200.00),
    (102, "Twilight Zone Pinball", "Bally", "Pinball", 3500.00),
    (103, "Addams Family Pinball", "Bally", "Pinball", 3300.00),
    (201, "8-Ball Pool Table", "Valley", "Pool Table", 1800.00),
    (202, "Coin-Op Pool Table Deluxe", "Valley", "Pool Table", 2100.00),
    (301, "CD Jukebox R-90", "Rowe", "Jukebox", 4200.00),
    (302, "Digital Jukebox NSM", "NSM", "Jukebox", 4500.00),
    (401, "Street Fighter II", "Capcom", "Video Game", 2600.00),
    (402, "Mortal Kombat", "Midway", "Video Game", 2800.00),
    (403, "NBA Jam", "Midway", "Video Game", 2700.00),
    (404, "Galaga Classic", "Namco", "Video Game", 1500.00),
]

# id, name, type, address, city, state, zip, phone, manager
LOCATIONS = [
    (1, "R&S Headquarters", "Headquarters", "100 Main St", "Lafayette", "IN", "47901", "(765) 555-0100", "Marge Brooks"),
    (2, "Central Warehouse", "Warehouse", "200 Depot Rd", "Lafayette", "IN", "47901", "(765) 555-0101", "Marge Brooks"),
    (3, "John's Pizza King", "Site", "15 College Ave", "Lafayette", "IN", "47904", "(765) 555-0111", "Mike Anderson"),
    (4, "Tippecanoe Tavern", "Site", "88 River Rd", "Lafayette", "IN", "47905", "(765) 555-0112", "Mike Anderson"),
    (5, "Mike's Bar & Grill", "Site", "300 Calhoun St", "Fort Wayne", "IN", "46802", "(260) 555-0120", "Mark Davis"),
    (6, "Coliseum Arcade", "Site", "410 Coliseum Blvd", "Fort Wayne", "IN", "46805", "(260) 555-0121", "Mark Davis"),
    (7, "Rensselaer Bowl", "Site", "22 Front St", "Rensselaer", "IN", "47978", "(219) 555-0130", "Foster Reed"),
    (8, "Jasper County Diner", "Site", "55 Cullen St", "Rensselaer", "IN", "47978", "(219) 555-0131", "Foster Reed"),
]
SITE_IDS = [3, 4, 5, 6, 7, 8]
WAREHOUSE_ID = 2

TECHS = [
    (1, "David Foster", "Lafayette", "(765) 555-0201"),
    (2, "Tom Reynolds", "Fort Wayne", "(260) 555-0202"),
    (3, "Carl Jensen", "Rensselaer", "(219) 555-0203"),
]

# contracts per site: id, location, share %, start, end, status
CONTRACTS = [
    (1, 3, 60.00, datetime(2022, 1, 15), datetime(2027, 1, 14), "Active"),
    (2, 4, 55.00, datetime(2022, 6, 1), datetime(2027, 5, 31), "Active"),
    (3, 5, 65.00, datetime(2021, 9, 1), datetime(2026, 8, 31), "Active"),
    (4, 6, 50.00, datetime(2023, 3, 1), datetime(2028, 2, 29), "Active"),
    (5, 7, 58.00, datetime(2022, 11, 1), datetime(2027, 10, 31), "Active"),
    (6, 8, 52.00, datetime(2023, 7, 1), datetime(2028, 6, 30), "Active"),
]
LOC_TO_CONTRACT = {c[1]: c[0] for c in CONTRACTS}


def dt(d):
    return datetime(d.year, d.month, d.day)


def main():
    conn = pymysql.connect(**get_connect_kwargs(autocommit=False))
    cur = conn.cursor()
    extend_schema(cur)
    conn.commit()
    truncate_all(cur)

    # vendors / products / locations / technicians
    cur.executemany("INSERT INTO vendor VALUES (%s,%s,%s,%s,%s)", VENDORS)
    cur.executemany(
        "INSERT INTO product (product_no,product_name,manufacturer,machine_type,list_price) "
        "VALUES (%s,%s,%s,%s,%s)", PRODUCTS)
    cur.executemany(
        "INSERT INTO business_location (location_id,location_name,location_type,"
        "address,city,state,zipcode,phone,manager_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        LOCATIONS)
    cur.executemany(
        "INSERT INTO technician (technician_id,technician_name,region,phone) "
        "VALUES (%s,%s,%s,%s)", TECHS)
    cur.executemany(
        "INSERT INTO contract (contract_id,location_id,contract_date,start_date,"
        "end_date,contract_status,revenue_share_pct) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        [(c[0], c[1], c[3], c[3], c[4], c[5], c[2]) for c in CONTRACTS])

    prod_by_no = {p[0]: p for p in PRODUCTS}
    vendor_products = {  # which vendor sells which products
        1: [101, 102, 103, 401, 402, 403, 404],
        2: [201, 202, 401, 404],
        3: [101, 102, 103],
        4: [301, 302],
    }

    # ---- Purchase Orders across fiscal years 2022..2026
    po_rows, poi_rows, inv_rows, invi_rows = [], [], [], []
    machine_rows = []
    mlh_rows, mch_rows = [], []
    repair_rows, revenue_rows = [], []

    po_id = 45                # start PO numbering near doc example 00045
    inv_no = 9001
    serial = 303558700
    mlh_id = 1
    mch_id = 1
    repair_id = 1
    rev_id = 1

    # PO definitions: (year, month, day, vendor, status, [(product, qty, unit_price)])
    po_defs = [
        (2022, 2, 10, 3, "Received", [(101, 3, 3100), (102, 2, 3450)]),
        (2022, 5, 18, 4, "Received", [(301, 2, 4100), (302, 1, 4450)]),
        (2022, 9, 7, 2, "Received", [(201, 4, 1750), (202, 2, 2050)]),
        (2023, 1, 23, 1, "Received", [(401, 3, 2550), (402, 2, 2750)]),
        (2023, 6, 14, 1, "Received", [(403, 2, 2650), (404, 4, 1450)]),
        (2023, 11, 2, 3, "Received", [(103, 2, 3250)]),
        (2024, 3, 19, 4, "Received", [(301, 1, 4150)]),
        (2024, 8, 27, 2, "Received", [(201, 2, 1780), (404, 2, 1480)]),
        (2025, 4, 9, 1, "Received", [(402, 2, 2790)]),
        (2025, 10, 15, 3, "Pending", [(101, 2, 3180)]),
        (2026, 2, 4, 4, "Pending", [(302, 1, 4490)]),
        (2026, 5, 20, 1, "Cancelled", [(403, 1, 2690)]),
    ]

    # locations cycle for installing machines
    install_cycle = [3, 5, 7, 4, 6, 8, 3, 5, 7, 4, 6, 8]
    machine_type_status = []  # collect for later revenue/repair gen

    for (yy, mm, dd, vend, status, items) in po_defs:
        pdate = datetime(yy, mm, dd)
        po_rows.append((po_id, vend, pdate, status))
        for (pno, qty, up) in items:
            poi_rows.append((pno, po_id, qty, up))

        if status == "Received":
            # invoice received ~10-25 days later
            idate = pdate + timedelta(days=random.randint(8, 25))
            inv_rows.append((inv_no, po_id, vend, idate, "Paid",
                             "Net 30 days. FOB destination."))
            for (pno, qty, up) in items:
                invi_rows.append((pno, inv_no, qty, up))
                p = prod_by_no[pno]
                for _ in range(qty):
                    serial += 1
                    # decide placement
                    r = random.random()
                    install_date = idate + timedelta(days=random.randint(3, 40))
                    if install_date.date() > TODAY:
                        install_date = dt(TODAY) - timedelta(days=random.randint(5, 20))
                    if r < 0.68:
                        loc = install_cycle[serial % len(install_cycle)]
                        mstatus = "Active"
                    elif r < 0.80:
                        loc = WAREHOUSE_ID
                        mstatus = "In Warehouse"
                        install_date = None
                    elif r < 0.90:
                        loc = install_cycle[serial % len(install_cycle)]
                        mstatus = "Under Repair"
                    else:
                        loc = WAREHOUSE_ID
                        mstatus = "Disposed"
                    machine_rows.append(dict(
                        serial=serial, inv=inv_no, loc=loc,
                        name=p[1], model=f"{p[1]} {yy}", status=mstatus,
                        manuf=p[2], mtype=p[3], price=up, pdate=pdate,
                        idate=install_date))
                    machine_type_status.append(serial)
            inv_no += 1
        po_id += 1

    cur.executemany("INSERT INTO purchase_order VALUES (%s,%s,%s,%s)", po_rows)
    cur.executemany("INSERT INTO purchase_order_item VALUES (%s,%s,%s,%s)", poi_rows)
    cur.executemany("INSERT INTO invoice VALUES (%s,%s,%s,%s,%s,%s)", inv_rows)
    cur.executemany("INSERT INTO invoice_item VALUES (%s,%s,%s,%s)", invi_rows)

    # machines
    m_insert = []
    for m in machine_rows:
        disposal_date = None
        disposal_reason = None
        if m["status"] == "Disposed":
            disposal_date = dt(TODAY) - timedelta(days=random.randint(30, 300))
            disposal_reason = random.choice(["Junk", "Sold", "Stolen", "Fire", "Vandalism"])
        m_insert.append((
            m["serial"], m["inv"], m["loc"], m["name"], m["model"], m["status"],
            m["manuf"], m["mtype"], m["price"], m["pdate"], m["idate"],
            disposal_date, disposal_reason))
    cur.executemany(
        "INSERT INTO machine (serial_number,invoice_number,location_id,machine_name,"
        "model_name,machine_status,manufacturer,machine_type,purchase_price,"
        "purchase_date,installation_date,disposal_date,disposal_reason) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", m_insert)

    # location history + contract history + revenue + repairs (active/repair machines)
    for m in machine_rows:
        if m["status"] in ("Active", "Under Repair") and m["idate"]:
            loc = m["loc"]
            install = m["idate"]
            # ~30% of machines previously sat at another site (relocated) -> history
            if random.random() < 0.32:
                prev_loc = random.choice([s for s in SITE_IDS if s != loc])
                prev_start = install - timedelta(days=random.randint(200, 500))
                prev_end = install - timedelta(days=1)
                perf = random.choice(["Low", "Average", "Low"])
                mlh_rows.append((mlh_id, m["serial"], prev_loc, prev_start, prev_end, perf))
                mlh_id += 1
            mlh_rows.append((mlh_id, m["serial"], loc, install, None, None))
            mlh_id += 1

            # contract history (current)
            cid = LOC_TO_CONTRACT.get(loc)
            if cid:
                mch_rows.append((mch_id, m["serial"], cid, install, datetime(2027, 12, 31)))
                mch_id += 1

            # monthly revenue from install to today (cap 24 months)
            base = {"Pinball": 480, "Jukebox": 320, "Pool Table": 260,
                    "Video Game": 380}[m["mtype"]]
            # some machines are deliberately low performers
            low = random.random() < 0.30
            factor = 0.35 if low else random.uniform(0.8, 1.4)
            # generate the most recent 24 months of revenue up to today,
            # never starting before the machine was installed
            stop = date(TODAY.year, TODAY.month, 1)
            window_start_idx = stop.year * 12 + (stop.month - 1) - 23
            inst_idx = install.year * 12 + (install.month - 1)
            start_idx = max(window_start_idx, inst_idx)
            idx = start_idx
            stop_idx = stop.year * 12 + (stop.month - 1)
            while idx <= stop_idx:
                cur_m = date(idx // 12, idx % 12 + 1, 1)
                amt = round(base * factor * random.uniform(0.7, 1.3), 2)
                revenue_rows.append((rev_id, m["serial"], cur_m, amt))
                rev_id += 1
                idx += 1

            # repairs: more for under-repair / low performers
            n_rep = 0
            if m["status"] == "Under Repair":
                n_rep = random.randint(2, 5)
            elif low:
                n_rep = random.randint(1, 4)
            elif random.random() < 0.4:
                n_rep = random.randint(0, 2)
            for _ in range(n_rep):
                rdate = install + timedelta(days=random.randint(20, 600))
                if rdate.date() > TODAY:
                    rdate = dt(TODAY) - timedelta(days=random.randint(5, 60))
                cost = round(random.uniform(80, 650), 2)
                desc = random.choice([
                    "Coin mechanism jam", "Display board replacement",
                    "Power supply repair", "Control panel rewire",
                    "Felt / bumper replacement", "Speaker & amp fix",
                    "Flipper coil replacement", "Monitor recalibration"])
                repair_rows.append((repair_id, m["serial"], rdate, cost, desc))
                repair_id += 1

    cur.executemany(
        "INSERT INTO machine_location_hst (hst_id,serial_number,location_id,"
        "start_date,end_date,performance_note) VALUES (%s,%s,%s,%s,%s,%s)", mlh_rows)
    cur.executemany(
        "INSERT INTO machine_contract_hst (machine_contract_no,serial_number,"
        "contract_id,contract_start_date,contract_end_date) VALUES (%s,%s,%s,%s,%s)",
        mch_rows)
    cur.executemany(
        "INSERT INTO machine_repair (repair_id,serial_number,repair_date,cost,description) "
        "VALUES (%s,%s,%s,%s,%s)", repair_rows)
    cur.executemany(
        "INSERT INTO machine_revenue (revenue_id,serial_number,revenue_month,amount) "
        "VALUES (%s,%s,%s,%s)", revenue_rows)

    # ---- a few completed move orders (history)
    order_rows = []
    oid = 980
    active_serials = [m["serial"] for m in machine_rows if m["status"] == "Active"][:6]
    techs_by_region = {3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 3}
    for s in active_serials:
        m = next(mm for mm in machine_rows if mm["serial"] == s)
        loc = m["loc"]
        tech = techs_by_region.get(loc, 1)
        rdate = m["idate"] - timedelta(days=2) if m["idate"] else dt(TODAY)
        sched = m["idate"] or dt(TODAY)
        order_rows.append((
            oid, s, tech, WAREHOUSE_ID, loc, loc, "Install", "Completed",
            sched, rdate, sched, "Tech-Signed", "Installed and tested on site.",
            LOCATIONS[loc - 1][8] if loc <= len(LOCATIONS) else "Marge Brooks"))
        oid += 1

    cur.executemany(
        "INSERT INTO `order` (order_id,serial_number,technician_id,from_location_id,"
        "to_location_id,location_id,order_type,order_status,competion_date,request_date,"
        "scheduled_datetime,signature,notes,issuing_manager) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", order_rows)

    conn.commit()

    # report counts
    print("\nSeed complete. Row counts:")
    for t in ["vendor", "product", "business_location", "technician", "contract",
              "purchase_order", "purchase_order_item", "invoice", "invoice_item",
              "machine", "machine_location_hst", "machine_contract_hst",
              "machine_repair", "machine_revenue", "order"]:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        print(f"  {t:24s} {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
