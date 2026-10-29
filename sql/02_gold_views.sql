-- GOLD: business-ready views (no load, no storage - always reflects silver).

CREATE OR REPLACE VIEW gold.beds_by_wing AS
SELECT COALESCE(wing, 'Unknown')                 AS wing,
       COUNT(*)                                  AS wards,
       COUNT(beds_available)                     AS wards_reporting_beds,
       COALESCE(SUM(beds_available), 0)          AS total_beds_available,
       ROUND(AVG(beds_available), 1)             AS avg_beds_per_ward
FROM silver.wards
GROUP BY COALESCE(wing, 'Unknown')
ORDER BY wing;

CREATE OR REPLACE VIEW gold.beds_by_department AS
SELECT COALESCE(department, 'Unknown')           AS department,
       COUNT(*)                                  AS wards,
       COUNT(beds_available)                     AS wards_reporting_beds,
       COALESCE(SUM(beds_available), 0)          AS total_beds_available,
       ROUND(AVG(beds_available), 1)             AS avg_beds_per_ward
FROM silver.wards
GROUP BY COALESCE(department, 'Unknown')
ORDER BY department;

CREATE OR REPLACE VIEW gold.wards_needing_attention AS
SELECT ward_id,
       wing,
       department,
       beds_available,
       capacity_status,
       CASE
           WHEN capacity_status = 'Full'    THEN 'No beds available'
           WHEN capacity_status = 'Low'     THEN 'Low bed availability'
           WHEN capacity_status = 'Unknown' THEN 'Bed count missing or invalid'
           ELSE 'Data issue flagged during cleaning'
       END AS reason,
       notes
FROM silver.wards
WHERE capacity_status IN ('Full', 'Low', 'Unknown')
   OR notes IS NOT NULL
ORDER BY ward_id;

CREATE OR REPLACE VIEW gold.data_quality_summary AS
SELECT COUNT(*)                                          AS total_wards,
       COUNT(*) FILTER (WHERE wing IS NULL)              AS missing_wing,
       COUNT(*) FILTER (WHERE department IS NULL)        AS missing_department,
       COUNT(*) FILTER (WHERE beds_available IS NULL)    AS missing_beds,
       COUNT(*) FILTER (WHERE merged_duplicates)         AS wards_from_merged_duplicates,
       COUNT(*) FILTER (WHERE notes IS NOT NULL)         AS wards_with_notes,
       (SELECT COUNT(*) FROM silver.rejected_rows)       AS rejected_rows
FROM silver.wards;
