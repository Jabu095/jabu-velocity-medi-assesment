"""
AI Chat views for conversational event discovery.
"""

import json
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone

from .chat_models import ChatConversation, ChatMessage, UserTokenUsage
from .models import Event
from .serializers import EventListSerializer

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Rough estimate of tokens (1 token ≈ 4 characters)."""
    return len(text) // 4


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_send_message(request):
    """
    Send a message to the AI chat and get a response.
    
    POST /api/ai/chat/
    Body: {
        "message": "Find jazz concerts this weekend",
        "conversation_id": 1  # optional
    }
    """
    message = request.data.get('message', '').strip()
    conversation_id = request.data.get('conversation_id')
    
    if not message:
        return Response(
            {'error': 'Message is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get or create conversation
    if conversation_id:
        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id,
                user=request.user
            )
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Create new conversation
        conversation = ChatConversation.objects.create(
            user=request.user,
            title=message[:50]  # Use first 50 chars as title
        )
    
    # Get user's token usage
    token_usage = UserTokenUsage.get_or_create_for_user(request.user)
    
    # Estimate tokens for user message
    user_tokens = estimate_tokens(message)
    
    # Check rate limit (10,000 tokens per user)
    if not token_usage.can_use_tokens(user_tokens + 500):  # Reserve 500 for response
        return Response(
            {
                'error': 'Token limit exceeded',
                'tokens_used': token_usage.tokens_used,
                'limit': token_usage.monthly_limit,
                'message': f'You have used {token_usage.tokens_used}/{token_usage.monthly_limit} tokens. Please wait for the next reset period.'
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Save user message
    user_message = ChatMessage.objects.create(
        conversation=conversation,
        role='user',
        content=message,
        tokens_used=user_tokens
    )
    token_usage.add_tokens(user_tokens)
    
    # Generate AI response
    try:
        response_content, response_tokens = generate_ai_response(
            message,
            conversation,
            request.user
        )
        
        # Save assistant message
        assistant_message = ChatMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=response_content,
            tokens_used=response_tokens
        )
        token_usage.add_tokens(response_tokens)
        
        # Update conversation title if it's the first message
        if conversation.messages.count() == 2:  # User + Assistant
            conversation.title = message[:50]
            conversation.save()
        
        return Response({
            'conversation_id': conversation.id,
            'message': {
                'role': 'assistant',
                'content': response_content,
                'created_at': assistant_message.created_at.isoformat()
            },
            'tokens_used': token_usage.tokens_used,
            'tokens_remaining': token_usage.monthly_limit - token_usage.tokens_used
        })
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return Response(
            {'error': 'Failed to generate response. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_ai_response(message: str, conversation: ChatConversation, user) -> tuple[str, int]:
    """
    Generate AI response using OpenAI or fallback.
    
    Returns:
        Tuple of (response_content, tokens_used)
    """
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        # Fallback: Simple keyword-based response
        return generate_fallback_response(message, conversation)
    
    try:
        import openai
        from .ai_services import NaturalLanguageSearch
        
        client = openai.OpenAI(api_key=api_key)
        
        # Get conversation history (last 10 messages for context)
        recent_messages = conversation.messages.order_by('-created_at')[:10]
        history = []
        for msg in reversed(recent_messages):
            history.append({
                'role': msg.role,
                'content': msg.content
            })
        
        # Add system prompt
        system_prompt = """You are a helpful assistant for the Velocity Media Events app. 
