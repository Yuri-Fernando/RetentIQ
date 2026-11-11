-- SQL dump generated using DBML (dbml.dbdiagram.io)
-- Database: PostgreSQL
-- Generated at: 2026-11-10T20:33:37.577Z

CREATE TABLE "dim_country" (
  "country_id" integer PRIMARY KEY,
  "country" text UNIQUE NOT NULL
);

CREATE TABLE "dim_customer" (
  "customer_id" integer PRIMARY KEY,
  "primary_country" text NOT NULL
);

CREATE TABLE "dim_date" (
  "date_id" integer PRIMARY KEY,
  "date" date NOT NULL,
  "year" integer NOT NULL,
  "month" integer NOT NULL,
  "day" integer NOT NULL,
  "weekday" text NOT NULL,
  "is_weekend" boolean NOT NULL
);

CREATE TABLE "dim_product" (
  "stock_code" text PRIMARY KEY,
  "description" text NOT NULL
);

CREATE TABLE "etl_load_audit" (
  "load_id" bigint PRIMARY KEY,
  "loaded_at_utc" timestamptz NOT NULL,
  "source_name" text NOT NULL,
  "source_sha256" text,
  "source_rows" bigint NOT NULL,
  "dropped_missing_customer" bigint NOT NULL,
  "dropped_duplicates" bigint NOT NULL,
  "dropped_invalid_sales" bigint NOT NULL,
  "fact_sales_rows" bigint NOT NULL,
  "fact_cancelled_rows" bigint NOT NULL,
  "fact_sales_revenue" numeric(16,4) NOT NULL
);

CREATE TABLE "fact_sales" (
  "sale_id" bigint PRIMARY KEY,
  "invoice" text NOT NULL,
  "stock_code" text NOT NULL,
  "customer_id" integer NOT NULL,
  "country_id" integer NOT NULL,
  "date_id" integer NOT NULL,
  "invoice_date" timestamp NOT NULL,
  "quantity" integer NOT NULL,
  "price" numeric(12,4) NOT NULL,
  "revenue" numeric(14,4) NOT NULL
);

CREATE TABLE "fact_sales_cancelled" (
  "cancel_id" bigint PRIMARY KEY,
  "invoice" text NOT NULL,
  "stock_code" text NOT NULL,
  "customer_id" integer NOT NULL,
  "country_id" integer,
  "date_id" integer NOT NULL,
  "invoice_date" timestamp NOT NULL,
  "quantity" integer NOT NULL,
  "price" numeric(12,4) NOT NULL,
  "revenue" numeric(14,4) NOT NULL
);

CREATE INDEX "idx_fact_sales_customer" ON "fact_sales" ("customer_id");

CREATE INDEX "idx_fact_sales_date" ON "fact_sales" ("date_id");

CREATE INDEX "idx_fact_sales_product" ON "fact_sales" ("stock_code");

ALTER TABLE "fact_sales" ADD FOREIGN KEY ("country_id") REFERENCES "dim_country" ("country_id");

ALTER TABLE "fact_sales" ADD FOREIGN KEY ("customer_id") REFERENCES "dim_customer" ("customer_id");

ALTER TABLE "fact_sales" ADD FOREIGN KEY ("date_id") REFERENCES "dim_date" ("date_id");

ALTER TABLE "fact_sales" ADD FOREIGN KEY ("stock_code") REFERENCES "dim_product" ("stock_code");
