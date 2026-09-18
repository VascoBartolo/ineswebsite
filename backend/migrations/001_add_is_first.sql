-- Adds bookings.is_first (TRUE = primeira consulta, FALSE = seguimento,
-- NULL = not recorded) and backfills the rows whose value can be derived with
-- certainty from how the app priced and sized the consultation.
--
-- Run ONCE against production Postgres BEFORE deploying the code that uses the
-- column. entrypoint.sh calls db.create_all(), which creates missing tables but
-- never adds columns to existing ones — so without this the column will not
-- exist and every query touching it fails.
--
-- Safe to re-run: the ALTER is guarded, and each UPDATE only touches rows still
-- NULL, so values set by hand afterwards are never overwritten.

BEGIN;

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_first BOOLEAN;

-- 1. Only a bebé's FIRST consultation was ever 90 minutes (compute_duration),
--    whatever the regime.
UPDATE bookings SET is_first = TRUE
 WHERE is_first IS NULL AND duration_minutes = 90;

-- 2. Presencial was priced 55€ first / 50€ following (compute_price). Online was
--    always 50€, so it says nothing and is excluded.
UPDATE bookings SET is_first = TRUE
 WHERE is_first IS NULL AND lower(regime) = 'presencial' AND price = 55;

UPDATE bookings SET is_first = FALSE
 WHERE is_first IS NULL AND lower(regime) = 'presencial' AND price = 50;

-- 3. A bebé at 60 minutes was therefore not a first consultation.
UPDATE bookings SET is_first = FALSE
 WHERE is_first IS NULL AND lower(sujeito) LIKE 'beb%' AND duration_minutes = 60;

-- Anything still NULL is an online adult consultation: 50€ and 60 minutes
-- whether first or following, so it is genuinely unrecoverable. Left NULL
-- rather than guessed.

COMMIT;

-- Check the outcome:
--   SELECT is_first, count(*) FROM bookings GROUP BY is_first;
