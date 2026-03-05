"""
Rate Limiter
Controls sending velocity and daily limits per mailbox
"""
from __future__ import annotations
import time
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict


class RateLimiter:
    """Manages rate limiting for email sending"""
    
    def __init__(self):
        self.last_sent: Dict[int, float] = defaultdict(float)
        self.min_delay = 2  # Minimum seconds between emails
        self.max_delay = 5  # Maximum seconds between emails
        self.max_per_minute = 5  # Max emails per minute per mailbox
    
    def can_send(self, mailbox_id: int, daily_limit: int = 500) -> bool:
        """
        Check if we can send an email now for this mailbox.
        Note: Daily limit is checked by MailboxPool, this handles velocity.
        """
        now = time.time()
        last = self.last_sent[mailbox_id]
        
        # Check velocity (emails per minute)
        if last > 0:
            time_since_last = now - last
            min_interval = 60 / self.max_per_minute  # e.g., 12 seconds for 5/min
            if time_since_last < min_interval:
                return False
        
        return True
    
    def record_sent(self, mailbox_id: int):
        """Record that an email was sent"""
        self.last_sent[mailbox_id] = time.time()
    
    def get_delay(self) -> float:
        """Get randomized delay between sends (to avoid detection)"""
        return random.uniform(self.min_delay, self.max_delay)
    
    def reset(self, mailbox_id: int = None):
        """Reset rate limiter for a mailbox or all"""
        if mailbox_id:
            self.last_sent.pop(mailbox_id, None)
        else:
            self.last_sent.clear()

