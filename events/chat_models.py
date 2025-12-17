"""
Chat models for AI conversation tracking and rate limiting.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ChatConversation(models.Model):
    """Stores AI chat conversations."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_conversations',
        help_text="User who owns this conversation"
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Auto-generated conversation title"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Chat Conversation'
        verbose_name_plural = 'Chat Conversations'
    
    def __str__(self):
        return f"{self.user.username} - {self.title or 'Untitled'} ({self.created_at.strftime('%Y-%m-%d')})"


class ChatMessage(models.Model):
    """Individual messages in a conversation."""
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Conversation this message belongs to"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Message role (user, assistant, system)"
    )
    content = models.TextField(
        help_text="Message content"
    )
    tokens_used = models.IntegerField(
        default=0,
        help_text="Number of tokens used for this message"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class UserTokenUsage(models.Model):
    """Tracks token usage per user for rate limiting."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='token_usage',
        help_text="User whose token usage is tracked"
    )
    tokens_used = models.IntegerField(
        default=0,
        help_text="Total tokens used (resets monthly or on reset)"
    )
    last_reset = models.DateTimeField(
        auto_now_add=True,
        help_text="When token usage was last reset"
    )
    monthly_limit = models.IntegerField(
        default=10000,
        help_text="Monthly token limit per user"
    )
    
    class Meta:
        verbose_name = 'User Token Usage'
        verbose_name_plural = 'User Token Usage'
    
    def __str__(self):
        return f"{self.user.username}: {self.tokens_used}/{self.monthly_limit} tokens"
    
    def reset_if_needed(self):
        """Reset token usage if a month has passed."""
        from datetime import timedelta
        if timezone.now() - self.last_reset > timedelta(days=30):
            self.tokens_used = 0
            self.last_reset = timezone.now()
            self.save()
    
    def can_use_tokens(self, tokens: int) -> bool:
        """Check if user can use specified number of tokens."""
        self.reset_if_needed()
        return (self.tokens_used + tokens) <= self.monthly_limit
    
    def add_tokens(self, tokens: int):
        """Add tokens to usage count."""
        self.reset_if_needed()
        self.tokens_used += tokens
        self.save()
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create token usage tracking for a user."""
        usage, created = cls.objects.get_or_create(
            user=user,
            defaults={'tokens_used': 0, 'monthly_limit': 10000}
        )
        return usage