You help users discover events in Johannesburg and Pretoria, South Africa.
You can search for events, answer questions about events, and provide recommendations.
Be friendly, concise, and helpful. If you find relevant events, mention them specifically."""
        
        messages = [
            {'role': 'system', 'content': system_prompt}
        ] + history + [
            {'role': 'user', 'content': message}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else estimate_tokens(content)
        
        # Try to find relevant events if the query seems like a search
        if any(keyword in message.lower() for keyword in ['find', 'search', 'show', 'events', 'concerts', 'music', 'sports']):
            events = search_events_from_query(message)
            if events:
                content += f"\n\n📅 **Found {len(events)} relevant events:**\n"
                for event in events[:5]:  # Show top 5
                    date_str = event.start_date.strftime('%b %d, %Y') if event.start_date else 'TBD'
                    content += f"- **{event.title}** ({event.city}) - {date_str}\n"
        
        return content, tokens_used
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return generate_fallback_response(message, conversation)


def generate_fallback_response(message: str, conversation: ChatConversation) -> tuple[str, int]:
    """Generate a simple fallback response without AI."""
    from .ai_services import NaturalLanguageSearch
    
    nlp = NaturalLanguageSearch()
    params = nlp.parse_query(message)
    
    # Search for events
    events = search_events_from_query(message)
    
    if events:
        response = f"I found {len(events)} events that might interest you:\n\n"
        for event in events[:5]:
            date_str = event.start_date.strftime('%b %d, %Y') if event.start_date else 'TBD'
            response += f"• **{event.title}** in {event.city} - {date_str}\n"
        response += "\nWould you like more details about any of these events?"
    else:
        response = "I couldn't find specific events matching your query. Try asking about:\n"
        response += "- Music concerts\n- Sports events\n- Food festivals\n- Arts exhibitions\n"
        response += "Or be more specific with location (Johannesburg/Pretoria) and date."
    
    tokens = estimate_tokens(response)
    return response, tokens


def search_events_from_query(query: str):
    """Search events based on natural language query."""
    from .ai_services import NaturalLanguageSearch
    from django.db.models import Q
    
    nlp = NaturalLanguageSearch()
    params = nlp.parse_query(query)
    
    queryset = Event.objects.filter(start_date__gte=timezone.now())
    
    if params.get('city'):
        queryset = queryset.filter(city__iexact=params['city'])
    
    if params.get('category'):
        queryset = queryset.filter(category__iexact=params['category'])
    
    if params.get('keywords'):
        keyword_q = Q()
        for keyword in params['keywords']:
            keyword_q |= (
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(venue_name__icontains=keyword)
            )
        queryset = queryset.filter(keyword_q)
    
    if params.get('date_range'):
        start_date, end_date = params['date_range']
        if start_date and end_date:
            queryset = queryset.filter(
                start_date__date__gte=start_date,
                start_date__date__lte=end_date
            )
    
    return list(queryset[:10])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_conversations(request):
    """Get all conversations for the current user."""
    conversations = ChatConversation.objects.filter(user=request.user)
    
    data = []
    for conv in conversations:
        data.append({
            'id': conv.id,
            'title': conv.title,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
            'message_count': conv.messages.count()
        })
    
    return Response({'conversations': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_messages(request, conversation_id):
    """Get all messages in a conversation."""
    try:
        conversation = ChatConversation.objects.get(
            id=conversation_id,
            user=request.user
        )
    except ChatConversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    messages = conversation.messages.all()
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'tokens_used': msg.tokens_used
        })
    
    return Response({'messages': data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def chat_delete_conversation(request, conversation_id):
    """Delete a conversation."""
    try:
        conversation = ChatConversation.objects.get(
            id=conversation_id,
            user=request.user
        )
        conversation.delete()
        return Response({'success': True})
    except ChatConversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_token_usage(request):
    """Get current token usage for the user."""
    token_usage = UserTokenUsage.get_or_create_for_user(request.user)
    token_usage.reset_if_needed()
    
    return Response({
        'tokens_used': token_usage.tokens_used,
        'tokens_limit': token_usage.monthly_limit,
        'tokens_remaining': token_usage.monthly_limit - token_usage.tokens_used,
        'percentage_used': (token_usage.tokens_used / token_usage.monthly_limit * 100) if token_usage.monthly_limit > 0 else 0,
        'last_reset': token_usage.last_reset.isoformat()
    })

