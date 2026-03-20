# TokenBudget Frontend — Developer Documentation

## Overview

React 18 SPA with TypeScript, Vite, TailwindCSS, Recharts, and React Query. Dark theme throughout. Supports demo mode for showcasing without a running API.

## Running Locally

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Requires Node.js 18+ (v24 recommended). If multiple Node versions are installed, ensure the correct one is on PATH.

---

## Project Structure

```
frontend/src/
├── main.tsx                    # React DOM root
├── App.tsx                     # Router + QueryClient + auth guard
├── api/                        # API client layer
│   ├── client.ts               # Axios instance with auth interceptor
│   ├── types.ts                # TypeScript interfaces
│   ├── analytics.ts            # Analytics API functions
│   ├── budgets.ts              # Budget API functions
│   ├── keys.ts                 # Key API functions
│   └── projects.ts             # Project API functions
├── hooks/                      # React Query hooks
│   ├── useAnalytics.ts         # useSummary, useByModel, useTimeseries, useByUser
│   ├── useBudgets.ts           # useBudgets, useCreateBudget, useDeleteBudget
│   ├── useKeys.ts              # useKeys, useCreateKey, useDeleteKey
│   └── useProjects.ts          # useProjects, useProject, useCreateProject, useDeleteProject
├── pages/                      # Route-level components
│   ├── Landing.tsx             # Public landing page (/)
│   ├── Login.tsx               # Auth page (/login)
│   ├── Onboarding.tsx          # First-time key creation
│   ├── Dashboard.tsx           # Main dashboard (/dashboard)
│   ├── Projects.tsx            # Project list (/dashboard/projects)
│   ├── ProjectDetail.tsx       # Single project (/dashboard/projects/:id)
│   ├── Analytics.tsx           # Deep analytics (/dashboard/analytics)
│   ├── Budgets.tsx             # Budget management (/dashboard/budgets)
│   ├── ApiKeys.tsx             # Key management (/dashboard/keys)
│   ├── Settings.tsx            # Settings (/dashboard/settings)
│   └── NotFound.tsx            # 404 page
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx         # Fixed left nav with active state
│   │   ├── Header.tsx          # Top bar with period selector
│   │   └── PageShell.tsx       # Sidebar + Header + DemoBanner + Outlet
│   ├── charts/
│   │   ├── SpendOverTime.tsx   # Recharts AreaChart with gradient
│   │   ├── ModelBreakdown.tsx  # Recharts PieChart / donut
│   │   ├── UserBreakdown.tsx   # Recharts horizontal BarChart
│   │   └── BudgetGauge.tsx     # SVG arc gauge (green→amber→red)
│   └── ui/
│       ├── Card.tsx            # StatCard + Card wrapper
│       ├── Badge.tsx           # Status badge
│       ├── Modal.tsx           # Dialog overlay (ESC to close)
│       ├── DataTable.tsx       # Sortable table
│       ├── Skeleton.tsx        # Loading skeletons (StatCard, Chart)
│       ├── EmptyState.tsx      # No-data placeholder
│       └── DemoBanner.tsx      # Yellow demo mode banner
├── lib/
│   ├── formatters.ts           # Currency, number, date, latency formatting
│   ├── constants.ts            # Model colors, plan tiers, period options
│   └── demoData.ts             # Full demo dataset + isDemoMode() helper
└── styles/
    └── globals.css             # Tailwind + custom properties + animations
```

---

## Routing

| Path | Component | Auth | Description |
|------|-----------|------|-------------|
| `/` | Landing | No | Public landing page |
| `/home` | Landing | No | Alias for landing |
| `/login` | Login | No | Email + API key auth |
| `/onboarding` | Onboarding | No | First-time key creation |
| `/dashboard` | Dashboard | Yes | Main overview |
| `/dashboard/projects` | Projects | Yes | Project list |
| `/dashboard/projects/:id` | ProjectDetail | Yes | Single project |
| `/dashboard/analytics` | Analytics | Yes | Deep analytics |
| `/dashboard/budgets` | Budgets | Yes | Budget management |
| `/dashboard/keys` | ApiKeys | Yes | API key management |
| `/dashboard/settings` | Settings | Yes | Preferences |
| `*` | NotFound | No | 404 page |

**Auth guard**: `RequireAuth` component checks `localStorage.tb_api_key`. If missing, redirects to `/login`.

---

## API Client (`src/api/client.ts`)

Axios instance with:
- **Base URL**: `VITE_API_URL` env var (default: `""` for relative URLs, proxied by Vite)
- **Request interceptor**: Adds `Authorization: Bearer <key>` from `localStorage.tb_api_key`
- **Response interceptor**: On 401, clears stored key and redirects to `/login`

---

## React Query Hooks

All hooks support **demo mode** — when `localStorage.tokenbudget_demo === 'true'`, they return `Promise.resolve(DEMO_DATA)` instead of making API calls.

### `useAnalytics.ts`
| Hook | Returns | API |
|------|---------|-----|
| `useSummary(period)` | `AnalyticsSummary` | GET /api/analytics/summary |
| `useByModel(period)` | `ModelBreakdown[]` | GET /api/analytics/by-model |
| `useTimeseries(period, granularity)` | `TimeseriesPoint[]` | GET /api/analytics/timeseries |
| `useByUser(period)` | `UserBreakdown[]` | GET /api/analytics/by-user |

