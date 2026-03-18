# Nova Flow Kit

A smart calendar and AI assistant application.

## Tech Stack

- **Vite** — Fast build tool and dev server
- **React 18** — UI framework
- **TypeScript** — Type-safe JavaScript
- **Tailwind CSS** — Utility-first CSS framework
- **shadcn/ui** — Accessible UI components
- **Supabase** — Backend-as-a-service (auth, database, real-time)
- **React Query** — Server state management
- **React Router** — Client-side routing

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or later)
- npm (comes with Node.js)

### Installation

```sh
# 1. Clone the repository
git clone <YOUR_GIT_URL>

# 2. Navigate to the project directory
cd nova-flow-kit-main

# 3. Install dependencies
npm install

# 4. Start the development server
npm run dev
```

The app will be available at `http://localhost:8080`.

### Available Scripts

| Command          | Description                          |
|------------------|--------------------------------------|
| `npm run dev`    | Start the dev server with HMR        |
| `npm run build`  | Build for production                 |
| `npm run preview`| Preview the production build locally |
| `npm run lint`   | Run ESLint                           |
| `npm run test`   | Run tests                            |

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
VITE_BACKEND_API_URL=http://localhost:8000
```

`VITE_BACKEND_API_URL` should point to the FastAPI server in `Backend-agent`.

## Deployment

Build the project and deploy the `dist/` folder to any static hosting provider (Vercel, Netlify, Cloudflare Pages, etc.):

```sh
npm run build
```
