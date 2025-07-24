# Gmail Integration

This module provides Gmail integration with callback functionality for incoming emails using Google Cloud Pub/Sub.

## Overview

The integration allows you to:
- Send emails via Gmail API
- Receive emails with callback functions
- Use Google Cloud Pub/Sub for real-time email notifications

## Setup

### Prerequisites

1. Google Cloud project (project ID: `darcy-457705`)
2. Gmail API enabled
3. Pub/Sub API enabled
4. Service account: `ai@dscubed.org.au`

### Authentication

1. Login to Google Cloud:
```bash
gcloud auth login
```

2. Ensure correct project is selected:
```bash
gcloud config get-value project
# Should output: darcy-457705
```

3. If needed, set application default credentials:
```bash
gcloud auth application-default login
```

### Configuration Files

Place the following files in the `sub/` directory:
- `token.json` - OAuth token
- `credentials.json` - Service account credentials

### Running the Demo

```bash
python3 "gcloud/gmail/3_gmail_demo_sub_pub.py"
```

## Initial Setup

If setting up from scratch:
1. Run the setup script: `./setup.sh`
2. Note: The script may have some issues with the original email configuration, but should work with the current email setup

## Architecture

The integration uses:
- Gmail API for email operations
- Google Cloud Pub/Sub for real-time notifications
- Callback functions for email event handling