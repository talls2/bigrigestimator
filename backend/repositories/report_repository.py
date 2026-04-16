"""
ReportRepository: Analytical queries for shop reporting.
Provides standalone report generation methods (does not inherit BaseRepository).
"""
from config.database import get_db, rows_to_list
from datetime import datetime, timedelta


class ReportRepository:
    """Shop reporting and analytics."""

    def production_summary(self, start_date: str | None = None,
                          end_date: str | None = None) -> dict:
        """
        Generate production summary report.
        Returns counts and totals of ROs, estimates, payments by status/date range.
        Dates in ISO format: "2026-04-15".
        """
        with get_db() as db:
            query_parts = []
            params = []

            # Repair orders by status
            ro_status = db.execute(
                """
                SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount,
                       SUM(amount_paid) as amount_paid, SUM(balance_due) as balance_due
                FROM repair_orders
                WHERE 1=1
                """
                + ("" if not start_date else " AND created_at >= ?")
                + ("" if not end_date else " AND created_at <= ?")
                + """
                GROUP BY status
                ORDER BY status
                """
            )
            if start_date:
                ro_status = db.execute(
                    """
                    SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount,
                           SUM(amount_paid) as amount_paid, SUM(balance_due) as balance_due
                    FROM repair_orders
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY status
                    ORDER BY status
                    """,
                    (start_date, end_date or "2099-12-31")
                )
            else:
                ro_status = db.execute(
                    """
                    SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount,
                           SUM(amount_paid) as amount_paid, SUM(balance_due) as balance_due
                    FROM repair_orders
                    GROUP BY status
                    ORDER BY status
                    """
                )

            # Estimates by status
            est_status = db.execute(
                """
                SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount
                FROM estimates
                WHERE 1=1
                """
                + ("" if not start_date else " AND created_at >= ?")
                + ("" if not end_date else " AND created_at <= ?")
                + """
                GROUP BY status
                ORDER BY status
                """
                if not start_date else
                """
                SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount
                FROM estimates
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY status
                ORDER BY status
                """
            )
            if start_date:
                est_rows = db.execute(
                    """
                    SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount
                    FROM estimates
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY status
                    ORDER BY status
                    """,
                    (start_date, end_date or "2099-12-31")
                ).fetchall()
            else:
                est_rows = db.execute(
                    """
                    SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount
                    FROM estimates
                    GROUP BY status
                    ORDER BY status
                    """
                ).fetchall()

            # Get RO rows
            if start_date:
                ro_rows = db.execute(
                    """
                    SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount,
                           SUM(amount_paid) as amount_paid, SUM(balance_due) as balance_due
                    FROM repair_orders
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY status
                    ORDER BY status
                    """,
                    (start_date, end_date or "2099-12-31")
                ).fetchall()
            else:
                ro_rows = db.execute(
                    """
                    SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount,
                           SUM(amount_paid) as amount_paid, SUM(balance_due) as balance_due
                    FROM repair_orders
                    GROUP BY status
                    ORDER BY status
                    """
                ).fetchall()

            return {
                "repair_orders": rows_to_list(ro_rows),
                "estimates": rows_to_list(est_rows),
                "date_range": {
                    "start": start_date,
                    "end": end_date
                }
            }

    def ar_aging(self) -> list[dict]:
        """
        Generate accounts receivable aging report.
        Breaks down balance_due by age (0-30, 31-60, 61-90, 90+ days).
        """
        with get_db() as db:
            rows = db.execute(
                """
                SELECT
                    CASE
                        WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 30
                            THEN '0-30 days'
                        WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 60
                            THEN '31-60 days'
                        WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 90
                            THEN '61-90 days'
                        ELSE '90+ days'
                    END as age_bucket,
                    COUNT(*) as count,
                    SUM(balance_due) as balance_due,
                    SUM(total_amount) as total_amount
                FROM repair_orders
                WHERE balance_due > 0 AND status != 'closed'
                GROUP BY age_bucket
                ORDER BY
                    CASE age_bucket
                        WHEN '0-30 days' THEN 1
                        WHEN '31-60 days' THEN 2
                        WHEN '61-90 days' THEN 3
                        ELSE 4
                    END
                """
            ).fetchall()
        return rows_to_list(rows)

    def employee_productivity(self) -> list[dict]:
        """
        Generate employee productivity report.
        Shows hours worked and ROs completed per employee.
        """
        with get_db() as db:
            rows = db.execute(
                """
                SELECT
                    e.id, e.first_name, e.last_name,
                    COUNT(DISTINCT tc.id) as time_card_count,
                    ROUND(SUM(CAST((julianday(tc.clock_out) - julianday(tc.clock_in)) AS REAL) * 24), 2) as hours_worked,
                    COUNT(DISTINCT ro.id) as ro_completed
                FROM employees e
                LEFT JOIN time_cards tc ON e.id = tc.employee_id
                LEFT JOIN repair_orders ro ON (
                    e.id = ro.tech_id OR e.id = ro.painter_id OR e.id = ro.estimator_id
                )
                WHERE e.is_active = 1
                GROUP BY e.id, e.first_name, e.last_name
                ORDER BY hours_worked DESC
                """
            ).fetchall()
        return rows_to_list(rows)

    def parts_summary(self) -> list[dict]:
        """
        Generate parts usage summary.
        Shows parts costs by vendor and overall.
        """
        with get_db() as db:
            rows = db.execute(
                """
                SELECT
                    v.id, v.vendor_name,
                    COUNT(DISTINCT rol.id) as line_count,
                    SUM(rol.parts_cost) as total_parts_cost,
                    COUNT(DISTINCT rol.repair_order_id) as ro_count
                FROM vendors v
                LEFT JOIN ro_lines rol ON v.id = rol.vendor_id
                GROUP BY v.id, v.vendor_name
                HAVING total_parts_cost > 0 OR line_count > 0
                ORDER BY total_parts_cost DESC
                """
            ).fetchall()
        return rows_to_list(rows)

    def cycle_time(self) -> dict:
        """
        Generate cycle time report.
        Calculates average time from RO creation to completion by status.
        """
        with get_db() as db:
            rows = db.execute(
                """
                SELECT
                    CASE
                        WHEN ro.status = 'completed' OR ro.status = 'closed'
                            THEN ROUND(AVG(CAST((julianday(ro.updated_at) - julianday(ro.created_at)) AS REAL)), 1)
                        ELSE NULL
                    END as avg_days_to_complete,
                    MIN(CAST((julianday(ro.updated_at) - julianday(ro.created_at)) AS REAL)) as min_days,
                    MAX(CAST((julianday(ro.updated_at) - julianday(ro.created_at)) AS REAL)) as max_days,
                    COUNT(*) as total_completed
                FROM repair_orders ro
                WHERE ro.status IN ('completed', 'closed')
                """
            ).fetchall()

        result = rows_to_list(rows)
        return result[0] if result else {
            "avg_days_to_complete": None,
            "min_days": None,
            "max_days": None,
            "total_completed": 0
        }
