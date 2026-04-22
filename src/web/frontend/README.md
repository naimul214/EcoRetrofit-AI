# EcoRetrofit Frontend Dashboard

Next.js dashboard for real-time HVAC telemetry, AI insights, projected energy, and manual override controls.

## Prerequisites

- Node.js 20.9+

## Local Setup

1. Install dependencies:

```bash
npm install
```

2. Configure environment variables:

```bash
# Linux/Mac
cp .env.example .env.local

# Windows PowerShell
Copy-Item .env.example .env.local
```

3. Start development server:

```bash
npm run dev
```

Open http://localhost:3000.

## Environment Variables

- `NEXT_PUBLIC_BACKEND_URL`: Backend API base URL (example: `http://localhost:8010`).

## Scripts

- `npm run dev`: Start development server.
- `npm run build`: Build production bundle.
- `npm run start`: Start production server.
- `npm run lint`: Run ESLint.
