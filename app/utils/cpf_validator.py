#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDV Ibix - Validador de CPF
Utilitário para validação e formatação de CPF usando algoritmo oficial
"""

import re
from typing import Optional, Tuple


class CPFValidator:
    """Classe para validação e formatação de CPF"""

    @staticmethod
    def limpar_cpf(cpf: str) -> str:
        """Remove caracteres não numéricos do CPF"""
        return re.sub(r'[^0-9]', '', str(cpf or ''))

    @staticmethod
    def formatar_cpf(cpf: str) -> str:
        """Formata CPF no padrão XXX.XXX.XXX-XX"""
        cpf_limpo = CPFValidator.limpar_cpf(cpf)
        if len(cpf_limpo) == 11:
            return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        return cpf

    @staticmethod
    def validar_sequencia_repetida(cpf: str) -> bool:
        """Verifica se o CPF é uma sequência repetida"""
        return len(set(cpf)) == 1 if len(cpf) == 11 else False

    @staticmethod
    def calcular_digito_verificador(cpf_base: str) -> int:
        """Calcula dígito verificador do CPF (pesos 10,9,8,7,6,5,4,3,2 para primeiro; 11,10,...,2 para segundo)."""
        pesos = list(range(len(cpf_base) + 1, 1, -1))
        soma = sum(int(cpf_base[i]) * pesos[i] for i in range(len(cpf_base)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    @staticmethod
    def validar_cpf(cpf: str) -> Tuple[bool, Optional[str]]:
        """
        Valida CPF completo.
        Returns:
            Tuple[bool, Optional[str]]: (é_válido, mensagem_erro)
        """
        cpf_limpo = CPFValidator.limpar_cpf(cpf)
        if len(cpf_limpo) != 11:
            return False, f"CPF deve ter 11 dígitos, tem {len(cpf_limpo)}"
        if CPFValidator.validar_sequencia_repetida(cpf_limpo):
            return False, "CPF inválido - sequência repetida"
        dig1 = CPFValidator.calcular_digito_verificador(cpf_limpo[:9])
        if dig1 != int(cpf_limpo[9]):
            return False, "CPF inválido (dígitos verificadores)"
        dig2 = CPFValidator.calcular_digito_verificador(cpf_limpo[:10])
        if dig2 != int(cpf_limpo[10]):
            return False, "CPF inválido (dígitos verificadores)"
        return True, None

    @staticmethod
    def validar_e_formatar(cpf: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Valida CPF e retorna versão formatada.
        Returns:
            Tuple[bool, cpf_formatado ou None, mensagem_erro ou None]
        """
        valido, erro = CPFValidator.validar_cpf(cpf)
        if valido:
            return True, CPFValidator.formatar_cpf(cpf), None
        return False, None, erro
