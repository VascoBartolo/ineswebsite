# Frontend Review & Fix Plan (2026-09-21)

> **Status: IMPLEMENTED on `feature/frontend-review`, one commit per task.** Answers: Q1 yes, Q2 delete the scaffold and all unused images, Q3 lucide, Q4 você, Q5 yes, Q6 one commit per task.
> Changes from the plan:
> - The time-zone badge became a note giving the Azores offset for the chosen date (UTC−1 winter, UTC+0 summer), plus each slot's local time for visitors in other zones.
> - Page titles use a `usePageTitle` hook rather than React `<title>`, because index.html's static `<title>` wins.
> - `baby1`/`baby2` were left as they were: recompressing them made them larger.
> - **Still open:** wiring `eslint-plugin-jsx-a11y` into `eslint.config.js`, which is blocked by the config-protection hook. The code already passes its recommended rules, except the deliberate `autoFocus` on the admin login.
>
> Branch: `feature/frontend-review` (from `main` @ `8947026`).
> Verify every task with: `cd website && npx eslint . && npx vite build`, plus the browser checks listed in each task.

**Scope:** `website/` only: React 19 + Vite 8, plain JSX, nginx image. The backend was reviewed separately (`2026-09-21-backend-hardening.md`, PR branch `feature/backend-review`). Items that need a backend change are listed separately and not planned here.

---

## How this was reviewed

