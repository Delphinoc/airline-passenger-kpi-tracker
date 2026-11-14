-- Attribute each segment row to the listed airline whose reported figures it should count toward.
-- mainline: the airline's own rows
-- wholly_owned / sole_contract: regional carrier flies for exactly one airline
-- multi_contract: regional flies for several airlines, so assign by hub endpoint only when exactly one partner's hub matches
CREATE OR REPLACE TEMP VIEW multi_match AS
SELECT s.row_id,
       COLLECT_SET(h.partner) AS hub_partners
FROM segments s
JOIN regional_partners rp ON rp.regional_carrier = s.carrier AND rp.link_type = 'multi_contract'
LEFT JOIN partner_hubs h ON h.partner = rp.partner AND h.airport IN (s.origin, s.dest)
GROUP BY s.row_id;

CREATE OR REPLACE TEMP VIEW attributed AS
SELECT s.*, s.carrier AS airline, 'mainline' AS link_type
FROM segments s
WHERE s.carrier IN (SELECT DISTINCT carrier FROM reported)
UNION ALL
SELECT s.*, rp.partner AS airline, rp.link_type
FROM segments s
JOIN regional_partners rp ON rp.regional_carrier = s.carrier AND rp.link_type IN ('wholly_owned', 'sole_contract')
UNION ALL
SELECT s.*,
       CASE WHEN SIZE(m.hub_partners) = 1 THEN m.hub_partners[0] ELSE 'UNALLOCATED' END AS airline,
       'multi_contract' AS link_type
FROM segments s
JOIN multi_match m ON m.row_id = s.row_id;
