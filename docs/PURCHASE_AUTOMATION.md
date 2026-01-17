# Purchase Automation

This module provides automated product purchasing for WooCommerce sites.

## Features

- Add products to cart with specific variations and attributes
- Complete checkout with billing, shipping, and payment information
- Dry-run mode for testing
- Clear cart before purchasing

## Configuration

1. Copy the example configuration:
```bash
cp conf/purchase.yaml.example conf/purchase.yaml
```

2. Edit `conf/purchase.yaml` with your details:

```yaml
base_url: https://www.wagashi.com.tw

product:
  product_id: 2909        # Product ID from the website
  variation_id: 686214    # Variation ID for the specific variant
  quantity: 1
  attributes:
    盒數: "5盒"          # Product attributes

billing_info:
  first_name: "John"
  last_name: "Doe"
  phone: "0912345678"
  email: "john@example.com"
  # ... more billing fields

shipping_info:
  method: "local_pickup:8"
  delivery_date: "2026-01-15"

payment_info:
  method: "sinopac-self-hosted-credit"
  card_number: "1234 5678 1111 2222"
  expiry_month: "01"
  expiry_year: "30"
  cvv: "123"
```

## Usage

### Basic Purchase

```bash
./scripts/purchase_product.py -c conf/purchase.yaml
```

### Dry Run (Test without purchasing)

```bash
./scripts/purchase_product.py -c conf/purchase.yaml --dry-run
```

This will add the product to cart but skip the checkout step.

### Clear Cart Before Purchase

```bash
./scripts/purchase_product.py -c conf/purchase.yaml --clear-cart
```

### Verbose Logging

```bash
./scripts/purchase_product.py -c conf/purchase.yaml -v
```

## Finding Product and Variation IDs

You can extract product and variation IDs from the HAR file captured from your browser:

1. Open browser DevTools (F12)
2. Go to Network tab
3. Add product to cart
4. Export HAR file
5. Search for the add-to-cart request:

```python
import json

with open('your_file.har', 'r') as f:
    har = json.load(f)

for entry in har['log']['entries']:
    request = entry['request']
    if request['method'] == 'POST' and 'product' in request['url']:
        # Extract from POST data
        print(request['postData'])
```

## Security Notes

**WARNING**: The configuration file contains sensitive payment information.

- Never commit `conf/purchase.yaml` to version control
- Keep the configuration file secure with appropriate file permissions:
  ```bash
  chmod 600 conf/purchase.yaml
  ```
- Consider using environment variables for sensitive data
- Use test/sandbox payment credentials for testing

## Architecture

### Components

1. **WooCommercePurchaser** (`src/core/purchaser.py`)
   - Implements the `Purchaser` interface
   - Handles add-to-cart, checkout, and cart management
   - Maintains session state with cookies

2. **PurchaseConfig** (`src/config/models.py`)
   - Pydantic models for configuration validation
   - Separate models for product, billing, shipping, and payment info

3. **CLI Script** (`scripts/purchase_product.py`)
   - Command-line interface for purchase automation
   - Supports dry-run and cart clearing

### Workflow

1. Load configuration from YAML file
2. Initialize WooCommercePurchaser with session
3. Optionally clear cart
4. Add product to cart with variations/attributes
5. Build checkout payload from configuration
6. Submit checkout request
7. Return order ID on success

## Error Handling

The module raises `PurchaseError` for any purchase-related failures:

- Network errors
- Invalid product/variation IDs
- Checkout validation failures
- Payment processing errors

## Limitations

- Currently supports WooCommerce sites only
- Payment methods supported: Sinopac credit card
- Requires valid session cookies (maintained automatically)
- No captcha/reCAPTCHA handling

## Future Enhancements

- [ ] Support for multiple products in one order
- [ ] Additional payment methods
- [ ] Captcha handling
- [ ] Retry logic with exponential backoff
- [ ] Order status tracking
- [ ] Notification on successful purchase
