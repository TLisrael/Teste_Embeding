from flask import Flask, render_template_string, request, jsonify
import requests
import json
import warnings
import re
import uuid
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta
from contextlib import contextmanager

# Suprimir ResourceWarning temporariamente
warnings.filterwarnings("ignore", category=ResourceWarning)

app = Flask(__name__)

# Configuração do banco de dados
DATABASE = 'chatbot_memory.db'

# Configuração de debug - altere para False em produção
DEBUG_MEMORY = True

class DatabaseManager:
    def __init__(self, db_path=DATABASE):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados e cria as tabelas necessárias"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de usuários (identificados por IP)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_hash TEXT UNIQUE NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 0
                )
            ''')
            
            # Tabela de conversas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Tabela de mensagens
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    message_type TEXT NOT NULL, -- 'user' ou 'ai'
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_id TEXT UNIQUE,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            ''')
            
            # Índices para melhor performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_ip_hash ON users (ip_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)')
            
            conn.commit()
    
    def get_user_id(self, ip_address):
        """Obtém ou cria um usuário baseado no IP"""
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tentar encontrar usuário existente
            cursor.execute('SELECT id FROM users WHERE ip_hash = ?', (ip_hash,))
            user = cursor.fetchone()
            
            if user:
                # Atualizar último acesso
                cursor.execute('''
                    UPDATE users 
                    SET last_seen = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user[0],))
                return user[0]
            else:
                # Criar novo usuário
                cursor.execute('''
                    INSERT INTO users (ip_hash, first_seen, last_seen) 
                    VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (ip_hash,))
                return cursor.lastrowid
    
    def get_current_conversation_id(self, user_id):
        """Obtém ou cria uma conversa única para o usuário (sem sessões separadas)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Procurar conversa existente do usuário (sempre a mesma)
            cursor.execute('''
                SELECT id FROM conversations 
                WHERE user_id = ?
                ORDER BY created_at ASC 
                LIMIT 1
            ''', (user_id,))
            
            conversation = cursor.fetchone()
            
            if conversation:
                # Atualizar timestamp da última mensagem
                cursor.execute('''
                    UPDATE conversations 
                    SET last_message_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (conversation[0],))
                return conversation[0]
            else:
                # Criar única conversa para o usuário
                cursor.execute('''
                    INSERT INTO conversations (user_id, session_id, created_at, last_message_at, title) 
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
                ''', (user_id, 'main_conversation', 'Conversa Principal'))
                return cursor.lastrowid
    
    def save_message(self, conversation_id, message_type, content, response_id=None):
        """Salva uma mensagem no banco"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (conversation_id, message_type, content, response_id, timestamp) 
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (conversation_id, message_type, content, response_id))
            
            # Atualizar última mensagem da conversa
            cursor.execute('''
                UPDATE conversations 
                SET last_message_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (conversation_id,))
            
            # Atualizar contador de mensagens do usuário
            cursor.execute('''
                UPDATE users 
                SET total_messages = total_messages + 1 
                WHERE id = (SELECT user_id FROM conversations WHERE id = ?)
            ''', (conversation_id,))
            
            return cursor.lastrowid
    
    def get_conversation_history(self, user_id, limit=20):
        """Obtém histórico recente de conversas do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT m.message_type, m.content, m.timestamp 
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
            
            return cursor.fetchall()
    
    def get_recent_session_messages(self, conversation_id, limit=6):
        """Obtém as mensagens mais recentes de uma conversa específica para contexto"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message_type, content, timestamp 
                FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (conversation_id, limit))
            
            return cursor.fetchall()
    
    def get_user_conversations(self, user_id):
        """Lista todas as conversas do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.id, c.session_id, c.created_at, c.last_message_at, c.title,
                       COUNT(m.id) as message_count,
                       MAX(CASE WHEN m.message_type = 'user' THEN m.content END) as first_message
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ?
                GROUP BY c.id, c.session_id, c.created_at, c.last_message_at, c.title
                ORDER BY c.last_message_at DESC
            ''', (user_id,))
            
            return cursor.fetchall()
    
    def get_conversation_messages(self, conversation_id, user_id):
        """Obtém todas as mensagens de uma conversa específica"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Verificar se a conversa pertence ao usuário
            cursor.execute('''
                SELECT id FROM conversations 
                WHERE id = ? AND user_id = ?
            ''', (conversation_id, user_id))
            
            if not cursor.fetchone():
                return []
            
            cursor.execute('''
                SELECT message_type, content, timestamp, response_id
                FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            ''', (conversation_id,))
            
            return cursor.fetchall()
    
    def update_conversation_title(self, conversation_id, title):
        """Atualiza o título de uma conversa"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE conversations 
                SET title = ? 
                WHERE id = ?
            ''', (title, conversation_id))
    
    def search_conversations(self, user_id, query):
        """Busca conversas por conteúdo"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT c.id, c.session_id, c.created_at, c.last_message_at, c.title,
                       m.content as matching_content
                FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ? AND m.content LIKE ?
                ORDER BY c.last_message_at DESC
                LIMIT 50
            ''', (user_id, f'%{query}%'))
            
            return cursor.fetchall()

