"""Deterministic benchmark datasets, ordered from simple to hard.

Level 1 is trivially flat; level 9 is adversarially irregular. Every dataset
is generated from a fixed seed so results are reproducible byte-for-byte.
"""

from __future__ import annotations

import random
from typing import Any

CITIES = [
    ("Boulder", "80301"), ("Helsinki", "00100"), ("Arlington", "22201"),
    ("Izmir", "35000"), ("Kyoto", "600-8001"), ("Lisbon", "1100-148"),
]
NAMES = ["Ada", "Linus", "Grace", "Edsger", "Alan", "Barbara", "Ken", "Dennis", "Radia", "Anita"]
ROLES = ["admin", "dev", "ops", "design", "pm"]
EVENTS = ["click", "view", "error", "purchase", "signup"]


def l1_flat_config() -> Any:
    return {
        "app": "checkout-service",
        "version": "2.14.1",
        "debug": False,
        "port": 8080,
        "timeoutMs": 30000,
        "region": "eu-central-1",
    }


def l2_flat_table() -> Any:
    rnd = random.Random(2)
    return {
        "employees": [
            {
                "id": i + 1,
                "name": rnd.choice(NAMES),
                "role": rnd.choice(ROLES),
                "salary": rnd.randrange(50000, 150000, 500),
                "remote": rnd.random() < 0.5,
            }
            for i in range(100)
        ]
    }


def l3_primitive_arrays() -> Any:
    rnd = random.Random(3)
    return {
        "ids": [rnd.randrange(1, 10_000) for _ in range(200)],
        "tags": [rnd.choice(EVENTS) for _ in range(100)],
        "readings": [round(rnd.uniform(-40, 40), 2) for _ in range(150)],
        "flags": [rnd.random() < 0.5 for _ in range(50)],
    }


def _order(rnd: random.Random, i: int) -> dict[str, Any]:
    city, zipc = rnd.choice(CITIES)
    return {
        "id": i + 1,
        "status": rnd.choice(["shipped", "pending", "cancelled"]),
        "customer": {
            "name": rnd.choice(NAMES),
            "tier": rnd.choice(["gold", "silver", "bronze"]),
            "address": {"city": city, "zip": zipc, "country": "US"},
        },
        "items": [
            {
                "sku": f"SKU-{rnd.randrange(1, 99)}",
                "qty": rnd.randrange(1, 5),
                "price": round(rnd.uniform(2, 40), 2),
            }
            for _ in range(rnd.randrange(1, 5))
        ],
    }


def l4_nested_uniform_small() -> Any:
    rnd = random.Random(4)
    return {"orders": [_order(rnd, i) for i in range(10)]}


def l5_nested_uniform_large() -> Any:
    rnd = random.Random(5)
    return {"orders": [_order(rnd, i) for i in range(100)]}


def l6_deeply_nested() -> Any:
    rnd = random.Random(6)
    return {
        "org": {
            "name": "acme",
            "teams": [
                {
                    "team": f"team-{t}",
                    "lead": rnd.choice(NAMES),
                    "projects": [
                        {
                            "key": f"PRJ-{t}{p}",
                            "budget": rnd.randrange(10, 500) * 1000,
                            "tasks": [
                                {
                                    "id": t * 1000 + p * 100 + k,
                                    "title": f"task {k} of {p}",
                                    "done": rnd.random() < 0.5,
                                    "assignee": {"name": rnd.choice(NAMES), "role": rnd.choice(ROLES)},
                                }
                                for k in range(rnd.randrange(2, 6))
                            ],
                        }
                        for p in range(rnd.randrange(2, 4))
                    ],
                }
                for t in range(6)
            ],
        }
    }


def l7_semi_uniform() -> Any:
    rnd = random.Random(7)
    events = []
    for i in range(120):
        ev: dict[str, Any] = {"ts": 1_700_000_000 + i * 37, "type": rnd.choice(EVENTS)}
        if rnd.random() < 0.7:
            ev["user"] = {"id": rnd.randrange(1, 500), "plan": rnd.choice(["free", "pro"])}
        if rnd.random() < 0.4:
            ev["meta"] = {"ua": "Mozilla/5.0", "lang": rnd.choice(["en", "tr", "fi"])}
        if ev["type"] == "error":
            ev["code"] = rnd.choice([500, 502, 503])
            ev["fatal"] = rnd.random() < 0.2
        if rnd.random() < 0.25:
            ev["tags"] = [rnd.choice(EVENTS) for _ in range(rnd.randrange(1, 3))]
        events.append(ev)
    return {"events": events}


