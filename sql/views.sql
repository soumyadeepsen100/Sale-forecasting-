-- Monthly aggregation: the base time series for forecasting
DROP VIEW IF EXISTS monthly_sales;
CREATE VIEW monthly_sales AS
SELECT strftime('%Y-%m-01', o.order_date) AS month,
       ROUND(SUM(i.sales), 2)             AS sales,
       SUM(i.quantity)                    AS quantity,
       ROUND(AVG(i.discount), 4)          AS avg_discount,
       ROUND(SUM(i.profit), 2)            AS profit,
       COUNT(DISTINCT o.order_id)         AS orders
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
GROUP BY month;

-- Window-function features: lags, moving averages, growth, running total
DROP VIEW IF EXISTS monthly_features;
CREATE VIEW monthly_features AS
SELECT month,
       sales,
       LAG(sales, 1)  OVER w AS lag_1,
       LAG(sales, 12) OVER w AS lag_12,
       ROUND(AVG(sales) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS ma_3,
       ROUND(100.0 * (sales - LAG(sales, 1) OVER w) / LAG(sales, 1) OVER w, 2)            AS mom_growth_pct,
       ROUND(100.0 * (sales - LAG(sales, 12) OVER w) / LAG(sales, 12) OVER w, 2)          AS yoy_growth_pct,
       ROUND(SUM(sales) OVER (PARTITION BY substr(month, 1, 4) ORDER BY month), 2)        AS ytd_sales
FROM monthly_sales
WINDOW w AS (ORDER BY month);

-- Sales by sub-category per year, with rank inside each year
DROP VIEW IF EXISTS subcategory_yearly;
CREATE VIEW subcategory_yearly AS
SELECT substr(o.order_date, 1, 4) AS year,
       p.sub_category,
       ROUND(SUM(i.sales), 2)     AS sales,
       RANK() OVER (PARTITION BY substr(o.order_date, 1, 4) ORDER BY SUM(i.sales) DESC) AS rank_in_year
FROM order_items i
JOIN orders o   ON o.order_id = i.order_id
JOIN products p ON p.product_id = i.product_id
GROUP BY year, p.sub_category;

-- Sales by region and segment
DROP VIEW IF EXISTS region_segment_sales;
CREATE VIEW region_segment_sales AS
SELECT l.region, c.segment,
       ROUND(SUM(i.sales), 2)  AS sales,
       ROUND(SUM(i.profit), 2) AS profit
FROM order_items i
JOIN orders o     ON o.order_id = i.order_id
JOIN customers c  ON c.customer_id = o.customer_id
JOIN locations l  ON l.location_id = o.location_id
GROUP BY l.region, c.segment;
