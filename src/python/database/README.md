# Why use Raw SQL in some crud functions?

Raw SQL is used in the `get_balance_sheet_by_date()` and `get_income_statement_by_date()` functions for performance reasons:

1. **Window Function Support**: The code uses `ROW_NUMBER() OVER (PARTITION BY...)` window functions which are more verbose and complex to express in SQLAlchemy's ORM syntax, especially the ranking operations.

2. **Complex Query Structure**: The query uses a Common Table Expression (CTE) with `WITH ranked_values AS (...)` to create a temporary result set that's then filtered. This pattern is more straightforward in raw SQL.

3. **Performance Overhead**: SQLAlchemy's ORM adds abstraction layers that can introduce performance overhead, particularly for complex queries with window functions and subqueries.

4. **Date-Based Proximity Logic**: The query finds the closest financial data to a given date using `ORDER BY ABS(EXTRACT(EPOCH FROM (value_date - :target_date)))`, which would require more verbose code in SQLAlchemy's expression language.

5. **Query Readability**: For complex financial data queries, raw SQL can sometimes be more readable and maintainable than equivalent ORM code.

For simpler CRUD operations elsewhere in the file, the code uses SQLAlchemy's ORM approach, which provides better type safety and abstraction. The hybrid approach uses each tool where it makes the most sense.