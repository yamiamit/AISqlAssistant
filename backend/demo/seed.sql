-- =============================================================================
-- AI SQL Assistant — Live Demo Seed Data
-- Run after schema.sql, against an empty database (schema.sql already DROPs
-- and recreates every table, so IDs always start from 1).
--
-- Every value below is either a literal or a deterministic expression over a
-- fixed input (a row's own generated number, or a FK it just received) --
-- there is no call to random() anywhere in this file. Re-running schema.sql
-- + seed.sql against a fresh database always produces byte-identical data,
-- which the "Try with sample data" demo (and anything scripted against it)
-- depends on for stability.
--
-- categories:   8   (literal)
-- suppliers:    12  (literal)
-- customers:    200 (literal rows, generated once by a throwaway script using
--               fixed lookup arrays + modulo arithmetic -- no `random`)
-- products:     80  (literal name/category/price/cost; supplier_id,
--               stock_quantity, and created_at are inline SQL expressions
--               over the product's own row number, so Postgres computes them
--               exactly instead of us hand-computing 80 modulo results)
-- orders:       1000, spread 2023-01-01..2025-12-31
-- order_items:  ~2500 (1-4 per order, deterministic on order_id)
-- payments:     1000 (one per order)
-- reviews:      ~360 (deterministic subset of order_items, covering all 80 products)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- categories
-- -----------------------------------------------------------------------------
INSERT INTO categories (category_name, description) VALUES
('Electronics', 'Phones, laptops, and gadgets'),
('Home & Kitchen', 'Appliances and kitchenware'),
('Books', 'Fiction, non-fiction, and academic'),
('Clothing', 'Men''s and women''s apparel'),
('Sports & Outdoors', 'Fitness and outdoor gear'),
('Beauty & Personal Care', 'Skincare and grooming'),
('Toys & Games', 'Kids toys and board games'),
('Office Supplies', 'Stationery and office equipment');

-- -----------------------------------------------------------------------------
-- suppliers
-- -----------------------------------------------------------------------------
INSERT INTO suppliers (supplier_name, country, contact_email, lead_time_days) VALUES
('Nova Electronics Ltd', 'China', 'contact@novaelectronics.example', 14),
('Everest Home Goods', 'India', 'sales@everesthome.example', 10),
('PageTurner Distributors', 'USA', 'orders@pageturner.example', 5),
('Fabrique Textiles', 'Bangladesh', 'info@fabriquetextiles.example', 21),
('Summit Sports Supply', 'Vietnam', 'contact@summitsports.example', 18),
('Pure Glow Cosmetics', 'South Korea', 'hello@pureglow.example', 12),
('Playtime Manufacturing', 'China', 'sales@playtimemfg.example', 16),
('OfficeCraft Supplies', 'Germany', 'info@officecraft.example', 7),
('BrightTech Components', 'Taiwan', 'support@brighttech.example', 9),
('HomeStyle Imports', 'Vietnam', 'contact@homestyle.example', 20),
('Northwind Books Ltd', 'UK', 'orders@northwindbooks.example', 6),
('Active Gear Co', 'USA', 'sales@activegear.example', 8);

-- -----------------------------------------------------------------------------
-- customers (200 rows)
-- -----------------------------------------------------------------------------
INSERT INTO customers (first_name, last_name, email, phone, city, country, signup_date, is_active) VALUES
('Aarav', 'Khan', 'aarav.khan1@example.com', '+1-555-2001', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '0 days', TRUE),
('Priya', 'Reddy', 'priya.reddy2@example.com', '+1-555-2002', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '547 days', TRUE),
('James', 'Das', 'james.das3@example.com', '+1-555-2003', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1094 days', TRUE),
('Emma', 'Johnson', 'emma.johnson4@example.com', '+1-555-2004', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '546 days', TRUE),
('Liam', 'Taylor', 'liam.taylor5@example.com', '+1-555-2005', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1093 days', TRUE),
('Olivia', 'Moore', 'olivia.moore6@example.com', '+1-555-2006', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '545 days', TRUE),
('Noah', 'Sharma', 'noah.sharma7@example.com', '+1-555-2007', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1092 days', TRUE),
('Ava', 'Patel', 'ava.patel8@example.com', '+1-555-2008', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '544 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer9@example.com', '+1-555-2009', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1091 days', TRUE),
('Mia', 'Kumar', 'mia.kumar10@example.com', '+1-555-2010', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '543 days', TRUE),
('Henry', 'Williams', 'henry.williams11@example.com', '+1-555-2011', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1090 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson12@example.com', '+1-555-2012', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '542 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson13@example.com', '+1-555-2013', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1089 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta14@example.com', '+1-555-2014', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '541 days', TRUE),
('Ethan', 'Singh', 'ethan.singh15@example.com', '+1-555-2015', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1088 days', TRUE),
('Isla', 'Verma', 'isla.verma16@example.com', '+1-555-2016', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '540 days', TRUE),
('Kabir', 'Smith', 'kabir.smith17@example.com', '+1-555-2017', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1087 days', FALSE),
('Sophia', 'Brown', 'sophia.brown18@example.com', '+1-555-2018', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '539 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas19@example.com', '+1-555-2019', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1086 days', TRUE),
('Grace', 'Martin', 'grace.martin20@example.com', '+1-555-2020', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '538 days', TRUE),
('Aarav', 'Khan', 'aarav.khan21@example.com', '+1-555-2021', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1085 days', TRUE),
('Priya', 'Reddy', 'priya.reddy22@example.com', '+1-555-2022', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '537 days', TRUE),
('James', 'Das', 'james.das23@example.com', '+1-555-2023', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1084 days', TRUE),
('Emma', 'Johnson', 'emma.johnson24@example.com', '+1-555-2024', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '536 days', TRUE),
('Liam', 'Taylor', 'liam.taylor25@example.com', '+1-555-2025', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1083 days', TRUE),
('Olivia', 'Moore', 'olivia.moore26@example.com', '+1-555-2026', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '535 days', TRUE),
('Noah', 'Sharma', 'noah.sharma27@example.com', '+1-555-2027', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1082 days', TRUE),
('Ava', 'Patel', 'ava.patel28@example.com', '+1-555-2028', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '534 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer29@example.com', '+1-555-2029', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1081 days', TRUE),
('Mia', 'Kumar', 'mia.kumar30@example.com', '+1-555-2030', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '533 days', TRUE),
('Henry', 'Williams', 'henry.williams31@example.com', '+1-555-2031', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1080 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson32@example.com', '+1-555-2032', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '532 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson33@example.com', '+1-555-2033', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1079 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta34@example.com', '+1-555-2034', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '531 days', FALSE),
('Ethan', 'Singh', 'ethan.singh35@example.com', '+1-555-2035', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1078 days', TRUE),
('Isla', 'Verma', 'isla.verma36@example.com', '+1-555-2036', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '530 days', TRUE),
('Kabir', 'Smith', 'kabir.smith37@example.com', '+1-555-2037', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1077 days', TRUE),
('Sophia', 'Brown', 'sophia.brown38@example.com', '+1-555-2038', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '529 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas39@example.com', '+1-555-2039', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1076 days', TRUE),
('Grace', 'Martin', 'grace.martin40@example.com', '+1-555-2040', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '528 days', TRUE),
('Aarav', 'Khan', 'aarav.khan41@example.com', '+1-555-2041', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1075 days', TRUE),
('Priya', 'Reddy', 'priya.reddy42@example.com', '+1-555-2042', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '527 days', TRUE),
('James', 'Das', 'james.das43@example.com', '+1-555-2043', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1074 days', TRUE),
('Emma', 'Johnson', 'emma.johnson44@example.com', '+1-555-2044', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '526 days', TRUE),
('Liam', 'Taylor', 'liam.taylor45@example.com', '+1-555-2045', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1073 days', TRUE),
('Olivia', 'Moore', 'olivia.moore46@example.com', '+1-555-2046', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '525 days', TRUE),
('Noah', 'Sharma', 'noah.sharma47@example.com', '+1-555-2047', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1072 days', TRUE),
('Ava', 'Patel', 'ava.patel48@example.com', '+1-555-2048', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '524 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer49@example.com', '+1-555-2049', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1071 days', TRUE),
('Mia', 'Kumar', 'mia.kumar50@example.com', '+1-555-2050', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '523 days', TRUE),
('Henry', 'Williams', 'henry.williams51@example.com', '+1-555-2051', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1070 days', FALSE),
('Charlotte', 'Anderson', 'charlotte.anderson52@example.com', '+1-555-2052', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '522 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson53@example.com', '+1-555-2053', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1069 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta54@example.com', '+1-555-2054', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '521 days', TRUE),
('Ethan', 'Singh', 'ethan.singh55@example.com', '+1-555-2055', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1068 days', TRUE),
('Isla', 'Verma', 'isla.verma56@example.com', '+1-555-2056', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '520 days', TRUE),
('Kabir', 'Smith', 'kabir.smith57@example.com', '+1-555-2057', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1067 days', TRUE),
('Sophia', 'Brown', 'sophia.brown58@example.com', '+1-555-2058', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '519 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas59@example.com', '+1-555-2059', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1066 days', TRUE),
('Grace', 'Martin', 'grace.martin60@example.com', '+1-555-2060', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '518 days', TRUE),
('Aarav', 'Khan', 'aarav.khan61@example.com', '+1-555-2061', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1065 days', TRUE),
('Priya', 'Reddy', 'priya.reddy62@example.com', '+1-555-2062', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '517 days', TRUE),
('James', 'Das', 'james.das63@example.com', '+1-555-2063', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1064 days', TRUE),
('Emma', 'Johnson', 'emma.johnson64@example.com', '+1-555-2064', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '516 days', TRUE),
('Liam', 'Taylor', 'liam.taylor65@example.com', '+1-555-2065', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1063 days', TRUE),
('Olivia', 'Moore', 'olivia.moore66@example.com', '+1-555-2066', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '515 days', TRUE),
('Noah', 'Sharma', 'noah.sharma67@example.com', '+1-555-2067', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1062 days', TRUE),
('Ava', 'Patel', 'ava.patel68@example.com', '+1-555-2068', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '514 days', FALSE),
('Vivaan', 'Iyer', 'vivaan.iyer69@example.com', '+1-555-2069', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1061 days', TRUE),
('Mia', 'Kumar', 'mia.kumar70@example.com', '+1-555-2070', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '513 days', TRUE),
('Henry', 'Williams', 'henry.williams71@example.com', '+1-555-2071', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1060 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson72@example.com', '+1-555-2072', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '512 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson73@example.com', '+1-555-2073', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1059 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta74@example.com', '+1-555-2074', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '511 days', TRUE),
('Ethan', 'Singh', 'ethan.singh75@example.com', '+1-555-2075', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1058 days', TRUE),
('Isla', 'Verma', 'isla.verma76@example.com', '+1-555-2076', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '510 days', TRUE),
('Kabir', 'Smith', 'kabir.smith77@example.com', '+1-555-2077', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1057 days', TRUE),
('Sophia', 'Brown', 'sophia.brown78@example.com', '+1-555-2078', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '509 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas79@example.com', '+1-555-2079', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1056 days', TRUE),
('Grace', 'Martin', 'grace.martin80@example.com', '+1-555-2080', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '508 days', TRUE),
('Aarav', 'Khan', 'aarav.khan81@example.com', '+1-555-2081', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1055 days', TRUE),
('Priya', 'Reddy', 'priya.reddy82@example.com', '+1-555-2082', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '507 days', TRUE),
('James', 'Das', 'james.das83@example.com', '+1-555-2083', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1054 days', TRUE),
('Emma', 'Johnson', 'emma.johnson84@example.com', '+1-555-2084', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '506 days', TRUE),
('Liam', 'Taylor', 'liam.taylor85@example.com', '+1-555-2085', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1053 days', FALSE),
('Olivia', 'Moore', 'olivia.moore86@example.com', '+1-555-2086', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '505 days', TRUE),
('Noah', 'Sharma', 'noah.sharma87@example.com', '+1-555-2087', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1052 days', TRUE),
('Ava', 'Patel', 'ava.patel88@example.com', '+1-555-2088', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '504 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer89@example.com', '+1-555-2089', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1051 days', TRUE),
('Mia', 'Kumar', 'mia.kumar90@example.com', '+1-555-2090', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '503 days', TRUE),
('Henry', 'Williams', 'henry.williams91@example.com', '+1-555-2091', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1050 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson92@example.com', '+1-555-2092', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '502 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson93@example.com', '+1-555-2093', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1049 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta94@example.com', '+1-555-2094', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '501 days', TRUE),
('Ethan', 'Singh', 'ethan.singh95@example.com', '+1-555-2095', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1048 days', TRUE),
('Isla', 'Verma', 'isla.verma96@example.com', '+1-555-2096', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '500 days', TRUE),
('Kabir', 'Smith', 'kabir.smith97@example.com', '+1-555-2097', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '997 days', TRUE),
('Sophia', 'Brown', 'sophia.brown98@example.com', '+1-555-2098', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '499 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas99@example.com', '+1-555-2099', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1046 days', TRUE),
('Grace', 'Martin', 'grace.martin100@example.com', '+1-555-2100', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '498 days', TRUE),
('Aarav', 'Khan', 'aarav.khan101@example.com', '+1-555-2101', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1045 days', TRUE),
('Priya', 'Reddy', 'priya.reddy102@example.com', '+1-555-2102', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '497 days', FALSE),
('James', 'Das', 'james.das103@example.com', '+1-555-2103', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1044 days', TRUE),
('Emma', 'Johnson', 'emma.johnson104@example.com', '+1-555-2104', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '496 days', TRUE),
('Liam', 'Taylor', 'liam.taylor105@example.com', '+1-555-2105', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1043 days', TRUE),
('Olivia', 'Moore', 'olivia.moore106@example.com', '+1-555-2106', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '495 days', TRUE),
('Noah', 'Sharma', 'noah.sharma107@example.com', '+1-555-2107', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1042 days', TRUE),
('Ava', 'Patel', 'ava.patel108@example.com', '+1-555-2108', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '494 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer109@example.com', '+1-555-2109', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1041 days', TRUE),
('Mia', 'Kumar', 'mia.kumar110@example.com', '+1-555-2110', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '493 days', TRUE),
('Henry', 'Williams', 'henry.williams111@example.com', '+1-555-2111', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1040 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson112@example.com', '+1-555-2112', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '492 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson113@example.com', '+1-555-2113', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1039 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta114@example.com', '+1-555-2114', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '491 days', TRUE),
('Ethan', 'Singh', 'ethan.singh115@example.com', '+1-555-2115', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1038 days', TRUE),
('Isla', 'Verma', 'isla.verma116@example.com', '+1-555-2116', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '490 days', TRUE),
('Kabir', 'Smith', 'kabir.smith117@example.com', '+1-555-2117', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1037 days', TRUE),
('Sophia', 'Brown', 'sophia.brown118@example.com', '+1-555-2118', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '489 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas119@example.com', '+1-555-2119', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1036 days', FALSE),
('Grace', 'Martin', 'grace.martin120@example.com', '+1-555-2120', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '488 days', TRUE),
('Aarav', 'Khan', 'aarav.khan121@example.com', '+1-555-2121', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1035 days', TRUE),
('Priya', 'Reddy', 'priya.reddy122@example.com', '+1-555-2122', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '487 days', TRUE),
('James', 'Das', 'james.das123@example.com', '+1-555-2123', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1034 days', TRUE),
('Emma', 'Johnson', 'emma.johnson124@example.com', '+1-555-2124', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '486 days', TRUE),
('Liam', 'Taylor', 'liam.taylor125@example.com', '+1-555-2125', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1033 days', TRUE),
('Olivia', 'Moore', 'olivia.moore126@example.com', '+1-555-2126', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '485 days', TRUE),
('Noah', 'Sharma', 'noah.sharma127@example.com', '+1-555-2127', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1032 days', TRUE),
('Ava', 'Patel', 'ava.patel128@example.com', '+1-555-2128', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '484 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer129@example.com', '+1-555-2129', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1031 days', TRUE),
('Mia', 'Kumar', 'mia.kumar130@example.com', '+1-555-2130', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '483 days', TRUE),
('Henry', 'Williams', 'henry.williams131@example.com', '+1-555-2131', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1030 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson132@example.com', '+1-555-2132', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '482 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson133@example.com', '+1-555-2133', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1029 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta134@example.com', '+1-555-2134', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '481 days', TRUE),
('Ethan', 'Singh', 'ethan.singh135@example.com', '+1-555-2135', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1028 days', TRUE),
('Isla', 'Verma', 'isla.verma136@example.com', '+1-555-2136', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '480 days', FALSE),
('Kabir', 'Smith', 'kabir.smith137@example.com', '+1-555-2137', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1027 days', TRUE),
('Sophia', 'Brown', 'sophia.brown138@example.com', '+1-555-2138', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '479 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas139@example.com', '+1-555-2139', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1026 days', TRUE),
('Grace', 'Martin', 'grace.martin140@example.com', '+1-555-2140', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '478 days', TRUE),
('Aarav', 'Khan', 'aarav.khan141@example.com', '+1-555-2141', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1025 days', TRUE),
('Priya', 'Reddy', 'priya.reddy142@example.com', '+1-555-2142', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '477 days', TRUE),
('James', 'Das', 'james.das143@example.com', '+1-555-2143', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1024 days', TRUE),
('Emma', 'Johnson', 'emma.johnson144@example.com', '+1-555-2144', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '476 days', TRUE),
('Liam', 'Taylor', 'liam.taylor145@example.com', '+1-555-2145', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1023 days', TRUE),
('Olivia', 'Moore', 'olivia.moore146@example.com', '+1-555-2146', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '475 days', TRUE),
('Noah', 'Sharma', 'noah.sharma147@example.com', '+1-555-2147', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1022 days', TRUE),
('Ava', 'Patel', 'ava.patel148@example.com', '+1-555-2148', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '474 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer149@example.com', '+1-555-2149', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1021 days', TRUE),
('Mia', 'Kumar', 'mia.kumar150@example.com', '+1-555-2150', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '473 days', TRUE),
('Henry', 'Williams', 'henry.williams151@example.com', '+1-555-2151', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1020 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson152@example.com', '+1-555-2152', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '472 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson153@example.com', '+1-555-2153', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1019 days', FALSE),
('Amelia', 'Gupta', 'amelia.gupta154@example.com', '+1-555-2154', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '471 days', TRUE),
('Ethan', 'Singh', 'ethan.singh155@example.com', '+1-555-2155', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1018 days', TRUE),
('Isla', 'Verma', 'isla.verma156@example.com', '+1-555-2156', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '470 days', TRUE),
('Kabir', 'Smith', 'kabir.smith157@example.com', '+1-555-2157', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1017 days', TRUE),
('Sophia', 'Brown', 'sophia.brown158@example.com', '+1-555-2158', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '469 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas159@example.com', '+1-555-2159', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1016 days', TRUE),
('Grace', 'Martin', 'grace.martin160@example.com', '+1-555-2160', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '468 days', TRUE),
('Aarav', 'Khan', 'aarav.khan161@example.com', '+1-555-2161', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1015 days', TRUE),
('Priya', 'Reddy', 'priya.reddy162@example.com', '+1-555-2162', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '467 days', TRUE),
('James', 'Das', 'james.das163@example.com', '+1-555-2163', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1014 days', TRUE),
('Emma', 'Johnson', 'emma.johnson164@example.com', '+1-555-2164', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '466 days', TRUE),
('Liam', 'Taylor', 'liam.taylor165@example.com', '+1-555-2165', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1013 days', TRUE),
('Olivia', 'Moore', 'olivia.moore166@example.com', '+1-555-2166', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '465 days', TRUE),
('Noah', 'Sharma', 'noah.sharma167@example.com', '+1-555-2167', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1012 days', TRUE),
('Ava', 'Patel', 'ava.patel168@example.com', '+1-555-2168', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '464 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer169@example.com', '+1-555-2169', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1011 days', TRUE),
('Mia', 'Kumar', 'mia.kumar170@example.com', '+1-555-2170', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '463 days', FALSE),
('Henry', 'Williams', 'henry.williams171@example.com', '+1-555-2171', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1010 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson172@example.com', '+1-555-2172', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '462 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson173@example.com', '+1-555-2173', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '1009 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta174@example.com', '+1-555-2174', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '461 days', TRUE),
('Ethan', 'Singh', 'ethan.singh175@example.com', '+1-555-2175', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '1008 days', TRUE),
('Isla', 'Verma', 'isla.verma176@example.com', '+1-555-2176', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '460 days', TRUE),
('Kabir', 'Smith', 'kabir.smith177@example.com', '+1-555-2177', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '1007 days', TRUE),
('Sophia', 'Brown', 'sophia.brown178@example.com', '+1-555-2178', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '459 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas179@example.com', '+1-555-2179', 'London', 'UK', DATE '2023-01-01' + INTERVAL '1006 days', TRUE),
('Grace', 'Martin', 'grace.martin180@example.com', '+1-555-2180', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '458 days', TRUE),
('Aarav', 'Khan', 'aarav.khan181@example.com', '+1-555-2181', 'New York', 'USA', DATE '2023-01-01' + INTERVAL '1005 days', TRUE),
('Priya', 'Reddy', 'priya.reddy182@example.com', '+1-555-2182', 'Manchester', 'UK', DATE '2023-01-01' + INTERVAL '457 days', TRUE),
('James', 'Das', 'james.das183@example.com', '+1-555-2183', 'Mumbai', 'India', DATE '2023-01-01' + INTERVAL '1004 days', TRUE),
('Emma', 'Johnson', 'emma.johnson184@example.com', '+1-555-2184', 'Seattle', 'USA', DATE '2023-01-01' + INTERVAL '456 days', TRUE),
('Liam', 'Taylor', 'liam.taylor185@example.com', '+1-555-2185', 'Bristol', 'UK', DATE '2023-01-01' + INTERVAL '1003 days', TRUE),
('Olivia', 'Moore', 'olivia.moore186@example.com', '+1-555-2186', 'Delhi', 'India', DATE '2023-01-01' + INTERVAL '455 days', TRUE),
('Noah', 'Sharma', 'noah.sharma187@example.com', '+1-555-2187', 'Chicago', 'USA', DATE '2023-01-01' + INTERVAL '1002 days', FALSE),
('Ava', 'Patel', 'ava.patel188@example.com', '+1-555-2188', 'Sydney', 'Australia', DATE '2023-01-01' + INTERVAL '454 days', TRUE),
('Vivaan', 'Iyer', 'vivaan.iyer189@example.com', '+1-555-2189', 'Bengaluru', 'India', DATE '2023-01-01' + INTERVAL '1001 days', TRUE),
('Mia', 'Kumar', 'mia.kumar190@example.com', '+1-555-2190', 'San Francisco', 'USA', DATE '2023-01-01' + INTERVAL '453 days', TRUE),
('Henry', 'Williams', 'henry.williams191@example.com', '+1-555-2191', 'Melbourne', 'Australia', DATE '2023-01-01' + INTERVAL '1000 days', TRUE),
('Charlotte', 'Anderson', 'charlotte.anderson192@example.com', '+1-555-2192', 'Pune', 'India', DATE '2023-01-01' + INTERVAL '452 days', TRUE),
('Aditya', 'Jackson', 'aditya.jackson193@example.com', '+1-555-2193', 'Austin', 'USA', DATE '2023-01-01' + INTERVAL '999 days', TRUE),
('Amelia', 'Gupta', 'amelia.gupta194@example.com', '+1-555-2194', 'Toronto', 'Canada', DATE '2023-01-01' + INTERVAL '451 days', TRUE),
('Ethan', 'Singh', 'ethan.singh195@example.com', '+1-555-2195', 'Hyderabad', 'India', DATE '2023-01-01' + INTERVAL '998 days', TRUE),
('Isla', 'Verma', 'isla.verma196@example.com', '+1-555-2196', 'Boston', 'USA', DATE '2023-01-01' + INTERVAL '450 days', TRUE),
('Kabir', 'Smith', 'kabir.smith197@example.com', '+1-555-2197', 'Vancouver', 'Canada', DATE '2023-01-01' + INTERVAL '997 days', TRUE),
('Sophia', 'Brown', 'sophia.brown198@example.com', '+1-555-2198', 'Chennai', 'India', DATE '2023-01-01' + INTERVAL '449 days', TRUE),
('Rohan', 'Thomas', 'rohan.thomas199@example.com', '+1-555-2199', 'London', 'UK', DATE '2023-01-01' + INTERVAL '996 days', TRUE),
('Grace', 'Martin', 'grace.martin200@example.com', '+1-555-2200', 'Singapore', 'Singapore', DATE '2023-01-01' + INTERVAL '448 days', TRUE);

-- -----------------------------------------------------------------------------
-- products (80 rows). supplier_id / stock_quantity / created_at are inline
-- deterministic expressions over the product's own row number (1..80) so
-- Postgres computes them exactly -- see file header.
-- -----------------------------------------------------------------------------
INSERT INTO products (product_name, category_id, supplier_id, price, cost, stock_quantity, created_at) VALUES
    ('Wireless Mouse', 1, (((1 - 1) % 12) + 1), 19.99, 9.50, (15 + ((1 * 11) % 200)), (DATE '2023-01-01' + ((1 * 9) % 700))),
    ('Mechanical Keyboard', 1, (((2 - 1) % 12) + 1), 59.99, 28.00, (15 + ((2 * 11) % 200)), (DATE '2023-01-01' + ((2 * 9) % 700))),
    ('27-inch 4K Monitor', 1, (((3 - 1) % 12) + 1), 249.99, 140.00, (15 + ((3 * 11) % 200)), (DATE '2023-01-01' + ((3 * 9) % 700))),
    ('Noise Cancelling Headphones', 1, (((4 - 1) % 12) + 1), 129.99, 65.00, (15 + ((4 * 11) % 200)), (DATE '2023-01-01' + ((4 * 9) % 700))),
    ('USB-C Hub', 1, (((5 - 1) % 12) + 1), 34.99, 15.00, (15 + ((5 * 11) % 200)), (DATE '2023-01-01' + ((5 * 9) % 700))),
    ('Smartphone Stand', 1, (((6 - 1) % 12) + 1), 14.99, 6.00, (15 + ((6 * 11) % 200)), (DATE '2023-01-01' + ((6 * 9) % 700))),
    ('Portable Bluetooth Speaker', 1, (((7 - 1) % 12) + 1), 44.99, 20.00, (15 + ((7 * 11) % 200)), (DATE '2023-01-01' + ((7 * 9) % 700))),
    ('1TB External SSD', 1, (((8 - 1) % 12) + 1), 89.99, 55.00, (15 + ((8 * 11) % 200)), (DATE '2023-01-01' + ((8 * 9) % 700))),
    ('Wireless Charging Pad', 1, (((9 - 1) % 12) + 1), 24.99, 10.00, (15 + ((9 * 11) % 200)), (DATE '2023-01-01' + ((9 * 9) % 700))),
    ('Webcam 1080p', 1, (((10 - 1) % 12) + 1), 39.99, 18.00, (15 + ((10 * 11) % 200)), (DATE '2023-01-01' + ((10 * 9) % 700))),
    ('Stainless Steel Cookware Set', 2, (((11 - 1) % 12) + 1), 89.99, 45.00, (15 + ((11 * 11) % 200)), (DATE '2023-01-01' + ((11 * 9) % 700))),
    ('Air Fryer 5L', 2, (((12 - 1) % 12) + 1), 79.99, 40.00, (15 + ((12 * 11) % 200)), (DATE '2023-01-01' + ((12 * 9) % 700))),
    ('Electric Kettle', 2, (((13 - 1) % 12) + 1), 29.99, 13.00, (15 + ((13 * 11) % 200)), (DATE '2023-01-01' + ((13 * 9) % 700))),
    ('Ceramic Dinnerware Set', 2, (((14 - 1) % 12) + 1), 64.99, 30.00, (15 + ((14 * 11) % 200)), (DATE '2023-01-01' + ((14 * 9) % 700))),
    ('Robot Vacuum Cleaner', 2, (((15 - 1) % 12) + 1), 199.99, 110.00, (15 + ((15 * 11) % 200)), (DATE '2023-01-01' + ((15 * 9) % 700))),
    ('Non-Stick Frying Pan', 2, (((16 - 1) % 12) + 1), 22.99, 9.50, (15 + ((16 * 11) % 200)), (DATE '2023-01-01' + ((16 * 9) % 700))),
    ('Coffee Maker', 2, (((17 - 1) % 12) + 1), 54.99, 26.00, (15 + ((17 * 11) % 200)), (DATE '2023-01-01' + ((17 * 9) % 700))),
    ('Knife Block Set', 2, (((18 - 1) % 12) + 1), 49.99, 22.00, (15 + ((18 * 11) % 200)), (DATE '2023-01-01' + ((18 * 9) % 700))),
    ('Bedding Sheet Set Queen', 2, (((19 - 1) % 12) + 1), 39.99, 17.00, (15 + ((19 * 11) % 200)), (DATE '2023-01-01' + ((19 * 9) % 700))),
    ('Memory Foam Pillow', 2, (((20 - 1) % 12) + 1), 27.99, 11.00, (15 + ((20 * 11) % 200)), (DATE '2023-01-01' + ((20 * 9) % 700))),
    ('The Silent Orchard (Novel)', 3, (((21 - 1) % 12) + 1), 14.99, 6.00, (15 + ((21 * 11) % 200)), (DATE '2023-01-01' + ((21 * 9) % 700))),
    ('Atomic Habits Workbook', 3, (((22 - 1) % 12) + 1), 12.99, 5.00, (15 + ((22 * 11) % 200)), (DATE '2023-01-01' + ((22 * 9) % 700))),
    ('A History of Modern India', 3, (((23 - 1) % 12) + 1), 21.99, 9.00, (15 + ((23 * 11) % 200)), (DATE '2023-01-01' + ((23 * 9) % 700))),
    ('Introduction to Algorithms', 3, (((24 - 1) % 12) + 1), 59.99, 30.00, (15 + ((24 * 11) % 200)), (DATE '2023-01-01' + ((24 * 9) % 700))),
    ('The Midnight Library', 3, (((25 - 1) % 12) + 1), 13.99, 5.50, (15 + ((25 * 11) % 200)), (DATE '2023-01-01' + ((25 * 9) % 700))),
    ('Cooking for Beginners', 3, (((26 - 1) % 12) + 1), 18.99, 7.50, (15 + ((26 * 11) % 200)), (DATE '2023-01-01' + ((26 * 9) % 700))),
    ('Kids'' Picture Atlas', 3, (((27 - 1) % 12) + 1), 16.99, 6.50, (15 + ((27 * 11) % 200)), (DATE '2023-01-01' + ((27 * 9) % 700))),
    ('Financial Freedom Handbook', 3, (((28 - 1) % 12) + 1), 19.99, 8.00, (15 + ((28 * 11) % 200)), (DATE '2023-01-01' + ((28 * 9) % 700))),
    ('The Art of SQL', 3, (((29 - 1) % 12) + 1), 34.99, 15.00, (15 + ((29 * 11) % 200)), (DATE '2023-01-01' + ((29 * 9) % 700))),
    ('Mystery at Ravenswood', 3, (((30 - 1) % 12) + 1), 11.99, 4.50, (15 + ((30 * 11) % 200)), (DATE '2023-01-01' + ((30 * 9) % 700))),
    ('Men''s Cotton T-Shirt', 4, (((31 - 1) % 12) + 1), 15.99, 6.00, (15 + ((31 * 11) % 200)), (DATE '2023-01-01' + ((31 * 9) % 700))),
    ('Women''s Denim Jacket', 4, (((32 - 1) % 12) + 1), 49.99, 22.00, (15 + ((32 * 11) % 200)), (DATE '2023-01-01' + ((32 * 9) % 700))),
    ('Running Shorts', 4, (((33 - 1) % 12) + 1), 19.99, 8.00, (15 + ((33 * 11) % 200)), (DATE '2023-01-01' + ((33 * 9) % 700))),
    ('Wool Blend Sweater', 4, (((34 - 1) % 12) + 1), 44.99, 20.00, (15 + ((34 * 11) % 200)), (DATE '2023-01-01' + ((34 * 9) % 700))),
    ('Formal Dress Shirt', 4, (((35 - 1) % 12) + 1), 34.99, 15.00, (15 + ((35 * 11) % 200)), (DATE '2023-01-01' + ((35 * 9) % 700))),
    ('Yoga Leggings', 4, (((36 - 1) % 12) + 1), 27.99, 11.00, (15 + ((36 * 11) % 200)), (DATE '2023-01-01' + ((36 * 9) % 700))),
    ('Winter Puffer Jacket', 4, (((37 - 1) % 12) + 1), 89.99, 42.00, (15 + ((37 * 11) % 200)), (DATE '2023-01-01' + ((37 * 9) % 700))),
    ('Cotton Socks (3-pack)', 4, (((38 - 1) % 12) + 1), 9.99, 3.50, (15 + ((38 * 11) % 200)), (DATE '2023-01-01' + ((38 * 9) % 700))),
    ('Summer Sundress', 4, (((39 - 1) % 12) + 1), 32.99, 14.00, (15 + ((39 * 11) % 200)), (DATE '2023-01-01' + ((39 * 9) % 700))),
    ('Leather Belt', 4, (((40 - 1) % 12) + 1), 24.99, 10.00, (15 + ((40 * 11) % 200)), (DATE '2023-01-01' + ((40 * 9) % 700))),
    ('Yoga Mat', 5, (((41 - 1) % 12) + 1), 24.99, 10.00, (15 + ((41 * 11) % 200)), (DATE '2023-01-01' + ((41 * 9) % 700))),
    ('Adjustable Dumbbell Set', 5, (((42 - 1) % 12) + 1), 129.99, 65.00, (15 + ((42 * 11) % 200)), (DATE '2023-01-01' + ((42 * 9) % 700))),
    ('Camping Tent 4-Person', 5, (((43 - 1) % 12) + 1), 149.99, 78.00, (15 + ((43 * 11) % 200)), (DATE '2023-01-01' + ((43 * 9) % 700))),
    ('Insulated Water Bottle', 5, (((44 - 1) % 12) + 1), 19.99, 8.00, (15 + ((44 * 11) % 200)), (DATE '2023-01-01' + ((44 * 9) % 700))),
    ('Trail Running Shoes', 5, (((45 - 1) % 12) + 1), 74.99, 35.00, (15 + ((45 * 11) % 200)), (DATE '2023-01-01' + ((45 * 9) % 700))),
    ('Resistance Bands Set', 5, (((46 - 1) % 12) + 1), 17.99, 6.50, (15 + ((46 * 11) % 200)), (DATE '2023-01-01' + ((46 * 9) % 700))),
    ('Cycling Helmet', 5, (((47 - 1) % 12) + 1), 39.99, 17.00, (15 + ((47 * 11) % 200)), (DATE '2023-01-01' + ((47 * 9) % 700))),
    ('Hiking Backpack 40L', 5, (((48 - 1) % 12) + 1), 69.99, 32.00, (15 + ((48 * 11) % 200)), (DATE '2023-01-01' + ((48 * 9) % 700))),
    ('Foam Roller', 5, (((49 - 1) % 12) + 1), 22.99, 9.00, (15 + ((49 * 11) % 200)), (DATE '2023-01-01' + ((49 * 9) % 700))),
    ('Sleeping Bag', 5, (((50 - 1) % 12) + 1), 54.99, 26.00, (15 + ((50 * 11) % 200)), (DATE '2023-01-01' + ((50 * 9) % 700))),
    ('Vitamin C Serum', 6, (((51 - 1) % 12) + 1), 24.99, 9.50, (15 + ((51 * 11) % 200)), (DATE '2023-01-01' + ((51 * 9) % 700))),
    ('Electric Toothbrush', 6, (((52 - 1) % 12) + 1), 39.99, 18.00, (15 + ((52 * 11) % 200)), (DATE '2023-01-01' + ((52 * 9) % 700))),
    ('Hair Dryer 1800W', 6, (((53 - 1) % 12) + 1), 34.99, 15.00, (15 + ((53 * 11) % 200)), (DATE '2023-01-01' + ((53 * 9) % 700))),
    ('Moisturizing Face Cream', 6, (((54 - 1) % 12) + 1), 19.99, 7.50, (15 + ((54 * 11) % 200)), (DATE '2023-01-01' + ((54 * 9) % 700))),
    ('Beard Trimmer Kit', 6, (((55 - 1) % 12) + 1), 29.99, 13.00, (15 + ((55 * 11) % 200)), (DATE '2023-01-01' + ((55 * 9) % 700))),
    ('Sunscreen SPF50', 6, (((56 - 1) % 12) + 1), 14.99, 5.50, (15 + ((56 * 11) % 200)), (DATE '2023-01-01' + ((56 * 9) % 700))),
    ('Shampoo & Conditioner Set', 6, (((57 - 1) % 12) + 1), 22.99, 9.00, (15 + ((57 * 11) % 200)), (DATE '2023-01-01' + ((57 * 9) % 700))),
    ('Makeup Brush Set', 6, (((58 - 1) % 12) + 1), 17.99, 6.50, (15 + ((58 * 11) % 200)), (DATE '2023-01-01' + ((58 * 9) % 700))),
    ('Electric Shaver', 6, (((59 - 1) % 12) + 1), 44.99, 20.00, (15 + ((59 * 11) % 200)), (DATE '2023-01-01' + ((59 * 9) % 700))),
    ('Nail Care Kit', 6, (((60 - 1) % 12) + 1), 12.99, 4.50, (15 + ((60 * 11) % 200)), (DATE '2023-01-01' + ((60 * 9) % 700))),
    ('Wooden Building Blocks', 7, (((61 - 1) % 12) + 1), 29.99, 12.00, (15 + ((61 * 11) % 200)), (DATE '2023-01-01' + ((61 * 9) % 700))),
    ('Remote Control Car', 7, (((62 - 1) % 12) + 1), 39.99, 17.00, (15 + ((62 * 11) % 200)), (DATE '2023-01-01' + ((62 * 9) % 700))),
    ('Board Game: Strategy Quest', 7, (((63 - 1) % 12) + 1), 34.99, 14.00, (15 + ((63 * 11) % 200)), (DATE '2023-01-01' + ((63 * 9) % 700))),
    ('1000-Piece Jigsaw Puzzle', 7, (((64 - 1) % 12) + 1), 16.99, 6.00, (15 + ((64 * 11) % 200)), (DATE '2023-01-01' + ((64 * 9) % 700))),
    ('Plush Teddy Bear', 7, (((65 - 1) % 12) + 1), 19.99, 7.50, (15 + ((65 * 11) % 200)), (DATE '2023-01-01' + ((65 * 9) % 700))),
    ('Kids'' Art Supply Kit', 7, (((66 - 1) % 12) + 1), 24.99, 9.00, (15 + ((66 * 11) % 200)), (DATE '2023-01-01' + ((66 * 9) % 700))),
    ('Educational Tablet for Kids', 7, (((67 - 1) % 12) + 1), 79.99, 38.00, (15 + ((67 * 11) % 200)), (DATE '2023-01-01' + ((67 * 9) % 700))),
    ('Action Figure Set', 7, (((68 - 1) % 12) + 1), 22.99, 9.00, (15 + ((68 * 11) % 200)), (DATE '2023-01-01' + ((68 * 9) % 700))),
    ('Card Game: Number Rush', 7, (((69 - 1) % 12) + 1), 9.99, 3.50, (15 + ((69 * 11) % 200)), (DATE '2023-01-01' + ((69 * 9) % 700))),
    ('Building Blocks Mega Set', 7, (((70 - 1) % 12) + 1), 54.99, 24.00, (15 + ((70 * 11) % 200)), (DATE '2023-01-01' + ((70 * 9) % 700))),
    ('Ergonomic Office Chair', 8, (((71 - 1) % 12) + 1), 189.99, 95.00, (15 + ((71 * 11) % 200)), (DATE '2023-01-01' + ((71 * 9) % 700))),
    ('Standing Desk Converter', 8, (((72 - 1) % 12) + 1), 149.99, 75.00, (15 + ((72 * 11) % 200)), (DATE '2023-01-01' + ((72 * 9) % 700))),
    ('Wireless Keyboard & Mouse Combo', 8, (((73 - 1) % 12) + 1), 44.99, 20.00, (15 + ((73 * 11) % 200)), (DATE '2023-01-01' + ((73 * 9) % 700))),
    ('A4 Printer Paper (5 Reams)', 8, (((74 - 1) % 12) + 1), 29.99, 14.00, (15 + ((74 * 11) % 200)), (DATE '2023-01-01' + ((74 * 9) % 700))),
    ('Desk Organizer Set', 8, (((75 - 1) % 12) + 1), 19.99, 8.00, (15 + ((75 * 11) % 200)), (DATE '2023-01-01' + ((75 * 9) % 700))),
    ('Permanent Markers (12-pack)', 8, (((76 - 1) % 12) + 1), 8.99, 3.00, (15 + ((76 * 11) % 200)), (DATE '2023-01-01' + ((76 * 9) % 700))),
    ('Laminator Machine', 8, (((77 - 1) % 12) + 1), 39.99, 18.00, (15 + ((77 * 11) % 200)), (DATE '2023-01-01' + ((77 * 9) % 700))),
    ('Sticky Notes Bulk Pack', 8, (((78 - 1) % 12) + 1), 12.99, 4.50, (15 + ((78 * 11) % 200)), (DATE '2023-01-01' + ((78 * 9) % 700))),
    ('Desk Lamp LED', 8, (((79 - 1) % 12) + 1), 24.99, 10.00, (15 + ((79 * 11) % 200)), (DATE '2023-01-01' + ((79 * 9) % 700))),
    ('Filing Cabinet 3-Drawer', 8, (((80 - 1) % 12) + 1), 99.99, 48.00, (15 + ((80 * 11) % 200)), (DATE '2023-01-01' + ((80 * 9) % 700)));

-- -----------------------------------------------------------------------------
-- orders (1000 rows, spread 2023-01-01..2025-12-31 via generate_series).
-- total_amount is a placeholder here -- backfilled below once order_items
-- exist, so it always equals the real sum of that order's line items.
-- -----------------------------------------------------------------------------
INSERT INTO orders (customer_id, order_date, shipped_date, status, total_amount)
SELECT
    customer_id,
    order_date,
    CASE WHEN status IN ('shipped', 'delivered') THEN order_date + (3 + (n % 5)) ELSE NULL END,
    status,
    0
FROM (
    SELECT
        n,
        ((n - 1) % 200) + 1 AS customer_id,
        DATE '2023-01-01' + ((n * 37) % 1095) AS order_date,
        CASE
            WHEN (n % 20) = 0 THEN 'cancelled'
            WHEN (n % 20) IN (1, 2) THEN 'pending'
            WHEN (n % 20) IN (3, 4) THEN 'processing'
            WHEN (n % 20) BETWEEN 5 AND 9 THEN 'shipped'
            ELSE 'delivered'
        END AS status
    FROM generate_series(1, 1000) AS s(n)
) sub;

-- -----------------------------------------------------------------------------
-- order_items (~2500 rows: 1-4 per order, deterministic on order_id).
-- unit_price is copied from the product's current price, matching the
-- real-world "price captured at order time" semantics documented on the
-- column (see schema.sql).
-- -----------------------------------------------------------------------------
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT
    o.order_id,
    p.product_id,
    (1 + ((o.order_id + j.j) % 3)) AS quantity,
    p.price AS unit_price
FROM orders o
CROSS JOIN LATERAL generate_series(1, 1 + (o.order_id % 4)) AS j(j)
JOIN products p ON p.product_id = (((o.order_id * 7 + j.j * 13) - 1) % 80) + 1;

-- Backfill orders.total_amount from the line items that now exist.
UPDATE orders o
SET total_amount = totals.total
FROM (
    SELECT order_id, SUM(quantity * unit_price) AS total
    FROM order_items
    GROUP BY order_id
) totals
WHERE o.order_id = totals.order_id;

-- -----------------------------------------------------------------------------
-- payments (one per order; amount matches the order's real total)
-- -----------------------------------------------------------------------------
INSERT INTO payments (order_id, payment_date, amount, payment_method, status)
SELECT
    o.order_id,
    o.order_date + (o.order_id % 3) AS payment_date,
    o.total_amount,
    (ARRAY['credit_card', 'debit_card', 'paypal', 'bank_transfer', 'upi'])[((o.order_id - 1) % 5) + 1],
    CASE
        WHEN o.status = 'cancelled' THEN 'refunded'
        WHEN o.order_id % 23 = 0 THEN 'failed'
        WHEN o.order_id % 11 = 0 THEN 'pending'
        ELSE 'completed'
    END
FROM orders o;

-- -----------------------------------------------------------------------------
-- reviews (a deterministic 1-in-7 subset of order_items, one review per
-- distinct product/customer pair drawn that way -- ~357 rows, touching all
-- 80 products. NOTE: this was originally `% 5 = 0`, which happened to
-- resonate with the order_items product-id formula above and only ever
-- touched 20 of 80 products; verified against a live database that `% 7`
-- covers all 80 -- see backend/demo/README.md for how this was checked.
-- -----------------------------------------------------------------------------
INSERT INTO reviews (product_id, customer_id, rating, review_text, review_date)
SELECT DISTINCT ON (oi.product_id, o.customer_id)
    oi.product_id,
    o.customer_id,
    (1 + ((oi.order_item_id * 3) % 5)) AS rating,
    CASE
        WHEN oi.order_item_id % 3 = 0 THEN NULL
        ELSE (ARRAY[
            'Works great, exactly as described.',
            'Good value for the price.',
            'Arrived quickly, well packaged.',
            'Not bad, but expected a bit more.',
            'Would buy again.'
        ])[((oi.order_item_id / 3) % 5) + 1]
    END AS review_text,
    o.order_date + (oi.order_item_id % 10) AS review_date
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE oi.order_item_id % 7 = 0
ORDER BY oi.product_id, o.customer_id, oi.order_item_id;
