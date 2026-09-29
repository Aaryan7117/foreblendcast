import json
import httpx
import argparse
from pathlib import Path
import asyncio

async def dispatch_all():
    parser = argparse.ArgumentParser(description="Batch dispatch SMS alerts for RED/ORANGE districts")
    parser.add_argument("--phone", required=True, help="Judge's phone number to receive the demo SMS")
    parser.add_argument("--lang", default="en", choices=["en", "hi", "te", "ta", "mr"], help="Language (en/hi/te/ta/mr)")
    args = parser.parse_args()

    results_dir = Path(__file__).parent.parent / "results"
    with open(results_dir / "districts_L1.json") as f:
        data = json.load(f)
        districts = data.get("districts", [])

    alerts = [d for d in districts if d["tier"].lower() in ["red", "orange"]]
    
    if not alerts:
        print("No RED or ORANGE districts found for Lead Day 1.")
        # For demo purposes, we will force Ratnagiri to alert
        alerts = [d for d in districts if d["id"] == "MH-RATNAGIRI"]
        if alerts:
            alerts[0]["tier"] = "red"
            alerts[0]["p_gt_115p6"] = 0.72

    print(f"Found {len(alerts)} districts requiring alerts.")
    
    async with httpx.AsyncClient() as client:
        for d in alerts:
            print(f"Dispatching alert for {d['name']} ({d['tier'].upper()}) to {args.phone}...")
            payload = {
                "district_id": d["id"],
                "phone": args.phone,
                "language": args.lang
            }
            try:
                resp = await client.post("http://127.0.0.1:8000/api/sms/dispatch", json=payload)
                resp.raise_for_status()
                res_data = resp.json()
                print(f"SUCCESS: {res_data['text']}")
            except Exception as e:
                print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(dispatch_all())
