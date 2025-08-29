#!/usr/bin/env python3
"""
Email Notifier for Verified Predictions
Sends email notifications when predictions are verified as TRUE
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import logging
import os

from verification_result import VerificationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SENDER_EMAIL', 'calledit@example.com')
        self.sender_password = os.getenv('SENDER_PASSWORD', '')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL', 'user@example.com')
    
    def send_verification_email(self, prediction: Dict[str, Any], result: VerificationResult):
        """Send email notification for verified TRUE prediction"""
        try:
            # Create email content
            subject = f"🎯 Prediction Verified TRUE: {prediction.get('prediction_statement', 'Unknown')[:50]}..."
            
            body = self._create_email_body(prediction, result)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.notification_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            if self.sender_password:  # Only send if credentials are configured
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
                
                logger.info(f"📧 Sent verification email for: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
            else:
                logger.info(f"📧 Email notification (not sent - no credentials): {subject}")
                
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            # Don't raise - email failure shouldn't stop verification
    
    def _create_email_body(self, prediction: Dict[str, Any], result: VerificationResult) -> str:
        """Create HTML email body"""
        statement = prediction.get('prediction_statement', 'Unknown')
        category = prediction.get('verifiable_category', 'unknown')
        verification_date = prediction.get('verification_date', 'Unknown')
        
        return f"""
        <html>
        <body>
            <h2>🎯 Prediction Verified TRUE!</h2>
            
            <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Prediction Details</h3>
                <p><strong>Statement:</strong> {statement}</p>
                <p><strong>Category:</strong> {category}</p>
                <p><strong>Original Verification Date:</strong> {verification_date}</p>
                <p><strong>Verified On:</strong> {result.verification_date.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div style="background-color: #f0fff0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Verification Results</h3>
                <p><strong>Status:</strong> ✅ TRUE</p>
                <p><strong>Confidence:</strong> {result.confidence:.1%}</p>
                <p><strong>Method:</strong> {result.verification_method or 'Standard verification'}</p>
                <p><strong>Tools Used:</strong> {', '.join(result.tools_used) if result.tools_used else 'None'}</p>
            </div>
            
            <div style="background-color: #fffacd; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Agent Reasoning</h3>
                <p>{result.reasoning}</p>
                
                <details>
                    <summary>Full Agent Analysis</summary>
                    <p style="font-family: monospace; white-space: pre-wrap; background-color: #f5f5f5; padding: 10px; border-radius: 3px;">
{result.agent_thoughts}
                    </p>
                </details>
            </div>
            
            <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0; font-size: 12px; color: #666;">
                <p>Processing Time: {result.processing_time_ms}ms</p>
                <p>Prediction ID: {result.prediction_id}</p>
            </div>
            
            <hr>
            <p style="font-size: 12px; color: #888;">
                This email was sent by the CalledIt Prediction Verification System.<br>
                Your prediction was automatically verified using AI agents and available tools.
            </p>
        </body>
        </html>
        """

def main():
    """Test email notification"""
    from verification_result import VerificationResult, VerificationStatus
    from datetime import datetime
    
    notifier = EmailNotifier()
    
    # Mock prediction and result for testing
    mock_prediction = {
        'prediction_statement': 'The sun will rise tomorrow morning',
        'verifiable_category': 'agent_verifiable',
        'verification_date': '2025-01-28T06:00:00Z'
    }
    
    mock_result = VerificationResult(
        prediction_id="test_email",
        status=VerificationStatus.TRUE,
        confidence=0.95,
        reasoning="Verified through astronomical knowledge and natural laws",
        verification_date=datetime.now(),
        tools_used=['reasoning'],
        agent_thoughts="The sun rises every day due to Earth's rotation. This is a fundamental astronomical fact that can be verified through established scientific knowledge.",
        processing_time_ms=2500,
        verification_method='agent_reasoning'
    )
    
    print("🧪 Testing email notification...")
    notifier.send_verification_email(mock_prediction, mock_result)
    print("✅ Email notification test complete")

if __name__ == "__main__":
    main()