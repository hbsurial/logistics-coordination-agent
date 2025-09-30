"""
Notification utilities for the Logistics Coordination Agent.

This module provides functions for sending notifications and alerts
to stakeholders about logistics operations.
"""

import logging
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional, Union

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manager for sending notifications to stakeholders.
    
    This class handles the sending of notifications through various channels,
    including email, SMS, dashboard updates, and API webhooks.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the Notification Manager.
        
        Args:
            config: Agent configuration settings
        """
        self.config = config
        
        # Get notification settings from config
        self.channels = config.notification_channels
        
        # Email settings
        self.email_enabled = self.channels.get("email", False)
        self.email_settings = self._get_email_settings()
        
        # SMS settings
        self.sms_enabled = self.channels.get("sms", False)
        self.sms_settings = self._get_sms_settings()
        
        # Dashboard settings
        self.dashboard_enabled = self.channels.get("dashboard", False)
        self.dashboard_settings = self._get_dashboard_settings()
        
        # API webhook settings
        self.webhook_enabled = self.channels.get("api_webhook", False)
        self.webhook_settings = self._get_webhook_settings()
        
        logger.info("Notification Manager initialized")

    def _get_email_settings(self) -> Dict[str, Any]:
        """
        Get email notification settings from environment variables.
        
        Returns:
            Dictionary of email settings
        """
        import os
        
        return {
            "smtp_server": os.getenv("NOTIFY_EMAIL_SMTP_SERVER", "smtp.example.com"),
            "smtp_port": int(os.getenv("NOTIFY_EMAIL_SMTP_PORT", "587")),
            "username": os.getenv("NOTIFY_EMAIL_USERNAME", ""),
            "password": os.getenv("NOTIFY_EMAIL_PASSWORD", ""),
            "from_address": os.getenv("NOTIFY_EMAIL_FROM", "logistics@example.com"),
            "recipients": os.getenv("NOTIFY_EMAIL_RECIPIENTS", "").split(",")
        }

    def _get_sms_settings(self) -> Dict[str, Any]:
        """
        Get SMS notification settings from environment variables.
        
        Returns:
            Dictionary of SMS settings
        """
        import os
        
        return {
            "api_url": os.getenv("NOTIFY_SMS_API_URL", "https://sms-api.example.com"),
            "api_key": os.getenv("NOTIFY_SMS_API_KEY", ""),
            "from_number": os.getenv("NOTIFY_SMS_FROM", ""),
            "recipients": os.getenv("NOTIFY_SMS_RECIPIENTS", "").split(",")
        }

    def _get_dashboard_settings(self) -> Dict[str, Any]:
        """
        Get dashboard notification settings from environment variables.
        
        Returns:
            Dictionary of dashboard settings
        """
        import os
        
        return {
            "api_url": os.getenv("NOTIFY_DASHBOARD_API_URL", "https://dashboard-api.example.com"),
            "api_key": os.getenv("NOTIFY_DASHBOARD_API_KEY", ""),
            "org_id": os.getenv("NOTIFY_DASHBOARD_ORG_ID", "")
        }

    def _get_webhook_settings(self) -> Dict[str, Any]:
        """
        Get API webhook notification settings from environment variables.
        
        Returns:
            Dictionary of webhook settings
        """
        import os
        
        return {
            "url": os.getenv("NOTIFY_WEBHOOK_URL", "https://webhook.example.com"),
            "secret": os.getenv("NOTIFY_WEBHOOK_SECRET", ""),
            "headers": json.loads(os.getenv("NOTIFY_WEBHOOK_HEADERS", "{}"))
        }

    def send_alert(self, alert_type: str, message: str, severity: str = "medium") -> bool:
        """
        Send an alert notification.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity ("low", "medium", "high")
            
        Returns:
            True if the alert was sent successfully, False otherwise
        """
        logger.info(f"Sending {severity} alert: {alert_type} - {message}")
        
        # Prepare alert data
        alert_data = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send through enabled channels
        success = True
        
        if self.email_enabled and severity != "low":
            email_success = self._send_email_alert(alert_data)
            success = success and email_success
        
        if self.sms_enabled and severity == "high":
            sms_success = self._send_sms_alert(alert_data)
            success = success and sms_success
        
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_alert(alert_data)
            success = success and dashboard_success
        
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("alert", alert_data)
            success = success and webhook_success
        
        return success

    def send_inventory_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """
        Send inventory alert notifications.
        
        Args:
            alerts: List of inventory alerts
            
        Returns:
            True if all alerts were sent successfully, False otherwise
        """
        if not alerts:
            return True
        
        logger.info(f"Sending {len(alerts)} inventory alerts")
        
        # Group alerts by severity
        alerts_by_severity = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        for alert in alerts:
            severity = alert.get("severity", "medium")
            alerts_by_severity[severity].append(alert)
        
        # Send high severity alerts individually
        success = True
        for alert in alerts_by_severity["high"]:
            message = (
                f"CRITICAL: Inventory alert for {alert['item_name']} in {alert['warehouse_name']}: "
                f"{alert['current_quantity']}/{alert['min_threshold']} {alert['unit']}"
            )
            alert_success = self.send_alert("inventory_critical", message, "high")
            success = success and alert_success
        
        # Send medium severity alerts as a group
        if alerts_by_severity["medium"]:
            items = [
                f"{a['item_name']} ({a['current_quantity']}/{a['min_threshold']} {a['unit']})"
                for a in alerts_by_severity["medium"]
            ]
            message = f"Inventory alert: {len(items)} items below threshold: {', '.join(items)}"
            alert_success = self.send_alert("inventory_warning", message, "medium")
            success = success and alert_success
        
        # Send low severity alerts as a group to dashboard only
        if alerts_by_severity["low"]:
            items = [
                f"{a['item_name']} ({a['current_quantity']}/{a['min_threshold']} {a['unit']})"
                for a in alerts_by_severity["low"]
            ]
            message = f"Inventory notice: {len(items)} items approaching threshold: {', '.join(items)}"
            alert_success = self.send_alert("inventory_notice", message, "low")
            success = success and alert_success
        
        # Send detailed inventory alerts to dashboard
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_inventory_alerts(alerts)
            success = success and dashboard_success
        
        # Send detailed inventory alerts to webhook
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("inventory_alerts", {
                "alerts": alerts,
                "timestamp": datetime.now().isoformat()
            })
            success = success and webhook_success
        
        return success

    def send_shipment_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """
        Send shipment alert notifications.
        
        Args:
            alerts: List of shipment alerts
            
        Returns:
            True if all alerts were sent successfully, False otherwise
        """
        if not alerts:
            return True
        
        logger.info(f"Sending {len(alerts)} shipment alerts")
        
        # Group alerts by severity
        alerts_by_severity = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        for alert in alerts:
            severity = alert.get("severity", "medium")
            alerts_by_severity[severity].append(alert)
        
        # Send high severity alerts individually
        success = True
        for alert in alerts_by_severity["high"]:
            message = (
                f"CRITICAL: Shipment {alert['shipment_id']} from {alert['origin']} to {alert['destination']} "
                f"is delayed by {alert['delay_minutes']:.1f} minutes"
            )
            alert_success = self.send_alert("shipment_critical", message, "high")
            success = success and alert_success
        
        # Send medium severity alerts as a group
        if alerts_by_severity["medium"]:
            shipments = [
                f"{a['shipment_id']} ({a['delay_minutes']:.1f} min)"
                for a in alerts_by_severity["medium"]
            ]
            message = f"Shipment alert: {len(shipments)} shipments delayed: {', '.join(shipments)}"
            alert_success = self.send_alert("shipment_warning", message, "medium")
            success = success and alert_success
        
        # Send low severity alerts as a group to dashboard only
        if alerts_by_severity["low"]:
            shipments = [
                f"{a['shipment_id']} ({a['delay_minutes']:.1f} min)"
                for a in alerts_by_severity["low"]
            ]
            message = f"Shipment notice: {len(shipments)} shipments slightly delayed: {', '.join(shipments)}"
            alert_success = self.send_alert("shipment_notice", message, "low")
            success = success and alert_success
        
        # Send detailed shipment alerts to dashboard
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_shipment_alerts(alerts)
            success = success and dashboard_success
        
        # Send detailed shipment alerts to webhook
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("shipment_alerts", {
                "alerts": alerts,
                "timestamp": datetime.now().isoformat()
            })
            success = success and webhook_success
        
        return success

    def send_route_alert(
        self, route_id: str, status: str, message: str, details: Dict[str, Any]
    ) -> bool:
        """
        Send a route condition alert notification.
        
        Args:
            route_id: ID of the route
            status: Status of the route
            message: Alert message
            details: Additional details about the route condition
            
        Returns:
            True if the alert was sent successfully, False otherwise
        """
        logger.info(f"Sending route alert for {route_id}: {status}")
        
        # Determine severity based on status
        severity = "high" if status == "disrupted" else "medium"
        
        # Prepare alert data
        alert_data = {
            "route_id": route_id,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send through enabled channels
        success = True
        
        if self.email_enabled and severity == "high":
            email_success = self._send_email_route_alert(alert_data)
            success = success and email_success
        
        if self.sms_enabled and severity == "high":
            sms_success = self._send_sms_route_alert(alert_data)
            success = success and sms_success
        
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_route_alert(alert_data)
            success = success and dashboard_success
        
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("route_alert", alert_data)
            success = success and webhook_success
        
        return success

    def send_shipment_update(
        self, shipment_id: str, status: str, message: str, details: Dict[str, Any]
    ) -> bool:
        """
        Send a shipment update notification.
        
        Args:
            shipment_id: ID of the shipment
            status: Status of the shipment
            message: Update message
            details: Additional details about the shipment
            
        Returns:
            True if the update was sent successfully, False otherwise
        """
        logger.info(f"Sending shipment update for {shipment_id}: {status}")
        
        # Prepare update data
        update_data = {
            "shipment_id": shipment_id,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send through enabled channels
        success = True
        
        if self.email_enabled and status in ["delivered", "cancelled", "rerouted"]:
            email_success = self._send_email_shipment_update(update_data)
            success = success and email_success
        
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_shipment_update(update_data)
            success = success and dashboard_success
        
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("shipment_update", update_data)
            success = success and webhook_success
        
        return success

    def send_inventory_update(
        self, update_type: str, message: str, details: Dict[str, Any]
    ) -> bool:
        """
        Send an inventory update notification.
        
        Args:
            update_type: Type of inventory update
            message: Update message
            details: Additional details about the inventory update
            
        Returns:
            True if the update was sent successfully, False otherwise
        """
        logger.info(f"Sending inventory update: {update_type}")
        
        # Prepare update data
        update_data = {
            "type": update_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send through enabled channels
        success = True
        
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_inventory_update(update_data)
            success = success and dashboard_success
        
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("inventory_update", update_data)
            success = success and webhook_success
        
        return success

    def send_logistics_update(
        self, update_type: str, message: str, details: Dict[str, Any]
    ) -> bool:
        """
        Send a logistics operation update notification.
        
        Args:
            update_type: Type of logistics update
            message: Update message
            details: Additional details about the logistics update
            
        Returns:
            True if the update was sent successfully, False otherwise
        """
        logger.info(f"Sending logistics update: {update_type}")
        
        # Prepare update data
        update_data = {
            "type": update_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send through enabled channels
        success = True
        
        if self.dashboard_enabled:
            dashboard_success = self._send_dashboard_logistics_update(update_data)
            success = success and dashboard_success
        
        if self.webhook_enabled:
            webhook_success = self._send_webhook_notification("logistics_update", update_data)
            success = success and webhook_success
        
        return success

    def _send_email_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert via email.
        
        Args:
            alert_data: Alert data
            
        Returns:
            True if the email was sent successfully, False otherwise
        """
        try:
            if not self.email_enabled:
                return False
            
            # Prepare email content
            subject = f"[{alert_data['severity'].upper()}] {alert_data['type']} Alert"
            body = f"{alert_data['message']}\n\nTimestamp: {alert_data['timestamp']}"
            
            # Send email
            return self._send_email(subject, body)
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            return False

    def _send_email_route_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send a route alert via email.
        
        Args:
            alert_data: Route alert data
            
        Returns:
            True if the email was sent successfully, False otherwise
        """
        try:
            if not self.email_enabled:
                return False
            
            # Prepare email content
            subject = f"Route Alert: {alert_data['route_id']} - {alert_data['status'].upper()}"
            
            body = f"{alert_data['message']}\n\n"
            body += f"Route: {alert_data['route_id']}\n"
            body += f"Status: {alert_data['status']}\n"
            body += f"Timestamp: {alert_data['timestamp']}\n\n"
            
            # Add details if available
            if "details" in alert_data:
                details = alert_data["details"]
                
                if "weather" in details:
                    weather = details["weather"]
                    body += "Weather Conditions:\n"
                    for key, value in weather.items():
                        body += f"- {key}: {value}\n"
                    body += "\n"
                
                if "road" in details:
                    road = details["road"]
                    body += "Road Conditions:\n"
                    for key, value in road.items():
                        body += f"- {key}: {value}\n"
            
            # Send email
            return self._send_email(subject, body)
        except Exception as e:
            logger.error(f"Failed to send email route alert: {str(e)}")
            return False

    def _send_email_shipment_update(self, update_data: Dict[str, Any]) -> bool:
        """
        Send a shipment update via email.
        
        Args:
            update_data: Shipment update data
            
        Returns:
            True if the email was sent successfully, False otherwise
        """
        try:
            if not self.email_enabled:
                return False
            
            # Prepare email content
            subject = f"Shipment Update: {update_data['shipment_id']} - {update_data['status'].upper()}"
            
            body = f"{update_data['message']}\n\n"
            body += f"Shipment ID: {update_data['shipment_id']}\n"
            body += f"Status: {update_data['status']}\n"
            body += f"Timestamp: {update_data['timestamp']}\n\n"
            
            # Add details if available
            if "details" in update_data:
                details = update_data["details"]
                body += "Details:\n"
                
                for key, value in details.items():
                    if key == "items":
                        body += "Items:\n"
                        for item in value:
                            body += f"- {item.get('name', 'Unknown')} ({item.get('quantity', 0)} {item.get('unit', 'units')})\n"
                    else:
                        body += f"- {key}: {value}\n"
            
            # Send email
            return self._send_email(subject, body)
        except Exception as e:
            logger.error(f"Failed to send email shipment update: {str(e)}")
            return False

    def _send_email(self, subject: str, body: str) -> bool:
        """
        Send an email.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            True if the email was sent successfully, False otherwise
        """
        try:
            if not self.email_enabled:
                return False
            
            # Get email settings
            smtp_server = self.email_settings["smtp_server"]
            smtp_port = self.email_settings["smtp_port"]
            username = self.email_settings["username"]
            password = self.email_settings["password"]
            from_address = self.email_settings["from_address"]
            recipients = self.email_settings["recipients"]
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_address
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            
            # Attach body
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def _send_sms_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert via SMS.
        
        Args:
            alert_data: Alert data
            
        Returns:
            True if the SMS was sent successfully, False otherwise
        """
        try:
            if not self.sms_enabled:
                return False
            
            # Prepare SMS content
            message = f"[{alert_data['severity'].upper()}] {alert_data['type']}: {alert_data['message']}"
            
            # Send SMS
            return self._send_sms(message)
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {str(e)}")
            return False

    def _send_sms_route_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send a route alert via SMS.
        
        Args:
            alert_data: Route alert data
            
        Returns:
            True if the SMS was sent successfully, False otherwise
        """
        try:
            if not self.sms_enabled:
                return False
            
            # Prepare SMS content
            message = f"Route {alert_data['route_id']} {alert_data['status'].upper()}: {alert_data['message']}"
            
            # Send SMS
            return self._send_sms(message)
        except Exception as e:
            logger.error(f"Failed to send SMS route alert: {str(e)}")
            return False

    def _send_sms(self, message: str) -> bool:
        """
        Send an SMS.
        
        Args:
            message: SMS message
            
        Returns:
            True if the SMS was sent successfully, False otherwise
        """
        try:
            if not self.sms_enabled:
                return False
            
            # Get SMS settings
            api_url = self.sms_settings["api_url"]
            api_key = self.sms_settings["api_key"]
            from_number = self.sms_settings["from_number"]
            recipients = self.sms_settings["recipients"]
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Send SMS to each recipient
            success = True
            for recipient in recipients:
                data = {
                    "from": from_number,
                    "to": recipient,
                    "message": message
                }
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.error(
                        f"Failed to send SMS to {recipient}: "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
                    success = False
            
            if success:
                logger.info(f"SMS sent to {len(recipients)} recipients")
            
            return success
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return False

    def _send_dashboard_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert to the dashboard.
        
        Args:
            alert_data: Alert data
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "alert",
                "data": alert_data
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard alert: {str(e)}")
            return False

    def _send_dashboard_inventory_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """
        Send inventory alerts to the dashboard.
        
        Args:
            alerts: List of inventory alerts
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "inventory_alerts",
                "data": {
                    "alerts": alerts,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard inventory alerts: {str(e)}")
            return False

    def _send_dashboard_shipment_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """
        Send shipment alerts to the dashboard.
        
        Args:
            alerts: List of shipment alerts
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "shipment_alerts",
                "data": {
                    "alerts": alerts,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard shipment alerts: {str(e)}")
            return False

    def _send_dashboard_route_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send a route alert to the dashboard.
        
        Args:
            alert_data: Route alert data
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "route_alert",
                "data": alert_data
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard route alert: {str(e)}")
            return False

    def _send_dashboard_shipment_update(self, update_data: Dict[str, Any]) -> bool:
        """
        Send a shipment update to the dashboard.
        
        Args:
            update_data: Shipment update data
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "shipment_update",
                "data": update_data
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard shipment update: {str(e)}")
            return False

    def _send_dashboard_inventory_update(self, update_data: Dict[str, Any]) -> bool:
        """
        Send an inventory update to the dashboard.
        
        Args:
            update_data: Inventory update data
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "inventory_update",
                "data": update_data
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard inventory update: {str(e)}")
            return False

    def _send_dashboard_logistics_update(self, update_data: Dict[str, Any]) -> bool:
        """
        Send a logistics update to the dashboard.
        
        Args:
            update_data: Logistics update data
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Prepare dashboard data
            dashboard_data = {
                "event_type": "logistics_update",
                "data": update_data
            }
            
            # Send to dashboard
            return self._send_dashboard_update(dashboard_data)
        except Exception as e:
            logger.error(f"Failed to send dashboard logistics update: {str(e)}")
            return False

    def _send_dashboard_update(self, dashboard_data: Dict[str, Any]) -> bool:
        """
        Send an update to the dashboard.
        
        Args:
            dashboard_data: Dashboard update data
            
        Returns:
            True if the dashboard update was sent successfully, False otherwise
        """
        try:
            if not self.dashboard_enabled:
                return False
            
            # Get dashboard settings
            api_url = self.dashboard_settings["api_url"]
            api_key = self.dashboard_settings["api_key"]
            org_id = self.dashboard_settings["org_id"]
            
            # Add organization ID
            dashboard_data["org_id"] = org_id
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Send update
            response = requests.post(
                api_url,
                headers=headers,
                json=dashboard_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Failed to send dashboard update: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                return False
            
            logger.info(f"Dashboard update sent: {dashboard_data['event_type']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send dashboard update: {str(e)}")
            return False

    def _send_webhook_notification(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a notification via webhook.
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            True if the webhook notification was sent successfully, False otherwise
        """
        try:
            if not self.webhook_enabled:
                return False
            
            # Get webhook settings
            webhook_url = self.webhook_settings["url"]
            webhook_secret = self.webhook_settings["secret"]
            webhook_headers = self.webhook_settings["headers"]
            
            # Prepare webhook data
            webhook_data = {
                "event_type": event_type,
                "data": data,
                "agent": self.config.agent_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Prepare request
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Secret": webhook_secret
            }
            
            # Add custom headers
            for key, value in webhook_headers.items():
                headers[key] = value
            
            # Send webhook notification
            response = requests.post(
                webhook_url,
                headers=headers,
                json=webhook_data,
                timeout=10
            )
            
            if response.status_code not in [200, 201, 202]:
                logger.error(
                    f"Failed to send webhook notification: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                return False
            
            logger.info(f"Webhook notification sent: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            return False
