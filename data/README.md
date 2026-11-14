# Data

## Raw data (not committed, ~79 MB)

`raw/T_T100_SEGMENT_ALL_CARRIER.csv`: BTS T-100 Segment (All Carriers), January to July 2024. One row per carrier, origin, destination, aircraft type and month, with departures, seats, passengers and distance. The pipeline uses Q1 and Q2 2024 (Jan–Jun).

Download it either way:

1. **BTS TranStats** (official): https://www.transtats.bts.gov → Air Carrier Statistics (Form 41 Traffic) – All Carriers → *T-100 Segment (All Carriers)*. Select 2024, months Jan–Jun (or Jan–Jul), all fields, and download as CSV.
2. **Public mirror**: `data/T_T100_SEGMENT_ALL_CARRIER.csv` in https://github.com/admacpherson/T-100-Aviation-Data

Save it as `data/raw/T_T100_SEGMENT_ALL_CARRIER.csv`.

## Reference data (committed)

| File | What it is |
|---|---|
| `reference/reported_operating_stats.csv` | Q1 and Q2 2024 passengers, RPMs and ASMs as reported by each airline, with the source filing for every number. Q1 values are six-month totals minus Q2 where the Q2 release gave both (noted in `source_metric_name`). |
| `reference/regional_partners.csv` | Which mainline airline(s) each regional carrier flew for in 2024, and how (wholly owned, sole contract, or shared across several airlines). |
| `reference/partner_hubs.csv` | Hub airports used to assign shared regional flying to one airline. |

Reported figures come from each airline's Q2 2024 earnings release or 10-Q:

- Southwest: https://www.sec.gov/Archives/edgar/data/92380/000009238024000108/er-6302024xerdoc.htm
- United: https://www.sec.gov/Archives/edgar/data/0000100517/000010051724000117/ual_06302024erex991.htm
- Delta: https://www.sec.gov/Archives/edgar/data/27904/000168316824004743/delta_ex9901.htm
- JetBlue: Q2 2024 10-Q (https://s202.q4cdn.com/853609783/files/doc_financials/2024/q2/e722bdf1-bd56-436a-96fe-00c20704f7b4.pdf) and Q1 2024 release (https://www.businesswire.com/news/home/20240423551519/en)
