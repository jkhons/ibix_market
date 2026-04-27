# Modelo para vender o serviço de Faturamento e NF-e

**Objetivo:** Poder começar a vender o módulo de emissão de nota fiscal (NF-e) integrado ao PDV/Pedidos.

---

## Modelo de venda: Cliente Administrador (CA)

**A partir de agora, a venda segue o modelo CA:**

- **CA = Cliente Administrador:** quem compra o sistema e usa o módulo fiscal. Cada CA gerencia **apenas** as suas notas e os seus sistemas, tudo **por dentro do seu próprio ambiente** (isolado dos demais clientes).
- **Autogestão:** o CA faz todo o gerenciamento das notas (emissão, consulta, download, cancelamento) **sem depender da operação** para configurar cada emissor.
- **Certificado válido:** o CA (ou usuário com permissão) **apenas insere o certificado digital válido para emissão de nota** na sua empresa fiscal. Com isso, o sistema emite NF-e em nome do CNPJ do CA usando esse certificado.
- **Isolamento:** as notas e dados fiscais de um CA não são visíveis nem acessíveis por outro CA.

**Frase para venda:** *“Cada cliente administrador (CA) gerencia as suas notas e os seus sistemas sozinho, só inserindo o certificado válido para emissão de nota.”*

---

## O que estamos vendendo (após Fase 1)

**Nome do serviço:** Emissão de NF-e integrada ao PDV / Pedidos (modelo CA)

**Em uma frase:** O CA faturar o pedido no sistema e a NF-e sair direto para a SEFAZ; ele gerencia tudo dentro do sistema, apenas com o certificado válido cadastrado.

**Benefícios para o CA:**
- Gerencia **todas** as suas notas e sistemas em um só lugar (dentro do seu ambiente).
- Apenas **insere o certificado digital válido para emissão de nota** na empresa; o resto o sistema faz.
- Um clique para faturar o pedido e gerar a NF-e.
- Dados fiscais corretos (NCM, CFOP, impostos) a partir do cadastro.
- Envio e autorização na SEFAZ; download de XML e PDF (DANFE) e cancelamento.
- Registro de quem baixou o quê (auditoria).

---

## O que precisa estar pronto para vender

| Item | Status sugerido |
|------|------------------|
| Integração com provedor real (ex.: Focus NFE) | Fase 1 – obrigatório |
| **CA insere certificado válido por empresa; escopo isolado por CA** | Fase 1 – obrigatório |
| Itens da nota com NCM, CFOP, impostos ao faturar | Fase 1 – obrigatório |
| Cadastro da empresa + certificado para emissão | Fase 1 – obrigatório |
| Produtos com NCM (e CFOP quando exigido) | Fase 1 – obrigatório |
| Link “Ver nota” após faturar / filtro por pedido | Fase 2 – desejável |
| Relatórios fiscais / múltiplos provedores | Fase 3 – opcional |

---

## Como precificar (exemplos)

- **Incluso no plano:** Módulo Fiscal incluso no plano “Completo” ou “Fiscal” do PDV.
- **Módulo avulso:** Valor mensal fixo pelo módulo + custo do provedor (repasse ou incluído).
- **Por uso:** Pacote de X notas/mês; excedente por nota.

*(Ajustar valores e nomes dos planos conforme a estratégia comercial.)*

---

## Checklist antes de fechar a venda

- [ ] Provedor definido (Focus NFE, NFS-e Nacional, outro).
- [ ] **CA** tem ou terá cadastro de empresa (CNPJ, IE, endereço).
- [ ] **CA** terá **certificado digital válido para emissão de nota** e fará o cadastro no sistema (por empresa).
- [ ] Produtos terão NCM (e CFOP quando for o caso).
- [ ] Deixar claro: o CA gerencia suas notas e sistemas sozinho, apenas inserindo o certificado válido.
- [ ] Combinar com o CA: uso em homologação primeiro ou direto em produção.

---

## Próximo passo técnico

Implementar **Fase 1** do [PLANO_FATURAMENTO_NOTA_FISCAL.md](./PLANO_FATURAMENTO_NOTA_FISCAL.md): provedor real + dados fiscais nos itens + validação + série padrão.

Depois disso, o serviço está pronto para ser vendido e entregue com emissão real de NF-e.
