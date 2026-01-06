# Quick Start Guide

## Initial Setup

1. **Install dependencies** (already done):
```bash
poetry install
```

2. **Create your configuration file**:
```bash
cp conf/config.example.yaml conf/config.yaml
```

3. **Edit `conf/config.yaml`** and update:

   - **Add your product URLs**: Replace the example products with the ones you want to monitor
   - **Add your Slack webhook URL**: Replace `YOUR/WEBHOOK/URL` with your actual Slack webhook

## Get Your Slack Webhook URL

1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create your Slack app"
3. Choose "From scratch"
4. Name your app (e.g., "Food Reminder")
5. Select your workspace
6. In the left sidebar, click "Incoming Webhooks"
7. Toggle "Activate Incoming Webhooks" to ON
8. Click "Add New Webhook to Workspace"
9. Select the channel where you want notifications
10. Copy the Webhook URL

## Add Product URLs

To get product URLs from wagashi.com.tw:

1. Browse to https://www.wagashi.com.tw
2. Find products you want to monitor
3. Copy the product page URL (e.g., `https://www.wagashi.com.tw/product/%e8%8d%89%e8%8e%93%e5%a4%a7%e7%a6%8f/`)
4. Add them to your `conf/config.yaml`:

```yaml
products:
  - url: "YOUR_PRODUCT_URL_HERE"
    name: "Optional Product Name"  # Or omit, it will be auto-generated
```

## Run the Checker

```bash
# Run with verbose logging to see what's happening
poetry run python scripts/check_availability.py -v

# Or use the Makefile
make run
```

## Example Output

When a product is in stock and hasn't been notified:
```
2026-01-04 15:30:00 - __main__ - INFO - Loading configuration from conf/config.yaml
2026-01-04 15:30:00 - src.core.service - INFO - Checking 2 products
2026-01-04 15:30:01 - src.core.checker - INFO - Product availability determined from class: True
2026-01-04 15:30:01 - src.core.service - INFO - Strawberry Daifuku 8-pack is available - sending notification
2026-01-04 15:30:01 - src.core.notifier - INFO - Sending Slack notification for Strawberry Daifuku 8-pack
2026-01-04 15:30:02 - src.core.notifier - INFO - Slack notification sent successfully
2026-01-04 15:30:02 - src.core.state - INFO - Marked https://www.wagashi.com.tw/product/... as notified at 2026-01-04 15:30:02
2026-01-04 15:30:02 - src.core.service - INFO - Check complete - Checked: 2, Available: 1, Notified: 1, Already notified: 0, Errors: 0
```

## Testing Without Slack

If you want to test without setting up Slack yet, you can:

1. Comment out the notification code temporarily, OR
2. Use a test webhook URL from https://webhook.site to see the payloads

## Next Steps

- Set up a cron job or scheduled task to run the checker periodically
- Add more products to monitor
- Check `state/notifications.json` to see notification history

## Troubleshooting

**"Configuration file not found"**:
- Make sure you copied `config.example.yaml` to `config.yaml` in the `conf/` directory

**"Failed to send Slack notification"**:
- Verify your Slack webhook URL is correct
- Make sure it starts with `https://hooks.slack.com/services/`

**Product showing as out of stock when it's available**:
- The website structure may have changed
- Run with `-v` flag to see detailed logs
- Check the HTML manually to see if the stock detection logic needs updating

## Useful Commands

```bash
# Run with verbose logging
poetry run python scripts/check_availability.py -v

# Use custom config file
poetry run python scripts/check_availability.py -c /path/to/custom/config.yaml

# Clear notification state for a product (to get notified again)
poetry run python scripts/check_availability.py --clear-state "https://www.wagashi.com.tw/product/example/"

# Run tests
make test

# Format code
make format

# Run all quality checks
make check
```