# Inicializar o gerenciador de banco de dados
db_manager = DatabaseManager()

# Dicionário para armazenar as respostas temporariamente (mantido para compatibilidade)
stored_responses = {}

def get_client_ip():
    """Obtém o IP real do cliente considerando proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def build_context_from_history(history, max_context=6):
    """Constrói contexto das conversas anteriores - garante pelo menos 3 interações completas"""
    if not history:
        return ""
    
    # Reorganizar mensagens por ordem cronológica (mais antigas primeiro)
    history_ordered = list(reversed(history[:max_context]))
    
    context_messages = []
    user_ai_pairs = []
    current_pair = {}
    
    # Agrupar mensagens em pares usuário-IA para manter contexto completo
    for msg_type, content, timestamp in history_ordered:
        if msg_type == "user":
            if current_pair:  # Se já existe um par incompleto, adicionar à lista
                user_ai_pairs.append(current_pair)
            current_pair = {"user": content, "timestamp": timestamp}
        elif msg_type == "ai" and current_pair:
            current_pair["ai"] = content
            user_ai_pairs.append(current_pair)
            current_pair = {}
    
    # Se sobrou um par incompleto (só pergunta sem resposta), adicionar também
    if current_pair:
        user_ai_pairs.append(current_pair)
    
    # Pegar as últimas 3 interações completas
    last_interactions = user_ai_pairs[-3:] if len(user_ai_pairs) >= 3 else user_ai_pairs
    
    if last_interactions:
        context_messages.append("🔍 **Contexto das conversas anteriores:**\n")
        
        for i, interaction in enumerate(last_interactions, 1):
            # Limitar tamanho das mensagens para não sobrecarregar o contexto
            user_msg = interaction.get("user", "")[:150] + ("..." if len(interaction.get("user", "")) > 150 else "")
            ai_msg = interaction.get("ai", "")[:200] + ("..." if len(interaction.get("ai", "")) > 200 else "")
            
            context_messages.append(f"**Interação {i}:**")
            context_messages.append(f"👤 Usuário: {user_msg}")
            if ai_msg:
                context_messages.append(f"🤖 Assistente: {ai_msg}")
            context_messages.append("")  # Linha em branco para separação
        
        context_messages.append("---\n**Conversa atual:**\n")
        return "\n".join(context_messages)
    
    return ""

@app.route('/')
def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>SmartOps AI</title>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        :root {
          --primary-black: #000000;
          --primary-white: #ffffff;
          --gray-50: #fafafa;
          --gray-100: #f5f5f5;
          --gray-200: #e5e5e5;
          --gray-300: #d4d4d4;
          --gray-400: #a3a3a3;
          --gray-500: #737373;
          --gray-600: #525252;
          --gray-700: #404040;
          --gray-800: #262626;
          --gray-900: #171717;
          --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
          --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
          --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
          --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
        }
        
        body {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          background: var(--primary-white);
          color: var(--primary-black);
          line-height: 1.6;
          min-height: 100vh;
          transition: all 0.3s ease;
        }
        
        body.dark-mode {
          background: var(--primary-black);
          color: var(--primary-white);
        }
        
        /* Header Styles */
        .header {
          background: var(--primary-black);
          padding: 1rem 2rem;
          box-shadow: var(--shadow-lg);
          position: sticky;
          top: 0;
          z-index: 100;
        }
        
        body.dark-mode .header {
          background: var(--gray-900);
          border-bottom: 1px solid var(--gray-800);
        }
        
        .header-content {
          max-width: 1400px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .logo {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }
        
        .logo-icon {
          width: 40px;
          height: 40px;
          background: var(--primary-white);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--primary-black);
        }
        
        .logo-text {
          color: var(--primary-white);
          font-size: 1.5rem;
          font-weight: 700;
          letter-spacing: -0.025em;
        }
        
        .header-controls {
          display: flex;
          gap: 1rem;
          align-items: center;
        }
        
        .btn {
          background: transparent;
          border: 2px solid var(--primary-white);
          color: var(--primary-white);
          padding: 0.5rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.875rem;
          transition: all 0.2s ease;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .btn:hover {
          background: var(--primary-white);
          color: var(--primary-black);
        }
        
        body.dark-mode .btn {
          border-color: var(--gray-400);
          color: var(--gray-400);
        }
        
        body.dark-mode .btn:hover {
          background: var(--gray-400);
          color: var(--primary-black);
        }
        
        /* Main Layout */
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem;
          min-height: calc(100vh - 80px);
          display: flex;
          justify-content: center;
          align-items: flex-start;
          align-items: start;
        }
        
        /* Sidebar */
        .sidebar {
          background: var(--gray-50);
          border-radius: 16px;
          padding: 2rem;
          box-shadow: var(--shadow);
          height: fit-content;
          position: sticky;
          top: 100px;
        }
        
        body.dark-mode .sidebar {
          background: var(--gray-900);
          border: 1px solid var(--gray-800);
        }
        
        .sidebar-title {
          font-size: 1.25rem;
          font-weight: 600;
          margin-bottom: 1rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .sidebar-subtitle {
          color: var(--gray-600);
          font-size: 0.875rem;
          margin-bottom: 1.5rem;
          line-height: 1.5;
        }
        
        body.dark-mode .sidebar-subtitle {
          color: var(--gray-400);
        }
        
        /* Removed History Sidebar CSS - no longer needed */
        
        /* Chat Section */
        .chat-section {
          background: var(--primary-white);
          border-radius: 16px;
          box-shadow: var(--shadow-xl);
          overflow: hidden;
          height: 600px;
          width: 100%;
          max-width: 800px;
          display: flex;
          flex-direction: column;
          border: 1px solid var(--gray-200);
        }
        
        body.dark-mode .chat-section {
          background: var(--gray-900);
          border-color: var(--gray-800);
        }
        
        .chat-header {
          background: var(--primary-black);
          padding: 1.5rem 2rem;
          border-bottom: 1px solid var(--gray-200);
        }
        
        body.dark-mode .chat-header {
          background: var(--gray-800);
          border-bottom-color: var(--gray-700);
        }
        
        .chat-header-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        
        .chat-info-left {
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        
        .chat-avatar {
          width: 48px;
          height: 48px;
          background: var(--primary-white);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
        }
        
        .chat-info h3 {
          color: var(--primary-white);
          font-size: 1.125rem;
          font-weight: 600;
          margin-bottom: 0.25rem;
        }
        
        .chat-status {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: var(--gray-300);
          font-size: 0.875rem;
        }
        
        .status-indicator {
          width: 8px;
          height: 8px;
          background: #10b981;
          border-radius: 50%;
        }
        
        /* Removed new-chat-btn styles - no longer needed */
        
        /* Messages */
        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          background: var(--gray-50);
        }
        
        body.dark-mode .chat-messages {
          background: var(--primary-black);
        }
        
        .chat-messages::-webkit-scrollbar {
          width: 6px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
          background: transparent;
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
          background: var(--gray-300);
          border-radius: 3px;
        }
        
        body.dark-mode .chat-messages::-webkit-scrollbar-thumb {
          background: var(--gray-600);
        }
        
        .message {
          max-width: 80%;
          padding: 1rem 1.25rem;
          border-radius: 16px;
          font-size: 0.875rem;
          line-height: 1.5;
          animation: slideIn 0.3s ease-out;
          word-wrap: break-word;
          white-space: pre-wrap;
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .message.user {
          align-self: flex-end;
          background: var(--primary-black);
          color: var(--primary-white);
          border-bottom-right-radius: 4px;
        }
        
        body.dark-mode .message.user {
          background: var(--gray-700);
        }
        
        .message.ai {
          align-self: flex-start;
          background: var(--primary-white);
          color: var(--primary-black);
          border: 1px solid var(--gray-200);
          border-bottom-left-radius: 4px;
          position: relative;
        }
        
        body.dark-mode .message.ai {
          background: var(--gray-800);
          color: var(--primary-white);
          border-color: var(--gray-700);
        }
        
        .message.typing {
          align-self: flex-start;
          background: var(--gray-200);
          color: var(--gray-600);
          font-style: italic;
        }
        
        body.dark-mode .message.typing {
          background: var(--gray-700);
          color: var(--gray-400);
        }
        
        .html-generate-btn {
          position: absolute;
          top: -8px;
          right: -8px;
          width: 28px;
          height: 28px;
          background: var(--primary-black);
          color: var(--primary-white);
          border: none;
          border-radius: 50%;
          font-size: 12px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: var(--shadow);
          transition: all 0.2s ease;
        }
        
        .html-generate-btn:hover {
          background: var(--gray-700);
          transform: scale(1.1);
        }
        
        body.dark-mode .html-generate-btn {
          background: var(--primary-white);
          color: var(--primary-black);
        }
        
        body.dark-mode .html-generate-btn:hover {
          background: var(--gray-200);
        }
        
        /* Input Area */
        .chat-input-area {
          padding: 1.5rem;
          background: var(--primary-white);
          border-top: 1px solid var(--gray-200);
        }
        
        body.dark-mode .chat-input-area {
          background: var(--gray-900);
          border-top-color: var(--gray-800);
        }
        
        .input-container {
          display: flex;
          gap: 0.75rem;
          align-items: flex-end;
        }
        
        .chat-input {
          flex: 1;
          padding: 0.75rem 1rem;
          border: 2px solid var(--gray-200);
          border-radius: 12px;
          font-size: 0.875rem;
          resize: none;
          outline: none;
          transition: all 0.2s ease;
          font-family: inherit;
          max-height: 100px;
          min-height: 44px;
        }
        
        .chat-input:focus {
          border-color: var(--primary-black);
        }
        
        body.dark-mode .chat-input {
          background: var(--gray-800);
          border-color: var(--gray-700);
          color: var(--primary-white);
        }
        
        body.dark-mode .chat-input:focus {
          border-color: var(--gray-500);
        }
        
        .send-button {
          width: 44px;
          height: 44px;
          background: var(--primary-black);
          color: var(--primary-white);
          border: none;
          border-radius: 12px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          flex-shrink: 0;
        }
        
        .send-button:hover:not(:disabled) {
          background: var(--gray-800);
        }
        
        .send-button:disabled {
          background: var(--gray-300);
          cursor: not-allowed;
        }
        
        body.dark-mode .send-button {
          background: var(--gray-700);
        }
        
        body.dark-mode .send-button:hover:not(:disabled) {
          background: var(--gray-600);
        }
        
        body.dark-mode .send-button:disabled {
          background: var(--gray-800);
        }
        
        /* Removed Modal Styles - no longer needed */
        
        /* Responsive Design */
        @media (max-width: 1200px) {
          .container {
            grid-template-columns: 250px 1fr;
            gap: 1.5rem;
          }
          
          .history-sidebar {
            display: none;
          }
        }
        
        @media (max-width: 1024px) {
          .container {
            grid-template-columns: 1fr;
            gap: 1.5rem;
            padding: 1rem;
          }
          
          .sidebar {
            position: relative;
            top: 0;
          }
          
          .chat-section {
            height: 500px;
          }
        }
        
        @media (max-width: 768px) {
          .header {
            padding: 1rem;
          }
          
          .header-content {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
          }
          
          .logo {
            justify-content: center;
          }
          
          .container {
            padding: 1rem 0.5rem;
          }
          
          .sidebar,
          .chat-section {
            border-radius: 12px;
          }
          
          .sidebar {
            padding: 1.5rem;
          }
          
          .chat-header {
            padding: 1rem 1.5rem;
          }
          
          .chat-messages {
            padding: 1rem;
          }
          
          .chat-input-area {
            padding: 1rem 1.5rem;
          }
          
          .message {
            max-width: 90%;
            padding: 0.875rem 1rem;
          }
        }
      </style>
      <script>
        // Removido currentSessionId - agora usando conversa única contínua
        
        window.addEventListener('DOMContentLoaded', function() {
          // Theme toggle functionality
          const themeBtn = document.getElementById('theme-toggle');
          themeBtn.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            if(document.body.classList.contains('dark-mode')) {
              themeBtn.textContent = 'Modo Claro';
            } else {
              themeBtn.textContent = 'Modo Escuro';
            }
          });

          // Removed loadConversationHistory() - no longer needed

          // Chat functionality  
          const chatInput = document.getElementById('chat-input');
          const sendBtn = document.getElementById('send-button');
          const messagesContainer = document.getElementById('chat-messages');

          // Removed search functionality - no longer needed

          function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
          }

          function createHtmlButton(responseId) {
            const btn = document.createElement('button');
            btn.className = 'html-generate-btn';
            btn.innerHTML = '📄';
            btn.title = 'Gerar HTML desta resposta';
            btn.onclick = function(e) {
              e.stopPropagation();
              generateHtml(responseId);
            };
            return btn;
          }

          async function generateHtml(responseId) {
            try {
              const response = await fetch('/generate_html', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ response_id: responseId })
              });

              const data = await response.json();
             
              if (data.success) {
                window.open('/view_html/' + responseId, '_blank');
              } else {
                alert('Erro ao gerar HTML: ' + (data.error || 'Erro desconhecido'));
              }
            } catch (error) {
              console.error('Erro ao gerar HTML:', error);
              alert('Erro ao gerar HTML. Tente novamente.');
            }
          }

          function addMessage(content, type, responseId = null) {
            const message = document.createElement('div');
            message.className = `message ${type}`;
            message.textContent = content;
           
            if (type === 'ai' && responseId) {
              message.style.position = 'relative';
              const htmlBtn = createHtmlButton(responseId);
              message.appendChild(htmlBtn);
            }
           
            messagesContainer.appendChild(message);
            setTimeout(scrollToBottom, 100);
          }

          // Removed loadConversationHistory, loadConversation, and searchConversations functions - no longer needed

          async function sendMessage() {
            const message = chatInput.value.trim();
            if (message && !sendBtn.disabled) {
              sendBtn.disabled = true;
              chatInput.disabled = true;

              addMessage(message, 'user');

              const typingMessage = document.createElement('div');
              typingMessage.className = 'message ai typing';
              typingMessage.textContent = 'SmartOps AI está digitando...';
              messagesContainer.appendChild(typingMessage);
              scrollToBottom();

              chatInput.value = '';

              try {
                const response = await fetch('/chat', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                  },
                  body: JSON.stringify({ 
                    message: message
                    // Removed session_id - using single continuous conversation
                  })
                });

                const data = await response.json();
                messagesContainer.removeChild(typingMessage);
                addMessage(
                  data.response || 'Desculpe, não consegui processar sua mensagem.',
                  'ai',
                  data.response_id
                );

                // Removed loadConversationHistory() call - no longer needed

              } catch (error) {
                console.error('Erro ao enviar mensagem:', error);
                messagesContainer.removeChild(typingMessage);
                addMessage('Desculpe, ocorreu um erro na comunicação. Tente novamente.', 'ai');
              }

              sendBtn.disabled = false;
              chatInput.disabled = false;
              chatInput.focus();
            }
          }

          sendBtn.addEventListener('click', sendMessage);
          chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey && !sendBtn.disabled) {
              e.preventDefault();
              sendMessage();
            }
          });

          chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
          });

          // Removed history modal functionality - no longer needed
          
          // Load current conversation on page load
          async function loadCurrentConversation() {
            try {
              const response = await fetch('/get_current_conversation');
              const data = await response.json();
              
              if (data.success && data.messages.length > 0) {
                messagesContainer.innerHTML = '';
                data.messages.forEach(msg => {
                  addMessage(msg.content, msg.message_type, msg.response_id);
                });
              } else {
                // Show welcome message if no conversation exists
                addMessage('Olá! Sou o SmartOps AI. Como posso ajudá-lo hoje?', 'ai');
              }
            } catch (error) {
              console.error('Erro ao carregar conversa:', error);
              addMessage('Olá! Sou o SmartOps AI. Como posso ajudá-lo hoje?', 'ai');
            }
          }
          
          // Load conversation on page load
          loadCurrentConversation();
          
          // Removed loadConversationHistory() - no longer needed
        });
      </script>
    </head>
    <body>
      <!-- Header -->
      <header class="header">
        <div class="header-content">
          <div class="logo">
            <div class="logo-icon">W</div>
            <div class="logo-text">SmartOps AI</div>
          </div>
          <div class="header-controls">
            <!-- Removed history button - no longer needed -->
            <button id="theme-toggle" class="btn">Modo Escuro</button>
          </div>
        </div>
      </header>

      <!-- Main Container -->
      <div class="container">
        <!-- Left Sidebar -->
        <aside class="sidebar">
          <h2 class="sidebar-title">
            🧠 Assistente Virtual Wood
          </h2>
          <p class="sidebar-subtitle">
            Seu agente inteligente para automação e operações. Otimize seus processos de TI com o poder da inteligência artificial.
          </p>
        </aside>

        <!-- Chat Section -->
        <main class="chat-section">
          <div class="chat-header">
            <div class="chat-header-content">
              <div class="chat-info-left">
                <div class="chat-avatar">🤖</div>
                <div class="chat-info">
                  <h3>SmartOps AI</h3>
                  <div class="chat-status">
                    <div class="status-indicator"></div>
                    <span>Online</span>
                  </div>
                </div>
              </div>
              <!-- Removed Nova Conversa button - using single continuous chat -->
            </div>
          </div>

          <div class="chat-messages" id="chat-messages">
            <!-- Messages will appear here -->
          </div>

          <div class="chat-input-area">
            <div class="input-container">
              <textarea 
                id="chat-input" 
                class="chat-input" 
                placeholder="Digite sua mensagem..." 
                rows="1"
              ></textarea>
              <button id="send-button" class="send-button">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
        </main>

        <!-- Removed Right Sidebar - History no longer needed -->
      </div>

      <!-- Removed History Modal - No longer needed -->
    </body>
    </html>
    """
    return render_template_string(html_content)

