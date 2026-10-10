# Setting Up Google Earth Engine Service Account

This guide walks you through creating a GEE service account so the backend can
query Sentinel-2 data without interactive OAuth.

## Prerequisites

- A Google account
- A GCP project (free tier is fine)

## Steps

### 1. Create or select a GCP project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click the project selector (top-left) → **New Project**
3. Name it (e.g. `clean-water-initiative`) → **Create**
4. Note down the **Project ID** (you'll need it for the `GEE_PROJECT_ID` env var)

### 2. Enable the Earth Engine API

1. In your GCP project, go to **APIs & Services → Library**
2. Search for **"Earth Engine API"**
3. Click **Enable**

### 3. Create a service account

1. Go to **IAM & Admin → Service Accounts**
2. Click **+ Create Service Account**
3. Name: `gee-backend` (or similar)
4. Grant role: **Earth Engine Resource Viewer** (or just proceed without a role — the EE registration step handles permissions)
5. Click **Done**
6. Note down the service account **email** (e.g. `gee-backend@your-project.iam.gserviceaccount.com`) — you'll need it for `GEE_SERVICE_ACCOUNT_EMAIL`

### 4. Generate a JSON key

1. Click on the service account you just created
2. Go to **Keys** tab → **Add Key → Create new key**
3. Choose **JSON** → **Create**
4. A `.json` file will download. This is your service account key.

### 5. Register the service account with Earth Engine

> [!IMPORTANT]
> This step is required — GCP IAM alone doesn't grant Earth Engine access.

1. Go to [signup.earthengine.google.com/#!/service_accounts](https://signup.earthengine.google.com/#!/service_accounts)
2. Enter your service account email
3. Select your GCP project
4. Submit the registration request
5. Wait for approval (usually instant for existing EE users, may take a few hours for new accounts)

### 6. Set environment variables

Open the JSON key file and set these env vars in your `.env` or deployment config:

```bash
# The ENTIRE contents of the JSON key file, as a single-line string
GEE_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n","client_email":"gee-backend@your-project.iam.gserviceaccount.com",...}

# Your GCP project ID
GEE_PROJECT_ID=your-project-id

# The service account email
GEE_SERVICE_ACCOUNT_EMAIL=gee-backend@your-project.iam.gserviceaccount.com
```

### 7. Verify it works

```python
import json, os, ee

key_data = json.loads(os.environ["GEE_SERVICE_ACCOUNT_KEY"])
credentials = ee.ServiceAccountCredentials(
    os.environ["GEE_SERVICE_ACCOUNT_EMAIL"],
    key_data=key_data
)
ee.Initialize(credentials=credentials, project=os.environ["GEE_PROJECT_ID"])

# Quick test: fetch a single pixel
point = ee.Geometry.Point([74.738, 19.095])
img = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
    .filterBounds(point) \
    .filterDate("2024-01-01", "2024-03-31") \
    .first()
print(img.getInfo()["id"])  # Should print a Sentinel-2 image ID
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ee.ee_exception.EEException: Not signed up for Earth Engine` | Step 5 — register the SA at signup.earthengine.google.com |
| `google.auth.exceptions.DefaultCredentialsError` | Check `GEE_SERVICE_ACCOUNT_KEY` env var is set and contains valid JSON |
| `Permission denied` on API call | Ensure Earth Engine API is enabled (Step 2) and SA is registered (Step 5) |
| `Quota exceeded` | Free tier has limits; consider upgrading or reducing query frequency |
