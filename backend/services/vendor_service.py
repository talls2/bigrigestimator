"""
VendorService: Business logic for vendor management.
Encapsulates validation and delegates data access to VendorRepository.
"""
from repositories.vendor_repository import VendorRepository


class VendorService:
    """Service for managing vendors."""

    def __init__(self):
        self.repo = VendorRepository()

    def list_vendors(self, search: str | None = None) -> list[dict]:
        """
        List all vendors, optionally filtered by search term.

        Args:
            search: Search term to filter vendors by name, contact, email, or phone

        Returns:
            List of vendor dictionaries
        """
        if search:
            return self.repo.search_vendors(search)
        return self.repo.get_all()

    def get_vendor(self, vendor_id: int) -> dict | None:
        """
        Get a vendor by ID.

        Args:
            vendor_id: Vendor ID

        Returns:
            Vendor dictionary or None if not found
        """
        return self.repo.get_by_id(vendor_id)

    def create_vendor(self, data: dict) -> int:
        """
        Create a new vendor.

        Args:
            data: Vendor data dict

        Returns:
            New vendor ID

        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get("vendor_name"):
            raise ValueError("Vendor must have a vendor_name")

        return self.repo.insert(data)

    def update_vendor(self, vendor_id: int, data: dict) -> None:
        """
        Update an existing vendor.

        Args:
            vendor_id: Vendor ID
            data: Updated vendor data

        Raises:
            ValueError: If vendor not found
        """
        existing = self.repo.get_by_id(vendor_id)
        if not existing:
            raise ValueError(f"Vendor {vendor_id} not found")

        self.repo.update(vendor_id, data)