| Check | Result |
|---|---|
| `eslint .` | **4 errors, 1 warning**: two `set-state-in-effect` errors (BookingPage.jsx:252, StatsTab.jsx:18), one unused variable (BookingPage.jsx:260) and one missing dep (useInView.js:21) |
| `npm audit` | **react-router 7.17.0: high** (open redirect, route-matching DoS, plus RSC advisories that don't apply to our SPA). Dev tooling: 5 more (postcss, nanoid, brace-expansion, browserslist, baseline-browser-mapping). All have fixes available |
| `vite build` | One **532 KB** JS chunk (163 KB gzipped); admin panel, booking page and legal pages all ship to every visitor |
| Live site (`curl -I` against inesbandarranutricao.com) | JS served **uncompressed** (503 KB, no `Content-Encoding`); **no security headers** (no CSP, X-Frame-Options, nosniff or HSTS); **no Cache-Control**; hero photo is **2.1 MB** |
| Manual read | BookingPage.jsx, all of `src/admin/`, App.jsx, main.jsx, nginx.conf, Dockerfile, vite config |
| Second reviewer (react-reviewer agent) | Landing components, legal pages, index.html. Findings spot-checked: nav burger, reduced motion, image sizes, contrast |

**Done well:** the contact form (labels, double-submit guard, error states); `CalendarPicker`'s cancelled-fetch pattern; admin modals guard Escape during saves; the `toISO` helper avoids UTC date shifting; no `dangerouslySetInnerHTML`; `rel="noopener noreferrer"` on external links; `legalInfo.js` as a single source of truth; the email is deliberately kept out of deep-link URLs.

---

## Findings

### High

| # | Finding | Where |
|---|---|---|
| H1 | **Wrong time slots can be shown for a date.** `fetchSlots` has no cancellation: click day A, then day B quickly, and if A's response lands last, A's slots appear under B. The booking then fails with 409 (best case) | `BookingPage.jsx:264-286` |
| H2 | **Calendar days can't be used by keyboard or screen reader.** Days are `<div onClick>` with no role, focus or label; the month arrows are `‹` `›` with no accessible name | `BookingPage.jsx:125-149` |
| H3 | **Expired admin session fails silently.** `adminApi` throws `unauthorized`, but nothing catches it: the bookings table shows "Sem marcações para estes filtros." and Stats stays on "A carregar…" forever. Sessions now expire after 7 days (backend branch), so this will happen regularly | `adminApi.js:9`, `BookingsTab.jsx:32-45`, `StatsTab.jsx:12-18` |
| H4 | **No security headers** on the site or admin panel: the admin panel can be framed (clickjacking), with no CSP, nosniff, Referrer-Policy or HSTS | `nginx.conf` |
| H5 | **Vulnerable `react-router`** in the production bundle | `package.json` |
| H6 | **Form labels not linked to inputs** (no `htmlFor`/`id`) in booking step 4, the lookup form, the edit-request form, the admin edit modal, admin filters and admin login (placeholder only). Screen readers announce unlabeled fields | BookingPage.jsx:728-773, 821-840, 905-913; EditBookingModal.jsx:87-126; BookingsTab/StatsTab filters; AdminLogin.jsx:28 |
| H7 | **Mobile menu has no disclosure semantics**: no `aria-expanded`/`aria-controls`, no Escape, no focus handling | `Navbar.jsx:88` |
| H8 | **Motion ignores `prefers-reduced-motion`** on every public page (framer-motion slides, scales and parallax) | all `components/*.jsx`, BookingPage |

### Medium

| # | Finding | Where |
|---|---|---|
| M1 | Lint errors: deep-link sets state in an effect (use lazy initial state); unused `price`; StatsTab `load()` in an effect; `useInView` `options` dep | see lint row above |
| M2 | Admin search fires a request **on every keystroke**, and out-of-order responses can overwrite newer results. Same stale-response risk on filter changes in Stats | `BookingsTab.jsx:32-45`, `StatsTab.jsx` |
| M3 | Admin save errors all read "Não foi possível guardar." The backend now returns `invalid_email`, `field_too_long`, `invalid_price` etc. with a `field`; show them. Login shows "Palavra-passe incorreta." even when throttled (429) | `EditBookingModal.jsx:71-76`, `AdminLogin.jsx:15` |
| M4 | Admin modals: no `role="dialog"`/`aria-labelledby`, no initial focus, focus not restored on close. The edit modal's backdrop click closes it mid-save and discards edits (Escape is guarded, the backdrop isn't) | `EditBookingModal.jsx:81`, `ConfirmModal.jsx` |
| M5 | Admin cancel always emails the client. The backend branch adds `notify`; the confirm dialog should offer "Notificar o cliente por email" | `BookingsTab.jsx:186-193`, `adminApi.js:30` |
| M6 | Chart labels strip a hardcoded `'2026-'`, so from January they read "2027-S03" | `MiniBarChart.jsx:25` |
| M7 | No input `maxLength` matching the server caps (name 200, email 200, phone 50, context/message 2000), so over-long input comes back as a generic error | BookingPage step 4 and edit-request |
| M8 | Booking tabs and choice cards aren't exposed as tabs or toggles (`aria-selected`/`aria-pressed`). Step changes don't move focus or announce, and errors lack `role="alert"` | `BookingPage.jsx:481-488, 515-575, 776` |
| M9 | "Horário dos Açores (GMT-1)" is wrong half the year: the Azores are UTC+0 in summer | `BookingPage.jsx:665` |
| M10 | Mixed register on the booking page: *Receberás / Guarda / O teu email / Verifica a tua conexão* (tu) next to *Escolha / Descreva / Introduza* (você). The emails were standardised on *você* | `BookingPage.jsx:335, 428, 445, 753` |
| M11 | **Images**: hero 2.1 MB (eager, no dimensions → layout shift); About 2.2 + 1.9 MB (not lazy); logo `vermelho.png` 724 KB, loaded on every page **and in every email** | Hero.jsx:108, About.jsx:47-50, `public/images` |
| M12 | nginx: **gzip off**; no long-cache for hashed `/assets/*`; `index.html` has no `no-cache`; `server_tokens` on | `nginx.conf` |
| M13 | No code splitting: admin, booking and legal pages in the home bundle | `App.jsx` |
| M14 | No 404 route (unknown paths render a blank page); scroll position carries across route changes; only legal pages set `<title>` | `App.jsx`, `LegalLayout.jsx:14-19` |
| M15 | Rose outline button text is 3.45:1 on white (AA needs 4.5:1); footer copyright is ~3.75:1 on dark | `Hero.css:131`, `Footer.css:102` |
| M16 | No skip-to-content link | `App.jsx` |
| M17 | Docker build uses `npm install`, not `npm ci`, so it doesn't honour the lockfile strictly | `Dockerfile:5` |
| M18 | Phone and email hardcoded in Contact, Footer and the BookingPage footer, although `legalInfo.js` already holds them | Contact.jsx:107,114,226; Footer.jsx:67; BookingPage.jsx:951 |

### Low

| # | Finding |
|---|---|
| L1 | Cancel/"Pedir Alteração" buttons are shown for bookings whose date has passed; the backend refuses, but the client sees an error after clicking |
| L2 | Admin icon buttons (✎ ⊘ 🗑) are named by their glyph; `title` isn't a reliable accessible name, so add `aria-label` |
| L3 | Admin tabs lack tab semantics; Toast is a clickable `<div>` |
| L4 | `robots.txt` allows `/admin`, and the admin page has no `noindex` |
| L5 | Two icon libraries: lucide-react (Navbar, Contact, Footer, LegalLayout, BookingPage) and @phosphor-icons/react (About, Services) |
| L6 | Unused files: `src/assets/{hero.png,react.svg,vite.svg}` (Vite scaffold) and `public/icons.svg`; plus 9 unreferenced photos in `public/images` (~8.5 MB shipped in the image, never loaded) |
| L7 | Admin edit modal: `sujeito` is free text; a select (adulto/bebé plus the current value if different) would match the booking form |
| L8 | Opening hours are typed out in BookingPage.jsx:661-663 and duplicate the backend's `WORK_WINDOWS` |

