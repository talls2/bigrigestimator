"""
RepairOrderService: Business logic for repair order management.
Encapsulates validation, numbering, line items, payments, and status management.
Delegates data access to RepairOrderRepository and PaymentRepository.
"""
from repositories.repair_order_repository import RepairOrderRepository
from repositories.payment_repository import PaymentRepository


class RepairOrderService:
    """Service for managing repair orders with totals and payments."""

    def __init__(self):
        self.repo = RepairOrderRepository()
        self.payment_repo = PaymentRepository()

    def list_ros(self, status: str | None = None, search: str | None = None) -> list[dict]:
        """
        List repair orders with optional status and search filtering.

        Args:
            status: Filter by RO status (e.g., 'open', 'in_progress', 'completed', 'closed')
            search: Search term to filter by customer name or vehicle info

        Returns:
            List of repair order dictionaries with customer and vehicle info
        """
        return self.repo.list_with_details(status=status, search=search)

    def get_ro(self, ro_id: int) -> dict | None:
        """
        Get a complete repair order with all details (customer, vehicle, lines, payments, timecards, schedule).

        Args:
            ro_id: Repair order ID

        Returns:
            Repair order dictionary with all related data or None if not found
        """
        return self.repo.get_full(ro_id)

    def create_ro(self, data: dict) -> int:
        """
        Create a new repair order with auto-generated RO number.

        Args:
            data: Repair order data dict (repair_order_number will be auto-generated)

        Returns:
            New repair order ID

        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get("customer_id"):
            raise ValueError("Repair order must have a customer_id")

        # Auto-generate RO number
        data["ro_number"] = self.repo.next_number()

        # Set default status and amounts if not provided
        if "status" not in data:
            data["status"] = "open"
        if "amount_paid" not in data:
            data["amount_paid"] = 0
        if "balance_due" not in data:
            data["balance_due"] = 0

        return self.repo.insert(data)

    def update_ro(self, ro_id: int, data: dict) -> None:
        """
        Update an existing repair order.

        Args:
            ro_id: Repair order ID
            data: Updated repair order data

        Raises:
            ValueError: If repair order not found
        """
        existing = self.repo.get_by_id(ro_id)
        if not existing:
            raise ValueError(f"Repair order {ro_id} not found")

        self.repo.update(ro_id, data)

    def add_line(self, ro_id: int, data: dict) -> int:
        """
        Add a line item to a repair order and recalculate totals.

        Args:
            ro_id: Repair order ID
            data: Line item data (labor_hours, labor_rate, parts_cost, paint_cost, other_cost, description, vendor_id)

        Returns:
            New line item ID

        Raises:
            ValueError: If repair order not found
        """
        # Verify RO exists
        existing = self.repo.get_by_id(ro_id)
        if not existing:
            raise ValueError(f"Repair order {ro_id} not found")

        # Add the line
        line_id = self.repo.add_line(ro_id, data)

        # Recalculate totals
        self.repo.recalc_totals(ro_id)

        return line_id

    def add_payment(self, ro_id: int, data: dict) -> int:
        """
        Add a payment to a repair order and recalculate totals/balance.

        Args:
            ro_id: Repair order ID
            data: Payment data (amount, payment_date, payment_method, notes)

        Returns:
            New payment ID

        Raises:
            ValueError: If repair order not found or amount invalid
        """
        # Verify RO exists
        existing = self.repo.get_by_id(ro_id)
        if not existing:
            raise ValueError(f"Repair order {ro_id} not found")

        # Validate payment amount
        if not data.get("amount"):
            raise ValueError("Payment must have an amount")

        amount = float(data["amount"])
        if amount <= 0:
            raise ValueError("Payment amount must be greater than 0")

        # Add payment using payment repository
        payment_id = self.payment_repo.add_payment(ro_id, data)

        # Recalculate totals (updates amount_paid and balance_due)
        self.repo.recalc_totals(ro_id)

        return payment_id

    def update_status(self, ro_id: int, new_status: str) -> None:
        """
        Update the status of a repair order.

        Args:
            ro_id: Repair order ID
            new_status: New status value (e.g., 'open', 'in_progress', 'completed', 'closed')

        Raises:
            ValueError: If repair order not found
        """
        existing = self.repo.get_by_id(ro_id)
        if not existing:
            raise ValueError(f"Repair order {ro_id} not found")

        self.repo.update(ro_id, {"status": new_status})
