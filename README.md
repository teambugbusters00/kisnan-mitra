# KisanLink — Capacitor App

KisanLink is the SIH26132 prototype: **Connecting Farmers to Better Markets**.

This repository contains a mobile-first frontend designed from the supplied KisanLink reference screens.

## Included flows

- Home / product landing
- Farmer login
- Farmer dashboard
- Mandi market prices
- Sell produce
- Verified buyer marketplace
- FPO & cooperative hub
- Transactions & escrow wallet
- Notifications
- Profile & settings

## Capacitor

The project is configured for Capacitor.

```bash
npm install
npm run build
npx cap add android
npx cap sync
npx cap open android
```

For iOS:

```bash
npx cap add ios
npx cap sync
npx cap open ios
```

The native `android/` and `ios/` folders are intentionally generated on the target development machine with Capacitor instead of being checked in by this web-first commit.

## Run locally

```bash
npm install
npm run dev
```

## Design

The UI is mobile-first and follows the supplied KisanLink reference screens: green agriculture branding, compact cards, market-price intelligence, direct buyer bidding, FPO logistics and transparent settlement flows.

The market numbers and buyer/transaction records in this prototype are **demo data** and must be replaced by verified live sources before production use.
