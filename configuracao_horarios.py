#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuração de horários para o Bot Shopee Telegram
"""

# Configuração de horários de execução
HORARIOS_EXECUCAO = [
    "09:00", "10:00", "11:00", "12:00", "13:00", "14:41", 
    "15:00", "16:57", "17:13", "18:00", "19:00", "20:00", 
    "21:00", "22:00", "23:00", "01:59"
]

# Configurações adicionais
CONFIGURACOES = {
    "execucao_imediata": False,  # NÃO executa imediatamente ao iniciar
    "intervalo_verificacao": 60,  # Verifica a cada 60 segundos
    "limite_produtos_por_execucao": 5,  # Reduzido para não sobrecarregar
    "intervalo_entre_mensagens": 3,  # Reduzido para ser mais rápido
}

def obter_horarios():
    """Retorna a lista de horários configurados"""
    return HORARIOS_EXECUCAO

def obter_configuracoes():
    """Retorna as configurações gerais"""
    return CONFIGURACOES

def mostrar_horarios():
    """Mostra os horários configurados de forma organizada"""
    print("🕐 HORÁRIOS CONFIGURADOS:")
    print("=" * 40)
    
    for i, horario in enumerate(HORARIOS_EXECUCAO, 1):
        print(f"{i:2d}. {horario}")
    
    print("=" * 40)
    print(f" Total: {len(HORARIOS_EXECUCAO)} execuções por dia")
    print(f"⏱️  Intervalo: A cada 1 hora")
    print(f"🕐 Período: 9:00 às 00:00")

if __name__ == "__main__":
    mostrar_horarios()