def extract_clean_response(result):
    """Extrai a resposta de texto da estrutura retornada pelo Langflow"""
    try:
        if isinstance(result, str):
            result = json.loads(result)

        outputs = result.get("outputs", [])
        if isinstance(outputs, list) and outputs:
            first_output = outputs[0]
            nested_outputs = first_output.get("outputs", [])
            if isinstance(nested_outputs, list) and nested_outputs:
                deep_output = nested_outputs[0]
                message_data = deep_output.get("results", {}).get("message", {}).get("data", {})
                text = message_data.get("text")
                if text:
                    return text
        return "Desculpe, não consegui interpretar a resposta."
    except Exception as e:
        return f"Erro ao extrair resposta: {str(e)}"

def text_to_markdown(text):
    """Converte texto da IA em markdown melhor formatado preservando formatação existente"""
    # Normalizar quebras de linha e remover espaços extras no início/fim
    text = text.strip()
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    
    # Separar o texto em linhas
    lines = text.split('\n')
    processed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Linha vazia - preservar
        if not line:
            processed_lines.append('')
            i += 1
            continue
        
        # Detectar se já tem formatação markdown (títulos)
        if re.match(r'^#{1,6}\s+', line):
            processed_lines.append(line)
            i += 1
            continue
        
        # Detectar listas com marcadores existentes
        if re.match(r'^[\*\-\+]\s+', line):
            processed_lines.append(line)
            i += 1
            continue
            
        # Detectar listas numeradas existentes
        if re.match(r'^\d+\.\s+', line):
            processed_lines.append(line)
            i += 1
            continue
        
        # Detectar possível título (linha curta, sem pontuação final, seguida de conteúdo)
        is_title = (
            len(line) < 80 and
            not line.endswith(('.', '!', '?', ':', ';', ',')) and
            i + 1 < len(lines) and
            lines[i + 1].strip() and
            not re.match(r'^[\*\-\+\d]\s*', lines[i + 1].strip()) and
            not line.lower().startswith(('por', 'para', 'como', 'quando', 'onde', 'se', 'mas', 'e ', 'ou ', 'de ', 'do ', 'da ', 'em ', 'no ', 'na '))
        )
        
        if is_title:
            processed_lines.append(f"## {line}")
        else:
            processed_lines.append(line)
        
        i += 1
    
    # Reconectar as linhas
    markdown_text = '\n'.join(processed_lines)
    
    # Adicionar espaçamento após títulos se não existir
    markdown_text = re.sub(r'^(#{1,6}\s+.+)$(?!\n\n)', r'\1\n', markdown_text, flags=re.MULTILINE)
    
    return markdown_text

