"""
EstimateService: Business logic for estimate management.
Encapsulates validation, numbering, and line item management.
Delegates data access to EstimateRepository and RepairOrderRepository.
"""
from repositories.estimate_repository import EstimateRepository
from repositories.repair_order_repository import RepairOrderRepository


class EstimateService:
    """Service for managing estimates with totals and conversions."""

    def __init__(self):
        self.estimate_repo = EstimateRepository()
        self.ro_repo = RepairOrderRepository()

    def list_estimates(self, status: str | None = None, search: str | None = None) -> list[dict]:
        """
        List estimates with optional status and search filtering.

        Args:
            status: Filter by estimate status (e.g., 'pending', 'accepted', 'converted')
            search: Search term to filter by customer name or vehicle info

        Returns:
            List of estimate dictionaries with customer and vehicle info
        """
        return self.estimate_repo.list_with_details(status=status, search=search)

    def get_estimate(self, estimate_id: int) -> dict | None:
        """
        Get a complete estimate with all details (customer, vehicle, lines, etc.).

        Args:
            estimate_id: Estimate ID

        Returns:
            Estimate dictionary with all related data or None if not found
        """
        return self.estimate_repo.get_full(estimate_id)

    def create_estimate(self, data: dict) -> int:
        """
        Create a new estimate with auto-generated estimate number.

        Args:
            data: Estimate data dict (estimate_number will be auto-generated)

        Returns:
            New estimate ID

        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get("customer_id"):
            raise ValueError("Estimate must have a customer_id")

        # Auto-generate estimate number
        data["estimate_number"] = self.estimate_repo.next_number()

        # Set default status if not provided
        if "status" not in data:
            data["status"] = "pending"

        return self.estimate_repo.insert(data)

    def update_estimate(self, estimate_id: int, data: dict) -> None:
        """
        Update an existing estimate.

        Args:
            estimate_id: Estimate ID
            data: Updated estimate data

        Raises:
            ValueError: If estimate not found
        """
        existing = self.estimate_repo.get_by_id(estimate_id)
        if not existing:
            raise ValueError(f"Estimate {estimate_id} not found")

        self.estimate_repo.update(estimate_id, data)

    def add_line(self, estimate_id: int, data: dict) -> int:
        """
        Add a line item to an estimate and recalculate totals.

        Args:
            estimate_id: Estimate ID
            data: Line item data (labor_hours, labor_rate, parts_cost, paint_cost, other_cost, description)

        Returns:
            New line item ID

        Raises:
            ValueError: If estimate not found
        """
        # Verify estimate exists
        existing = self.estimate_repo.get_by_id(estimate_id)
        if not existing:
            raise ValueError(f"Estimate {estimate_id} not found")

        # Add the line
        line_id = self.estimate_repo.add_line(estimate_id, data)

        # Recalculate totals
        self.estimate_repo.recalc_totals(estimate_id)

        return line_id

    def delete_line(self, estimate_id: int, line_id: int) -> None:
        """
        Delete a line item from an estimate and recalculate totals.

        Args:
            estimate_id: Estimate ID
            line_id: Line item ID

        Raises:
            ValueError: If estimate not found
        """
        # Verify estimate exists
        existing = self.estimate_repo.get_by_id(estimate_id)
        if not existing:
            raise ValueError(f"Estimate {estimate_id} not found")

        # Delete the line
        self.estimate_repo.delete_line(estimate_id, line_id)

        # Recalculate totals
        self.estimate_repo.recalc_totals(estimate_id)

    def convert_to_ro(self, estimate_id: int) -> int:
        """
        Convert an estimate to a repair order.
        Creates a new RO with all estimate data and lines copied over.
        Marks the estimate as 'converted'.

        Args:
            estimate_id: Estimate ID to convert

        Returns:
            New repair order ID

        Raises:
            ValueError: If estimate not found or already converted
        """
        # Get full estimate data
        estimate = self.estimate_repo.get_full(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        if estimate.get("status") == "converted":
            raise ValueError(f"Estimate {estimate_id} is already converted")

        # Prepare RO data from estimate
        ro_data = {
            "customer_id": estimate.get("customer_id"),
            "vehicle_id": estimate.get("vehicle_id"),
            "insurance_company_id": estimate.get("insurance_company_id"),
            "estimator_id": estimate.get("estimator_id"),
            "estimate_id": estimate_id,
            "ro_number": self.ro_repo.next_number(),
            "claim_number": estimate.get("claim_number"),
            "policy_number": estimate.get("policy_number"),
            "deductible": estimate.get("deductible", 0),
            "loss_date": estimate.get("loss_date"),
            "status": "open",
            "subtotal_labor": estimate.get("subtotal_labor", 0),
            "subtotal_parts": estimate.get("subtotal_parts", 0),
            "subtotal_paint": estimate.get("subtotal_paint", 0),
            "subtotal_other": estimate.get("subtotal_other", 0),
            "tax_amount": estimate.get("tax_amount", 0),
            "total_amount": estimate.get("total_amount", 0),
            "balance_due": estimate.get("total_amount", 0),
        }

        # Create the RO
        ro_id = self.ro_repo.insert(ro_data)

        # Copy all estimate lines to RO lines
        if estimate.get("lines"):
            for line in estimate["lines"]:
                ro_line_data = {
                    "line_type": line.get("line_type", "labor"),
                    "operation": line.get("operation"),
                    "description": line.get("description"),
                    "part_number": line.get("part_number"),
                    "part_type": line.get("part_type"),
                    "quantity": line.get("quantity", 1),
                    "labor_hours": line.get("labor_hours", 0),
                    "labor_rate": line.get("labor_rate", 0),
                    "paint_hours": line.get("paint_hours", 0),
                    "paint_rate": line.get("paint_rate", 0),
                    "part_price": line.get("part_price", 0),
                    "part_cost": line.get("part_cost", 0),
                }
                self.ro_repo.add_line(ro_id, ro_line_data)

        # Mark estimate as converted
        self.estimate_repo.update(estimate_id, {"status": "converted"})

        return {"id": ro_id, "ro_number": ro_data["ro_number"], "message": "Repair order created from estimate"}
