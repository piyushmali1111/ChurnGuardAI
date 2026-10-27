# ChurnGuardAI — Frontend Build Prompt

Paste this entire file into your Agentic IDE (Claude Code, Cursor, etc.) as the first instruction for the frontend. It contains the product context, the exact tech stack, a full design system, every screen to build, and the API contract to build against. Follow it in order — do not skip the design system section, it exists specifically so the UI does not come out looking like a generic AI-generated dashboard.

---

## 1. What You Are Building

**ChurnGuardAI** is a web app for small e-commerce businesses. It shows a support/ops team:
- which customers are at risk of churning (leaving and never coming back),
- why the AI thinks so (a churn risk score, explained),
- support tickets coming in and their detected sentiment,
- retention offers drafted automatically by AI agents, waiting for a human to approve, edit, or reject before they're sent to the customer.

The person using this app is a small-business support/ops manager — not a data scientist. The tone should feel calm, clear, and trustworthy: this app is showing them decisions an AI made about real customers and real money (discounts), so clarity and a sense of control matter more than flashiness.

This is being built as a portfolio/resume project (for an Agentic AI Engineer role) and as a college Data Science project, so the UI quality needs to look like a real, fundable SaaS product — not a rough dashboard template.

---

## 2. Tech Stack (use exactly this)

- **Framework:** Next.js 14+ (App Router), React, TypeScript (strict mode on)
- **Styling:** Tailwind CSS
- **Components:** shadcn/ui (install and customize — do not leave it looking like default shadcn)
- **Icons:** lucide-react
- **Charts:** Recharts
- **State management:** Zustand (for selected customer, pending offers list, live agent-activity feed)
- **Data fetching:** native `fetch` with a small typed API client (`/lib/api.ts`), or TanStack Query if you prefer caching/refetching
- **Real-time updates:** a WebSocket client hook (`useAgentActivityStream`) connecting to the backend's `/ws/agent-activity` endpoint
- **Deployment target:** Vercel (structure the app so it deploys with zero config)

Do not add authentication complexity for the MVP — a simple mocked "logged in as Support Manager" state is enough. Do not use Streamlit, Bootstrap, or Material UI.

---

## 3. Design System — Read This Before Writing Any UI Code

Do not default to generic AI-generated SaaS patterns. Specifically avoid: a warm cream background with a terracotta/clay accent; a near-black background with a single neon accent; identical rounded cards with the same soft grey shadow on everything; ALL-CAPS eyebrow labels above every heading; middle-dot separated meta text; arrows (→) appended to every button label; numbered 01/02/03 markers on content that isn't actually a sequence.

Instead, build to this specific design direction — it is deliberately chosen for this product (an AI making real decisions about real customers, that a human must trust and approve):

### Color palette
| Token | Hex | Use |
|---|---|---|
| `ink` (primary/dark) | `#14213D` | Primary text, nav rail, primary buttons |
| `paper` (background) | `#FAF7F3` | Main app background — warm, not stark white |
| `amber` (attention/risk) | `#E8A33D` | High-risk badges, pending-approval indicators |
| `teal` (safe/success) | `#1F9D82` | Retained/approved/low-risk states |
| `rose` (danger/reject) | `#D14D4D` | Reject actions, critical alerts |
| `ink-muted` | `#5B6472` | Secondary text |
| `line` | `#E3DDD3` | Borders/dividers (hairline, not card shadows) |

Do NOT use a drop-shadow on every card. Use the `line` color as a 1px border/divider instead — this is a deliberate choice: it reads as a calm "case file / ledger" aesthetic rather than a generic floating-card SaaS look.

### Typography
- **Display/headings:** `Fraunces` (a warm, characterful serif — gives the product personality without looking corporate-cold). Use it for page titles and section headers only.
- **Body & UI text:** `Inter` — for everything else: labels, buttons, paragraphs, nav.
- **Numbers & scores:** `IBM Plex Mono` — use this specifically for the churn risk score, percentages, and any statistic. This is intentional: mono numerals signal "this is a measured value, not a guess," which reinforces user trust in the AI's output.

