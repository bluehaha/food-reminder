"""Configuration models using Pydantic."""

from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ProductConfig(BaseModel):
    """Configuration for a single product to monitor."""

    url: HttpUrl
    name: Optional[str] = None  # Optional friendly name

    @field_validator("name", mode="before")
    @classmethod
    def set_name_from_url(cls, v: Optional[str], info: any) -> str:
        """Auto-generate name from URL if not provided."""
        if not v and "url" in info.data:
            # Extract product name from URL
            url_str = str(info.data["url"])
            # Get the last path segment before any trailing slash
            path_segments = [seg for seg in url_str.split("/") if seg]
            if path_segments:
                return path_segments[-1].replace("%", " ").replace("-", " ").title()
        return v or "Unknown Product"


class SlackConfig(BaseModel):
    """Slack notification configuration."""

    webhook_url: HttpUrl
    username: str = "Food Availability Bot"
    icon_emoji: str = ":bento:"


class StateConfig(BaseModel):
    """State management configuration."""

    file_path: Path = Field(default=Path("state/notifications.json"))

    @field_validator("file_path")
    @classmethod
    def ensure_parent_exists(cls, v: Path) -> Path:
        """Ensure parent directory exists."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v


class Config(BaseModel):
    """Main application configuration."""

    products: List[ProductConfig]
    slack: SlackConfig
    state: StateConfig = Field(default_factory=StateConfig)

    # HTTP settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        description="User agent for HTTP requests",
    )

    # Retry settings
    max_retries: int = Field(default=3, description="Max HTTP retries")
    retry_delay: int = Field(default=2, description="Delay between retries in seconds")

    model_config = {"validate_assignment": True}


class PurchaseProductConfig(BaseModel):
    """Configuration for a product to purchase."""

    url: str  # Product URL (e.g., "product/草莓大福/" or full URL)
    product_id: int
    variation_id: int
    quantity: int = 1
    attributes: Optional[Dict[str, str]] = None


class BillingInfoConfig(BaseModel):
    """Billing information configuration."""

    first_name: str
    last_name: str
    company: str = ""
    country: str = "TW"
    address_1: str = "none"
    city: str = "none"
    postcode: str = "none"
    phone: str = ""
    email: str = ""
    carruer_type: int = 1
    invoice_type: str = "p"
    customer_identifier: str = ""
    love_code: str = ""
    carruer_num: str = ""


class ShippingInfoConfig(BaseModel):
    """Shipping information configuration."""

    first_name: str = ""
    last_name: str = ""
    company: str = ""
    country: str = "TW"
    address_1: str = ""
    address_2: str = ""
    city: str = ""
    state: str = ""
    postcode: str = ""
    phone: str = ""
    method: str = "local_pickup:8"


class PaymentInfoConfig(BaseModel):
    """Payment information configuration."""

    method: str = "sinopac-self-hosted-credit"
    card_number: str = ""
    expiry_month: str = ""
    expiry_year: str = ""
    cvv: str = ""


class PurchaseConfig(BaseModel):
    """Purchase automation configuration."""

    base_url: HttpUrl
    product: PurchaseProductConfig
    billing_info: BillingInfoConfig
    shipping_info: ShippingInfoConfig
    payment_info: PaymentInfoConfig
    slack: SlackConfig
    state: StateConfig = Field(default_factory=StateConfig)
    timeout: int = Field(default=30, description="Request timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        description="User agent for HTTP requests",
    )
