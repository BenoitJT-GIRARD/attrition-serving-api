SELECT COUNT(*) AS n_employees FROM employees;
SELECT COUNT(*) AS n_predictions FROM predictions;

SELECT employee_id, features
FROM employees
LIMIT 3;
