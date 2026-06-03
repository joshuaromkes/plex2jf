# plex2jf Frontend

React + TypeScript + Vite web UI for managing plex2jf.

## Stack

- **React 19** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- Arr-style dark theme

## Development

```bash
cd frontend
npm install
npm run dev        # Dev server at http://localhost:5173
```

The dev server proxies API requests to the backend at `http://localhost:8000`.

## Build

```bash
npm run build      # Production build → dist/
```

The Docker multi-stage build handles this automatically — no need to build separately.

## Structure

```
frontend/
├── src/
│   ├── components/   # Reusable UI components
│   │   └── layout/   # Sidebar, PageWrapper
│   ├── pages/        # Route pages (Dashboard, Servers, etc.)
│   ├── services/     # API client
│   └── types/        # TypeScript interfaces
├── index.html
├── vite.config.ts
└── tailwind.config.js
```
