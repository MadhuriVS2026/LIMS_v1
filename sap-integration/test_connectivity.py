"""
One-off connectivity check against the SAP Integration Suite (CPI) endpoints
defined in the LIMS QAS Postman collection. Reads credentials from .env
(never printed) and hits a couple of safe, read-only GET endpoints.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed; loading .env manually")
    load_dotenv = None

env_path = Path(__file__).parent / ".env"

if load_dotenv:
    load_dotenv(env_path)
else:
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

import requests
from requests.auth import HTTPBasicAuth

BASE_URL = os.environ["SAP_CPI_BASE_URL"]
USERNAME = os.environ["SAP_CPI_USERNAME"]
PASSWORD = os.environ["SAP_CPI_PASSWORD"]

auth = HTTPBasicAuth(USERNAME, PASSWORD)

endpoints_to_test = [
    ("GET", "/http/Dev/Get/WMS_PlantData", None),
]

for method, path, body in endpoints_to_test:
    url = f"{BASE_URL}{path}"
    print(f"\n--- {method} {path} ---")
    try:
        resp = requests.request(method, url, auth=auth, json=body, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"Body (first 500 chars): {resp.text[:500]}")
    except Exception as e:
        print(f"Request failed: {e}")