---

## Tasks

Ordered so each is independently verifiable. Behaviour changes get a browser check; the repo has no frontend test runner, and adding one is not part of this plan.

### Task 1: Dependencies and build — H5, M17
- [ ] `npm audit fix` (react-router 7.x patch plus dev tooling). Confirm `npm audit` reports 0 and the build passes.
- [ ] Dockerfile: `npm install` → `npm ci`.

### Task 2: Lint clean, plus the a11y lint rules — M1
- [ ] BookingPage: read `?tab`/`?ref` in `useState(() => …)` initialisers instead of an effect; remove the unused `price`.
- [ ] StatsTab: move the fetch into the effect with a cancelled flag (this also fixes the stale-response part of M2).
- [ ] `useInView`: depend on the individual option values, or keep `options` in a ref.
- [ ] *(if Q1 = yes)* Add `eslint-plugin-jsx-a11y` (recommended config) and fix what it reports; most of it is covered by Tasks 4–6.
- [ ] Done when `npx eslint .` reports 0 problems.

### Task 3: Booking correctness — H1, M7, M9, L1
- [ ] `fetchSlots`: an `AbortController` per request, aborted when date or criteria change, so only the latest response is applied.
- [ ] `maxLength` on name (200), email (200), phone (50), context (2000) and the edit-request message (2000).
- [ ] Time-zone badge: "Horário dos Açores", with the current offset computed through `Intl.DateTimeFormat(..., { timeZone: 'Atlantic/Azores', timeZoneName: 'shortOffset' })`.
- [ ] Hide Cancel/Pedir Alteração when the booking's date and time have already passed.
- [ ] Browser: rapid date switching always shows the clicked date's slots (throttle the network in dev tools); a full booking works end to end against `dev-local`.

### Task 4: Booking accessibility and copy — H2, H6 (booking), M8, M10
- [ ] Calendar days become `<button>`s with an `aria-label` (for example "segunda-feira, 6 de outubro, 4 vagas"), `aria-pressed` for the selected day, and `disabled` when unavailable. Month arrows get `aria-label` "Mês anterior"/"Mês seguinte". The grid layout is unchanged.
- [ ] `htmlFor`/`id` on every label and input on the page.
- [ ] Tabs: `role="tablist"`/`tab`/`aria-selected`. Choice cards: `aria-pressed`.
- [ ] Step change: move focus to the step heading (`tabIndex={-1}`). Error messages get `role="alert"`.
- [ ] Rewrite the *tu* strings in the *você* register used everywhere else.
- [ ] Browser: complete a booking using only the keyboard; check with VoiceOver that the calendar days and fields are announced.

### Task 5: Admin panel — H3, H6 (admin), M2–M6, L2, L3, L7
- [ ] `adminApi`: an `onUnauthorized` hook that `AdminPage` registers to switch back to the login screen on any 401.
- [ ] BookingsTab: catch errors (show a toast); debounce search by 300 ms; abort superseded requests.
- [ ] EditBookingModal: map the server `error`/`field` to messages (for example "Email inválido.", "Nome demasiado longo."). AdminLogin: 429 → "Demasiadas tentativas. Tente mais tarde."
- [ ] Modals: `role="dialog"`/`alertdialog` with `aria-labelledby`; focus the first field on open and restore it on close; the backdrop is ignored while busy.
- [ ] Cancel confirm: a "Notificar o cliente por email" checkbox (default on) that sends `{ notify }`. Harmless before the backend branch merges (the old backend ignores the body).
- [ ] MiniBarChart: derive the label from the period itself, with no hardcoded year.
- [ ] `aria-label` on the icon buttons; tab semantics on the admin tabs; Toast becomes a `<button>` or loses its click handler.
- [ ] *(if Q5 = yes)* `sujeito` becomes a select with an "unlisted" fallback, like `tipo_consulta`.
- [ ] Browser: expire the cookie and click a filter, which should land on the login screen; type quickly in search, and results should match the final text; each validation error names its field.

