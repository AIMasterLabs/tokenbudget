# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Alert channel registry — maps channel names to their dispatch functions.

Each value is the dotted import path to an async function in the alert_dispatcher
service.  To add a new channel, register it here and implement the corresponding
``send_<channel>`` function in ``app.services.alert_dispatcher``.
"""

CHANNELS = {
    "slack": "app.services.alert_dispatcher.send_slack",
    "webhook": "app.services.alert_dispatcher.send_webhook",
    "email": "app.services.alert_dispatcher.send_email",
}
