"""
PaymentRepository: Payment CRUD for repair orders.
"""
from config.database import get_db, row_to_dict, rows_to_list
from .base_repository import BaseRepository


class PaymentRepository(BaseRepository):
    table_name = "payments"
    order_by = "payment_date DESC"

    def get_by_ro(self, ro_id: int, limit: int = 500) -> list[dict]:
        """
        Get all payments for a repair order, ordered by payment_date DESC.
        """
        with get_db() as db:
            rows = db.execute(
                f"""
                SELECT * FROM {self.table_name}
                WHERE ro_id = ?
                ORDER BY {self.order_by}
                LIMIT ?
                """,
                (ro_id, limit)
            ).fetchall()
        return rows_to_list(rows)

    def add_payment(self, ro_id: int, data: dict) -> int:
        """
        Add a payment to a repair order.
        Returns the payment id.
        """
        with get_db() as db:
            cols = ["ro_id"] + list(data.keys())
            vals = [ro_id] + list(data.values())
            placeholders = ", ".join(["?"] * len(cols))
            col_str = ", ".join(cols)

            cur = db.execute(
                f"INSERT INTO {self.table_name} ({col_str}) VALUES ({placeholders})",
                vals
            )
            db.commit()
            return cur.lastrowid