def markdown_to_html(markdown_text):
    """Converte markdown em HTML com formatação aprimorada"""
    html_content = markdown_text
    
    # Escapar caracteres HTML primeiro (exceto os que vamos processar)
    html_content = html_content.replace('&', '&amp;')
    html_content = html_content.replace('<', '&lt;')
    html_content = html_content.replace('>', '&gt;')
    
    html_content = html_content.replace('&', '&amp;')
    html_content = html_content.replace('<', '&lt;')
    html_content = html_content.replace('>', '&gt;')
    
    # Processar formatação inline (negrito e itálico)
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'(?<!\*)\*([^\*\n]+?)\*(?!\*)', r'<em>\1</em>', html_content)
    html_content = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'(?<!_)_([^_\n]+?)_(?!_)', r'<em>\1</em>', html_content)
    
    # Processar código inline
    html_content = re.sub(r'`([^`\n]+?)`', r'<code>\1</code>', html_content)
    
    # Processar links [texto](url)
    html_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html_content)
    
    # Separar em linhas para processar listas e parágrafos
    lines = html_content.split('\n')
    processed_lines = []
    in_ul = False
    in_ol = False
    
    for line in lines:
        stripped = line.strip()
        
        # Lista não ordenada
        if re.match(r'^[\*\-\+]\s+', stripped):
            if in_ol:
                processed_lines.append('</ol>')
                in_ol = False
            if not in_ul:
                processed_lines.append('<ul>')
                in_ul = True
            item_text = re.sub(r'^[\*\-\+]\s+', '', stripped)
            processed_lines.append(f'<li>{item_text}</li>')
        
        # Lista ordenada
        elif re.match(r'^\d+\.\s+', stripped):
            if in_ul:
                processed_lines.append('</ul>')
                in_ul = False
            if not in_ol:
                processed_lines.append('<ol>')
                in_ol = True
            item_text = re.sub(r'^\d+\.\s+', '', stripped)
            processed_lines.append(f'<li>{item_text}</li>')
        
        # Outras linhas
        else:
            if in_ul:
                processed_lines.append('</ul>')
                in_ul = False
            if in_ol:
                processed_lines.append('</ol>')
                in_ol = False
            
            if not stripped:
                processed_lines.append('')
            elif not stripped.startswith('<h') and stripped:
                # É um parágrafo regular
                processed_lines.append(f'<p>{stripped}</p>')
            else:
                processed_lines.append(stripped)
    
    # Fechar listas se ainda estiverem abertas
    if in_ul:
        processed_lines.append('</ul>')
    if in_ol:
        processed_lines.append('</ol>')
    
    return '\n'.join(processed_lines)

