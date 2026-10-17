# Sample run — alert AL-0001

*8 graph tool calls · 14 ms total graph time · 13774+2703 LLM tokens · local model qwen3.5-64k via Ollama*

## `get_alert`(AL-0001) — 1 ms

```json
{
  "alert_id": "AL-0001",
  "txn_id": "XFER-1002",
  "flagged_amount": 8150.5,
  "reasons": [
    "unusual velocity",
    "account age < 90 days"
  ],
  "src_id": "FR-04",
  "src_name": "Sofia Novak",
  "src_account_age_days": 69,
  "src_country": "SG",
  "dst_id": "FR-02",
  "dst_name": "Aarav Rossi",
  "dst_account_age_days": 47,
  "transfer_amount": 8150.5
}
```

## `account_profile`(FR-04) — 1 ms

```json
{
  "id": "FR-04",
  "name": "Sofia Novak",
  "country": "SG",
  "tier": "standard",
  "age_days": 69,
  "flagged": true,
  "transfers_sent": 1,
  "transfers_received": 1,
  "total_sent": 8150.5
}
```

## `account_profile`(FR-02) — 0 ms

```json
{
  "id": "FR-02",
  "name": "Aarav Rossi",
  "country": "SG",
  "tier": "standard",
  "age_days": 47,
  "flagged": true,
  "transfers_sent": 1,
  "transfers_received": 1,
  "total_sent": 7900.0
}
```

## `account_connections`(FR-04) — 6 ms

```json
{
  "devices": [
    "DEV-fr-a",
    "DEV-fr-b"
  ],
  "ips": [
    "IP-fr-1"
  ],
  "cards": [
    "CARD-a08a0add"
  ],
  "paid_to": [],
  "transfers_out": [
    {
      "txn": "XFER-1002",
      "to": "FR-02",
      "to_name": "Aarav Rossi",
      "amount": 8150.5,
      "age_days": 47
    }
  ],
  "transfers_in": [
    {
      "txn": "XFER-1001",
      "from": "FR-01",
      "from_name": "Zara Petrov",
      "amount": 8400.0,
      "age_days": 66
    }
  ]
}
```

## `account_connections`(FR-02) — 2 ms

```json
{
  "devices": [
    "DEV-fr-a",
    "DEV-fr-b"
  ],
  "ips": [
    "IP-fr-1"
  ],
  "cards": [
    "CARD-e3acfbdd"
  ],
  "paid_to": [],
  "transfers_out": [
    {
      "txn": "XFER-1003",
      "to": "FR-05",
      "to_name": "Noah Costa",
      "amount": 7900.0,
      "age_days": 53
    }
  ],
  "transfers_in": [
    {
      "txn": "XFER-1002",
      "from": "FR-04",
      "from_name": "Sofia Novak",
      "amount": 8150.5,
      "age_days": 69
    }
  ]
}
```

## `shared_endpoints`(FR-04) — 2 ms

```json
[
  {
    "endpoint": "DEV-fr-a",
    "endpoint_type": "Device",
    "sharers": [
      {
        "age_days": 685,
        "flagged": false,
        "id": "A-8dcb74f2",
        "name": "Olivia Silva"
      },
      {
        "age_days": 66,
        "flagged": true,
        "id": "FR-01",
        "name": "Zara Petrov"
      },
      {
        "age_days": 47,
        "flagged": true,
        "id": "FR-02",
        "name": "Aarav Rossi"
      },
      {
        "age_days": 83,
        "flagged": true,
        "id": "FR-03",
        "name": "Leila Kim"
      },
      {
        "age_days": 53,
        "flagged": true,
        "id": "FR-05",
        "name": "Noah Costa"
      },
      {
        "age_days": 18,
        "flagged": true,
        "id": "FR-06",
        "name": "Ivy Silva"
      }
    ]
  },
  {
    "endpoint": "IP-fr-1",
    "endpoint_type": "Ip",
    "sharers": [
      {
        "age_days": 66,
        "flagged": true,
        "id": "FR-01",
        "name": "Zara Petrov"
      },
      {
        "age_days": 47,
        "flagged": true,
        "id": "FR-02",
        "name": "Aarav Rossi"
      },
      {
        "age_days": 83,
        "flagged": true,
        "id": "FR-03",
        "name": "Leila Kim"
      },
      {
        "age_days": 53,
        "flagged": true,
        "id": "FR-05",
        "name": "Noah Costa"
      },
      {
        "age_days": 18,
        "flagged": true,
        "id": "FR-06",
        "name": "Ivy Silva"
      }
    ]
  },
  {
    "endpoin
```

## `shared_endpoints`(FR-02) — 1 ms

```json
[
  {
    "endpoint": "DEV-fr-a",
    "endpoint_type": "Device",
    "sharers": [
      {
        "age_days": 685,
        "flagged": false,
        "id": "A-8dcb74f2",
        "name": "Olivia Silva"
      },
      {
        "age_days": 66,
        "flagged": true,
        "id": "FR-01",
        "name": "Zara Petrov"
      },
      {
        "age_days": 83,
        "flagged": true,
        "id": "FR-03",
        "name": "Leila Kim"
      },
      {
        "age_days": 69,
        "flagged": true,
        "id": "FR-04",
        "name": "Sofia Novak"
      },
      {
        "age_days": 53,
        "flagged": true,
        "id": "FR-05",
        "name": "Noah Costa"
      },
      {
        "age_days": 18,
        "flagged": true,
        "id": "FR-06",
        "name": "Ivy Silva"
      }
    ]
  },
  {
    "endpoint": "IP-fr-1",
    "endpoint_type": "Ip",
    "sharers": [
      {
        "age_days": 66,
        "flagged": true,
        "id": "FR-01",
        "name": "Zara Petrov"
      },
      {
        "age_days": 83,
        "flagged": true,
        "id": "FR-03",
        "name": "Leila Kim"
      },
      {
        "age_days": 69,
        "flagged": true,
        "id": "FR-04",
        "name": "Sofia Novak"
      },
      {
        "age_days": 53,
        "flagged": true,
        "id": "FR-05",
        "name": "Noah Costa"
      },
      {
        "age_days": 18,
        "flagged": true,
        "id": "FR-06",
        "name": "Ivy Silva"
      }
    ]
  },
  {
    "endpoin
```

## `trace_money_path`(FR-04, 3) — 1 ms

```json
[
  {
    "accounts": [
      "FR-04",
      "FR-02"
    ],
    "amounts": [
      8150.5
    ],
    "txns": [
      "XFER-1002"
    ],
    "hops": 1
  },
  {
    "accounts": [
      "FR-04",
      "FR-02",
      "FR-05"
    ],
    "amounts": [
      8150.5,
      7900.0
    ],
    "txns": [
      "XFER-1002",
      "XFER-1003"
    ],
    "hops": 2
  },
  {
    "accounts": [
      "FR-04",
      "FR-02",
      "FR-05",
      "FR-03"
    ],
    "amounts": [
      8150.5,
      7900.0,
      7350.0
    ],
    "txns": [
      "XFER-1002",
      "XFER-1003",
      "XFER-1004"
    ],
    "hops": 3
  }
]
```
