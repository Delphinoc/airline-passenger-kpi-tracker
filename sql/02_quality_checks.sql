-- Each check returns one row: check name, rows flagged, and the action taken
SELECT 'null_keys' AS check_name, COUNT(*) AS rows_flagged, 'fail if > 0' AS action
FROM segments WHERE carrier IS NULL OR origin IS NULL OR dest IS NULL OR month IS NULL
UNION ALL
SELECT 'negative_values', COUNT(*), 'fail if > 0'
FROM segments WHERE seats < 0 OR passengers < 0 OR distance < 0 OR departures < 0
UNION ALL
SELECT 'quarter_month_mismatch', COUNT(*), 'fail if > 0'
FROM segments WHERE quarter <> CAST(CEIL(month / 3.0) AS INT)
UNION ALL
SELECT 'exact_duplicate_rows', COALESCE(SUM(n - 1), 0), 'fail if > 0'
FROM (SELECT carrier, origin, dest, month, service_class, aircraft_type, departures, seats, passengers, distance, COUNT(*) AS n
      FROM segments GROUP BY ALL HAVING COUNT(*) > 1)
UNION ALL
SELECT 'passengers_exceed_seats', COUNT(*), 'flag only'
FROM segments WHERE passengers > seats
UNION ALL
SELECT 'passengers_without_departures', COUNT(*), 'flag only'
FROM segments WHERE passengers > 0 AND departures = 0
UNION ALL
SELECT 'inconsistent_distance_same_pair', COUNT(*), 'flag only'
FROM (SELECT origin, dest FROM segments GROUP BY origin, dest HAVING COUNT(DISTINCT distance) > 1)
