from flask import Flask, render_template_string, request, jsonify
import requests
import json
import warnings
import re
import uuid
import os
from datetime import datetime

# Suprimir ResourceWarning temporariamente
warnings.filterwarnings("ignore", category=ResourceWarning)

app = Flask(__name__)

# Dicionário para armazenar as respostas temporariamente
stored_responses = {}

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
          max-width: 1200px;
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
        
        .theme-toggle {
          background: transparent;
          border: 2px solid var(--primary-white);
          color: var(--primary-white);
          padding: 0.5rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.875rem;
          transition: all 0.2s ease;
        }
        
        .theme-toggle:hover {
          background: var(--primary-white);
          color: var(--primary-black);
        }
        
        body.dark-mode .theme-toggle {
          border-color: var(--gray-400);
          color: var(--gray-400);
        }
        
        body.dark-mode .theme-toggle:hover {
          background: var(--gray-400);
          color: var(--primary-black);
        }
        
        /* Main Layout */
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem;
          min-height: calc(100vh - 80px);
          display: grid;
          grid-template-columns: 1fr 2fr;
          gap: 2rem;
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
        
        .feature-list {
          list-style: none;
          space-y: 0.75rem;
        }
        
        .feature-list li {
          padding: 0.75rem;
          background: var(--primary-white);
          border-radius: 8px;
          font-size: 0.875rem;
          border: 1px solid var(--gray-200);
          margin-bottom: 0.5rem;
          transition: all 0.2s ease;
        }
        
        .feature-list li:hover {
          border-color: var(--gray-300);
          box-shadow: var(--shadow-sm);
        }
        
        body.dark-mode .feature-list li {
          background: var(--gray-800);
          border-color: var(--gray-700);
          color: var(--gray-200);
        }
        
        body.dark-mode .feature-list li:hover {
          border-color: var(--gray-600);
        }
        
        /* Chat Section */
        .chat-section {
          background: var(--primary-white);
          border-radius: 16px;
          box-shadow: var(--shadow-xl);
          overflow: hidden;
          height: 600px;
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
        
        /* Responsive Design */
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

          // Chat functionality
          const chatInput = document.getElementById('chat-input');
          const sendBtn = document.getElementById('send-button');
          const messagesContainer = document.getElementById('chat-messages');

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
                  body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                messagesContainer.removeChild(typingMessage);
                addMessage(
                  data.response || 'Desculpe, não consegui processar sua mensagem.',
                  'ai',
                  data.response_id
                );

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

          // Initial AI message
          setTimeout(() => {
            addMessage('Olá! Sou o SmartOps AI. Como posso ajudá-lo hoje?', 'ai');
          }, 500);
        });
      </script>
    </head>
    <body>
      <!-- Header -->
      <header class="header">
        <div class="header-content">
          <div class="logo">
            <img src="static/images/WoodLogoColour2.png " width=200px>
          </div>
          <button id="theme-toggle" class="theme-toggle">Modo Escuro</button>
        </div>
      </header>

      <!-- Main Container -->
      <div class="container">
        <!-- Sidebar -->
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
              <div class="chat-avatar">🤖</div>
              <div class="chat-info">
                <h3>SmartOps AI</h3>
                <div class="chat-status">
                  <div class="status-indicator"></div>
                  <span>Online</span>
                </div>
              </div>
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
      </div>
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
    
    # Processar títulos (# ## ###)
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    
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
       
        # Configuração do Langflow
        langflow_url = "http://localhost:7860"
        flow_id = "7da02070-24ec-4cc2-bb99-e089ce0cc283"
       
        payload = {
            "input_value": user_message,
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
               
        response_id = str(uuid.uuid4())
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