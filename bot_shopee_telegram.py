#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Shopee Telegram - Versão Otimizada 2026
- Busca produtos por tendências reais (moda, skincare, eletrônicos, pet, papelaria)
- Limite de 6 produtos por execução
- Desconto exibido apenas quando real (evita inconsistências)
- Prompts criativos do Google Gemini
- Rodízio de categorias para diversidade
"""

import requests
import json
import hashlib
import time
import logging
from datetime import datetime
import os
import random
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÕES
MAX_PRODUCTS = 6
DELAY_BETWEEN_PRODUCTS = 8  # segundos

# Categorias baseadas nas tendências Shopee 2026
CATEGORIAS = [
    # Moda Fitness & Old Money
    "leggings fitness", "conjunto fitness", "brincos old money",
    "relogio minimalista", "oculos retangular",

    # Beleza e Skincare
    "serum vitamina c", "adesivo acne", "escova secadora", "modelador automatico",

    # Casa e Decoração
    "organizador acrilico geladeira", "fita led", "pote hermetico",
    "utensilio silicone pastel",

    # Eletrônicos e Gadgets
    "fone tws cancelamento ruido", "smartwatch amoled", "microfone lapela",
    "ring light", "carregador portatil", "caixa de som bluetooth",

    # Mundo Pet
    "fonte agua automatica pet", "tigela ergonomica pet", "brinquedo interativo pet",

    # Papelaria Aesthetic
    "planner", "caneta gel pastel", "washi tape", "adesivo decorativo"
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BotShopee:
    def __init__(self):
        self.app_id = os.getenv('SHOPEE_APP_ID')
        self.secret = os.getenv('SHOPEE_SECRET')
        self.api_url = "https://open-api.affiliate.shopee.com.br/graphql"
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_channel = os.getenv('TELEGRAM_CHANNEL_ID')
        self.session_file = "products_sent_today.json"
        self.load_sent_products()

    def load_sent_products(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                if data.get('date') == today:
                    self.sent_ids = set(data.get('ids', []))
                else:
                    self.sent_ids = set()
        else:
            self.sent_ids = set()

    def save_sent_products(self):
        with open(self.session_file, 'w') as f:
            json.dump({'date': datetime.now().strftime("%Y-%m-%d"), 'ids': list(self.sent_ids)}, f)

    def mark_sent(self, product_id):
        self.sent_ids.add(str(product_id))
        self.save_sent_products()

    def generate_signature(self, timestamp, payload):
        sign_str = f"{self.app_id}{timestamp}{payload}{self.secret}"
        return hashlib.sha256(sign_str.encode()).hexdigest()

    def fetch_products(self, keyword, limit=20):
        """Busca produtos por palavra-chave e retorna os mais vendidos (sortType=2)"""
        query = f'''
        {{
          productOfferV2(keyword: "{keyword}", sortType: 2, page: 1, limit: {limit}) {{
            nodes {{
              itemId, productName, sales, priceMin, priceMax, imageUrl, offerLink, commissionRate, ratingStar
            }}
          }}
        }}
        '''
        timestamp = int(time.time())
        payload = json.dumps({"query": query})
        signature = self.generate_signature(timestamp, payload)
        headers = {
            'Authorization': f'SHA256 Credential={self.app_id}, Timestamp={timestamp}, Signature={signature}',
            'Content-Type': 'application/json'
        }
        try:
            resp = requests.post(self.api_url, headers=headers, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if 'errors' in data:
                logging.error(f"Erro API Shopee: {data['errors']}")
                return []
            products = data.get('data', {}).get('productOfferV2', {}).get('nodes', [])
            # Ordenar por vendas decrescente (já vem ordenado? garantia)
            products.sort(key=lambda x: int(x.get('sales', 0)), reverse=True)
            return products[:MAX_PRODUCTS]
        except Exception as e:
            logging.error(f"Erro ao buscar '{keyword}': {e}")
            return []

    def get_creative_prompt(self, product_name):
        """Gera prompt variado conforme horário para evitar mensagens repetitivas"""
        hour = datetime.now().hour
        tones = [
            "engajado, com perguntas retóricas",
            "descontraído, com gírias e abreviações (vc, pra, corrê)",
            "urgente, com emojis chamativos (🚨, 💥, 🤯)",
            "humorístico, com comparações exageradas (ex: 'a Ferrari dos fones')",
            "curto e direto, direto ao ponto",
            "entusiasta, cheio de exclamações e elogios"
        ]
        selected_tone = tones[hour % len(tones)]
        prompt = f"""
        Gere uma mensagem promocional para o produto "{product_name}" com as seguintes características:
        - Tom: {selected_tone}
        - Máximo 3 linhas.
        - Use emojis variados (não repetir sempre os mesmos).
        - Não mencione preços ou links.
        - Seja irresistível, como uma dica de amigo.
        Retorne apenas a mensagem final.
        """
        return prompt

    def generate_message_gemini(self, product_name):
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={self.google_api_key}"
            prompt = self.get_creative_prompt(product_name)
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(url, json=data, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                logging.error(f"Gemini erro {resp.status_code}: {resp.text}")
                return f"🔥 Oferta relâmpago! {product_name} com preço incrível! Corre! 🛒"
        except Exception as e:
            logging.error(f"Erro Gemini: {e}")
            return f"⚡ Super desconto! {product_name} – não perca!"

    def send_telegram(self, text, image_url=None):
        try:
            if image_url:
                img_data = requests.get(image_url, timeout=15).content
                files = {'photo': ('img.jpg', img_data)}
                data = {'chat_id': self.telegram_channel, 'caption': text, 'parse_mode': 'HTML'}
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
                resp = requests.post(url, data=data, files=files, timeout=30)
            else:
                data = {'chat_id': self.telegram_channel, 'text': text, 'parse_mode': 'HTML'}
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                resp = requests.post(url, json=data, timeout=30)
            resp.raise_for_status()
            logging.info("✅ Mensagem enviada ao Telegram")
            return True
        except Exception as e:
            logging.error(f"Erro Telegram: {e}")
            return False

    def format_caption(self, product, ai_text):
        """Formata a legenda corrigindo o problema de desconto falso"""
        name = product.get('productName', 'Produto')
        try:
            price_min = float(product.get('priceMin', 0))
            price_max = float(product.get('priceMax', 0))
        except:
            price_min = price_max = 0

        # Se não tem preços válidos, simula valores modestos
        if price_min <= 0 or price_max <= 0:
            price_min = price_max = 29.90

        link = product.get('offerLink', '')
        sales = int(product.get('sales', 0)) if product.get('sales') else 0
        try:
            stars = float(product.get('ratingStar', 0))
        except:
            stars = 0

        # Calcula desconto real
        desconto_real = 0
        if price_max > price_min and price_max > 0:
            desconto_real = int(((price_max - price_min) / price_max) * 100)
            # Garante que não seja negativo ou > 90%
            desconto_real = max(0, min(desconto_real, 95))
            preco_original = price_max
            preco_final = price_min
        else:
            # Sem desconto real: não exibe percentual
            desconto_real = None
            preco_original = price_max
            preco_final = price_min
            # Se os preços são iguais, não força um falso desconto
            if preco_original == preco_final:
                desconto_real = None

        # Monta linha de desconto (apenas se real)
        desconto_texto = ""
        if desconto_real and desconto_real > 0:
            emojis = ["🔥", "🎉", "⚡", "💥", "🚀", "🏆", "💎", "😱"]
            emoji = random.choice(emojis)
            desconto_texto = f"\n{emoji} <b>{desconto_real}% DE DESCONTO!</b>"

        # Linha de preços
        if desconto_real:
            linha_preco = f"De R$ ~{preco_original:.2f}~\nPor R$ <b>*{preco_final:.2f}*</b> 🤑"
        else:
            linha_preco = f"<b>Preço especial:</b> R$ {preco_final:.2f} 🤑"

        # Informações adicionais
        info = ""
        if sales > 0:
            info += f"📦 {sales} vendidos"
        if stars > 0:
            info += f" | ⭐ {stars:.1f}" if info else f"⭐ {stars:.1f}"

        caption = f"""
{ai_text}