def format_markdown_to_html(markdown_text, user_question=""):
    """Converte markdown em HTML bem formatado com template simples para impressão"""
    
    # Primeiro aplicar melhorias no markdown
    improved_markdown = text_to_markdown(markdown_text)
    
    # Converter para HTML
    html_content = markdown_to_html(improved_markdown)
    
    # Template HTML simples para impressão
    full_html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartOps AI - Resposta</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Times New Roman', Times, serif;
            line-height: 1.6;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
            background: white;
            color: #000;
            font-size: 12pt;
        }}
       
        .header {{
            text-align: center;
            border-bottom: 2px solid #000;
            padding-bottom: 10mm;
            margin-bottom: 15mm;
        }}
       
        .header h1 {{
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 5mm;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .content {{
            text-align: justify;
            font-size: 12pt;
            line-height: 1.5;
        }}
       
        .content h1 {{
            font-size: 16pt;
            font-weight: bold;
            margin: 15mm 0 8mm 0;
            text-transform: uppercase;
            border-bottom: 1px solid #000;
            padding-bottom: 2mm;
        }}
       
        .content h2 {{
            font-size: 14pt;
            font-weight: bold;
            margin: 12mm 0 6mm 0;
            text-decoration: underline;
        }}
       
        .content h3 {{
            font-size: 13pt;
            font-weight: bold;
            margin: 10mm 0 5mm 0;
            font-style: italic;
        }}
       
        .content p {{
            margin: 5mm 0;
            text-indent: 8mm;
        }}
       
        .content ul, .content ol {{
            margin: 6mm 0;
            padding-left: 10mm;
        }}
       
        .content li {{
            margin: 3mm 0;
            line-height: 1.4;
        }}
       
        .content ul li {{
            list-style-type: disc;
        }}
        
        .content ol li {{
            list-style-type: decimal;
        }}
       
        .content strong {{
            font-weight: bold;
        }}
       
        .content em {{
            font-style: italic;
        }}
       
        .content code {{
            font-family: 'Courier New', monospace;
            font-size: 11pt;
            background: #f0f0f0;
            padding: 1mm 2mm;
            border: 1px solid #ccc;
        }}
        
        .content a {{
            color: #000;
            text-decoration: underline;
        }}
       
        .footer {{
            margin-top: 20mm;
            padding-top: 5mm;
            border-top: 1px solid #000;
            font-size: 10pt;
            text-align: center;
        }}
       
        .print-btn {{
            background: #fff;
            color: #000;
            border: 2px solid #000;
            padding: 3mm 6mm;
            cursor: pointer;
            font-size: 11pt;
            font-weight: bold;
            margin-bottom: 10mm;
            display: block;
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
        }}
        
        .print-btn:hover {{
            background: #f0f0f0;
        }}
        
        /* Estilos específicos para impressão */
        @media print {{
            body {{
                padding: 15mm;
                font-size: 11pt;
            }}
            
            .print-btn {{
                display: none;
            }}
            
            .content h1 {{
                page-break-after: avoid;
            }}
            
            .content h2, .content h3 {{
                page-break-after: avoid;
                page-break-inside: avoid;
            }}
            
            .content p {{
                page-break-inside: avoid;
                orphans: 2;
                widows: 2;
            }}
            
            .content ul, .content ol {{
                page-break-inside: avoid;
            }}
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 5mm;
                font-size: 11pt;
            }}
            
            .header h1 {{
                font-size: 16pt;
            }}
            
            .content h1 {{
                font-size: 14pt;
            }}
            
            .content h2 {{
                font-size: 13pt;
            }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">IMPRIMIR DOCUMENTO</button>
    
    <div class="header">
        <h1>SmartOps AI - Assistente Virtual Wood</h1>
    </div>
      
    <div class="content">
        {html_content}
    </div>
   
    <div class="footer">
        <p><strong>Documento gerado em:</strong> {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}</p>
        <p>SmartOps AI - Wood Plc</p>
    </div>
</body>
</html>"""
    
    return full_html

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        # session_id não é mais usado - removido para conversas contínuas
        
        # Obter IP do cliente e ID do usuário
        client_ip = get_client_ip()
        user_id = db_manager.get_user_id(client_ip)
        
        # Obter ou criar conversa única do usuário
        conversation_id = db_manager.get_current_conversation_id(user_id)
        
        # Obter mensagens recentes da conversa única do usuário
        # Busca mais mensagens para manter contexto completo
        recent_messages = db_manager.get_recent_session_messages(conversation_id, limit=12)
        
        # Construir contexto das mensagens anteriores
        context = build_context_from_history(recent_messages)
        
        # Salvar mensagem do usuário
        db_manager.save_message(conversation_id, 'user', user_message)
        
        # Preparar mensagem com contexto para o Langflow
        contextual_message = context + user_message if context else user_message
        
        # Log para debug (configurável)
        if DEBUG_MEMORY:
            print(f"\n🔄 Nova mensagem do usuário (IP: {client_ip[:10]}...):")
            print(f"📝 Mensagem: {user_message}")
            print(f"🧠 Contexto aplicado: {'Sim' if context else 'Não'}")
            if context:
                print(f"📊 Tamanho do contexto: {len(context)} caracteres")
                print(f"📋 Mensagens na conversa: {len(recent_messages)}")
        
        # Configuração do Langflow
        langflow_url = "http://localhost:7860"
        flow_id = "7da02070-24ec-4cc2-bb99-e089ce0cc283"
        
        payload = {
            "input_value": contextual_message,
            "output_type": "chat",
            "input_type": "chat",
            "tweaks": {}
        }
        
        with requests.Session() as session:
            response = session.post(
                f"{langflow_url}/api/v1/run/{flow_id}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=1200
            )
           
            if response.status_code == 200:
                result = response.json()
                ai_response = extract_clean_response(result)
            else:
                ai_response = f"Erro na comunicação com o agente (Status: {response.status_code})"
        
        # Gerar response_id e salvar resposta da IA
        response_id = str(uuid.uuid4())
        db_manager.save_message(conversation_id, 'ai', ai_response, response_id)
        
        # Manter compatibilidade com sistema antigo
        stored_responses[response_id] = {
            'response': ai_response,
            'question': user_message,
            'timestamp': datetime.now()
        }
       
        return jsonify({
            "response": ai_response,
            "response_id": response_id
        })
               
    except requests.exceptions.RequestException as e:
        ai_response = f"Erro de conexão: {str(e)}"
        return jsonify({"response": ai_response})
    except Exception as e:
        ai_response = f"Erro interno: {str(e)}"
        return jsonify({"response": ai_response})

@app.route('/get_current_conversation', methods=['GET'])
def get_current_conversation():
    """Retorna as mensagens da conversa única do usuário"""
    try:
        client_ip = get_client_ip()
        user_id = db_manager.get_user_id(client_ip)
        
        # Obter a conversa única do usuário
        conversation_id = db_manager.get_current_conversation_id(user_id)
        
        # Buscar todas as mensagens da conversa
        messages = db_manager.get_conversation_messages(conversation_id, user_id)
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'message_type': msg[0],
                'content': msg[1],
                'timestamp': msg[2],
                'response_id': msg[3]
            })
        
        return jsonify({
            "success": True,
            "messages": formatted_messages
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get_conversations', methods=['GET'])
def get_conversations():
    """Retorna lista de conversas do usuário"""
    try:
        client_ip = get_client_ip()
        user_id = db_manager.get_user_id(client_ip)
        
        conversations = db_manager.get_user_conversations(user_id)
        
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                'id': conv[0],
                'session_id': conv[1],
                'created_at': conv[2],
                'last_message_at': conv[3],
                'title': conv[4],
                'message_count': conv[5],
                'first_message': conv[6]
            })
        
        return jsonify({
            "conversations": formatted_conversations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_conversation/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Retorna mensagens de uma conversa específica"""
    try:
        client_ip = get_client_ip()
        user_id = db_manager.get_user_id(client_ip)
        
        messages = db_manager.get_conversation_messages(conversation_id, user_id)
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'message_type': msg[0],
                'content': msg[1],
                'timestamp': msg[2],
                'response_id': msg[3]
            })
        
        return jsonify({
            "success": True,
            "messages": formatted_messages
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/search_conversations', methods=['POST'])
def search_conversations():
    """Busca conversas por conteúdo"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query.strip():
            return jsonify({"results": []})
        
        client_ip = get_client_ip()
        user_id = db_manager.get_user_id(client_ip)
        
        results = db_manager.search_conversations(user_id, query)
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                'id': result[0],
                'session_id': result[1],
                'created_at': result[2],
                'last_message_at': result[3],
                'title': result[4],
                'matching_content': result[5]
            })
        
        return jsonify({
            "results": formatted_results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_full_history', methods=['GET'])
def get_full_history():
    """Retorna histórico completo do usuário para o modal"""
    try:
        client_ip = get_client_ip()
        user_id = db_manager.get_user_id(client_ip)
        
        # Buscar histórico mais extenso para o modal
        history = db_manager.get_conversation_history(user_id, limit=100)
        
        formatted_history = []
        for msg in history:
            formatted_history.append({
                'message_type': msg[0],
                'content': msg[1],
                'timestamp': msg[2]
            })
        
        # Reverter ordem para mostrar do mais antigo para o mais novo no modal
        formatted_history.reverse()
        
        return jsonify({
            "history": formatted_history
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_html', methods=['POST'])
def generate_html():
    try:
        data = request.get_json()
        response_id = data.get('response_id')
       
        if not response_id or response_id not in stored_responses:
            return jsonify({"success": False, "error": "Resposta não encontrada"})
       
        return jsonify({"success": True})
       
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/view_html/<response_id>')
def view_html(response_id):
    if response_id not in stored_responses:
        return "<h1>Resposta não encontrada</h1>", 404
   
    response_data = stored_responses[response_id]
    html_content = format_markdown_to_html(
        response_data['response'],
        response_data['question']
    )
   
    return html_content

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)