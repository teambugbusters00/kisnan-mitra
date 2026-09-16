# KisanLink production integrations

## Already implemented without private credentials

- PostgreSQL/Neon persistence
- JWT authentication and login-first routing
- Device/browser location capture and storage
- Weather via Open-Meteo using latitude/longitude (no API key required for the current endpoint)
- Government mandi adapter for the AGMARKNET/data.gov.in daily market dataset
- Market insight calculations over returned observations
- Provider-ready computer-vision upload endpoint
- Provider-ready OTP endpoints
- Provider-ready payment signature/webhook endpoints
- Device-token storage endpoint for future FCM/APNs delivery

## Credentials / access you must supply manually

### 1. Mandi prices
Render backend environment variable:
`DATA_GOV_API_KEY`

Create a key from data.gov.in for resource `9ef84268-d588-465a-a308-a864a43d0070`.

### 2. Mobile OTP
Choose Twilio Verify (already wired):
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_VERIFY_SERVICE_SID`

### 3. KYC
An authorized KYC/AgriStack partner account and API documentation/credentials are required. Do not put Aadhaar numbers or other sensitive identity data in frontend code.

### 4. Buyer verification
Provide the authorized verification provider/API or business registry endpoint plus credentials. The app must not invent verified-buyer status.

### 5. Computer vision
Provide a deployed inference endpoint and token:
- `VISION_API_URL`
- `VISION_API_TOKEN` (if required)

The endpoint should accept a multipart `file` and return the model's grading/quality result.

### 6. Payments / escrow
Razorpay signature verification is wired. For live payment processing supply:
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`

Actual DBT/bank settlement still requires an authorized banking/DBT integration; Razorpay is not a substitute for government DBT rails.

### 7. Push notifications
Provide a Firebase project and native Android/iOS configuration. The backend has device-token storage ready. For real FCM sending, supply Firebase service-account credentials securely through Render; for iOS/APNs, configure the Apple credentials in the Firebase project.

### 8. FPO data
Provide the authorized FPO registry/API endpoint and credentials. Until then, FPO pages show a provider-unconfigured state rather than fabricated companies or member counts.

### 9. Warehouse data
Provide the WDRA/warehouse operator API or approved inventory source and credentials. Until then, warehouse capacity is not fabricated.

### 10. Logistics / GPS
Device GPS is implemented. For route optimization, live truck tracking, ETAs and freight quotes, provide a logistics/Maps provider API key and endpoint (e.g. an approved routing provider).

## Render

Frontend and backend deploy automatically from `main`:
- Frontend: `kisanlink-frontend`
- Backend: `kisanlink-api`

Set the environment variables above in the backend Render service. Never commit secrets to GitHub.
