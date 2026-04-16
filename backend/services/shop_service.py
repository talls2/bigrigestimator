"""
ShopService: Business logic for shop configuration and reference data.
Encapsulates shop info, rates, and templates management.
Delegates data access to ShopRepository.
"""
from repositories.shop_repository import ShopRepository


class ShopService:
    """Service for managing shop configuration and reference data."""

    def __init__(self):
        self.repo = ShopRepository()

    def get_info(self) -> dict | None:
        """
        Get shop information (name, address, phone, etc.).

        Returns:
            Shop info dictionary or None if not configured
        """
        return self.repo.get_shop_info()

    def update_info(self, data: dict) -> None:
        """
        Update shop information.

        Args:
            data: Shop info fields to update
        """
        self.repo.update_shop_info(data)

    def get_rates(self) -> list[dict]:
        """
        Get all active shop rates (labor rates, etc.).

        Returns:
            List of rate dictionaries
        """
        return self.repo.get_rates()

    def get_templates(self) -> list[dict]:
        """
        Get all letter templates for correspondence.

        Returns:
            List of template dictionaries
        """
        return self.repo.get_templates()
