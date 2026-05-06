#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Shopee Telegram - Automatização de Ofertas Diárias
Script para buscar ofertas da Shopee e enviar mensagens personalizadas para o Telegram
"""

import requests
import json
import hashlib
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from configuracao_horarios import obter_horarios, obter_configuracoes, mostrar_horarios
import csv
import sys

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_shopee_telegram.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class Configuracao:
    """Classe para gerenciar todas as configurações do bot"""
    
    def __init__(self):
        self.shopee_app_id = os.getenv('SHOPEE_APP_ID')
        self.shopee_secret = os.getenv('SHOPEE_SECRET')
        self.shopee_api_url = "https://open-api.affiliate.shopee.com.br/graphql"
        
        # CORRIGIDO: Modelo Gemini 2.5 mais estável
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_api_url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"
        
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_bot_token}"
        
        self.limite_ofertas_por_execucao = int(os.getenv('LIMITE_OFERTAS', '5'))  # REDUZIDO para evitar 429
        self.intervalo_entre_mensagens = int(os.getenv('INTERVALO_MENSAGENS', '8'))  # AUMENTADO para evitar 429
        
        self._validar_configuracoes()
    
    def _validar_configuracoes(self):
        configuracoes_obrigatorias = {
            'SHOPEE_APP_ID': self.shopee_app_id,
            'SHOPEE_SECRET': self.shopee_secret,
            'GOOGLE_API_KEY': self.google_api_key,
            'TELEGRAM_BOT_TOKEN': self.telegram_bot_token,
            'TELEGRAM_CHANNEL_ID': self.telegram_channel_id
        }
        for nome, valor in configuracoes_obrigatorias.items():
            if not valor:
                raise ValueError(f"Configuração obrigatória não encontrada: {nome}")

class APIShopee:
    def __init__(self, configuracao: Configuracao):
        self.config = configuracao
    
    def _gerar_assinatura(self, timestamp: int, payload: str) -> str:
        credencial = self.config.shopee_app_id
        secret = self.config.shopee_secret
        string_para_assinatura = f"{credencial}{timestamp}{payload}{secret}"
        return hashlib.sha256(string_para_assinatura.encode('utf-8')).hexdigest()
    
    def _fazer_requisicao(self, query: str) -> Dict:
        timestamp = int(time.time())
        payload = json.dumps({"query": query})
        assinatura = self._gerar_assinatura(timestamp, payload)
        
        headers = {
            'Authorization': f'SHA256 Credential={self.config.shopee_app_id}, Timestamp={timestamp}, Signature={assinatura}',
            'Content-Type': 'application/json'
        }
        
        try:
            resposta = requests.post(self.config.shopee_api_url, headers=headers, data=payload, timeout=30)
            resposta.raise_for_status()
            return resposta.json()
        except Exception as e:
            logging.error(f"Erro na API Shopee: {e}")
            return {"errors": [{"message": str(e)}]}

class GoogleAI:
    def __init__(self, configuracao: Configuracao):
        self.config = configuracao
    
    def gerar_mensagem_personalizada(self, nome_produto: str) -> str:
        prompt = f"""
        Gere uma mensagem para um post promocional para o produto "{nome_produto}".
        Use português brasileiro informal, com emojis chamativos (ex: 🚨, 💥, 🤯).
        Máximo 3 linhas. Não inclua preços ou links.
        """
        try:
            url = f"{self.config.google_api_url}?key={self.config.google_api_key}"
            dados = {"contents": [{"parts": [{"text": prompt}]}]}
            resposta = requests.post(url, json=dados, timeout=30)
            resposta.raise_for_status()
            resultado = resposta.json()
            return resultado['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            logging.error(f"Erro Google AI: {e}")
            return f"🔥 OFERTA IMPERDÍVEL! {nome_produto} com preço incrível! 🎉"

class TelegramBot:
    def __init__(self, configuracao: Configuracao):
        self.config = configuracao
    
    # MELHORIA PRINCIPAL: Baixa a imagem localmente antes de enviar
    def enviar_mensagem(self, texto: str, imagem_url: Optional[str] = None) -> bool:
        try:
            if imagem_url:
                try:
                    # Baixa a imagem com User-Agent para evitar bloqueios
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response_img = requests.get(imagem_url, headers=headers, timeout=15)
                    response_img.raise_for_status()
                    
                    # Envia como arquivo local
                    files = {'photo': ('image.jpg', response_img.content, 'image/jpeg')}
                    dados = {'chat_id': self.config.telegram_channel_id, 'caption': texto, 'parse_mode': 'HTML'}
                    resposta = requests.post(f"{self.config.telegram_api_url}/sendPhoto", data=dados, files=files, timeout=30)
                    resposta.raise_for_status()
                    logging.info("✅ Mensagem com imagem enviada")
                    return True
                except Exception as e_img:
                    logging.warning(f"Não foi possível enviar imagem ({e_img}). Enviando apenas texto...")
                    return self.enviar_mensagem(texto, imagem_url=None)
            else:
                # Fallback: apenas texto
                dados = {'chat_id': self.config.telegram_channel_id, 'text': texto, 'parse_mode': 'HTML'}
                resposta = requests.post(f"{self.config.telegram_api_url}/sendMessage", json=dados, timeout=30)
                resposta.raise_for_status()
                logging.info("✅ Mensagem de texto enviada")
                return True
        except Exception as e:
            logging.error(f"Erro no envio: {e}")
            return False

    def formatar_mensagem_oferta(self, produto: Dict, mensagem_personalizada: str) -> str:
        nome_produto = produto.get('productName', 'Produto')
        comissao = float(produto.get('commissionRate', '0')) * 100
        link_afiliado = produto.get('offerLink', '')
        
        # CORREÇÃO: Tratamento seguro de preços
        try:
            preco_min = str(produto.get('priceMin', '0')).replace(',', '.')
            preco_max = str(produto.get('priceMax', '0')).replace(',', '.')
            preco_min = float(preco_min) if preco_min and preco_min != 'None' else 0
            preco_max = float(preco_max) if preco_max and preco_max != 'None' else 0
        except:
            preco_min, preco_max = 0, 0
        
        # CORREÇÃO: Conversão segura de vendas
        vendas_raw = produto.get('sales', 0)
        try:
            vendas_num = int(vendas_raw) if str(vendas_raw).isdigit() else 0
        except:
            vendas_num = 0
        
        # CORREÇÃO: Conversão segura de avaliação
        avaliacao_raw = produto.get('ratingStar', '0')
        try:
            avaliacao_num = float(avaliacao_raw) if str(avaliacao_raw).replace('.', '').isdigit() else 0
        except:
            avaliacao_num = 0
        
        # Cálculo de desconto e preços
        desconto_percentual = min(int(comissao * 3), 80)
        if preco_min > 0 and preco_max > 0 and preco_max > preco_min:
            preco_original = preco_max
            preco_descontado = preco_min
            desconto_real = int(((preco_original - preco_descontado) / preco_original) * 100)
            desconto_percentual = max(desconto_real, desconto_percentual)
        else:
            preco_original = round(100 + (comissao * 10), 2)
            preco_descontado = round(preco_original * (1 - desconto_percentual/100), 2)
        
        # Info de vendas e avaliação
        info_produto = ""
        if vendas_num > 0:
            info_produto += f"📦 {vendas_num} vendidos"
        if avaliacao_num > 0:
            info_produto += f" | ⭐ {avaliacao_num:.1f}" if info_produto else f"⭐ {avaliacao_num:.1f}"
        
        emoji = ['😱', '🎉', '💥', '⚡', '🔥', '💎', '🎯', '🏆'][int(time.time()) % 8]
        
        return f"""
{mensagem_personalizada}