Set a clear type scale (don't eyeball sizes): e.g. Display 32/40, H2 22/28, Body 15/22, Small 13/18, Mono-stat 28/32.

### Layout concept — "Case File," not "Card Grid"
Sketch (for your own reference while building):
```
┌───────────┬───────────────────────────────────────────────┐
│           │  Top strip: 4 big mono numbers, hairline       │
│  Left     │  dividers between them (not boxes)             │
│  rail nav │─────────────────────────────────────────────── │
│           │  Main content: either a queue/list (left,      │
│  - Overview│  narrower) + a detail panel (right, wider,     │
│  - Tickets │  "case file" style with sections, not cards)   │
│  - Approvals│  OR a full-width table/timeline depending     │
│  - Customers│  on the page                                  │
│  - Settings│                                                │
└───────────┴───────────────────────────────────────────────┘
```
- Left rail: persistent, `ink` background, white/paper text, icon + label nav items.
- Risk levels are shown as a left-border accent color on list rows (amber/teal/rose), not as separate colored card backgrounds — keep list rows visually quiet, let the accent color carry the meaning.
- The "why is this customer at risk" explanation (SHAP-style) should render as a simple horizontal bar list (factor name + bar + weight), not a generic pie chart.

### Motion
Use motion in exactly one place, deliberately: when an AI agent's status updates live (e.g. "Risk-Fusion Agent: analyzing…" → "Retention Agent: drafting offer…"), animate that status line with a subtle fade/typewriter-style transition. Do not add hover-lift effects or fade-in-on-scroll to every card — that reads as generic and templated.

### Writing/copy tone
Write from the support manager's point of view, plain language, active voice. Buttons say exactly what they do: "Approve offer," "Send reply," not "Submit." Empty states should explain what to do next, not just say "No data."

---

## 4. Screens to Build

### 4.1 Overview / Dashboard (`/`)
- Top strip: 4 stats in mono numerals with small labels — Total Customers, Flagged High-Risk Today, Retention Rate (last 30 days), Offers Pending Approval.
- A line chart (Recharts) showing "Customers Retained vs Churned" over the last 8 weeks.
- A short list preview: "Needs Your Attention" — top 5 pending offers, click-through to Approvals.

### 4.2 Ticket Queue (`/tickets`)
- List of support tickets: customer name, ticket snippet, a sentiment tag (Angry / Neutral / Happy — color-coded using the palette above), timestamp.
- Clicking a ticket opens a detail view: full conversation thread, the Support Agent's drafted/sent reply, and the customer's current churn risk score inline.

### 4.3 Customer Detail (`/customers/[id]`)
- Customer profile header: name, tenure, last order date, lifetime value.
- Churn Risk Score — large mono number (0–100) with a colored ring/indicator (teal/amber/rose by threshold).
- "Why this score" — horizontal bar list of top contributing factors (e.g. "Days since last order: 45 — high impact").
- Ticket history timeline for this customer.
- If there's a pending or past retention offer for this customer, show it inline with its status.

### 4.4 Approval Inbox (`/approvals`)
- This is the most important screen — it's where the human stays in control.
- List of AI-drafted retention offers awaiting a decision. Each row/panel shows: customer name + risk score, the drafted offer message (editable text area), the discount/action proposed, and a short "reasoning" line from the Retention Agent (e.g. "Customer frustrated about late delivery + 45 days since last order").
- Three actions per offer: **Approve & Send**, **Edit**, **Reject**. Edits should be saveable before sending.
- Show a small "Agent Activity" live feed on this page (via the WebSocket) so it feels like you're watching the AI team work — e.g. "Support Agent replied to ticket #482" → "Risk-Fusion Agent flagged customer as High Risk" → "Retention Agent drafted an offer."

### 4.5 Customers List (`/customers`)
- Table of all customers with churn score, last order date, and status (Safe / Watching / High Risk), sortable by risk score.

### 4.6 Settings (`/settings`)
- Simple form for business rules the Verifier Agent enforces: max discount %, risk score threshold for triggering an offer, proactive scan frequency (daily/weekly).

---

## 5. State Management (Zustand)

Create stores for:
- `useOffersStore` — pending offers list, approve/reject/edit actions (optimistic update, then call API)
- `useAgentActivityStore` — live feed of agent status events (populated by the WebSocket hook)
- `useSelectedCustomerStore` — currently viewed customer (used across dashboard ↔ detail navigation)

---

## 6. API Contract (build the frontend against this; backend will match it)

Base URL: read from `NEXT_PUBLIC_API_URL` env var.

```
GET  /api/dashboard/summary
GET  /api/customers
GET  /api/customers/{id}
GET  /api/tickets
POST /api/tickets                     (simulate a new incoming ticket)
GET  /api/offers/pending
POST /api/offers/{id}/approve
POST /api/offers/{id}/reject
PATCH /api/offers/{id}                (edit the drafted message before approving)
POST /api/scan/run                    (manually trigger the proactive batch scan, for demos)
WS   /ws/agent-activity               (streams { agent, message, timestamp } events)
```

While the backend isn't ready yet, build a `/lib/mockData.ts` file with realistic fake data matching these shapes exactly, and a feature flag (`USE_MOCK_DATA`) so you can develop the full UI before the backend exists, then flip it to real API calls later with zero component changes.

---

## 7. Non-Functional Requirements (quality floor — do not skip)

- Fully responsive down to mobile width (the left rail collapses to a bottom nav or hamburger on small screens).
- Visible keyboard focus states on all interactive elements.
- Respect `prefers-reduced-motion`.
- Color contrast must pass WCAG AA (check your palette combinations, especially amber-on-paper).
- No console errors/warnings on any screen.

---

## 8. Build Order

1. Scaffold Next.js + TypeScript + Tailwind + shadcn/ui. Configure the fonts (Fraunces, Inter, IBM Plex Mono via `next/font`) and Tailwind theme tokens for the color palette above.
2. Build the left rail nav + app shell layout.
3. Build `/lib/mockData.ts` and the typed API client.
4. Build the Overview/Dashboard screen.
5. Build the Ticket Queue + Ticket Detail.
6. Build the Customer Detail screen (including the "why this score" bar list).
7. Build the Approval Inbox (the centerpiece screen) + live Agent Activity feed (WebSocket hook, mock the stream with a fake timer until backend exists).
8. Build the Customers List and Settings screens.
9. Pass over every screen for responsiveness, focus states, and reduced-motion.
10. Wire `USE_MOCK_DATA = false` and connect to the real backend once it's ready.

## Definition of Done
- [ ] All 6 screens built and navigable from the left rail
- [ ] Design system (colors, fonts, layout style) applied consistently — no default shadcn look, no card-grid-with-shadows default
- [ ] Mock data mode works end-to-end with zero backend running
- [ ] Approval Inbox actions (approve/edit/reject) work against mock data with optimistic UI updates
- [ ] Responsive on mobile, keyboard-accessible, passes basic contrast check
- [ ] Ready to swap to the real API by flipping one flag
