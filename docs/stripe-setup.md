# Stripe setup — IB Nutrição

How online consultations are paid: the client pays on Stripe's hosted Checkout when booking.
Cards (incl. Apple Pay / Google Pay) and PayPal are **held** and only **charged when Inês
confirms**; MB WAY is charged at once and refunded if the booking is not confirmed. Presencial
consultations are not paid online.

Dashboard menu names drift over time. If a label differs, use the dashboard search bar (top)
with the name given here.

## A. Create and secure the account (Inês)

1. Go to `dashboard.stripe.com/register` and sign up with `inesbandarranutricao@gmail.com`.
   Country **Portugal**.
2. Turn on two-step authentication (Settings → Personal details → Two-step authentication).
   Stripe requires it before going live.
3. Invite Vasco as a team member with the **Developer** role (Settings → Team and security →
   Team → Add member), so no login is shared.

## B. Activate the account (live payments only; testing works without it)

4. Settings → Business → **Activate payments**:
   - Business type: **Individual / sole proprietor** (trabalhadora independente), Portugal.
   - Personal details: legal name, date of birth, home address, phone, **NIF**.
   - Industry: medical / health practitioner. Website: `https://inesbandarranutricao.com`.
     Product description: "Consultas de nutrição online, pagas antecipadamente na marcação."
   - Public details: statement descriptor **`IB NUTRICAO`** (what appears on bank statements),
     support email and phone from `website/src/pages/legalInfo.js`.
   - Payouts: the **IBAN** that receives the money.
   - Identity: upload the Cartão de Cidadão when asked.
5. Accept the Stripe Services Agreement. It incorporates Stripe's Data Processing Agreement
   (RGPD art. 28), so no separate DPA needs signing. Save a PDF of both for the compliance
   records.

## C. Payment methods

6. Settings → Payments → **Payment methods** (default configuration):
   - **On:** Cards, Apple Pay, Google Pay, **MB WAY**.
   - **PayPal:** *Turn on*. Stripe asks you to connect or create a **PayPal Business** account;
     approval can take a few days.
   - **Off:** everything else. **This list is what clients see**: the code takes the methods
     from the dashboard, so only switch on what Inês wants to accept. Multibanco is always
     excluded in code (`backend/payments.py`, `EXCLUDED_METHODS`) because it settles days later.
   - **PayPal**: the dashboard asks for a registered domain — PayPal → *Configurar domínios* →
     add `inesbandarranutricao.com` (in the sandbox *and* in live mode). Checkout decides per
     browser which methods to show: embedded/automated browsers may hide PayPal next to other
     methods, so check it in a normal Chrome or Safari window.
   - Apple Pay and Google Pay need nothing extra. Google Pay only shows in Chrome with a card
     saved in the Google account; Apple Pay only in Safari/Apple devices with Wallet set up.
7. Settings → **Branding**: logo, brand colour; check the Checkout preview.
8. Settings → **Customer emails**: optionally turn on *Successful payments* and *Refunds*
   receipts. These are Stripe receipts, **not** faturas — the fatura-recibo still comes from
   Portal das Finanças.
9. Settings → **Payouts**: weekly or daily. New accounts have an initial payout delay of about
   7 days.
10. Leave Stripe Tax **off** (services likely VAT-exempt under art. 9.º CIVA; confirm with the
    accountant). Leave Radar on its default rules.

## D. Developer keys (test mode first)

11. Turn on **Test mode** (toggle top right, or use a Sandbox).
12. Developers → API keys → **Create restricted key** "ib-nutricao-backend":
    - Write: Checkout Sessions, PaymentIntents, Refunds.
    - Read: Charges, Events.
    - None: everything else.

    Copy the `rk_test_…` key into `STRIPE_SECRET_KEY`. A restricted key limits the damage if it
    leaks. No publishable key is needed: the site redirects server-side and loads no Stripe code.
13. Developers → **Webhooks** → *Add endpoint / destination*:
    - URL: `https://inesbandarranutricao.com/api/stripe/webhook`
    - API version: `2026-08-26.dahlia` (pinned by `stripe==15.6.1` in `backend/requirements.txt`).
    - Events: `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
      `checkout.session.async_payment_failed`, `checkout.session.expired`,
      `payment_intent.canceled`, `charge.refunded`.
    - Copy the **signing secret** `whsec_…` into `STRIPE_WEBHOOK_SECRET`.

## E. Local development (Vasco)

14. `brew install stripe/stripe-cli/stripe`, then `stripe login` — on the browser page pick the
    **sandbox** (the account whose key is in `STRIPE_SECRET_KEY`); `stripe config --list` shows
    which account the CLI is on.
15. Forward the events the app handles (current CLI versions require `--events`); it prints a
    local `whsec_…`, which differs from the dashboard endpoint's:

    ```bash
    stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired,payment_intent.canceled,charge.refunded --forward-to 127.0.0.1:5055/api/stripe/webhook
    ```
16. Start the local stack with the test keys in the environment (`dev-local/backend.py` does not
    read `backend/.env`):

    ```bash
    STRIPE_SECRET_KEY=rk_test_… STRIPE_WEBHOOK_SECRET=whsec_… SITE_URL=http://localhost:5173 dev-local/start.sh
    ```
17. Test payments on the Checkout page (any future expiry, any CVC):
    - `4242 4242 4242 4242` — held, then captured when confirmed.
    - `4000 0025 0000 3155` — requires 3-D Secure.
    - `4000 0000 0000 0002` — declined.
    - MB WAY: any valid Portuguese mobile number (e.g. `912 345 678`); the sandbox approves it
      after a few seconds on the "Verifique seu aplicativo MB WAY" screen.
    - PayPal shows a Stripe test page with authorize/fail buttons.
18. `stripe trigger payment_intent.canceled` simulates a lapsed hold; refunds from the dashboard
    test the `charge.refunded` sync.

## F. Production secrets (Vasco)

19. Run `backend/migrations/002_add_payments.sql` against production Postgres **before**
    deploying the new backend, then verify the columns exist.
20. Add `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to `backend/.env` and run the deploy
    script; it sets them as the ACA secrets `stripe-secret-key` / `stripe-webhook-secret`, and
    skips them when they are absent so a re-run never blanks live keys. Never commit them and
    never put them in `website/`.

## G. Go live

21. Once activation (B) is approved, switch to **Live mode** and repeat steps 12–13. Live keys
    and webhooks are separate: you get new `rk_live_…` and `whsec_…` values.
22. Update `backend/.env`, redeploy, make one real online booking with your own card, confirm it
    from the email link, check the capture in Payments, then refund it from the admin panel and
    check it in Stripe.
23. Monthly: download Stripe's fee invoices (Settings → Documents) for the accountant —
    autoliquidação (reverse charge) may apply to Stripe's Irish fees even under the art. 9.º
    exemption. Reconcile payouts against the faturas-recibo issued, and issue a nota de crédito
    for every refund of an invoiced payment.
