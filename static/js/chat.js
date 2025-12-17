/**
 * AI Chat functionality for event discovery.
 */

let currentConversationId = null;
let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }
    
    // Load conversations and token usage
    loadConversations();
    loadTokenUsage();
    
    // Setup form handler
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    
    form.addEventListener('submit', handleSendMessage);
    
    // Auto-resize textarea
    input.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
    
    // Mobile sidebar toggle
    const sidebar = document.getElementById('chat-sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const headerSidebarToggle = document.getElementById('header-sidebar-toggle');
    const sidebarOverlay = document.createElement('div');
    sidebarOverlay.className = 'sidebar-overlay';
    sidebarOverlay.style.cssText = 'display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 998;';
    document.body.appendChild(sidebarOverlay);
    
    function toggleSidebar() {
        if (window.innerWidth <= 768 && sidebar) {
            sidebar.classList.toggle('active');
            sidebarOverlay.style.display = sidebar.classList.contains('active') ? 'block' : 'none';
            document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
        }
    }
    
    function closeSidebar() {
        if (window.innerWidth <= 768 && sidebar) {
            sidebar.classList.remove('active');
            sidebarOverlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    }
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleSidebar();
        });
    }
    
    if (headerSidebarToggle && sidebar) {
        headerSidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleSidebar();
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            closeSidebar();
        });
    }
    
    // Close sidebar when clicking a conversation on mobile
    const conversationList = document.getElementById('conversation-list');
    if (conversationList) {
        conversationList.addEventListener('click', function(e) {
            if (e.target.closest('.conversation-item') && window.innerWidth <= 768) {
                setTimeout(closeSidebar, 300);
            }
        });
    }
    
    // New chat button with sidebar close
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', function() {
            startNewChat();
            if (window.innerWidth <= 768) {
                setTimeout(closeSidebar, 100);
            }
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && sidebar) {
            sidebar.classList.remove('active');
            sidebarOverlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    });
});

