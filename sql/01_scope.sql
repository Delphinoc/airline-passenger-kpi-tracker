-- Rows in scope: Q1-Q2 2024, passenger service (scheduled F + non-scheduled L), one row per segment x aircraft type
CREATE OR REPLACE TEMP VIEW segments AS
SELECT
    row_id,
    UNIQUE_CARRIER                AS carrier,
    ORIGIN                        AS origin,
    DEST                          AS dest,
    CAST(YEAR AS INT)             AS year,
    CAST(QUARTER AS INT)          AS quarter,
    CAST(MONTH AS INT)            AS month,
    CLASS                         AS service_class,
    AIRCRAFT_TYPE                 AS aircraft_type,
    CAST(DEPARTURES_PERFORMED AS DOUBLE) AS departures,
    CAST(SEATS AS DOUBLE)         AS seats,
    CAST(PASSENGERS AS DOUBLE)    AS passengers,
    CAST(DISTANCE AS DOUBLE)      AS distance,
    CAST(PASSENGERS AS DOUBLE) * CAST(DISTANCE AS DOUBLE) AS rpm,
    CAST(SEATS AS DOUBLE)      * CAST(DISTANCE AS DOUBLE) AS asm
FROM raw_t100
WHERE CAST(YEAR AS INT) = 2024
  AND CAST(QUARTER AS INT) IN (1, 2)
  AND CLASS IN ('F', 'L')
