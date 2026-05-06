#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para descobrir o ID correto do canal do Telegram
"""

import requests
import json
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

def descobrir_id_canal():
    """Descobre o ID correto do canal do Telegram"""
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN não configurado no arquivo .env")
        return
    
    print("🔍 DESCUBRINDO ID DO CANAL TELEGRAM")
    print("=" * 50)
    print("")
    print("📋 INSTRUÇÕES:")
    print("1. Adicione o bot ao canal como administrador")
    print("2. Envie uma mensagem no canal")
    print("3. Execute este script")
    print("")
    
    input("Pressione Enter quando tiver enviado uma mensagem no canal...")
    
    try:
        # Obter updates do bot
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        resposta = requests.get(url, timeout=30)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            
            if dados.get('ok') and dados.get('result'):
                print("✅ Mensagens encontradas:")
                print("")
                
                for update in dados['result']:
                    if 'channel_post' in update:
                        chat = update['channel_post']['chat']
                        chat_id = chat['id']
                        chat_title = chat.get('title', 'Sem título')
                        chat_type = chat['type']
                        
                        print(f"📢 Canal: {chat_title}")
                        print(f"🆔 ID: {chat_id}")
                        print(f"📝 Tipo: {chat_type}")
                        print(f"📄 Username: @{chat.get('username', 'N/A')}")
                        print("-" * 30)
                
                print("")
                print("💡 Para usar o canal:")
                print("• Se for público: use @username_do_canal")
                print("• Se for privado: use o ID numérico (ex: -1001234567890)")
                print("")
                print("🔧 Atualize o arquivo .env com o ID correto")
                
            else:
                print("❌ Nenhuma mensagem encontrada")
                print("💡 Certifique-se de:")
                print("   - Bot adicionado ao canal como administrador")
                print("   - Mensagem enviada no canal")
                print("   - Aguardar alguns segundos antes de executar o script")
        else:
            print(f"❌ Erro HTTP {resposta.status_code}: {resposta.text}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def testar_canal_especifico():
    """Testa um canal específico"""
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    channel_input = input("Digite o ID do canal para testar: ").strip()
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN não configurado")
        return
    
    # Formatar o ID do canal corretamente
    channel_id = channel_input
    
    # Se for um username (começa com @ ou não tem @), adicionar @ se necessário
    if not channel_input.startswith('@') and not channel_input.startswith('-') and not channel_input.isdigit():
        channel_id = f"@{channel_input}"
        print(f"🔧 Formatando como username: {channel_id}")
    
    # Se for um username sem @, adicionar @
    elif channel_input.startswith('@'):
        channel_id = channel_input
    # Se for um ID numérico, manter como está
    elif channel_input.startswith('-') or channel_input.isdigit():
        channel_id = channel_input
    else:
        channel_id = f"@{channel_input}"
        print(f"🔧 Formatando como username: {channel_id}")
    
    print(f"🧪 Testando canal: {channel_id}")
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        dados = {
            'chat_id': channel_id,
            'text': '🧪 Teste de conexão - Se você vê esta mensagem, o ID está correto!',
            'parse_mode': 'HTML'
        }
        
        resposta = requests.post(url, json=dados, timeout=30)
        
        if resposta.status_code == 200:
            print("✅ Canal encontrado e mensagem enviada com sucesso!")
            print(f"💡 Use este ID no arquivo .env: {channel_id}")
        else:
            dados_erro = resposta.json()
            print(f"❌ Erro {resposta.status_code}: {dados_erro.get('description', 'Erro desconhecido')}")
            
            # Dicas específicas baseadas no erro
            if "chat not found" in dados_erro.get('description', '').lower():
                print("")
                print("💡 DICAS PARA RESOLVER:")
                print("• Para canais públicos: use @username_do_canal")
                print("• Para canais privados: use o ID numérico (ex: -1001234567890)")
                print("• Certifique-se de que o bot foi adicionado ao canal como administrador")
                print("• Verifique se o username está correto (sem espaços, caracteres especiais)")
                print("")
                print("🔍 Tente executar a opção 1 para descobrir o ID automaticamente")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def obter_info_detalhada_canal():
    """Obtém informações detalhadas sobre canais disponíveis"""
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN não configurado no arquivo .env")
        return
    
    print("🔍 OBTENDO INFORMAÇÕES DETALHADAS DOS CANAIS")
    print("=" * 50)
    print("")
    print("📋 INSTRUÇÕES:")
    print("1. Adicione o bot ao canal como administrador")
    print("2. Envie algumas mensagens no canal")
    print("3. Execute este script")
    print("")
    
    input("Pressione Enter quando tiver enviado mensagens no canal...")
    
    try:
        # Obter updates do bot
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        resposta = requests.get(url, timeout=30)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            
            if dados.get('ok') and dados.get('result'):
                canais_encontrados = {}
                
                print("✅ Mensagens encontradas:")
                print("")
                
                for update in dados['result']:
                    if 'channel_post' in update:
                        chat = update['channel_post']['chat']
                        chat_id = chat['id']
                        chat_title = chat.get('title', 'Sem título')
                        chat_type = chat['type']
                        chat_username = chat.get('username', 'N/A')
                        
                        # Armazenar informações únicas por canal
                        if chat_id not in canais_encontrados:
                            canais_encontrados[chat_id] = {
                                'title': chat_title,
                                'type': chat_type,
                                'username': chat_username,
                                'id': chat_id
                            }
                
                if canais_encontrados:
                    print(f"📊 Total de canais encontrados: {len(canais_encontrados)}")
                    print("")
                    
                    for chat_id, info in canais_encontrados.items():
                        print(f"📢 Canal: {info['title']}")
                        print(f"🆔 ID: {info['id']}")
                        print(f"📝 Tipo: {info['type']}")
                        print(f"📄 Username: @{info['username']}")
                        
                        # Determinar o formato correto para usar
                        if info['username'] != 'N/A':
                            formato_correto = f"@{info['username']}"
                            print(f"✅ Use no .env: {formato_correto}")
                        else:
                            formato_correto = str(info['id'])
                            print(f"✅ Use no .env: {formato_correto}")
                        
                        print("-" * 40)
                    
                    print("")
                    print("💡 RESUMO:")
                    print("• Para canais públicos: use @username_do_canal")
                    print("• Para canais privados: use o ID numérico")
                    print("• Certifique-se de que o bot é administrador do canal")
                else:
                    print("❌ Nenhum canal encontrado")
                    print("💡 Certifique-se de:")
                    print("   - Bot adicionado ao canal como administrador")
                    print("   - Mensagens enviadas no canal")
                    print("   - Aguardar alguns segundos antes de executar")
            else:
                print("❌ Nenhuma mensagem encontrada")
                print("💡 Certifique-se de:")
                print("   - Bot adicionado ao canal como administrador")
                print("   - Mensagem enviada no canal")
                print("   - Aguardar alguns segundos antes de executar o script")
        else:
            print(f"❌ Erro HTTP {resposta.status_code}: {resposta.text}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def main():
    """Função principal"""
    
    print("🚀 ASSISTENTE DE DESCOBERTA DE CANAL")
    print("=" * 50)
    
    while True:
        print("")
        print("Escolha uma opção:")
        print("1. 🔍 Descobrir ID do canal automaticamente")
        print("2. 🧪 Testar ID específico")
        print("3. 📊 Obter informações detalhadas dos canais")
        print("4. 🚪 Sair")
        
        opcao = input("\nDigite sua escolha (1-4): ").strip()
        
        if opcao == "1":
            descobrir_id_canal()
        elif opcao == "2":
            testar_canal_especifico()
        elif opcao == "3":
            obter_info_detalhada_canal()
        elif opcao == "4":
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida. Tente novamente.")

if __name__ == "__main__":
    main() 