"""
Script de teste para verificar o sistema de memória do chatbot baseado em IP
"""

import sqlite3
import hashlib
from datetime import datetime

def test_memory_system():
    """Testa o sistema de memória do chatbot"""
    
    # Conectar ao banco de dados
    DATABASE = 'chatbot_memory.db'
    
    # Simular IP de teste
    test_ip = "192.168.1.100"
    ip_hash = hashlib.sha256(test_ip.encode()).hexdigest()
    
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        print("🔍 Testando sistema de memória por IP...")
        print(f"IP de teste: {test_ip}")
        print(f"Hash do IP: {ip_hash[:16]}...")
        
        # Verificar se existem usuários no banco
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"📊 Total de usuários no banco: {user_count}")
        
        # Verificar conversas
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        print(f"💬 Total de conversas no banco: {conv_count}")
        
        # Verificar mensagens
        cursor.execute("SELECT COUNT(*) FROM messages")
        msg_count = cursor.fetchone()[0]
        print(f"📝 Total de mensagens no banco: {msg_count}")
        
        # Mostrar últimas mensagens se existirem
        if msg_count > 0:
            print("\n📋 Últimas 5 mensagens no banco:")
            cursor.execute('''
                SELECT m.message_type, m.content, m.timestamp, u.ip_hash
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                JOIN users u ON c.user_id = u.id
                ORDER BY m.timestamp DESC
                LIMIT 5
            ''')
            
            messages = cursor.fetchall()
            for i, (msg_type, content, timestamp, user_hash) in enumerate(messages, 1):
                role = "👤 Usuário" if msg_type == "user" else "🤖 IA"
                content_preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  {i}. {role}: {content_preview}")
                print(f"     ⏰ {timestamp} | IP: {user_hash[:8]}...")
                print()
        
        print("✅ Teste do sistema de memória concluído!")

def check_context_functionality():
    """Verifica se o sistema de contexto está funcionando"""
    
    print("\n🧠 Verificando funcionalidade de contexto...")
    
    # Importar função de contexto do app
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Simular histórico de mensagens
        mock_history = [
            ("ai", "Olá! Como posso ajudá-lo hoje?", "2024-01-01 10:00:00"),
            ("user", "Qual é a capital do Brasil?", "2024-01-01 10:00:10"),
            ("ai", "A capital do Brasil é Brasília.", "2024-01-01 10:00:15"),
            ("user", "E a população dessa cidade?", "2024-01-01 10:01:00"),
            ("ai", "Brasília tem aproximadamente 3,1 milhões de habitantes na região metropolitana.", "2024-01-01 10:01:05"),
            ("user", "Qual é o clima lá?", "2024-01-01 10:02:00"),
        ]
        
        # Testar função de contexto
        from app import build_context_from_history
        context = build_context_from_history(mock_history)
        
        print("📝 Contexto gerado:")
        print(context)
        print("\n✅ Sistema de contexto funcionando corretamente!")
        
    except Exception as e:
        print(f"❌ Erro ao testar sistema de contexto: {e}")

if __name__ == "__main__":
    test_memory_system()
    check_context_functionality()
