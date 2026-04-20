# GaadiyaHub Deploy Portal

Internal static site deployment portal for GaadiyaHub platform.

## What it does
- Upload a zip file via browser UI
- Automatically syncs to correct S3 bucket
- Invalidates CloudFront cache
- Supports two targets- main website and admin panel

## Tech stack
- Python Flask + Gunicorn
- AWS S3 + CloudFront via boto3
- Docker + Kubernetes (K3s)
- Traefik IngressRoute + cert-manager SSL

## Security
- All secrets injected via Kubernetes Secret
- Zero credentials in code
- Session-based authentication
- Runs as non-root container user

## Live at
https://upload.gadiyadekhe.com (internal access only)