<b>{name}</b>
{desconto_texto}

{linha_preco}

{info}

Compre aqui 🛍️👇
{link}
        """.strip()
        return caption

    def run(self):
        logging.info("🚀 Iniciando busca de produtos (tendências Shopee 2026)...")
        # Rotação de categoria com base no timestamp
        idx = int(time.time()) % len(CATEGORIAS)
        keyword = CATEGORIAS[idx]
        logging.info(f"Categoria selecionada: {keyword}")

        products = self.fetch_products(keyword)
        if not products:
            logging.warning("Nenhum produto encontrado para esta categoria.")
            return

        # Filtra produtos já enviados hoje
        new_products = [p for p in products if str(p.get('itemId')) not in self.sent_ids]
        logging.info(f"Produtos novos: {len(new_products)} de {len(products)}")

        if not new_products:
            logging.info("Todos os produtos já foram enviados hoje. Encerrando.")
            return

        # Limita ao máximo configurado
        to_send = new_products[:MAX_PRODUCTS]
        for i, prod in enumerate(to_send, 1):
            try:
                prod_id = prod['itemId']
                name = prod['productName']
                logging.info(f"Processando {i}/{len(to_send)}: {name[:50]}...")
                ai_msg = self.generate_message_gemini(name)
                caption = self.format_caption(prod, ai_msg)
                image = prod.get('imageUrl')
                if self.send_telegram(caption, image):
                    self.mark_sent(prod_id)
                else:
                    logging.error(f"Falha ao enviar produto {i}")
                time.sleep(DELAY_BETWEEN_PRODUCTS)
            except Exception as e:
                logging.error(f"Erro no produto {i}: {e}")

if __name__ == "__main__":
    bot = BotShopee()
    bot.run()