### `useBudgets.ts`
| Hook | Returns | API |
|------|---------|-----|
| `useBudgets()` | `Budget[]` | GET /api/budgets |
| `useCreateBudget()` | mutation | POST /api/budgets |
| `useDeleteBudget()` | mutation | DELETE /api/budgets/:id |

### `useKeys.ts`
| Hook | Returns | API |
|------|---------|-----|
| `useKeys()` | `ApiKeyResponse[]` | GET /api/keys |
| `useCreateKey()` | mutation | POST /api/keys |
| `useDeleteKey()` | mutation | DELETE /api/keys/:id |

### `useProjects.ts`
| Hook | Returns | API |
|------|---------|-----|
| `useProjects()` | `Project[]` | GET /api/projects |
| `useProject(id)` | `Project` | GET /api/projects/:id |
| `useCreateProject()` | mutation | POST /api/projects |
| `useDeleteProject()` | mutation | DELETE /api/projects/:id |

---

## Demo Mode (`src/lib/demoData.ts`)

### Activation
```typescript
enableDemoMode()   // Sets localStorage flags + fake API key
disableDemoMode()  // Clears flags
isDemoMode()       // Returns boolean
```

### Available Demo Data
| Constant | Records | Description |
|----------|---------|-------------|
| `DEMO_SUMMARY` | 1 | Analytics summary: $11,408 spend, 1.3M requests |
| `DEMO_MODELS` | 5 | Model breakdown: gpt-4o (42%), claude-sonnet (26%), etc. |
| `DEMO_TIMESERIES` | 30 | 30 days of daily spend data with realistic patterns |
| `DEMO_BUDGETS` | 2 | Monthly ($15K, 73% used) + Daily ($500, 45% used) |
| `DEMO_KEYS` | 6 | 6 API keys across 4 projects |
| `DEMO_PROJECTS` | 4 | Mobile App, Web Dashboard, Internal Tools, Staging |
| `DEMO_EVENTS` | 10 | Recent events across models |
| `DEMO_USERS` | 4 | User breakdown with email + spend |

---

## Design System

### CSS Custom Properties (`globals.css`)
```css
--bg: #0a0a0f          /* Page background */
--surface: #111118      /* Card background */
--surface-2: #1a1a24    /* Elevated surface */
--surface-3: #21212e    /* Highest elevation */
--border: #1e1e2e       /* Default border */
--accent: #6366f1       /* Primary indigo */
--accent-2: #818cf8     /* Lighter indigo */
--text: #e2e8f0         /* Primary text */
--muted: #64748b        /* Secondary text */
--success: #10b981      /* Green */
--warning: #f59e0b      /* Amber */
--danger: #f43f5e       /* Red */
```

### Component Classes
| Class | Description |
|-------|-------------|
| `.card` | Surface container with border + rounded-xl |
| `.card-hover` | Card with indigo border glow on hover |
| `.btn-primary` | Indigo button with hover lift + shadow |
| `.btn-ghost` | Transparent button with hover highlight |
| `.input` | Dark input with indigo focus ring |
| `.gradient-text` | Indigo gradient text fill |
| `.skeleton` | Shimmer loading placeholder |
| `.animate-fade-in` | 0.3s opacity fade |
| `.animate-slide-up` | 0.35s translateY + opacity |
| `.animate-scale-in` | 0.25s scale + opacity |

### Animation Stagger
```css
.stagger-1 { animation-delay: 0ms; }
.stagger-2 { animation-delay: 60ms; }
.stagger-3 { animation-delay: 120ms; }
.stagger-4 { animation-delay: 180ms; }
```

---

## Landing Page Sections (`Landing.tsx`)

1. **NavBar** — Frosted glass fixed nav with logo + CTAs
2. **Hero** — Headline, subheadline, live ticker badge, CTA buttons
3. **PlatformStatsBar** — 4 stats (2 min setup, $0 cost, 3 providers, 1 line)
4. **SocialProofBanner** — 3 horror stats from real sources
5. **ProblemSection** — 4 pain point cards
6. **QuotesSection** — Jensen Huang (2) + Chamath (1) with accent bars
7. **SolutionSection** — Code block with syntax highlighting
8. **DashboardPreview** — Fake dashboard with SVG chart, model bars, live feed
9. **FeaturesSection** — 4 feature cards
10. **ReportPreviewSection** — PDF report mockup (white card)
11. **TestimonialsSection** — 3 customer testimonial cards with stars
12. **PricingSection** — 3 tiers (Free/Pro/Team) + waitlist form
13. **Footer** — Tagline + links

---

## Login Flow (`Login.tsx`)

Three views controlled by `AuthView` state:

1. **main** — Email input + "Send Magic Link" + Google (greyed out) + "API key" link
2. **magic-sent** — Confirmation message for email sent
3. **api-key** — API key paste input for existing users

On successful API key entry: stores in `localStorage.tb_api_key`, redirects to `/dashboard`.

---

## Adding a New Page

1. Create `src/pages/NewPage.tsx`
2. Add route in `App.tsx` under the `/dashboard` Route
3. Add nav item in `Sidebar.tsx` navItems array
4. If it needs API data: create hook in `hooks/`, add demo data in `demoData.ts`