### Task 6: Landing page accessibility — H7, H8, M15, M16
- [ ] Navbar: `aria-expanded`, `aria-controls`, Escape closes and refocuses the burger, focus moves into the panel on open.
- [ ] `<MotionConfig reducedMotion="user">` in `main.jsx`, plus a CSS `@media (prefers-reduced-motion: reduce)` guard for CSS animations and transitions.
- [ ] Skip link ("Saltar para o conteúdo") as the first focusable element; `id="main"` on each page's main landmark.
- [ ] Contrast: `.btn-secondary` text becomes `--mauve` (4.88:1); footer copyright opacity 0.4 becomes 0.65.
- [ ] Browser: with reduced motion emulated there are no slide/scale animations; the burger works with the keyboard on a 375 px viewport.

### Task 7: Routing, bundle, SEO — M13, M14, L4
- [ ] `React.lazy` + `Suspense` for `/marcar-consulta`, `/admin` and both legal pages. Expected result: a noticeably smaller home chunk (numbers reported after the build).
- [ ] A catch-all `*` route with a small branded 404 page.
- [ ] Scroll to the top on pathname change, keeping the Navbar's existing hash scrolling.
- [ ] A `<title>` per route (React 19 hoists `<title>`), replacing LegalLayout's `document.title` effect.
- [ ] `robots.txt`: `Disallow: /admin`; `<meta name="robots" content="noindex">` rendered on the admin page.

### Task 8: nginx — H4, M12
- [ ] `gzip on` for JS, CSS, SVG, JSON, text and HTML.
- [ ] `/assets/`: `Cache-Control: public, max-age=31536000, immutable`. `index.html`: `no-cache`. Images: 7 days.
- [ ] Security headers on every response: `Content-Security-Policy` (`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `Strict-Transport-Security: max-age=31536000`. `server_tokens off`.
  - `'unsafe-inline'` for styles is required, because framer-motion writes inline `style` attributes. Scripts stay strict: the only inline script is JSON-LD, a data block that CSP doesn't block.
- [ ] Verify: `docker build` the image, run it, `curl -I` for headers and `Content-Encoding: gzip`, then load every route in the browser with the console open and confirm there are **no CSP violations**.

### Task 9: Images and consistency — M11, M18, L5, L6, L8
- [ ] Resize and recompress the photos actually used, **keeping filenames** (index.html's og:image and the email logo URL depend on them), with macOS `sips`. Photos: longest edge 1600 px, JPEG quality 80. Logo `vermelho.png`: 600 px wide. Targets: hero under 300 KB, logo under 60 KB.
- [ ] `width`/`height` on the hero and About images; `loading="lazy"` on the About images (the hero stays eager with `fetchpriority="high"`).
- [ ] Contact, Footer and the BookingPage footer read phone and email from `legalInfo.js`.
- [ ] *(if Q2 = yes)* Delete the unused scaffold assets and the 9 unreferenced photos.
- [ ] *(if Q3 = yes)* Replace the phosphor icons in About and Services with lucide equivalents and drop the dependency.
- [ ] Browser: compare before and after screenshots of home at 1440 px and 375 px; the photos should look the same.

---

## Needs a backend change (not in this plan)

- **Booking lookup puts the client's email in the URL** (`GET /api/bookings/lookup?reference=…&email=…`, BookingPage.jsx:350). That lands in nginx access logs and browser history, which contradicts the page's own privacy comment (line 245). The fix is a `POST` endpoint; it belongs on the backend branch or a follow-up.
- Prices and durations are computed in both BookingPage.jsx (`getPrice`/`getDuration`) and the backend. The Stripe plan makes the server the only authority; until then they must be changed together.

## Open questions, which decide scope

1. **Add `eslint-plugin-jsx-a11y`** as a dev dependency, so accessibility regressions fail lint? *(recommended: yes)*
2. **Delete unused files**: 9 unreferenced photos in `public/images` (~8.5 MB) and the Vite scaffold assets? They could be originals you want to keep; if so, I'll leave them. *(recommended: delete the scaffold; you decide on the photos)*
3. **Unify the icon libraries** on lucide? The About and Services icons would change shape slightly. *(recommended: yes, small visual change)*
4. **Booking page register:** standardise on *você*, as in the emails? *(recommended: yes)*
5. **Admin `sujeito`** as a select instead of free text? *(recommended: yes)*
6. **Commit granularity:** one commit per task (recommended, easier to review) or a single commit.

## Not included

- Adding a frontend test framework (Vitest/Testing Library). There isn't one today; worth a separate decision.
- A visual redesign; copy changes beyond the register fix.
- TypeScript migration.
