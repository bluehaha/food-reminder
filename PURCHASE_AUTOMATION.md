# Purchase Automation Guide

## Overview

The purchase automation script now includes:
1. **Slack notifications** for exceptions and successful purchases (via `src/core/notifier.py`)
2. **State tracking** to prevent duplicate purchases when running via cron (via `src/core/state.py`)

## Architecture

The implementation reuses existing core modules:
- **SlackNotifier** (`src/core/notifier.py`): Extended to support error and success notifications
- **JsonStateStore** (`src/core/state.py`): Extended to track purchase state by product_id and variation_id

## Features

### 1. Slack Notifications

When configured, the script will send Slack notifications for:
- **Exceptions**: Any errors that occur during purchase (configuration errors, purchase failures, network issues, etc.)
- **Success**: Confirmation when a purchase is completed successfully

#### Configuration

Add the following to your `conf/purchase.yaml`:

```yaml
slack:
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  username: "Purchase Bot"
  icon_emoji: ":shopping_cart:"
```

To get a Slack webhook URL:
1. Go to https://api.slack.com/apps
2. Create a new app or select an existing one
3. Enable "Incoming Webhooks"
4. Add a new webhook to your workspace
5. Copy the webhook URL to your configuration

### 2. Duplicate Purchase Prevention

The script tracks successful purchases in a state file. When running via cron every minute, this ensures:
- A product is only purchased once
- Subsequent runs will detect the previous purchase and exit gracefully
- No duplicate orders are created

#### State File Location

By default, the state is stored in `state/notifications.json`. You can customize this:

```yaml
state:
  file_path: "state/purchase.json"
```

#### Clearing State

To allow re-purchasing a product (after consumption, for example), use the `--clear-state` flag:

```bash
python scripts/purchase_product.py --clear-state
```

## Usage Examples

### Basic Usage (with Slack notifications)

```bash
python scripts/purchase_product.py -c conf/purchase.yaml
```

### Cron Job Setup

To run the purchase script every minute via cron:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path to your project)
* * * * * cd /path/to/food-reminder && /path/to/python scripts/purchase_product.py -c conf/purchase.yaml >> logs/purchase.log 2>&1
```

The script will:
1. Check if the product was already purchased (via state file)
2. If yes, exit immediately (no duplicate purchase)
3. If no, attempt to purchase
4. On success, mark as purchased and send Slack notification
5. On error, send error details to Slack

### Dry Run Mode

Test without actually purchasing:

```bash
python scripts/purchase_product.py --dry-run
```

This will add the product to cart but skip checkout.

### Clear Purchase State

Reset the purchase tracking to allow re-purchase:

```bash
python scripts/purchase_product.py --clear-state
```

### Verbose Logging

Enable detailed debug logs:

```bash
python scripts/purchase_product.py -v
```

## Slack Notification Examples

### Error Notification

When an exception occurs, Slack receives:
- Error type (e.g., "PurchaseError", "ConnectionError")
- Error message
- Context information
- Full traceback
- Timestamp

### Success Notification

When purchase succeeds, Slack receives:
- Order ID
- Product URL/name
- Timestamp

## State File Format

The state file is JSON and tracks purchases by product/variation:

```json
{
  "2909_686214": {
    "order_id": "12345",
    "timestamp": "2026-01-17T10:30:00.123456",
    "product_id": 2909,
    "variation_id": 686214
  }
}
```

## Error Handling

All exceptions are caught and:
1. Logged to the console and log files
2. Sent to Slack (if configured)
3. Exit with appropriate error codes

Error exit codes:
- `0`: Success (or already purchased)
- `1`: Error occurred
- `130`: Cancelled by user (Ctrl+C)

## Best Practices

1. **Test first**: Use `--dry-run` to verify configuration
2. **Monitor Slack**: Set up a dedicated channel for purchase notifications
3. **Review state file**: Check `state/purchase.json` to see purchase history
4. **Secure credentials**: Keep `conf/purchase.yaml` private (contains payment info)
5. **Log rotation**: If running via cron, set up log rotation for `logs/purchase.log`

## Troubleshooting

### No Slack notifications

- Verify webhook URL is correct
- Check network connectivity
- Review logs for Slack API errors

### Duplicate purchases despite state tracking

- Check state file location is correct
- Ensure cron job uses absolute paths
- Verify file permissions on state directory

### State file not found

- The script will create it automatically on first run
- Ensure parent directory is writable
- Default location: `state/notifications.json`
