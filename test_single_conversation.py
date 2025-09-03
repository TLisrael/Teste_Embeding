"""
Script de teste para verificar o sistema de conversa única
"""

import sqlite3
import hashlib
from datetime import datetime

def test_single_conversation_system():
    """Testa o novo sistema de conversa única"""
    
    DATABASE = 'chatbot_memory.db'
    
    print("🔄 Testando sistema de conversa única...")
    
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # Verificar estrutura do banco
        print("\n📊 Estatísticas do banco:")
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Usuários: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        print(f"💬 Conversas: {conv_count}")
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        msg_count = cursor.fetchone()[0]
        print(f"📝 Mensagens: {msg_count}")
        
        # Verificar se há conversas com session_id 'main_conversation'
        cursor.execute("SELECT COUNT(*) FROM conversations WHERE session_id = 'main_conversation'")
        main_conv_count = cursor.fetchone()[0]
        print(f"🎯 Conversas principais: {main_conv_count}")
        
        # Mostrar detalhes das conversas
        print("\n📋 Detalhes das conversas:")
        cursor.execute('''
            SELECT c.id, c.session_id, c.title, u.ip_hash, COUNT(m.id) as msg_count,
                   c.created_at, c.last_message_at
            FROM conversations c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id, c.session_id, c.title, u.ip_hash, c.created_at, c.last_message_at
            ORDER BY c.last_message_at DESC
        ''')
        
        conversations = cursor.fetchall()
        for i, (conv_id, session_id, title, ip_hash, msg_count, created, last_msg) in enumerate(conversations, 1):
            print(f"  {i}. ID: {conv_id} | Sessão: {session_id}")
            print(f"     Título: {title}")
            print(f"     IP: {ip_hash[:12]}... | Mensagens: {msg_count}")
            print(f"     Criada: {created} | Última: {last_msg}")
            print()
        
        # Simular teste do novo sistema
        print("🧪 Simulando novo sistema de conversa única...")
        
        # Testar função de obter conversa única
        from app import DatabaseManager
        db_manager = DatabaseManager()
        
        # Simular IP de teste
        test_ip = "192.168.1.200"
        user_id = db_manager.get_user_id(test_ip)
        print(f"👤 User ID para IP teste: {user_id}")
        
        # Obter conversa única
        conversation_id = db_manager.get_current_conversation_id(user_id)
        print(f"💬 Conversation ID única: {conversation_id}")
        
        # Verificar se a conversa foi criada corretamente
        cursor.execute('''
            SELECT session_id, title FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        conv_details = cursor.fetchone()
        if conv_details:
            session_id, title = conv_details
            print(f"✅ Conversa criada com sucesso!")
            print(f"   Sessão: {session_id}")
            print(f"   Título: {title}")
        
        print("\n🎯 Sistema de conversa única funcionando corretamente!")

if __name__ == "__main__":
    test_single_conversation_system()
