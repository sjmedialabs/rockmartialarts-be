"""
One-time historical Razorpay repair script (last 12 months).

Safety:
- No deletes.
- Only updates `payments`/`enrollments` fields additively and idempotently.
- Writes an audit file with per-row outcomes.

Run:
  MONGO_URL=... DB_NAME=... RAZORPAY_KEY_ID=... RAZORPAY_KEY_SECRET=... \
  python3 scripts/repair_razorpay_payments_last_12_months.py
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

from utils.razorpay_reconciliation import ensure_collections_indexes, reconcile_one_payment_row


async def main():
    mongo_url = os.getenv("MONGO_URL") or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    db_name = os.getenv("DB_NAME", "marshalats")
    client = AsyncIOMotorClient(mongo_url, tlsInsecure=True)
    db = client.get_database(db_name)
    await ensure_collections_indexes(db)

    now = datetime.utcnow()
    since = now - timedelta(days=365)

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = out_dir / f"razorpay_repair_audit_{now.strftime('%Y%m%d_%H%M%S')}.jsonl"

    q = {
        "created_at": {"$gte": since},
        "$or": [
            {"payment_status": {"$in": ["pending", "processing"]}},
            {"razorpay_order_id": {"$exists": True, "$ne": None}},
            {"razorpay_payment_id": {"$exists": True, "$ne": None}},
        ],
    }

    checked = 0
    updated = 0
    errors = 0

    with audit_path.open("w", encoding="utf-8") as f:
        cursor = db.payments.find(q).sort("created_at", -1)
        async for row in cursor:
            checked += 1
            try:
                res = await reconcile_one_payment_row(
                    db,
                    row,
                    actor="historical_repair_script",
                    reason="historical_12_months",
                )
                if res.get("updated"):
                    updated += 1
                f.write(json.dumps(res, default=str) + "\n")
            except Exception as e:
                errors += 1
                f.write(
                    json.dumps(
                        {
                            "updated": False,
                            "error": str(e),
                            "payment_row_id": row.get("id") or str(row.get("_id")),
                        },
                        default=str,
                    )
                    + "\n"
                )

            # Progress print every 250 rows
            if checked % 250 == 0:
                print(f"checked={checked} updated={updated} errors={errors}")

    print("done")
    print(f"audit_file={audit_path}")
    print(f"checked={checked} updated={updated} errors={errors}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

