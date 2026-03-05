"""
AWS SES Provider
Single account, very cheap ($0.10 per 1,000 emails)
Most sustainable option - no account juggling needed!
"""
from __future__ import annotations
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional
from app.email.providers.base_provider import EmailProvider


class SESProvider(EmailProvider):
    """AWS SES email provider - single account, scalable, cheap"""
    
    def __init__(self, access_key: str, secret_key: str, region: str = "us-east-1"):
        """
        Initialize AWS SES provider
        
        Args:
            access_key: AWS Access Key ID
            secret_key: AWS Secret Access Key
            region: AWS region (default: us-east-1)
        """
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.region = region
        self._quota_cache = None
    
    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """
        Send email via AWS SES
        
        Returns:
            True if sent successfully
        """
        try:
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
            }
            
            if is_html:
                message['Body'] = {
                    'Html': {'Data': body, 'Charset': 'UTF-8'}
                }
            else:
                message['Body'] = {
                    'Text': {'Data': body, 'Charset': 'UTF-8'}
                }
            
            response = self.ses_client.send_email(
                Source=from_email,
                Destination={'ToAddresses': [to_email]},
                Message=message
            )
            
            # Response contains MessageId if successful
            return 'MessageId' in response
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            raise Exception(f"AWS SES error ({error_code}): {error_msg}")
        except Exception as e:
            raise Exception(f"Failed to send via AWS SES: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test AWS SES connection by checking send quota
        
        Returns:
            True if connection OK
        """
        try:
            # Try to get send quota (lightweight check)
            response = self.ses_client.get_send_quota()
            return 'MaxSendRate' in response
        except ClientError as e:
            # Check if it's a permissions error vs connection error
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'AccessDenied':
                # Connection works, but no permissions - still counts as "connected"
                return True
            return False
        except Exception:
            return False
    
    def get_daily_limit(self) -> int:
        """
        Get daily sending limit from AWS SES quota
        
        Returns:
            Daily limit in emails (based on MaxSendRate)
        """
        try:
            if self._quota_cache is None:
                response = self.ses_client.get_send_quota()
                # MaxSendRate is emails per second
                max_send_rate = response.get('MaxSendRate', 1)  # Default 1/sec if sandbox
                # Convert to daily: rate × seconds per day
                daily_limit = int(max_send_rate * 86400)
                self._quota_cache = daily_limit
            
            return self._quota_cache
        
        except Exception:
            # Default to sandbox limit if can't get quota
            return 200  # Sandbox: 200 emails/day
    
    def get_send_statistics(self) -> Dict:
        """
        Get sending statistics from AWS SES
        
        Returns:
            Dict with sending stats (bounces, complaints, delivery attempts, etc.)
        """
        try:
            response = self.ses_client.get_send_statistics()
            return response.get('SendDataPoints', [])
        except Exception:
            return []
