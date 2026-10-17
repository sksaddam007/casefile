"""Synthetic bank dataset generator.

Builds ~450 accounts with devices, IPs, cards and transfers — most of it
innocent noise — plus ONE deliberately planted 6-account laundering ring:

    FR-01 ─transfer→ FR-04 ─transfer→ FR-02 ─transfer→ FR-05 ─transfer→ FR-03 ─cash-out→ M-9f2c

The ring members share the *same two devices* and rotate between two
IPs — exactly the "connected data" an agent must hop through.

Deterministic: seed=42 → the demo is reproducible every run.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field

FIRST = [
    "Aarav", "Olivia", "Mateo", "Yuki", "Amara", "Liam", "Sofia", "Noah",
    "Zara", "Ethan", "Mei", "Lucas", "Nadia", "Omar", "Ivy", "Diego",
    "Priya", "Felix", "Hana", "Jonas", "Leila", "Marco", "Tara", "Ivan",
]
LAST = [
    "Reyes", "Okafor", "Tanaka", "Silva", "Khan", "Muller", "Rossi",
    "Chen", "Dupont", "Alvarez", "Kim", "Novak", "Haddad", "Smith",
    "Petrov", "Costa", "Ali", "Weber",
]
COUNTRIES = ["US", "GB", "DE", "IN", "BR", "JP", "NG", "AU", "FR", "SG"]
CATEGORIES = [
    "grocery", "gas", "electronics", "travel", "restaurant",
    "utilities", "insurance", "gambling", "crypto", "luxury",
]
CATMerchant: dict = {
    "C-3f81": "QuickMart",
    "C-77ba": "PetroFuel",
    "C-a1c2": "TechnoWorld",
    "C-9f2c": "SpeedXChange",     # the ring's cash-out merchant
    "C-b44e": "SkyJourney",
    "C-2d90": "Umami House",
    "C-5e13": "CityPower",
    "C-c7aa": "SafeGuard Ins",
    "C-6b8f": "LuckySpin",        # gambling — smell of risk, innocent here
    "C-d02b": "Velvet&Co",
}


@dataclass
class Dataset:
    accounts: list[dict] = field(default_factory=list)
    devices: list[dict] = field(default_factory=list)
    ips: list[dict] = field(default_factory=list)
    cards: list[dict] = field(default_factory=list)
    merchants: list[dict] = field(default_factory=list)
    uses_device: list[tuple[str, str]] = field(default_factory=list)
    logged_from: list[tuple[str, str]] = field(default_factory=list)
    has_card: list[tuple[str, str]] = field(default_factory=list)
    transferred: list[dict] = field(default_factory=list)      # acct -> acct
    paid: list[dict] = field(default_factory=list)             # acct -> merchant
    alerts: list[dict] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {k: len(v) for k, v in [
            ("accounts", self.accounts), ("devices", self.devices),
            ("ips", self.ips), ("cards", self.cards),
            ("merchants", self.merchants), ("uses_device", self.uses_device),
            ("logged_from", self.logged_from), ("has_card", self.has_card),
            ("transferred", self.transferred), ("paid", self.paid),
            ("alerts", self.alerts),
        ]}


RING = ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06"]
RING_DEVICES = ["DEV-fr-a", "DEV-fr-b"]
RING_IPS = ["IP-fr-1", "IP-fr-2"]
CASHOUT_MERCHANT = "M-9f2c"          # merchant id; name : SpeedXChange
FLAGGED_XFER = "XFER-1002"           # the alert will be on FR-02's cashout hop


def _hex(rng: random.Random, n: int = 8) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def generate(seed: int = 42) -> Dataset:
    rng = random.Random(seed)
    ds = Dataset()

    # --- merchants -------------------------------------------------------
    for mid, name in CATMerchant.items():
        cat = CATEGORIES[(ord(name[0]) + len(name)) % len(CATEGORIES)]
        ds.merchants.append({"id": mid, "name": name, "category": cat})

    # --- innocent accounts ----------------------------------------------
    innocent_ids: list[str] = []
    for i in range(400):
        aid = f"A-{_hex(rng)}"
        first = rng.choice(FIRST)
        last = rng.choice(LAST)
        acct = {
            "id": aid,
            "name": f"{first} {last}",
            "country": rng.choice(COUNTRIES),
            "tier": rng.choice(["basic", "standard", "premium"]),
            "opened_days_ago": rng.randint(30, 2600),
            "flagged": False,
        }
        ds.accounts.append(acct)
        innocent_ids.append(aid)

    # devices / ips / cards pools
    innocent_devices = [f"DEV-{_hex(rng, 10)}" for _ in range(430)]
    innocent_ips = [f"IP-{_hex(rng, 6)}" for _ in range(700)]
    innocent_cards = [f"CARD-{_hex(rng, 8)}" for _ in range(500)]

    for d in innocent_devices:
        ds.devices.append({"id": d, "os": rng.choice(["iOS", "Android", "Windows", "macOS"])})
    for ip in innocent_ips:
        ds.ips.append({"id": ip, "geo": rng.choice(COUNTRIES)})
    for c in innocent_cards:
        ds.cards.append({"id": c, "brand": rng.choice(["Visa", "MC", "Amex"])})

    # each innocent account: 1 primary device (+20% a second shared one),
    # 1-2 IPs, 1 card, some merchant payments
    for aid in innocent_ids:
        dev = rng.choice(innocent_devices)
        ds.uses_device.append((aid, dev))
        if rng.random() < 0.2:
            ds.uses_device.append((aid, rng.choice(innocent_devices)))
        for ip in rng.sample(innocent_ips, rng.randint(1, 2)):
            ds.logged_from.append((aid, ip))
        ds.has_card.append((aid, rng.choice(innocent_cards)))
        for _ in range(rng.randint(2, 6)):
            ds.paid.append({
                "src": aid, "dst": rng.choice(list(CATMerchant.keys())),
                "amount": round(rng.uniform(3, 180), 2),
                "ts": rng.randint(1_700_000_000, 1_760_000_000),
                "flagged": False,
            })

    # a little background noise: random account-to-account transfers
    for _ in range(40):
        a, b = rng.sample(innocent_ids, 2)
        ds.transferred.append({
            "id": f"XFER-{_hex(rng, 6)}", "src": a, "dst": b,
            "amount": round(rng.uniform(5, 600), 2),
            "ts": rng.randint(1_750_000_000, 1_760_000_000),
            "flagged": False,
        })

    # --- the planted fraud ring ------------------------------------------
    ds.devices.append({"id": RING_DEVICES[0], "os": "Android"})
    ds.devices.append({"id": RING_DEVICES[1], "os": "Android"})
    ds.ips.append({"id": RING_IPS[0], "geo": "US"})
    ds.ips.append({"id": RING_IPS[1], "geo": "US"})
    for aid in RING:
        fake_name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        ds.accounts.append({
            "id": aid, "name": fake_name,
            "country": rng.choice(["US", "GB", "SG"]),
            "tier": "standard",
            "opened_days_ago": rng.randint(14, 90),   # young accounts
            "flagged": True,
        })
        ring_card = f"CARD-{_hex(rng, 8)}"
        ds.cards.append({"id": ring_card, "brand": "Visa"})
        ds.has_card.append((aid, ring_card))
        # ring members share BOTH devices deliberately (the smoking gun)
        ds.uses_device.append((aid, RING_DEVICES[0]))
        ds.uses_device.append((aid, RING_DEVICES[1]))
        # IPs: everyone touches IP-fr-1, half touch IP-fr-2
        ds.logged_from.append((aid, RING_IPS[0]))
        if aid in ("FR-01", "FR-03", "FR-05"):
            ds.logged_from.append((aid, RING_IPS[1]))
        ds.paid.append({
            "src": aid, "dst": CASHOUT_MERCHANT,
            "amount": round(rng.uniform(90, 480), 2),
            "ts": rng.randint(1_748_000_000, 1_752_000_000),
            "flagged": False,
        })

    # laundering chain FR-01→FR-04→FR-02→FR-05→FR-03 (+two hops out to FR-06)
    chain = [("FR-01", "FR-04"), ("FR-04", "FR-02"), ("FR-02", "FR-05"),
             ("FR-05", "FR-03"), ("FR-01", "FR-06"), ("FR-06", "FR-03")]
    for i, (src, dst) in enumerate(chain, 1):
        ds.transferred.append({
            "id": f"XFER-100{i}", "src": src, "dst": dst,
            "amount": [8400.0, 8150.5, 7900.0, 7350.0, 6100.0, 5980.0][i - 1],
            "ts": 1_750_000_000 + i * 86400,
            "flagged": True,
        })

    # decoys: two innocent accounts that share ONE device with FR-04
    decoy_a, decoy_b = innocent_ids[7], innocent_ids[233]
    ds.uses_device.append((decoy_a, RING_DEVICES[0]))
    ds.uses_device.append((decoy_b, RING_DEVICES[1]))
    ring_names = {a["id"] for a in ds.accounts}

    # --- the alert our agent will investigate ----------------------------
    flagged = [t for t in ds.transferred if t["id"] == FLAGGED_XFER][0]
    ds.alerts.append({
        "id": "AL-0001", "txn_id": FLAGGED_XFER,
        "src": flagged["src"], "dst": flagged["dst"],
        "amount": flagged["amount"],
        "reasons": ["unusual velocity", "account age < 90 days"],
        "ts": flagged["ts"], "status": "open",
    })
    return ds


if __name__ == "__main__":
    ds = generate()
    print(ds.counts())
