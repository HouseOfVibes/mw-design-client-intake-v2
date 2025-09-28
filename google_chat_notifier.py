"""
MW Design Studio - Google Chat Webhook Notifications
Real-time notifications for client submissions and status updates
"""

import requests
from datetime import datetime
from typing import Dict
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleChatNotifier:
    """Handle Google Chat webhook notifications for MW Design Studio"""

    def __init__(self):
        self.webhook_url = self._load_webhook_config()
        
    def _load_webhook_config(self) -> str:
        """Load webhook URL from environment"""
        return os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    

    def send_simple_notification(self, form_data: Dict) -> bool:
        """Send a simple notification for the new simplified form structure"""
        try:
            webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
            if not webhook_url:
                logger.warning("Google Chat webhook URL not configured")
                return False

            # Security: Validate webhook URL format
            if not webhook_url.startswith('https://chat.googleapis.com/'):
                logger.error("Invalid Google Chat webhook URL format")
                return False

            # Create a simple card message
            services_list = ", ".join(form_data.get('services_needed', [])) if form_data.get('services_needed') else "None specified"

            # Get submitter name and current timestamp
            submitter_name = form_data.get("contact_name", "Unknown")
            business_name = form_data.get("business_name", "")
            timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')

            # Create title with submitter name
            title = f"🎉 New Inquiry from {submitter_name}"
            if business_name:
                title = f"🎉 New Inquiry from {submitter_name} ({business_name})"

            message = {
                "cards": [
                    {
                        "header": {
                            "title": title,
                            "subtitle": f"Submitted on {timestamp}",
                            "imageUrl": "https://img.icons8.com/color/48/000000/handshake.png",
                            "imageStyle": "AVATAR"
                        },
                        "sections": [
                            {
                                "header": "Contact Information",
                                "widgets": [
                                    {
                                        "keyValue": {
                                            "topLabel": "📅 Submission Time",
                                            "content": timestamp,
                                            "icon": "CLOCK"
                                        }
                                    },
                                    {
                                        "keyValue": {
                                            "topLabel": "Contact Person",
                                            "content": form_data.get("contact_name", "Not provided"),
                                            "icon": "PERSON"
                                        }
                                    },
                                    {
                                        "keyValue": {
                                            "topLabel": "Business Name",
                                            "content": form_data.get("business_name", "Not provided"),
                                            "icon": "STAR"
                                        }
                                    },
                                    {
                                        "keyValue": {
                                            "topLabel": "Email",
                                            "content": form_data.get("email", "Not provided"),
                                            "icon": "EMAIL"
                                        }
                                    }
                                ]
                            },
                            {
                                "header": "Project Details",
                                "widgets": [
                                    {
                                        "keyValue": {
                                            "topLabel": "Services Interested In",
                                            "content": services_list,
                                            "contentMultiline": True,
                                            "icon": "BOOKMARK"
                                        }
                                    },
                                    {
                                        "keyValue": {
                                            "topLabel": "Budget Range",
                                            "content": form_data.get("budget_range", "Not specified"),
                                            "icon": "DOLLAR"
                                        }
                                    },
                                    {
                                        "keyValue": {
                                            "topLabel": "Preferred Start Date",
                                            "content": form_data.get("start_date", "Not specified"),
                                            "icon": "CLOCK"
                                        }
                                    }
                                ]
                            },
                            {
                                "header": "Project Goals",
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": form_data.get("project_goals", "No details provided")[:300] + ("..." if len(form_data.get("project_goals", "")) > 300 else "")
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

            # Add phone if provided
            if form_data.get("phone"):
                message["cards"][0]["sections"][0]["widgets"].append({
                    "keyValue": {
                        "topLabel": "Phone",
                        "content": form_data.get("phone"),
                        "icon": "PHONE"
                    }
                })

            # Add preferred contact method if provided
            if form_data.get("preferred_contact"):
                message["cards"][0]["sections"][0]["widgets"].append({
                    "keyValue": {
                        "topLabel": "Preferred Contact",
                        "content": form_data.get("preferred_contact"),
                        "icon": "DESCRIPTION"
                    }
                })

            # Security: Sanitize data before sending to external service
            sanitized_message = self._sanitize_message_data(message)

            # Send the notification with security headers
            response = requests.post(
                webhook_url,
                json=sanitized_message,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'MW-Design-Studio/1.0'
                },
                timeout=10,
                verify=True  # Ensure SSL verification
            )

            if response.status_code == 200:
                logger.info("Successfully sent Google Chat notification")
                return True
            else:
                logger.error(f"Google Chat notification failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Google Chat notification: {str(e)}")
            return False

    def _sanitize_message_data(self, message: Dict) -> Dict:
        """Sanitize message data before sending to external service"""
        import html

        def sanitize_text(text):
            if isinstance(text, str):
                # Escape HTML and limit length
                return html.escape(text.strip())[:1000]
            return text

        def sanitize_dict(data):
            if isinstance(data, dict):
                return {k: sanitize_dict(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [sanitize_dict(item) for item in data]
            elif isinstance(data, str):
                return sanitize_text(data)
            return data

        return sanitize_dict(message)

    def test_webhook(self) -> bool:
        """Test the configured webhook"""
        if not self.webhook_url:
            logger.warning("No webhook URL configured")
            return False

        test_message = {
            "text": f"🧪 MW Design Studio Webhook Test • {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n" +
                   "This is a test message to verify your Google Chat webhook is working correctly. " +
                   "If you see this message, your webhook integration is properly configured!"
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=test_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Webhook test failed: {str(e)}")
            return False

# Global instance
google_chat_notifier = GoogleChatNotifier()