<b>{nome_produto}</b>

{emoji} <b>{desconto_percentual}% DE DESCONTO!!</b>

De R$ ~{preco_original:.2f}~
Por R$ <b>*{preco_descontado:.2f}*</b> 🤑

{info_produto}

Compre aqui 🛍️👇
{link_afiliado}
        """.strip()

class BotShopeeTelegram:
    def __init__(self):
        self.config = Configuracao()
        self.api_shopee = APIShopee(self.config)
        self.google_ai = GoogleAI(self.config)
        self.telegram = TelegramBot(self.config)
        self.session = SessionBot()
        self.horarios = []
    
    def definir_horarios(self, horarios):
        self.horarios = sorted(horarios)
    
    def processar_ofertas(self):
        logging.info("=== EXECUÇÃO INICIADA ===")
        try:
            # Busca ou carrega produtos
            keywords = ["Beleza", "Moda", "Eletrônicos", "Casa", "Esportes", "Brinquedos", "Pet", "Livros"]
            produtos = obter_top_produtos_por_keywords(
                self.config.shopee_app_id, self.config.shopee_secret, 
                self.config.shopee_api_url, keywords, limit=15, top_n=2
            )
            
            if not produtos:
                logging.warning("Nenhum produto encontrado")
                return
            
            # Filtra não enviados e limita
            novos = [p for p in produtos if not self.session.produto_ja_enviado(p.get('itemId'))]
            novos = novos[:self.config.limite_ofertas_por_execucao]
            logging.info(f"Processando {len(novos)} novos produtos")
            
            for i, prod in enumerate(novos, 1):
                try:
                    nome = prod.get('productName', 'Produto')
                    msg_ia = self.google_ai.gerar_mensagem_personalizada(nome)
                    msg_final = self.telegram.formatar_mensagem_oferta(prod, msg_ia)
                    imagem = prod.get('imageUrl')
                    
                    if self.telegram.enviar_mensagem(msg_final, imagem):
                        self.session.marcar_produto_enviado(prod.get('itemId'))
                        logging.info(f"✅ Produto {i}/{len(novos)} enviado")
                    else:
                        logging.error(f"❌ Falha no produto {i}")
                    
                    time.sleep(self.config.intervalo_entre_mensagens)  # Aguarda para evitar 429
                except Exception as e:
                    logging.error(f"Erro no produto {i}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Erro geral: {e}")
        logging.info("=== EXECUÇÃO CONCLUÍDA ===")
    
    def executar_diariamente(self):
        self.processar_ofertas()

class SessionBot:
    def __init__(self, arquivo='session_bot.json'):
        self.arquivo = arquivo
        self.enviados = self._carregar()
    
    def _carregar(self):
        try:
            if os.path.exists(self.arquivo):
                with open(self.arquivo, 'r') as f:
                    return set(json.load(f).get('produtos', []))
        except:
            pass
        return set()
    
    def _salvar(self):
        with open(self.arquivo, 'w') as f:
            json.dump({'produtos': list(self.enviados), 'atualizado': datetime.now().isoformat()}, f)
    
    def produto_ja_enviado(self, item_id):
        return str(item_id) in self.enviados
    
    def marcar_produto_enviado(self, item_id):
        self.enviados.add(str(item_id))
        self._salvar()

def obter_top_produtos_por_keywords(app_id, secret, api_url, keywords, limit=20, top_n=2):
    todos = {}
    for kw in keywords:
        query = f'{{ productOfferV2(keyword: "{kw}", sortType: 2, limit: {limit}) {{ nodes {{ itemId productName sales priceMin priceMax imageUrl offerLink commissionRate ratingStar }} }} }}'
        payload = json.dumps({"query": query})
        timestamp = int(time.time())
        assinatura = hashlib.sha256(f"{app_id}{timestamp}{payload}{secret}".encode()).hexdigest()
        headers = {'Authorization': f'SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={assinatura}', 'Content-Type': 'application/json'}
        try:
            resp = requests.post(api_url, headers=headers, data=payload, timeout=30).json()
            produtos = resp.get('data', {}).get('productOfferV2', {}).get('nodes', [])
            # Ordena por vendas
            for p in sorted(produtos, key=lambda x: int(x.get('sales',0)), reverse=True)[:top_n]:
                todos[p['itemId']] = p
            time.sleep(1.5)  # Evita 429
        except Exception as e:
            logging.error(f"Erro na keyword {kw}: {e}")
    return list(todos.values())

def main():
    try:
        bot = BotShopeeTelegram()
        horarios = obter_horarios()
        bot.definir_horarios(horarios)
        mostrar_horarios()
        
        # Suporte ao comando --now
        if len(sys.argv) > 1 and sys.argv[1] == '--now':
            logging.info("🕐 EXECUÇÃO FORÇADA (ignorando horários)")
            bot.executar_diariamente()
            return
        
        # Agendamento normal
        for horario in horarios:
            schedule.every().day.at(horario).do(bot.executar_diariamente)
        
        logging.info(f"Bot agendado. Próxima execução: {horarios[0] if horarios else 'N/A'}")
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Bot interrompido")
    except Exception as e:
        logging.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()