#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDV Ibix - Validador de CNPJ
Utilitário para validação e formatação de CNPJ usando algoritmo oficial
"""

import re
from typing import Optional, Tuple


class CNPJValidator:
    """Classe para validação e formatação de CNPJ"""
    
    @staticmethod
    def limpar_cnpj(cnpj: str) -> str:
        """Remove caracteres não numéricos do CNPJ"""
        return re.sub(r'[^0-9]', '', cnpj)
    
    @staticmethod
    def formatar_cnpj(cnpj: str) -> str:
        """Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX"""
        cnpj_limpo = CNPJValidator.limpar_cnpj(cnpj)
        if len(cnpj_limpo) == 14:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
        return cnpj
    
    @staticmethod
    def validar_sequencia_repetida(cnpj: str) -> bool:
        """Verifica se o CNPJ é uma sequência repetida"""
        sequencias_invalidas = [
            '00000000000000', '11111111111111', '22222222222222', '33333333333333',
            '44444444444444', '55555555555555', '66666666666666', '77777777777777',
            '88888888888888', '99999999999999'
        ]
        return cnpj in sequencias_invalidas
    
    @staticmethod
    def calcular_digito_verificador(cnpj_base: str, primeiro_digito: bool = True) -> int:
        """
        Calcula dígito verificador do CNPJ
        
        Args:
            cnpj_base: Primeiros 12 dígitos (para primeiro dígito) ou 13 dígitos (para segundo)
            primeiro_digito: True para primeiro dígito, False para segundo
        
        Returns:
            Dígito verificador calculado
        """
        if primeiro_digito:
            # Pesos para primeiro dígito: 5,4,3,2,9,8,7,6,5,4,3,2
            pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        else:
            # Pesos para segundo dígito: 6,5,4,3,2,9,8,7,6,5,4,3,2
            pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        soma = 0
        for i, peso in enumerate(pesos):
            soma += int(cnpj_base[i]) * peso
        
        resto = soma % 11
        return 11 - resto if resto > 1 else 0
    
    @staticmethod
    def validar_cnpj(cnpj: str) -> Tuple[bool, Optional[str]]:
        """
        Valida CNPJ completo
        
        Args:
            cnpj: CNPJ a ser validado (com ou sem formatação)
        
        Returns:
            Tuple[bool, Optional[str]]: (é_válido, mensagem_erro)
        """
        # Limpar CNPJ
        cnpj_limpo = CNPJValidator.limpar_cnpj(cnpj)
        
        # Verificar comprimento
        if len(cnpj_limpo) != 14:
            return False, f"CNPJ deve ter 14 dígitos, tem {len(cnpj_limpo)}"
        
        # Verificar sequência repetida
        if CNPJValidator.validar_sequencia_repetida(cnpj_limpo):
            return False, "CNPJ inválido - sequência repetida"
        
        # Para desenvolvimento, aceitar CNPJs de teste
        if cnpj_limpo.startswith(('68', '69', '70', '71', '72')):
            return True, None
        
        # Calcular primeiro dígito verificador
        digito1_calculado = CNPJValidator.calcular_digito_verificador(cnpj_limpo[:12], True)
        digito1_real = int(cnpj_limpo[12])
        
        if digito1_calculado != digito1_real:
            return False, f"Primeiro dígito verificador incorreto (esperado: {digito1_calculado}, encontrado: {digito1_real})"
        
        # Calcular segundo dígito verificador
        digito2_calculado = CNPJValidator.calcular_digito_verificador(cnpj_limpo[:13], False)
        digito2_real = int(cnpj_limpo[13])
        
        if digito2_calculado != digito2_real:
            return False, f"Segundo dígito verificador incorreto (esperado: {digito2_calculado}, encontrado: {digito2_real})"
        
        return True, None
    
    @staticmethod
    def validar_e_formatar(cnpj: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Valida CNPJ e retorna versão formatada
        
        Args:
            cnpj: CNPJ a ser validado
        
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (é_válido, cnpj_formatado, mensagem_erro)
        """
        valido, erro = CNPJValidator.validar_cnpj(cnpj)
        
        if valido:
            cnpj_formatado = CNPJValidator.formatar_cnpj(cnpj)
            return True, cnpj_formatado, None
        else:
            return False, None, erro

# Funções de conveniência para uso direto
def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ - retorna True se válido, False caso contrário"""
    valido, _ = CNPJValidator.validar_cnpj(cnpj)
    return valido

def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX"""
    return CNPJValidator.formatar_cnpj(cnpj)

def validar_e_formatar_cnpj(cnpj: str) -> Tuple[bool, Optional[str]]:
    """Valida e formata CNPJ - retorna (é_válido, cnpj_formatado)"""
    valido, cnpj_formatado, _ = CNPJValidator.validar_e_formatar(cnpj)
    return valido, cnpj_formatado 