def l8_mixed_kinds() -> Any:
    rnd = random.Random(8)
    rows = []
    for i in range(80):
        r = rnd.random()
        payload: Any
        if r < 0.4:
            payload = {"a": rnd.randrange(100), "b": rnd.choice(NAMES)}
        elif r < 0.7:
            payload = rnd.choice(["plain text value", "another message", "yet another"])
        elif r < 0.9:
            payload = [rnd.randrange(10) for _ in range(3)]
        else:
            payload = None
        rows.append({"seq": i, "payload": payload})
    return {"rows": rows}


def l10_sparse_api_response() -> Any:
    """API-list response with many mostly-default columns — the ELIDE
    sweet spot (SPEC §6.2). Modeled after Stripe/Shopify list endpoints:
    most rows in the "steady state" (status=active, currency=USD,
    country=US, etc.); a minority diverges."""
    rnd = random.Random(10)
    rows = []
    for i in range(100):
        row = {
            "id": i + 1,
            "object": "customer",
            "livemode": True,
            "currency": "usd",
            "country": "US",
            "status": "active",
            "delinquent": False,
            "email": f"user{i+1}@example.com",
            "plan": "starter",
        }
        # ~10% status divergence, ~5% currency/country divergence, ~8% delinquency.
        if rnd.random() < 0.10:
            row["status"] = rnd.choice(["past_due", "canceled", "unpaid"])
        if rnd.random() < 0.05:
            row["currency"] = rnd.choice(["eur", "gbp", "jpy"])
            row["country"] = rnd.choice(["DE", "GB", "JP"])
        if rnd.random() < 0.08:
            row["delinquent"] = True
        if rnd.random() < 0.03:
            row["livemode"] = False
        if rnd.random() < 0.15:
            row["plan"] = rnd.choice(["pro", "enterprise", "team"])
        rows.append(row)
    return {"data": rows}


def l11_shared_address_employees() -> Any:
    """Employees where most share one of a few head-office addresses —
    the REF sweet spot (SPEC §6.3). Modeled after HRIS/directory
    payloads where head-count concentrates in a few sites."""
    rnd = random.Random(11)
    hq = {"street": "1 Market St", "city": "San Francisco", "state": "CA", "zip": "94105", "country": "US"}
    dublin = {"street": "5 Grand Canal Sq", "city": "Dublin", "state": "D02", "zip": "D02WP70", "country": "IE"}
    tokyo = {"street": "1-9-2 Marunouchi", "city": "Tokyo", "state": "Chiyoda", "zip": "100-6390", "country": "JP"}
    offices = [hq, hq, hq, hq, hq, hq, dublin, dublin, tokyo]  # ~66% HQ, ~22% Dublin, ~11% Tokyo
    employees = []
    for i in range(90):
        office = rnd.choice(offices) if rnd.random() < 0.9 else {
            "street": f"{rnd.randrange(1, 200)} Remote Ln",
            "city": rnd.choice(["Boulder", "Austin", "Berlin"]),
            "state": rnd.choice(["CO", "TX", "BE"]),
            "zip": f"{rnd.randrange(10000, 99999)}",
            "country": rnd.choice(["US", "US", "DE"]),
        }
        employees.append({
            "id": i + 1,
            "name": rnd.choice(NAMES),
            "role": rnd.choice(ROLES),
            "office": office,
        })
    return {"employees": employees}


def l9_adversarial_nonuniform() -> Any:
    rnd = random.Random(9)
    out: list[Any] = []
    for i in range(40):
        r = rnd.random()
        if r < 0.3:
            out.append({f"k{i}": {f"n{j}": [j, [j + 1], {"x": None}] for j in range(rnd.randrange(1, 4))}})
        elif r < 0.6:
            out.append([i, [i + 1, [i + 2]], {"deep": {"deeper": [{"i": i}]}}])
        elif r < 0.8:
            out.append(rnd.choice(["str", 3.25, None, True]))
        else:
            out.append({"only": i})
    return {"chaos": out}


DATASETS = [
    ("L1 flat config", "flat object, 6 keys", l1_flat_config),
    ("L2 flat table", "100 uniform rows (TOON/CSV sweet spot)", l2_flat_table),
    ("L3 primitive arrays", "4 large scalar arrays", l3_primitive_arrays),
    ("L4 nested small", "10 orders, depth 3", l4_nested_uniform_small),
    ("L5 nested large", "100 orders, depth 3", l5_nested_uniform_large),
    ("L6 deeply nested", "tables inside tables, depth 5", l6_deeply_nested),
    ("L7 semi-uniform", "event log, optional fields", l7_semi_uniform),
    ("L8 mixed kinds", "field mixes object/string/array/null", l8_mixed_kinds),
    ("L9 adversarial", "irregular everything (worst case)", l9_adversarial_nonuniform),
    ("L10 sparse API response", "100 rows with ~90% default columns (ELIDE showcase)", l10_sparse_api_response),
    ("L11 shared-address employees", "90 employees, ~90% share few offices (REF showcase)", l11_shared_address_employees),
]
