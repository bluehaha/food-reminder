# Food Reminder

Monitor food product availability on wagashi.com.tw and receive Slack notifications when items become available.

## Features

- Monitor multiple product URLs
- Slack notifications when products become available
- State management to avoid duplicate notifications
- Automatic retry with exponential backoff
- Comprehensive error handling and logging
- CLI interface for manual execution

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry package manager

### Setup

1. Install dependencies:
```bash
poetry install
```

2. Create configuration file:
```bash
cp conf/config.example.yaml conf/config.yaml
```

3. Edit `conf/config.yaml` with your settings:
   - Add product URLs to monitor
   - Set your Slack webhook URL
   - Adjust other settings as needed

## Usage

### Check Product Availability

```bash
poetry run python scripts/check_availability.py
```

### Options

```bash
# Use custom config file
poetry run python scripts/check_availability.py -c /path/to/config.yaml

# Enable verbose logging
poetry run python scripts/check_availability.py -v

# Clear notification state for a product
poetry run python scripts/check_availability.py --clear-state "https://www.wagashi.com.tw/product/example/"
```

### Using Makefile

```bash
# Install dependencies
make install

# Run checker
make run

# Run tests
make test

# Format and lint
make check
```

## Configuration

See `conf/config.example.yaml` for configuration options.

### Product Configuration

```yaml
products:
  - url: "https://www.wagashi.com.tw/product/product-name/"
    name: "Friendly Product Name"  # Optional, auto-generated from URL if omitted
```

### Slack Configuration

Get a webhook URL from: https://api.slack.com/messaging/webhooks

```yaml
slack:
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  username: "Food Availability Bot"
  icon_emoji: ":bento:"
```

## Architecture

The project follows SOLID principles with clear separation of concerns:

- **Checker**: Checks product availability (WooCommerce-specific logic)
- **Notifier**: Sends Slack notifications
- **StateStore**: Manages notification state (JSON file)
- **MonitoringService**: Orchestrates the check-notify workflow
- **ConfigLoader**: Loads and validates configuration

All components use dependency injection and abstract interfaces for testability and extensibility.

## State Management

The application tracks which products have been notified in `state/notifications.json`:

```json
{
  "https://www.wagashi.com.tw/product/example/": "2026-01-04T10:30:00"
}
```

When a product goes back out of stock, the notification state is cleared automatically, so you'll be notified when it becomes available again.

## Development

### Project Structure

```
food-reminder/
├── src/
│   ├── core/              # Business logic
│   │   ├── interfaces.py  # Abstract interfaces
│   │   ├── checker.py     # Product availability checker
│   │   ├── notifier.py    # Slack notifier
│   │   ├── state.py       # State management
│   │   └── service.py     # Orchestration service
│   ├── config/            # Configuration management
│   ├── utils/             # Utilities (logging, exceptions)
├── scripts/               # CLI entry points
├── tests/                 # Unit and integration tests
├── conf/                  # Configuration files
└── state/                 # Runtime state (git-ignored)
```

### Running Tests

```bash
make test
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Run all checks
make check
```

## How It Works

### Stock Detection

The system checks product availability by analyzing the HTML of product pages:

1. **Primary Method**: Check the product `<div>` class attribute for `instock` or `outofstock`
2. **Secondary Method**: Check for the presence of `out_of_stock_wrapper` div

This approach was determined through analysis of the wagashi.com.tw website (WooCommerce-based).

### Notification Flow

1. Product becomes available (outofstock → instock)
2. Check state: not previously notified
3. Send Slack notification
4. Mark as notified in state file
5. **Future checks**: Skip notification while in stock
6. Product goes out of stock (instock → outofstock)
7. Clear notification state
8. **Next availability**: Will notify again (repeat from step 1)

## License

MIT
