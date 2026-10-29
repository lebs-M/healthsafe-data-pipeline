-- Ad-hoc analysis examples (the "Consume" layer). Run with: psql "$PSQL_URL" -f sql/queries.sql
SELECT * FROM gold.beds_by_wing;
SELECT * FROM gold.beds_by_department;
SELECT * FROM gold.wards_needing_attention;
SELECT * FROM gold.data_quality_summary;
SELECT * FROM silver.pipeline_runs ORDER BY run_id DESC LIMIT 5;
