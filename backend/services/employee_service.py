"""
EmployeeService: Business logic for employee management.
Encapsulates validation and delegates data access to EmployeeRepository.
"""
from repositories.employee_repository import EmployeeRepository
from config.database import get_db


class EmployeeService:
    """Service for managing employees."""

    def __init__(self):
        self.repo = EmployeeRepository()

    def list_employees(self, active_only: bool = True) -> list[dict]:
        """
        List employees, optionally filtered to active only.

        Args:
            active_only: If True, return only active employees (is_active = 1)

        Returns:
            List of employee dictionaries
        """
        if active_only:
            return self.repo.list_active()
        return self.repo.get_all()

    def get_employee(self, employee_id: int) -> dict | None:
        """
        Get an employee by ID with history (time cards and flag pay records).

        Args:
            employee_id: Employee ID

        Returns:
            Employee dictionary with time_cards and flag_pay lists, or None if not found
        """
        return self.repo.get_with_history(employee_id)

    def create_employee(self, data: dict) -> int:
        """
        Create a new employee.

        Args:
            data: Employee data dict

        Returns:
            New employee ID

        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get("first_name"):
            raise ValueError("Employee must have first_name")
        if not data.get("last_name"):
            raise ValueError("Employee must have last_name")

        # Set default is_active if not provided
        if "is_active" not in data:
            data["is_active"] = 1

        return self.repo.insert(data)

    def update_employee(self, employee_id: int, data: dict) -> None:
        """
        Update an existing employee.

        Args:
            employee_id: Employee ID
            data: Updated employee data

        Raises:
            ValueError: If employee not found
        """
        existing = self.repo.get_by_id(employee_id)
        if not existing:
            raise ValueError(f"Employee {employee_id} not found")

        self.repo.update(employee_id, data)

    def delete_employee(self, employee_id: int) -> None:
        """
        Delete an employee — but only if nothing depends on them.

        Raises:
            ValueError: If the employee doesn't exist or is referenced by other records.
        """
        existing = self.repo.get_by_id(employee_id)
        if not existing:
            raise ValueError(f"Employee {employee_id} not found")

        # Tables that reference employees(id). Each entry: (table, where-clause, label).
        ref_checks = [
            ("repair_orders",  "estimator_id = ? OR technician_id = ? OR painter_id = ?", "repair order(s)"),
            ("estimates",      "estimator_id = ?",                                          "estimate(s)"),
            ("ro_lines",       "assigned_tech_id = ?",                                      "RO line assignment(s)"),
            ("time_cards",     "employee_id = ?",                                           "time card(s)"),
            ("flag_pay",       "employee_id = ?",                                           "flag pay record(s)"),
            ("users",          "employee_id = ?",                                           "user account(s)"),
            ("vehicle_moves",  "moved_by = ?",                                              "production move(s)"),
        ]

        in_use = []
        with get_db() as db:
            for table, where, label in ref_checks:
                # Some tables may not exist on older installs — skip gracefully.
                try:
                    n_args = where.count("?")
                    n = db.execute(
                        f"SELECT COUNT(*) AS n FROM {table} WHERE {where}",
                        (employee_id,) * n_args,
                    ).fetchone()["n"]
                except Exception:
                    n = 0
                if n:
                    in_use.append(f"{n} {label}")

        if in_use:
            name = f"{existing.get('first_name','')} {existing.get('last_name','')}".strip() or f"#{employee_id}"
            raise ValueError(
                f"Cannot delete {name} — they're referenced by " + ", ".join(in_use)
                + ". Set their status to Inactive instead, which keeps the historical data intact."
            )

        self.repo.delete(employee_id)
