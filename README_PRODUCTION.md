# KisanLink production checklist

The UI is intentionally mobile-first and follows the supplied reference screens: authentication first, dashboard, live mandi prices, sell, buyer marketplace, transactions/wallet, notifications and profile.

## Required before calling data production-ready
- Set `VITE_API_BASE_URL` to the Render FastAPI URL.
- Backend must have `DATABASE_URL` and a strong `JWT_SECRET` configured in Render.
- Replace any seeded/demo rows in Neon with real or explicitly labelled test records.
- Configure an authorized mandi/e-NAM/APMC market feed. The app now shows an empty/stale state instead of inventing prices when that feed is absent.
- Configure an OTP provider if passwordless mobile login is required.
- Configure payment/bank webhooks before displaying escrow/settlement balances.
- Configure FCM/APNs for real push notifications.
- Configure logistics/GPS, warehouse, FPO and computer-vision services before exposing those insights as live.

## Render
Both services are configured for automatic deployment from `main`:
- `kisanlink-api` — FastAPI
- `kisanlink-frontend` — Vite static site

Never commit database passwords, JWT secrets, API keys, payment secrets or OTP credentials.
