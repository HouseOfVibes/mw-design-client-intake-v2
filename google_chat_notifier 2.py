"""
MW Design Studio - Google Chat Webhook Notifications
Real-time notifications for client submissions and status updates
"""

import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
import os
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WebhookConfig:
    """Configuration for Google Chat webhooks"""
    url: str
    name: str
    description: str
    enabled: bool = True

class GoogleChatNotifier:
    """Handle Google Chat webhook notifications for MW Design Studio"""
    
    def __init__(self):
        self.webhooks = self._load_webhook_config()
        
    def _load_webhook_config(self) -> Dict[str, WebhookConfig]:
        """Load webhook configuration from environment or defaults"""
        webhooks = {}
        
        # Primary team webhook
        primary_webhook = os.getenv("GOOGLE_CHAT_WEBHOOK_PRIMARY")
        if primary_webhook:
            webhooks["primary"] = WebhookConfig(
                url=primary_webhook,
                name="MW Design Studio - Main Team",
                description="Primary team notifications",
                enabled=True
            )
        
        # Sales team webhook
        sales_webhook = os.getenv("GOOGLE_CHAT_WEBHOOK_SALES")
        if sales_webhook:
            webhooks["sales"] = WebhookConfig(
                url=sales_webhook,
                name="MW Design Studio - Sales Team",
                description="Sales and lead notifications",
                enabled=True
            )
            
        # Admin alerts webhook
        admin_webhook = os.getenv("GOOGLE_CHAT_WEBHOOK_ADMIN")
        if admin_webhook:
            webhooks["admin"] = WebhookConfig(
                url=admin_webhook,
                name="MW Design Studio - Admin Alerts",
                description="System and admin notifications",
                enabled=True
            )
        
        return webhooks
    
    def _create_card_message(self, title: str, subtitle: str, sections: List[Dict], color: str = "#20B2AA") -> Dict:
        """Create a rich card message for Google Chat"""
        return {
            "cards": [
                {
                    "header": {
                        "title": title,
                        "subtitle": subtitle,
                        "imageUrl": "https://img.icons8.com/color/48/000000/handshake.png",
                        "imageStyle": "AVATAR"
                    },
                    "sections": sections
                }
            ]
        }
    
    def _format_submission_details(self, submission_data: Dict) -> List[Dict]:
        """Format submission data into Google Chat card sections"""
        sections = []
        
        # Business Information Section
        business_widgets = [
            {
                "keyValue": {
                    "topLabel": "Business Name",
                    "content": submission_data.get("business_name", "Not provided"),
                    "icon": "STAR"
                }
            },
            {
                "keyValue": {
                    "topLabel": "Contact Person",
                    "content": submission_data.get("contact_name", "Not provided"),
                    "icon": "PERSON"
                }
            },
            {
                "keyValue": {
                    "topLabel": "Email",
                    "content": submission_data.get("email", "Not provided"),
                    "icon": "EMAIL"
                }
            }
        ]
        
        if submission_data.get("phone"):
            business_widgets.append({
                "keyValue": {
                    "topLabel": "Phone",
                    "content": submission_data.get("phone"),
                    "icon": "PHONE"
                }
            })
            
        if submission_data.get("website"):
            business_widgets.append({
                "keyValue": {
                    "topLabel": "Website",
                    "content": submission_data.get("website"),
                    "icon": "BOOKMARK",
                    "contentMultiline": "false",
                    "button": {
                        "textButton": {
                            "text": "Visit Website",
                            "onClick": {
                                "openLink": {
                                    "url": submission_data.get("website")
                                }
                            }
                        }
                    }
                }
            })
        
        sections.append({
            "header": "📋 Business Information",
            "widgets": business_widgets
        })
        
        # Project Details Section
        project_widgets = []
        
        if submission_data.get("budget"):
            project_widgets.append({
                "keyValue": {
                    "topLabel": "Monthly Budget",
                    "content": submission_data.get("budget"),
                    "icon": "DOLLAR"
                }
            })
            
        if submission_data.get("timeline"):
            project_widgets.append({
                "keyValue": {
                    "topLabel": "Timeline",
                    "content": submission_data.get("timeline"),
                    "icon": "CLOCK"
                }
            })
            
        if submission_data.get("platforms"):
            platforms_text = ", ".join(submission_data.get("platforms", []))
            project_widgets.append({
                "keyValue": {
                    "topLabel": "Target Platforms",
                    "content": platforms_text,
                    "icon": "MULTIPLE_PEOPLE"
                }
            })
            
        if submission_data.get("goals"):
            goals_text = ", ".join(submission_data.get("goals", []))
            project_widgets.append({
                "keyValue": {
                    "topLabel": "Primary Goals",
                    "content": goals_text,
                    "icon": "STAR"
                }
            })
        
        if project_widgets:
            sections.append({
                "header": "🎯 Project Details",
                "widgets": project_widgets
            })
        
        # Action Buttons Section
        admin_base_url = os.getenv("ADMIN_BASE_URL", "https://your-render-app.onrender.com")
        action_widgets = [
            {
                "buttons": [
                    {
                        "textButton": {
                            "text": "View in Admin Dashboard",
                            "onClick": {
                                "openLink": {
                                    "url": f"{admin_base_url}/admin/submission/{submission_data.get('id', '')}"
                                }
                            }
                        }
                    },
                    {
                        "textButton": {
                            "text": "Generate PDF Report",
                            "onClick": {
                                "openLink": {
                                    "url": f"{admin_base_url}/admin/submission/{submission_data.get('id', '')}/pdf"
                                }
                            }
                        }
                    }
                ]
            }
        ]
        
        sections.append({
            "header": "🚀 Quick Actions",
            "widgets": action_widgets
        })
        
        return sections
    
    async def send_new_submission_notification(self, submission_data: Dict) -> bool:
        """Send notification for new client submission"""
        try:
            # Create the main notification message
            title = "🎉 New Client Submission Received!"
            subtitle = f"MW Design Studio • {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
            
            sections = self._format_submission_details(submission_data)
            message = self._create_card_message(title, subtitle, sections)
            
            # Send to primary and sales webhooks
            success = True
            for webhook_key in ["primary", "sales"]:
                if webhook_key in self.webhooks and self.webhooks[webhook_key].enabled:
                    webhook_success = await self._send_webhook(webhook_key, message)
                    success = success and webhook_success
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending new submission notification: {str(e)}")
            return False
    
    async def send_status_update_notification(self, submission_data: Dict, old_status: str, new_status: str) -> bool:
        """Send notification when submission status changes"""
        try:
            # Determine the appropriate emoji and color for the status
            status_config = {
                "New": {"emoji": "🆕", "color": "#1E3A8A"},
                "Contacted": {"emoji": "📞", "color": "#F59E0B"},
                "Proposal Sent": {"emoji": "📄", "color": "#8B5CF6"},
                "Won": {"emoji": "🎉", "color": "#10B981"},
                "Lost": {"emoji": "😔", "color": "#EF4444"}
            }
            
            config = status_config.get(new_status, {"emoji": "📝", "color": "#6B7280"})
            
            title = f"{config['emoji']} Status Update: {submission_data.get('business_name', 'Unknown Business')}"
            subtitle = f"Changed from '{old_status}' to '{new_status}' • {datetime.now().strftime('%I:%M %p')}"
            
            # Create simplified sections for status updates
            sections = [
                {
                    "header": "📋 Client Information",
                    "widgets": [
                        {
                            "keyValue": {
                                "topLabel": "Business",
                                "content": submission_data.get("business_name", "Not provided"),
                                "icon": "STAR"
                            }
                        },
                        {
                            "keyValue": {
                                "topLabel": "Contact",
                                "content": submission_data.get("contact_name", "Not provided"),
                                "icon": "PERSON"
                            }
                        },
                        {
                            "keyValue": {
                                "topLabel": "Status Change",
                                "content": f"{old_status} → {new_status}",
                                "icon": "CLOCK"
                            }
                        }
                    ]
                }
            ]
            
            message = self._create_card_message(title, subtitle, sections, config["color"])
            
            # Send to primary webhook only for status updates
            if "primary" in self.webhooks and self.webhooks["primary"].enabled:
                return await self._send_webhook("primary", message)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending status update notification: {str(e)}")
            return False
    
    async def send_admin_alert(self, alert_type: str, message: str, details: Dict = None) -> bool:
        """Send admin system alerts"""
        try:
            alert_configs = {
                "error": {"emoji": "🚨", "color": "#EF4444"},
                "warning": {"emoji": "⚠️", "color": "#F59E0B"},
                "info": {"emoji": "ℹ️", "color": "#3B82F6"},
                "success": {"emoji": "✅", "color": "#10B981"}
            }
            
            config = alert_configs.get(alert_type, alert_configs["info"])
            
            title = f"{config['emoji']} MW Design Studio System Alert"
            subtitle = f"{alert_type.upper()} • {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
            
            sections = [
                {
                    "header": "📋 Alert Details",
                    "widgets": [
                        {
                            "textParagraph": {
                                "text": message
                            }
                        }
                    ]
                }
            ]
            
            if details:
                detail_widgets = []
                for key, value in details.items():
                    detail_widgets.append({
                        "keyValue": {
                            "topLabel": key.replace("_", " ").title(),
                            "content": str(value),
                            "icon": "DESCRIPTION"
                        }
                    })
                
                sections.append({
                    "header": "🔍 Additional Information",
                    "widgets": detail_widgets
                })
            
            card_message = self._create_card_message(title, subtitle, sections, config["color"])
            
            # Send to admin webhook
            if "admin" in self.webhooks and self.webhooks["admin"].enabled:
                return await self._send_webhook("admin", card_message)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending admin alert: {str(e)}")
            return False
    
    async def _send_webhook(self, webhook_key: str, message: Dict) -> bool:
        """Send message to specific webhook"""
        try:
            webhook = self.webhooks.get(webhook_key)
            if not webhook or not webhook.enabled:
                logger.warning(f"Webhook '{webhook_key}' not configured or disabled")
                return False
            
            response = requests.post(
                webhook.url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent notification to {webhook.name}")
                return True
            else:
                logger.error(f"Failed to send notification to {webhook.name}: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending to {webhook_key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to {webhook_key}: {str(e)}")
            return False
    
    def test_webhooks(self) -> Dict[str, bool]:
        """Test all configured webhooks"""
        results = {}
        
        test_message = {
            "text": f"🧪 MW Design Studio Webhook Test • {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n" +
                   "This is a test message to verify your Google Chat webhook is working correctly. " +
                   "If you see this message, your webhook integration is properly configured! 🎉"
        }
        
        for webhook_key, webhook in self.webhooks.items():
            if webhook.enabled:
                try:
                    response = requests.post(
                        webhook.url,
                        json=test_message,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    results[webhook_key] = response.status_code == 200
                    
                except Exception as e:
                    logger.error(f"Test failed for {webhook_key}: {str(e)}")
                    results[webhook_key] = False
            else:
                results[webhook_key] = False
                
        return results

# Global instance
google_chat_notifier = GoogleChatNotifier()