async function loadConversations() {
    try {
        const data = await apiCall('/api/ai/chat/conversations/');
        displayConversations(data.conversations);
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
}

function displayConversations(conversations) {
    const list = document.getElementById('conversation-list');
    list.innerHTML = '';
    
    if (conversations.length === 0) {
        list.innerHTML = '<li style="padding: 1rem; color: var(--text-secondary); text-align: center;">No conversations yet</li>';
        return;
    }
    
    conversations.forEach(conv => {
        const item = document.createElement('li');
        item.className = 'conversation-item';
        if (conv.id === currentConversationId) {
            item.classList.add('active');
        }
        
        item.innerHTML = `
            <h4>${escapeHtml(conv.title || 'Untitled')}</h4>
            <p>${conv.message_count} messages</p>
        `;
        
        item.addEventListener('click', () => loadConversation(conv.id));
        
        list.appendChild(item);
    });
}

async function loadConversation(conversationId) {
    currentConversationId = conversationId;
    loadConversations(); // Refresh to highlight active
    
    try {
        const data = await apiCall(`/api/ai/chat/conversations/${conversationId}/messages/`);
        displayMessages(data.messages);
    } catch (error) {
        console.error('Failed to load conversation:', error);
        showError('Failed to load conversation');
    }
}

function displayMessages(messages) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    
    if (messages.length === 0) {
        container.innerHTML = `
            <div class="empty-chat">
                <h3>Start the conversation</h3>
                <p>Send a message to begin!</p>
            </div>
        `;
        return;
    }
    
    messages.forEach(msg => {
        addMessageToChat(msg.role, msg.content, msg.created_at);
    });
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

async function handleSendMessage(e) {
    e.preventDefault();
    
    if (isLoading) return;
    
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Clear input
    input.value = '';
    input.style.height = 'auto';
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Show loading
    showLoading();
    isLoading = true;
    document.getElementById('send-btn').disabled = true;
    
    try {
        const payload = {
            message: message
        };
        
        if (currentConversationId) {
            payload.conversation_id = currentConversationId;
        }
        
        const data = await apiCall('/api/ai/chat/', {
            method: 'POST',
            body: JSON.stringify(payload),
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // Hide loading
        hideLoading();
        
        // Update conversation ID
        if (data.conversation_id) {
            currentConversationId = data.conversation_id;
            loadConversations(); // Refresh sidebar
        }
        
        // Add assistant response
        addMessageToChat('assistant', data.message.content, data.message.created_at);
        
        // Update token usage
        if (data.tokens_used !== undefined) {
            updateTokenUsage(data.tokens_used, data.tokens_remaining);
        }
        
    } catch (error) {
        hideLoading();
        console.error('Failed to send message:', error);
        
        let errorMsg = 'Failed to send message. Please try again.';
        if (error.response && error.response.status === 429) {
            errorMsg = error.response.data?.message || 'Token limit exceeded. Please wait for the next reset period.';
        }
        
        showError(errorMsg);
    } finally {
        isLoading = false;
        document.getElementById('send-btn').disabled = false;
    }
}

function addMessageToChat(role, content, timestamp = null) {
    const container = document.getElementById('chat-messages');
    
    // Remove empty state if present
    const emptyChat = container.querySelector('.empty-chat');
    if (emptyChat) {
        emptyChat.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'You' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format content (support markdown-like formatting)
    contentDiv.innerHTML = formatMessageContent(content);
    
    if (timestamp) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const date = new Date(timestamp);
        timeDiv.textContent = date.toLocaleTimeString('en-ZA', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        contentDiv.appendChild(timeDiv);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function formatMessageContent(content) {
    // Simple formatting: bold (**text**), line breaks, links
    let formatted = escapeHtml(content);
    
    // Bold text
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Links (basic URL detection)
    formatted = formatted.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );
    
    return formatted;
}

function showLoading() {
    const container = document.getElementById('chat-messages');
    const loading = document.createElement('div');
    loading.className = 'message assistant';
    loading.id = 'loading-message';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    loadingDiv.innerHTML = `
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
    `;
    
    loading.appendChild(avatar);
    loading.appendChild(loadingDiv);
    container.appendChild(loading);
    container.scrollTop = container.scrollHeight;
}

function hideLoading() {
    const loading = document.getElementById('loading-message');
    if (loading) {
        loading.remove();
    }
}

function showError(message) {
    const container = document.getElementById('chat-messages');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message assistant';
    errorDiv.style.opacity = '0.7';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '!';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.style.color = '#dc2626';
    contentDiv.textContent = message;
    
    errorDiv.appendChild(avatar);
    errorDiv.appendChild(contentDiv);
    container.appendChild(errorDiv);
    container.scrollTop = container.scrollHeight;
}

async function loadTokenUsage() {
    try {
        const data = await apiCall('/api/ai/chat/token-usage/');
        updateTokenUsage(data.tokens_used, data.tokens_remaining);
    } catch (error) {
        console.error('Failed to load token usage:', error);
    }
}

function updateTokenUsage(used, remaining) {
    const total = used + remaining;
    const percentage = total > 0 ? (used / total * 100) : 0;
    
    document.getElementById('token-usage-text').textContent = 
        `${used.toLocaleString()}/${total.toLocaleString()} tokens`;
    
    const progressBar = document.getElementById('token-progress-bar');
    progressBar.style.width = `${percentage}%`;
    
    // Change color based on usage
    if (percentage > 90) {
        progressBar.style.backgroundColor = '#dc2626'; // Red
    } else if (percentage > 75) {
        progressBar.style.backgroundColor = '#f59e0b'; // Orange
    } else {
        progressBar.style.backgroundColor = 'var(--primary-color)';
    }
}

function startNewChat() {
    currentConversationId = null;
    loadConversations();
    
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="empty-chat">
            <h3>👋 New Conversation</h3>
            <p>Ask me about events in Johannesburg or Pretoria!</p>
            <p>Try: "Find jazz concerts this weekend"</p>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

