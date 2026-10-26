-- Adds terms acceptance (compliance plan, Workstream A) and Stripe payment
-- columns to bookings.
--
-- Run ONCE against production Postgres BEFORE deploying the code that uses the
-- columns: db.create_all() never adds columns to an existing table, and every
-- booking query selects all mapped columns.
--
-- Additive and nullable, so existing rows stay valid: presencial, admin-created
-- and pre-payment bookings simply have no payment (payment_status NULL).
-- Safe to re-run.

BEGIN;

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS terms_accepted_at     TIMESTAMP;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS terms_version         VARCHAR(32);

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_status        VARCHAR(20);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_method_type   VARCHAR(30);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS stripe_session_id     VARCHAR(255);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS stripe_payment_intent VARCHAR(255);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS amount_paid           NUMERIC(10,2);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS amount_refunded       NUMERIC(10,2);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS paid_at               TIMESTAMP;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS hold_expires_at       TIMESTAMP;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS capture_before        TIMESTAMP;

-- One Checkout Session can never back two bookings.
CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_stripe_session
    ON bookings (stripe_session_id) WHERE stripe_session_id IS NOT NULL;

COMMIT;

-- Check the outcome:
--   SELECT column_name, data_type, is_nullable FROM information_schema.columns
--    WHERE table_name = 'bookings' ORDER BY ordinal_position;
