-- Cumulative estimates by attribution stage, per airline and quarter
WITH stages AS (
    SELECT 1 AS stage, 'mainline only' AS stage_name, ARRAY('mainline') AS links
    UNION ALL SELECT 2, '+ wholly-owned regionals', ARRAY('mainline', 'wholly_owned')
    UNION ALL SELECT 3, '+ sole-contract regionals', ARRAY('mainline', 'wholly_owned', 'sole_contract')
    UNION ALL SELECT 4, '+ hub-allocated multi-contract regionals', ARRAY('mainline', 'wholly_owned', 'sole_contract', 'multi_contract')
)
SELECT st.stage, st.stage_name, a.airline, a.year, a.quarter,
       SUM(a.passengers) / 1e3 AS passengers,
       SUM(a.rpm) / 1e6        AS rpm,
       SUM(a.asm) / 1e6        AS asm
FROM attributed a
CROSS JOIN stages st
WHERE ARRAY_CONTAINS(st.links, a.link_type)
  AND a.airline IN (SELECT DISTINCT carrier FROM reported)
GROUP BY ALL
