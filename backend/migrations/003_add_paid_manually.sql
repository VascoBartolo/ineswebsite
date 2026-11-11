-- Adds paid_manually to bookings: an online booking the admin marks as paid
-- outside Stripe (e.g. booked before Stripe Checkout existed).
--
-- Run ONCE against production Postgres BEFORE deploying the code that uses the
-- column: db.create_all() never adds columns to an existing table, and every
-- booking query selects all mapped columns.
--
-- Additive and nullable, so existing rows stay valid (NULL = not marked).
-- Safe to re-run.

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS paid_manually BOOLEAN;
