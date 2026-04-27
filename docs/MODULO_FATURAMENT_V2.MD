# Módulo de Faturamento e Notas Fiscais (v2)

## Índice

| Parte | Conteúdo |
|-------|----------|
| **I** | [Contexto fiscal brasileiro](#parte-i---contexto-fiscal-brasileiro) — Tipos de documentos, NF-e, NFS-e, programas de incentivo |
| **II** | [Estrutura por esfera e programas estaduais](#parte-ii---estrutura-por-esfera-e-programas-estaduais) — Federal/Estadual/Municipal, Nota Paulista, estado 2026 |
| **III** | [Arquitetura técnica de integração](#parte-iii---arquitetura-técnica-de-integração) — Webservices, certificados, contingência, reforma CBS/IBS |
| **IV** | [Módulo NFS-e multi-município](#parte-iv---módulo-nfse-multi-município) — Core, providers, worker, modelo de dados |
| **V** | [Implementação: DDL, contratos e jobs](#parte-v---implementação-ddl-contratos-e-jobs) — Tabelas MySQL, Pydantic, provider interface, RBAC |
| **VI** | [Adequações no sistema atual](#parte-vi---adequações-no-sistema-atual) — IBGE, emissor OS/subscription, migrações, fluxos |
| **VII** | [Referência técnica e checklists](#parte-vii---referência-técnica-e-checklists) — Códigos de erro, retry, testes, deploy |

---

## PARTE I — Contexto fiscal brasileiro

### 1. Sistema de faturamento / notas fiscais no Brasil — Visão geral

No Brasil, o uso de notas fiscais eletrônicas é regra nacional há anos, mas a infraestrutura técnica pode variar conforme o tipo de nota e a jurisdição.

📌 Tipos principais de documentos fiscais eletrônicos
Documento	Quando é usado
NF-e (Nota Fiscal Eletrônica)	Venda de produtos/mercadorias (B2B e B2G)
NFS-e (Nota Fiscal de Serviço Eletrônica)	Prestação de serviços
NFC-e (Nota Fiscal ao Consumidor Eletrônica)	Vendas a consumidor final (PDV/Varejo)
CT-e (Conhecimento de Transporte Eletrônico)	Transporte de cargas
MDF-e (Manifesto Eletrônico de Documentos Fiscais)	Documento que agrega outros fiscais em transporte

➡️ Todas essas notas são eletrônicas (XML) e só têm validade depois que o SEFAZ autoriza a emissão.

🏛️ 2. A NF-e é “nacional”, mas com operação estadual

A Nota Fiscal Eletrônica (NF-e) tem layout e regras nacionais mas é recebida, autorizada e gerida por cada Secretaria da Fazenda estadual (SEFAZ) ou por ambientes integrados (SVAN ou SVRS).

Isso significa que, funcionalmente, cada estado tem seu próprio ambiente ou parceria técnica para autorizar a nota fiscal.

As regras tributárias (como ICMS, regimes e obrigações acessórias) variam conforme o estado, mesmo que a estrutura da NF-e seja a mesma.

📍 Exemplo de sistemas estaduais:

São Paulo (SP) tem seu próprio ambiente SEFAZ-SP para NF-e.

Minas Gerais (MG) e outros estados usam o SVRS (ambiente compartilhado).

Muitos estados ainda têm sistemas próprios com regras leves diferenças operacionais.

📊 3. E a Nota Fiscal Paulista? Qual o papel dela?

A Nota Fiscal Paulista é diferente das notas fiscais eletrônicas tradicionais (NF-e ou NFS-e):

É um programa de estímulo fiscal do governo do Estado de São Paulo para incentivar o cidadão consumidor a solicitar a nota fiscal no ato da compra.

Ao informar seu CPF ou CNPJ, o comprador pode acumular créditos fiscais e chances em sorteios.

Não é um tipo de nota fiscal diferente para empresas no sentido de emissão fiscal: é mais um programa de incentivo ligado à emissão da NF-e/NFC-e no estado.

👉 Ou seja, a Nota Fiscal Paulista não substitui a NF-e ou NFS-e: ela é um programa de incentivo à exigência e ao combate à sonegação fiscal no Estado de São Paulo.

📍 4. Outros estados têm programas parecidos?

Sim — alguns estados e cidades desenvolveram programas similares, com nomes e regras próprias:

Nota Paraná (Paraná) — programa estadual de incentivo com crédito e sorteios, similar à paulista.

Algumas prefeituras grandes também já têm programas municipais para incentivar nota em serviços (ex.: descontos em IPTU).

➡️ Mas não existe uma “Nota Fiscal X” estadual igual à paulista em todos os estados — São Paulo e Paraná são os exemplos mais conhecidos de programa próprio de incentivo ao consumidor.

🏢 5. NFS-e (serviços) — panorama nacional

Tradicionalmente, a NFS-e era emitida por sistemas municipais diferentes, porque ISS é um imposto municipal.

Até **2025/2026 está sendo implementado um Sistema Nacional de NFS-e para unificar a emissão entre prefeituras e simplificar processos.

Isso significa que, a partir de 2026, empresas poderão emitir NFS-e em um padrão unificado nacionalmente, independentemente do município — mas ainda será vinculada ao município de prestação do serviço.

🧠 6. Resumo comparativo
Aspecto	NF-e (produtos)	NFS-e (serviços)	Nota Fiscal Paulista
Validade fiscal	Sim	Sim	Não — é programa de incentivo
Tipo de operação	Mercadorias/produtos	Serviços	Qualquer nota vinculada a compras
Regulação principal	Federal + estadual	Federal + municipal (unificação 2026)	Estadual (São Paulo)
Sistema técnico	SEFAZ estadual/SVRS/SVAN	Sistemas municipais / nacional	Programa de crédito ao consumidor
📌 Conclusões principais

✅ A NF-e é o modelo padrão nacional de nota fiscal para circulação de bens, mas é autorizada por cada SEFAZ estadual e sujeita a regras específicas de ICMS e obrigações acessórias por estado.
✅ A NFS-e (serviços) tem sido descentralizada (municipal), mas será mais padronizada nacionalmente a partir de 2026.
✅ Programas como a Nota Fiscal Paulista existem em alguns estados, sendo iniciativas próprias de incentivo ao consumidor, não um tipo fiscal diferente de nota eletrônica.
✅ A emissão de qualquer documento fiscal no Brasil exige certificado digital e transmissão eletrônica para a autoridade competente antes da validade.



---

## PARTE II — Estrutura por esfera e programas estaduais

Estrutura técnica por esfera federativa (Federal → Estadual → Municipal) e programas de incentivo ao consumidor.

### 1. Estrutura Nacional do Sistema de Faturamento

No Brasil, o sistema fiscal é dividido por competência tributária:

Esfera	Tributo	Documento Fiscal	Autoridade
Federal	IPI, PIS, COFINS	NF-e	Receita Federal + SEFAZ
Estadual	ICMS	NF-e / NFC-e	SEFAZ Estadual
Municipal	ISS	NFS-e	Prefeitura
📦 2️⃣ NF-e (Mercadorias) — Padrão Nacional

A NF-e (modelo 55) é nacional, com:

Layout XML único (Manual de Orientação do Contribuinte – MOC)

Autorização prévia obrigatória

Assinatura digital (A1 ou A3)

Protocolo de autorização da SEFAZ

Autorização ocorre por:

SEFAZ própria do estado

Ou ambientes virtuais compartilhados:

SVRS (Rio Grande do Sul)

SVAN (Ambiente Nacional)

Exemplo:

Secretaria da Fazenda do Estado de São Paulo tem infraestrutura própria.

Estados menores utilizam SVRS.

⚠ O layout é igual no país inteiro.
⚠ O que muda estado a estado é regra de ICMS, benefícios fiscais, obrigações acessórias e credenciamento.

🛒 3️⃣ NFC-e (Consumidor Final – Varejo)

Substitui cupom fiscal (ECF).

Modelo 65

Emissão em tempo real

DANFE NFC-e com QR Code

Integração com SAT (em SP, ainda coexistindo em alguns casos)

Praticamente todos os estados já adotaram NFC-e.

🏢 4️⃣ NFS-e (Serviços) — Onde está a maior complexidade

O ISS é municipal.

Historicamente:

Cada prefeitura tinha seu próprio sistema

Layout diferente

Webservice diferente

Certificado diferente

Agora existe o:

🔹 Sistema Nacional da NFS-e

Coordenado pela Receita Federal + ENAT.

Objetivo:

Padronizar layout

Unificar API

Centralizar emissão

Municípios podem:

Aderir ao padrão nacional

Ou manter sistema próprio integrado

Exemplo:

Prefeitura do Município de São Paulo tem sistema próprio robusto.

Municípios menores já migraram para o padrão nacional.

🎁 5️⃣ Programas Estaduais de Incentivo ao Consumidor

Aqui é onde entra sua pergunta sobre “Nota Fiscal Paulista”.

Esses programas são estaduais, vinculados ao ICMS.

🟢 São Paulo
Nota Fiscal Paulista

Crédito de ICMS ao consumidor

Sorteios mensais

CPF na nota

Gestão pela Secretaria da Fazenda do Estado de São Paulo

Válido para NF-e e NFC-e

🟢 Paraná
Nota Paraná

Crédito + sorteios

CPF na nota

Cashback parcial

🟢 Rio de Janeiro
Nota Carioca

Diferença:

Vinculada ao ISS (municipal)

Crédito pode virar desconto no IPTU

Gerida pela Prefeitura da Cidade do Rio de Janeiro

🟢 Minas Gerais
Nota Fiscal Mineira

Relativamente recente

Sorteios e cashback digital

🟢 Bahia
Nota Premiada Bahia

Sorteios mensais

Apoio a entidades sociais

🟢 Distrito Federal
Nota Legal

Pode gerar desconto no IPTU e IPVA

Envolve ICMS e ISS

🟢 Rio Grande do Sul
Nota Fiscal Gaúcha

Cashback

Doação para entidades

Sorteios

🟢 Alagoas
Nota Fiscal Cidadã
🟢 Maranhão
Nota Legal Maranhense
🟢 Goiás
Nota Fiscal Goiana
🟢 Outros Estados

Alguns estados não têm programa ativo estruturado como SP/PR/RS.

🏗 6️⃣ Estado Atual (2026)
📌 Produtos (ICMS)

Totalmente padronizado nacionalmente

Diferença apenas tributária

Emissão via ERP ou API SEFAZ

📌 Serviços (ISS)

Ainda híbrido

Transição para padrão nacional

Municípios grandes mantêm autonomia

📌 Incentivo ao Consumidor

Varia estado a estado

Nem todos possuem

Não altera a estrutura fiscal da empresa

🔎 7️⃣ Do ponto de vista de sistema (ERP / SaaS)

Se você for implementar:

Para produtos:

Integração com SEFAZ estadual

Respeitar CFOP, CST, CSOSN

Tratamento de contingência (SVC)

Para serviços:

Identificar município

Verificar se aderiu ao padrão nacional

Ou integrar via provedor municipal

🧠 Conclusão Técnica

O Brasil é padronizado no layout, descentralizado na autoridade.

ICMS é estadual → SEFAZ.

ISS é municipal → Prefeitura.

“Nota Fiscal Paulista” não é um tipo de nota, é programa de incentivo.

Alguns estados replicaram o modelo com variações.


---

## PARTE III — Arquitetura técnica de integração

### 1. Arquitetura técnica (webservice, certificados, contingência)

#### 1.1 Peças do sistema (visão de arquitetura)

Camadas mínimas recomendadas (ERP/SaaS emissor):

Fiscal Core (motor de regras): CFOP/CST/CSOSN, impostos, validações, cálculo e consistência.

Gerador XML (NF-e/NFC-e/CT-e/MDF-e / NFS-e): monta XML conforme schema vigente.

Assinador: assina XML com certificado ICP-Brasil (normalmente A1 em servidor).

Transmissor / Autorizador: envia para a SEFAZ (ou Portal NFS-e Nacional) e trata retorno.

Gestor de eventos: CCe, Cancelamento, Inutilização, EPEC (quando aplicável), ciência da operação etc.

Armazenamento & Auditoria: XML assinado + protocolo + eventos + logs imutáveis.

Impressão/Render: DANFE/DANFCE (PDF) a partir do XML autorizado.

Monitoramento: fila, retries, indisponibilidade, contingência, SLA.

1.2. Integração NF-e/NFC-e (SEFAZ): como “fala” com o governo

Padrão de comunicação: historicamente SOAP (WS) com mTLS/SSL, assinaturas e schemas.
O emissor:

Valida o XML localmente (schema + regras de negócio)

Assina digitalmente

Transmite para a SEFAZ autorizadora (do seu estado) ou para ambiente compartilhado (SVRS/SVAN)

Recebe: Autorizado, Denegado, Rejeitado (com código) + protocolo

A contingência e o fluxo de autorização são descritos por portais SEFAZ e pelo material do projeto NF-e.

1.3. Certificados (ICP-Brasil): recomendações práticas

Para servidor (SaaS/ERP):

Use A1 (arquivo .pfx) em HSM/Key Vault quando possível, ou armazenamento seguro em disco com rotação e controle de acesso.

Separe por CNPJ emitente (multi-tenant) e registre:

serial, validade, cadeia, hash do certificado, status.

Proteja senha do PFX como segredo (Vault).

Tenha rotina de alarme de expiração (ex.: 30/15/7 dias).

Por que isso é crítico: sem assinatura válida, nada autoriza.

1.4. Estados e ambientes: Homologação vs Produção

Você sempre lida com:

Produção (valendo fiscalmente)

Homologação (teste)

E endpoints variam conforme:

UF

ambiente (prod/hom)

modelo (55 NF-e / 65 NFC-e)

versão do layout

Estratégia boa: um “registry” de endpoints + versões por UF, atualizado por configuração, não hardcode.

1.5. Tratamento de rejeições: regra de ouro

Rejeição ≠ erro técnico só. Pode ser:

Tributária (CFOP, CST, base, NCM, GTIN)

Cadastro (IE, CNPJ, município, regime)

Sequência/numeração (duplicidade, salto)

Schema/assinatura

Padrão de implementação:

Classificar rejeição por “reprocessável” vs “não reprocessável”

Retentativa com backoff apenas para falhas técnicas

Tela/lista de “pendências fiscais” com ação guiada

1.6. Contingência (quando SEFAZ cai)

Você precisa de 2 coisas:

detecção automática de indisponibilidade/intermitência

modo contingência com trilha de auditoria

Modalidades comuns (NF-e / NFC-e)

SVC (SEFAZ Virtual de Contingência): transmite para SVC e já sai autorizado por lá; DANFE em papel comum. É a modalidade “mais limpa” em muitos cenários.

FS / FS-DA: impressão do DANFE em formulário de segurança; usada em cenários específicos (regras podem aparecer em páginas estaduais).

EPEC: evento prévio (mais usado em NF-e, depende do cenário/regra do projeto).

Offline (mais típico no universo NFC-e em alguns estados/implementações): emite localmente e transmite depois conforme regras.

Implementação recomendada (engine):

Estados de emissão: NORMAL, CONTINGENCIA_SVC, CONTINGENCIA_FSDA, OFFLINE

Logar motivo, timestamp, UF, e “janela de retorno”

Assim que normalizar: retomar NORMAL e conciliar pendências

Observação: detalhes de prazo e procedimentos variam por documento e regra vigente; por isso é importante parametrizar por UF/Modelo e manter a documentação do projeto NF-e como fonte.

1.7. NFS-e (Serviços): mudança grande em 2026

A Receita informou que a NFS-e em padrão nacional passa a ser obrigatória a partir de janeiro de 2026, para simplificar o cenário municipal.

Impacto técnico direto:

Você passa a ter um alvo nacional (portal/padrão), reduzindo integrações “prefeitura por prefeitura”

Municípios ainda podem ter particularidades de adesão e transição, mas o padrão nacional vira o caminho dominante.

📊 2) Impacto da Reforma Tributária (CBS/IBS) no modelo atual
2.1. O que muda “na base”

A Emenda Constitucional 132/2023 cria o modelo de IVA dual:

CBS (União)

IBS (Estados + DF + Municípios)

A LC 214/2025 regulamenta e dá trilho de implementação para IBS/CBS.

2.2. Cronograma prático (o que você sente no sistema)

2026: início de operacionalização/entrada em vigor para testes e adequações (há comunicação oficial de fase orientadora).

Implementação é gradual até 2033 (transição longa).

Para sistemas, isso significa: por anos você terá convivência do “modelo antigo” (ICMS/ISS/PIS/COFINS etc.) com o “novo” (CBS/IBS), exigindo arquitetura preparada para dupla apuração.

2.3. Documentos fiscais: NF-e/NFC-e/NFS-e vão precisar carregar “novas informações”

O projeto NF-e já publicou nota de “Adequações NF-e/NFC-e” para o contexto da Reforma, incluindo direções como uso de notas de crédito e débito para ajustes ligados aos novos tributos.

Impacto no seu modelo de dados:

Novos grupos/fields no XML (progressivos por versão)

Novas naturezas de ajuste (crédito/débito)

Maior ênfase em trilha de crédito fiscal (IVA) e conciliação

2.4. Split payment (mudança operacional pesada)

A regulamentação discutiu/introduziu o conceito de split payment: separação automática do imposto no momento do pagamento (parte vai ao fornecedor, parte ao governo).

Impacto no “faturamento” (sistema financeiro/PDV):

Integração fiscal começa a encostar em meios de pagamento

Conciliação (venda ↔ recebível ↔ tributo recolhido) fica mais “tight”

Em SaaS/ERP: você vai precisar de trilhas de:

total bruto

tributo retido/segregado

líquido ao recebedor

eventos de estorno/chargeback

2.5. NFS-e nacional como “pré-requisito” da transição

A Receita também posiciona a NFS-e nacional como parte da modernização e preparação do ambiente para o novo IBS.

Na prática:

Seu módulo de serviços tende a ficar menos municipalizado tecnicamente

Você ganha escala e reduz custo de manutenção de dezenas de integrações

✅ Checklist direto para você (SaaS/ERP)
Para NF-e / NFC-e (mercadorias e varejo)

 Abstrair endpoints por UF/ambiente/modelo/versão

 Pipeline: schema → assinatura → envio → protocolo → storage imutável

 Classificador de rejeições + retentativas técnicas

 Módulo contingência com estados (SVC / FS-DA / Offline onde aplicável)

Para NFS-e (serviços)

 Implementar suporte ao padrão nacional (jan/2026)

 Camada “adapter” para exceções de municípios durante transição

Para Reforma CBS/IBS

 Modelar tributos “atuais” + “novos” coexistindo por período

 Preparar tabelas/eventos para notas de crédito/débito e ajustes

 Preparar conciliação com pagamentos pensando em split payment

 Monitorar versões de layout NF-e/NFC-e e mudanças de validação por fase da transição


---

## PARTE IV — Módulo NFS-e multi-município

### Como estruturar um módulo NFS-e (arquitetura “de verdade”)

A ideia é você não acoplar o core fiscal ao provedor. Você cria um núcleo único e pluga “adapters” por município / padrão nacional.

#### 1. Camadas do módulo

A) Core NFS-e (agnóstico de município)

Cadastro de Serviço (código LC 116 / item da lista, descrição padrão, alíquotas usuais, CNAE opcional)

Cadastro de Tomador (dados + endereço + município IBGE)

Regras de ISS (retenção, local da prestação, exigibilidade, benefício, base)

Motor de cálculo (base, deduções, retenções, líquido)

Geração de RPS (conceito universal no mundo NFS-e)

Estados do documento: DRAFT → SIGNED → SENT → AUTHORIZED / REJECTED → CANCELED

“Eventos” (cancelamento, substituição, carta/retificação se o município tiver)

B) Adapter/Provider layer (por destino)

ProviderNacionalNFS-e (padrão nacional)

ProviderMunicipal_SP (São Paulo capital tem particularidades)

ProviderMunicipal_XYZ (quando ainda existir legado)

C) Orquestração (fila/worker)

Job de emissão (assina → envia → consulta até obter autorização)

Job de cancelamento

Job de consulta/conciliar (importa status e números)

Retentativas técnicas (timeouts, 5xx) com backoff

D) Storage e auditoria

Guardar tudo: payload gerado, XML/JSON enviado, retorno, protocolo, PDF, logs

Modelo “append-only” para rastreabilidade (te ajuda em auditoria)

#### 2. Modelagem mínima de banco (prática)

Tabelas sugeridas:

nfse_invoice (a nota “universal”)

nfse_rps (RPS gerado antes da autorização)

nfse_provider (qual adapter usar e suas configs)

nfse_provider_credential (certificado, token, usuário, segredos)

nfse_event (cancelamento/substituição/retificação etc.)

nfse_log (request/response técnico, com redaction de dados sensíveis)

nfse_pdf (arquivo final ou caminho)

ibge_municipio (tabela IBGE + flags: “usa padrão nacional?”)

Campos-chave em nfse_invoice:

tenant_id, unidade_id

municipio_prestacao_ibge

status

total_servicos, base_iss, aliquota_iss, valor_iss

iss_retido (bool) + valor_iss_retido

tomador_* (cpf/cnpj, nome, endereço)

prestador_insc_municipal

provider_id

external_id (id retornado pelo município/nacional)

numero_nfse, codigo_verificacao

data_emissao, data_competencia

3) Como escolher automaticamente o “provider”

Regra simples e robusta:

Descobrir o município da prestação (IBGE).

Consultar ibge_municipio:

se usa_nfse_nacional = true → ProviderNacionalNFS-e

senão → provider municipal específico (ex.: SP capital legado)

Se não houver provider, bloquear emissão e mostrar “município não suportado” (com caminho de onboarding).

Isso permite:

Cobrir rápido com o padrão nacional

Tratar exceções/legados sem explodir complexidade

4) Certificado e assinatura (multi-tenant)

Em geral, NFS-e também exige certificado do prestador (A1 no servidor é o mais prático).

Você armazena a credencial por CNPJ/IM e vincula ao tenant.

Boa prática:

Rotina de expiração

Redação de segredos em logs

Permissões estritas no RBAC (quem pode emitir/cancelar)

5) UI/UX operacional (o que evita dor)

Tela “Pendências fiscais”:

erros reprocessáveis vs não reprocessáveis

botão “tentar novamente”

validações antes de enviar (campos IBGE, IM, item serviço, retenção)

Tela de “Configuração por município” (só admin)

Status sempre claro (autorizado, rejeitado, aguardando, em fila)

#### 4. Diferenças práticas por estado (SP, PR, MG, RS)

*Resumo para implementação real:* a grande diferença no dia a dia não é o XML em si — é o ecossistema de prefeitura/estado, credenciamento e estabilidade do endpoint.

1) São Paulo (SP)

SP é o caso mais “heterogêneo”:

Interior: muitas cidades aderem mais fácil ao padrão nacional ou usam provedores consolidados.

Capital (São Paulo): historicamente tem regras e integrações próprias e exigências específicas (cadastro, IM, regimes, retenções e validações mais “chatas”).
Prático:

Tenha adapter separado para São Paulo capital se você atender muito lá.

Faça validação forte de IM, município e retenção.

2) Paraná (PR)

Tende a ser mais “organizado” na parte fiscal digital, e o estado tem maturidade grande em SPED.
Prático:

Integrações e padronizações costumam ser menos caóticas.

Bom candidato para começar com “padrão nacional primeiro” + exceções mínimas.

3) Minas Gerais (MG)

MG é grande e diverso.

Muitas prefeituras com sistemas diferentes (legado), mas caminhando para padronização.
Prático:

Você vai pegar bastante variação por município.

Estratégia “adapter por provedor” ajuda muito.

4) Rio Grande do Sul (RS)

RS costuma ser tecnicamente consistente, e o estado historicamente puxa muita coisa via SVRS no universo SEFAZ (mercadorias). Em serviços, depende das prefeituras, mas o ecossistema é mais previsível em muitos municípios.
Prático:

Bom para estabilidade e processo.

Dá para operar bem com fila/consulta e poucos “casos malucos”.


🧱 1) Conceitos e limites do módulo NFS-e no seu cenário
Entidades que você já tem (ou equivalentes)

Tenant/CA: “dono” do ambiente.

Empresa (Estabelecimento): emissor (CNPJ + IM + município IBGE). Pode haver vários por CA.

Cliente: tomador (CPF/CNPJ + município IBGE).

OS / Atendimento / Venda avulsa: origem do serviço.

Billing / Assinatura: recorrência SaaS.

Regra de ouro do módulo

Quem emite = sempre uma Empresa/Estabelecimento (CNPJ/IM).
O restante (OS, venda, mensalidade) apenas “alimenta” a nota.

🏗 2) Arquitetura técnica (Core + Providers + Worker)
2.1 Camadas
A) Core NFS-e (agnóstico)

valida dados mínimos (tomador, serviço, município IBGE, IM do prestador)

calcula ISS (com flags: retido, deduções, exigibilidade)

gera RPS (sempre) e gera payload no formato do provider

controla estados e auditoria

B) Providers (adapters)

provider = "NACIONAL" (primeiro)

futuros: provider = "SP_CAPITAL", provider = "PROVEDOR_X", etc.

cada provider implementa: emitir, consultar, cancelar, substituir (se existir)

C) Worker/Fila (obrigatório)

Você não quer emissão síncrona em request web.

jobs idempotentes

retries técnicos

“poll”/consulta até finalizar

🗃️ 3) Modelo de dados (mínimo suficiente e extensível)

Vou focar no que você realmente vai usar no dia a dia.

3.1 Tabela nfse_invoice (documento “universal”)

Campos principais:

Escopo

id

tenant_id

empresa_id (estabelecimento emissor)

cliente_id (tomador, opcional se CPF/CNPJ avulso)

Origem

origin_type = BILLING | OS | SALE | MANUAL

origin_id (id da mensalidade/OS/venda)

Município / competência

municipio_prestacao_ibge

data_competencia

Valores

valor_servicos

valor_deducoes

base_iss

aliquota_iss

valor_iss

iss_retido (bool)

valor_iss_retido

Status

status = DRAFT | QUEUED | SENT | AUTHORIZED | REJECTED | CANCELED

last_error_code, last_error_msg

Retornos do fisco

provider (default NACIONAL)

external_id

numero_nfse

codigo_verificacao

url_consulta

data_emissao

Auditoria

created_at, updated_at

Índices:

(tenant_id, empresa_id, status)

(tenant_id, origin_type, origin_id) UNIQUE (idempotência)

(tenant_id, numero_nfse) (consulta rápida)

3.2 Tabela nfse_rps

id, tenant_id, empresa_id, invoice_id

serie, numero, tipo

status = RESERVED | USED | VOID

UNIQUE (tenant_id, empresa_id, serie, numero)

Aqui você controla numeração por estabelecimento, sem gambiarra.

3.3 Tabela nfse_provider_config

id, tenant_id, empresa_id

provider (NACIONAL, futuros…)

municipio_ibge (opcional; quando for “por município”)

parâmetros (JSON): ambiente, endpoints, etc.

3.4 Tabela nfse_credential

Como você não tem fluxo A1 ainda, isso é crítico:

id, tenant_id, empresa_id

type = A1_PFX

pfx_blob_encrypted (ou path seguro)

pfx_password_encrypted

cert_serial, valid_from, valid_to

status = ACTIVE | EXPIRED | REVOKED

Boas práticas mínimas:

criptografar em repouso

acesso só por RBAC (admin CA)

auditoria de upload/alteração

3.5 Tabela nfse_message_log (request/response)

invoice_id, direction (OUT/IN), http_status

payload_redacted, response_redacted

created_at

Isso é o que te salva em suporte e auditoria.

🔐 4) Fluxo de certificado A1 (o que implementar agora)

Você precisa de 3 telas/rotas:

Upload A1 por Empresa/Estabelecimento

Validação imediata (senha correta + leitura do subject + validade)

Monitor de expiração (alerta 30/15/7 dias)

E 2 garantias técnicas:

segredo criptografado (não plaintext em DB)

worker acessa via “credential manager”, não via ORM direto

⚙️ 5) Worker jobs (recorrente + avulso)
5.1 Jobs essenciais

nfse_issue_job(invoice_id)

valida pré-requisitos (A1 ok, IM ok, tomador ok)

reserva RPS

gera payload + assina

envia

marca SENT

nfse_poll_job(invoice_id)

consulta status no provider até AUTHORIZED ou REJECTED

nfse_cancel_job(invoice_id, reason)

nfse_pdf_job(invoice_id) (se gerar PDF/espelho)

5.2 Idempotência

origin_type+origin_id único: billing mensal não duplica

invoice_id reprocessável com lock de job (evita corrida)

5.3 Retentativa

retry somente em erro técnico (timeout/5xx)

rejeição fiscal vai pra “pendências” com ação humana

🧾 6) Integração com seu fluxo “Recorrente + Avulso”
6.1 Recorrente (mensalidade SaaS)

ao fechar ciclo (ex.: todo dia 1 ou no vencimento):

cria nfse_invoice com origin_type=BILLING

status QUEUED

worker emite em lote por empresa emissora

6.2 Avulso (OS/Atendimento)

ao concluir OS e marcar “Faturar”:

cria nfse_invoice com origin_type=OS

permite pré-visualização e edição mínima (tomador/serviço/retido)

emite

🧭 7) Estratégia “Padrão Nacional primeiro” com exceções depois

Você implementa agora:

ProviderNacional como default

provider_router(empresa_id, municipio_ibge):

se municipio.usa_padrao_nacional = true → NACIONAL

senão → “não suportado ainda” (e já deixa trilha pra onboarding)

Quando chegar SP capital/legado:

você só adiciona um adapter e marca municipio_ibge/config para roteamento.

💰 8) Diferenças práticas (SP, PR, MG, RS) — na vida real, para NFS-e

Como você vai no padrão nacional, a diferença principal vira adesão do município e “exceções”:

São Paulo (SP)

Interior: tendência a padronizar mais facilmente (bom pro nacional).

Capital: historicamente é o lugar que mais puxa exceção/adapter próprio.
Tradução prática: você provavelmente vai precisar de ProviderSPCapital em algum momento se atender muita empresa na capital.

Paraná (PR)

Em geral, ambiente fiscal costuma ser menos caótico operacionalmente.
Tradução prática: tende a te dar menos casos de “regra obscura”, e o padrão nacional costuma encaixar melhor.

Minas Gerais (MG)

Grande diversidade municipal (muitas cidades, muitos comportamentos).
Tradução prática: mesmo com padrão nacional, MG costuma ser onde aparecem mais “casos de borda” por município (cadastro/IM/parametrização).

Rio Grande do Sul (RS)

Ecossistema técnico costuma ser consistente.
Tradução prática: operação tende a ser mais previsível; seu maior ganho vem de ter worker+poll bem feito.

✅ 9) Entregável prático imediato (o que eu implementaria em 7 blocos)

Tabelas: nfse_invoice, nfse_rps, nfse_credential, nfse_message_log, nfse_provider_config

Tela/config: Empresa → “Config NFS-e” + upload A1 + validade

Core: validações + geração de invoice a partir de Billing/OS

Provider Nacional: emitir/consultar/cancelar

Worker: issue/poll/cancel/pdf

Painel operacional: fila, pendências, reprocessar, baixar XML/PDF

Observabilidade: logs redigidos + métricas (autorizadas, rejeitadas, tempo médio)






---

## PARTE V — Implementação: DDL, contratos e jobs

Pacote para implementar: DDL, contratos, provider interface, jobs, roteamento e RBAC (Padrão Nacional primeiro, exceções depois).

### 1. Entidades novas do módulo NFS-e (nomes/tabelas)

Sugestão de prefixo: nfse_* (evita colisão e deixa explícito).

#### 1.1 nfse_invoices (nota universal)

Função: documento único que liga origem (subscription/OS/manual) → emissor (empresa) → tomador (clientes) → retorno fiscal.

Campos (mínimo + extensível):

id (PK)

tenant_id (FK → tenants.id)

empresa_id (FK → empresa.id) emissor

cliente_id (FK → clientes.id, nullable) tomador

origin_type ENUM: SUBSCRIPTION | OS | MANUAL

origin_id (nullable) (id em subscriptions ou ordem_servico)

municipio_prestacao_ibge (int)

data_competencia (date)

descricao_servico (text) (espelho/descrição)

item_lista_servico (varchar) (LC116 / item)

cnae (varchar, nullable)

valor_servicos (decimal)

valor_deducoes (decimal)

base_iss (decimal)

aliquota_iss (decimal)

valor_iss (decimal)

iss_retido (tinyint/bool)

valor_iss_retido (decimal)

status ENUM: DRAFT | QUEUED | SENT | AUTHORIZED | REJECTED | CANCELED

provider ENUM: NACIONAL | SP_CAPITAL | OUTRO

external_id (varchar, nullable)

numero_nfse (varchar, nullable)

codigo_verificacao (varchar, nullable)

url_consulta (varchar, nullable)

data_emissao (datetime, nullable)

last_error_code (varchar, nullable)

last_error_msg (text, nullable)

created_at, updated_at

Índices críticos:

UNIQUE (tenant_id, origin_type, origin_id) (idempotência para recorrência e OS)

(tenant_id, empresa_id, status)

(tenant_id, numero_nfse)

#### 1.2 nfse_rps (numeração/controle de RPS por emissor)

id (PK)

tenant_id

empresa_id

nfse_invoice_id (nullable) (FK → nfse_invoices.id)

serie (varchar)

numero (bigint)

tipo (int) default 1

status ENUM: RESERVED | USED | VOID

created_at

Índices:

UNIQUE (tenant_id, empresa_id, serie, numero)

(tenant_id, empresa_id, status)

Você pode manter também um “sequenciador” por empresa: nfse_rps_sequence (mais simples) — mas a tabela acima dá trilha de auditoria.

#### 1.3 nfse_credentials (certificado A1 por empresa)

id (PK)

tenant_id

empresa_id

type ENUM: A1_PFX

pfx_blob (LONGBLOB) criptografado

pfx_password (VARBINARY) criptografado

cert_serial (varchar)

valid_from (date)

valid_to (date)

status ENUM: ACTIVE | EXPIRED | REVOKED

created_at, updated_at

Índices:

UNIQUE (tenant_id, empresa_id, status) (opcional: permitir só 1 ACTIVE)

#### 1.4 nfse_message_logs (request/response redigido)

id

tenant_id

nfse_invoice_id

direction ENUM: OUT | IN

http_status (int)

payload_redacted (longtext)

response_redacted (longtext)

created_at

#### 1.5 nfse_provider_configs (parametrização por empresa/município)

id

tenant_id

empresa_id

provider ENUM (NACIONAL, etc.)

municipio_ibge (nullable)

environment ENUM: HOMOLOG | PROD

config_json (json)

created_at, updated_at

### 2. DDL (MySQL 8) — pronto para migrar

```sql
CREATE TABLE nfse_invoices (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  empresa_id BIGINT NOT NULL,
  cliente_id BIGINT NULL,

  origin_type ENUM('SUBSCRIPTION','OS','MANUAL') NOT NULL,
  origin_id BIGINT NULL,

  municipio_prestacao_ibge INT NOT NULL,
  data_competencia DATE NOT NULL,

  descricao_servico TEXT NULL,
  item_lista_servico VARCHAR(20) NULL,
  cnae VARCHAR(20) NULL,

  valor_servicos DECIMAL(15,2) NOT NULL DEFAULT 0,
  valor_deducoes DECIMAL(15,2) NOT NULL DEFAULT 0,
  base_iss DECIMAL(15,2) NOT NULL DEFAULT 0,
  aliquota_iss DECIMAL(9,4) NOT NULL DEFAULT 0,
  valor_iss DECIMAL(15,2) NOT NULL DEFAULT 0,
  iss_retido TINYINT(1) NOT NULL DEFAULT 0,
  valor_iss_retido DECIMAL(15,2) NOT NULL DEFAULT 0,

  status ENUM('DRAFT','QUEUED','SENT','AUTHORIZED','REJECTED','CANCELED') NOT NULL DEFAULT 'DRAFT',
  provider ENUM('NACIONAL','SP_CAPITAL','OUTRO') NOT NULL DEFAULT 'NACIONAL',

  external_id VARCHAR(120) NULL,
  numero_nfse VARCHAR(60) NULL,
  codigo_verificacao VARCHAR(80) NULL,
  url_consulta VARCHAR(500) NULL,
  data_emissao DATETIME NULL,

  last_error_code VARCHAR(40) NULL,
  last_error_msg TEXT NULL,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_nfse_inv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_nfse_inv_empresa FOREIGN KEY (empresa_id) REFERENCES empresa(id),
  CONSTRAINT fk_nfse_inv_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),

  UNIQUE KEY uq_nfse_origin (tenant_id, origin_type, origin_id),
  KEY ix_nfse_status (tenant_id, empresa_id, status),
  KEY ix_nfse_numero (tenant_id, numero_nfse)
);

CREATE TABLE nfse_rps (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  empresa_id BIGINT NOT NULL,
  nfse_invoice_id BIGINT NULL,

  serie VARCHAR(10) NOT NULL DEFAULT '1',
  numero BIGINT NOT NULL,
  tipo INT NOT NULL DEFAULT 1,

  status ENUM('RESERVED','USED','VOID') NOT NULL DEFAULT 'RESERVED',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_nfse_rps_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_nfse_rps_empresa FOREIGN KEY (empresa_id) REFERENCES empresa(id),
  CONSTRAINT fk_nfse_rps_invoice FOREIGN KEY (nfse_invoice_id) REFERENCES nfse_invoices(id),

  UNIQUE KEY uq_nfse_rps (tenant_id, empresa_id, serie, numero),
  KEY ix_nfse_rps_status (tenant_id, empresa_id, status)
);

CREATE TABLE nfse_credentials (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  empresa_id BIGINT NOT NULL,

  type ENUM('A1_PFX') NOT NULL DEFAULT 'A1_PFX',
  pfx_blob LONGBLOB NOT NULL,
  pfx_password VARBINARY(512) NOT NULL,

  cert_serial VARCHAR(80) NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NOT NULL,

  status ENUM('ACTIVE','EXPIRED','REVOKED') NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_nfse_cred_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_nfse_cred_empresa FOREIGN KEY (empresa_id) REFERENCES empresa(id),
  KEY ix_nfse_cred_status (tenant_id, empresa_id, status)
);

CREATE TABLE nfse_provider_configs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  empresa_id BIGINT NOT NULL,

  provider ENUM('NACIONAL','SP_CAPITAL','OUTRO') NOT NULL DEFAULT 'NACIONAL',
  municipio_ibge INT NULL,
  environment ENUM('HOMOLOG','PROD') NOT NULL DEFAULT 'HOMOLOG',
  config_json JSON NOT NULL,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_nfse_pc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_nfse_pc_empresa FOREIGN KEY (empresa_id) REFERENCES empresa(id),
  KEY ix_nfse_pc (tenant_id, empresa_id, provider, municipio_ibge)
);

CREATE TABLE nfse_message_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  nfse_invoice_id BIGINT NOT NULL,

  direction ENUM('OUT','IN') NOT NULL,
  http_status INT NULL,

  payload_redacted LONGTEXT NULL,
  response_redacted LONGTEXT NULL,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_nfse_ml_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_nfse_ml_invoice FOREIGN KEY (nfse_invoice_id) REFERENCES nfse_invoices(id),

  KEY ix_nfse_ml (tenant_id, nfse_invoice_id, created_at)
);
```

### 3. Contratos (Pydantic) — mínimos
NfseInvoiceCreateFromSubscription

subscription_id

empresa_id (emissor)

cliente_id (tomador, se existir)

municipio_ibge

competencia

descricao_servico

valor_servicos

aliquota_iss

iss_retido + valor_iss_retido

NfseInvoiceCreateFromOS

ordem_servico_id

empresa_id

cliente_id

idem acima

NfseIssueRequest

invoice_id

NfseCancelRequest

invoice_id

reason (texto)

codigo_cancelamento (se o provider exigir)

4) Provider interface (adapter)

Interface única:

issue(invoice, empresa, credential) -> IssueResult

poll(invoice, empresa, credential) -> PollResult

cancel(invoice, empresa, credential, reason) -> CancelResult

E um ProviderRouter:

default: NACIONAL

depois: se municipio_ibge marcado como exceção → SP_CAPITAL

5) Jobs do worker (o que você implementa primeiro)
5.1 Emissão

valida credencial A1 ativa para empresa_id

reserva RPS (nfse_rps) de forma transacional

muda status QUEUED → SENT

chama provider.issue()

grava log OUT/IN

agenda poll

5.2 Poll

consulta até:

AUTHORIZED (preenche numero, verificação, url)

REJECTED (salva erro)

retentativa só em erro técnico

5.3 Cancelamento

valida status permitido

chama provider.cancel()

muda para CANCELED

6) Integração com suas origens reais
6.1 Subscription (tabela subscriptions)

Gatilho: fechamento do período / pagamento confirmado / vencimento (você decide)

Cria nfse_invoices com:

origin_type='SUBSCRIPTION'

origin_id=subscriptions.id

UNIQUE garante que não duplica

6.2 OS (tabela ordem_servico)

Gatilho: “Concluir + Faturar”

Cria nfse_invoices com:

origin_type='OS'

origin_id=ordem_servico.id

A descrição do serviço pode vir do resumo/itens (ordem_servico_itens)

7) RBAC mínimo (sem inventar complexidade)

Perfis:

Super Admin / Admin: tudo

Cliente Admin (CA):

pode configurar NFS-e para suas empresas (empresa)

pode subir certificado A1

pode emitir/cancelar

Usuário operacional do CA:

pode emitir (se permissão “fiscal_emitir”)

pode cancelar (se permissão “fiscal_cancelar”)

pode ver logs (opcional)

Regras:

Toda consulta e ação sempre filtra por tenant_id.

empresa_id deve pertencer ao tenant.

8) Diferenças práticas SP/PR/MG/RS (já pensando no seu “adapters depois”)

Como você vai começar pelo padrão nacional, as diferenças viram:

cadastro do prestador (IM, município, regime de tributação local)

adesão do município e eventuais exigências

SP capital é o caso com maior chance de exigir provider próprio no futuro

Em termos de roadmap:

Nacional (cobre a maioria, reduz custo)

SP capital adapter (se sua base tiver muita capital)

“provedor genérico” (caso apareça município legado específico)



---

## PARTE VI — Adequações no sistema atual

### 1. O que falta de verdade (e o que NÃO falta)

**Falta (crítico)**

Código IBGE do município para:

emissor (empresa / estabelecimento fiscal)

tomador (clientes)

Vínculo explícito do emissor para:

OS (ordem_servico)

subscriptions (recorrente) → escolher “empresa emissora padrão do tenant”

Não falta (já existe)

CNPJ, IM, endereço, CRT/regime, CNAE, código de serviço municipal, alíquota ISS

Ambiente e provedor fiscal (você já tem campos)

Já existe inclusive rascunho de “certificado” na empresa (path/blob/validade)

2) Ajustes mínimos no seu schema atual (sem refatorar tudo)
2.1 Adicionar IBGE na empresa e clientes

Você já tem cidade e uf. Só que isso não resolve para NFS-e com segurança.

empresa

Adicionar:

municipio_ibge INT NULL

(opcional) municipio_nome_norm VARCHAR(120) (para cache/diagnóstico)

clientes

Adicionar:

municipio_ibge INT NULL

(opcional) numero, bairro, complemento (se você quiser endereço completo; pra NFS-e alguns municípios exigem, outros não)

Você pode preencher automaticamente via tabela IBGE (cidade+UF → IBGE), mas tecnicamente é melhor armazenar o IBGE e deixar cidade/uf como “texto”.

2.2 Resolver o emissor da OS

Hoje ordem_servico não tem emissor. Isso vai te travar.

Adicionar em ordem_servico:

empresa_id BIGINT NULL (FK empresa.id) ou

estabelecimento_fiscal_id BIGINT NULL (FK estabelecimentos_fiscais.id)

Sugestão (mais simples no seu desenho): empresa_id direto na OS.

2.3 Resolver o emissor padrão do tenant (para subscriptions)

Como subscriptions não tem empresa vinculada, você precisa de um “default emissor”:

Opções (melhor → pior):

tenants.default_empresa_id

tabela tenant_fiscal_config (mais flexível)

“pegar a primeira empresa ativa” (ruim para auditoria)

Sugestão: adicionar em tenants:

default_empresa_id BIGINT NULL (FK empresa.id)

3) Como mapear seus dados atuais para a nfse_invoices (mapeamento campo-a-campo)

Vou usar o módulo NFS-e que propus (nfse_invoices) e mostrar exatamente de onde vem.

3.1 Emissão por Subscription (recorrente)

Entrada: subscriptions.id

Resolver emissor:

empresa_id = tenants.default_empresa_id (obrigatório)

Tomador:

aqui tem 2 modelos possíveis (você decide por regra):

B2C: tomador = o próprio CA (cliente “dono” do tenant) → precisa de cliente_id do CA

B2B: tomador = empresa do CA (mesma coisa, só muda dados)

Como hoje não há vínculo direto, você precisa de 1 campo adicional:

ou tenants.cliente_id_ca (cliente “dono”)

ou empresa.cliente_id como “dono” e usar isso como tomador para o subscription

Valores:

valor_servicos = subscriptions.valor_mensal_centavos / 100

data_competencia = subscriptions.period_start (ou mês de referência)

descricao_servico = “Mensalidade plano X — período Y”

aliquota_iss: usar empresa.aliquota_iss como default (override por tela)

Município da prestação:

regra padrão: município do emissor (empresa.municipio_ibge)

3.2 Emissão por OS (avulso)

Entrada: ordem_servico.id

Emissor:

empresa_id = ordem_servico.empresa_id (novo campo)

Tomador:

cliente_id = ordem_servico.cliente_id

Valores:

valor_servicos = SUM(ordem_servico_itens.valor_total)

descricao_servico = resumo da OS + itens (ou texto livre)

aliquota_iss: default empresa.aliquota_iss (editável)

Competência:

data_competencia = DATE(ordem_servico.data_conclusao) (ou data_abertura se preferir)

4) Certificado A1: você já tem campo na empresa — mas precisa “formalizar”

Você já tem em empresa:

certificado_a1_path, senha_certificado, certificado_a1_blob, certificado_validade

Isso é bom, dá pra reaproveitar. O que falta é:

armazenar senha criptografada

garantir 1 certificado ativo por empresa

rotina de expiração e RBAC

✅ Minha recomendação para você agora:

Em vez de criar nfse_credentials, use os campos da própria empresa inicialmente (MVP).

Depois, se quiser separar e auditar melhor, migra pra tabela nfse_credentials.

5) “Provider Nacional primeiro”: roteamento no seu cenário

Com IBGE preenchido:

provider = NACIONAL
if empresa.uf == 'SP' and empresa.municipio_ibge == 3550308 (São Paulo capital):
    provider = SP_CAPITAL (futuro)

Enquanto não existir adapter SP capital:

bloquear emissão para esse caso (mensagem clara)

ou permitir manual/export (fallback)

6) Diferenças práticas SP/PR/MG/RS (no seu contexto real)

Como você vai começar pelo padrão nacional, as diferenças que “batem” são estas:

SP

Maior chance de “caso especial” em capital e em algumas prefeituras grandes.

Seu sistema deve estar pronto para:

validação mais rígida de IM

regras de retenção mais frequentes

A maior probabilidade de precisar adapter é SP capital.

PR

Costuma dar menos dor operacional.

“Padrão nacional” tende a cobrir bem e com menos exceções.

MG

Maior diversidade municipal.

Mesmo no padrão nacional, aparece mais “variação de cadastro/parametrização”.

Aqui, sua tela de “pendências fiscais” vira essencial.

RS

Operação tende a ser mais previsível.

O que manda é: worker/retentativas/polling bem feito + logs.

7) Migrações mínimas (SQL) — o que eu aplicaria já
7.1 empresa + clientes (IBGE)
ALTER TABLE empresa ADD COLUMN municipio_ibge INT NULL;
ALTER TABLE clientes ADD COLUMN municipio_ibge INT NULL;
7.2 ordem_servico (emissor)
ALTER TABLE ordem_servico ADD COLUMN empresa_id BIGINT NULL;
-- depois criar FK se você já usa FKs
7.3 tenants (default emissor)
ALTER TABLE tenants ADD COLUMN default_empresa_id BIGINT NULL;
8) O que você ganha com esse desenho

Emissão NFS-e para recorrência e OS sem duplicar regra

Controle por empresa emissora (CNPJ) do CA

Sem dependência de “cidade/UF texto” para integração fiscal

Preparado para SP capital como exceção depois


### Desenho final: NFS-e para mensalidade (subscription)

#### Campo que falta para identificar o “Cliente CA” (tomador)

Você precisa de um vínculo explícito do Tenant/CA com um registro em clientes.

Opção recomendada (simples e limpa)

Adicionar em tenants:

ca_cliente_id BIGINT NULL → FK clientes.id

Assim, para qualquer cobrança recorrente:

Tomador = tenants.ca_cliente_id

SQL:

ALTER TABLE tenants ADD COLUMN ca_cliente_id BIGINT NULL;
-- (opcional) adicionar FK se seu banco estiver com FKs ativas
-- ALTER TABLE tenants ADD CONSTRAINT fk_tenants_ca_cliente FOREIGN KEY (ca_cliente_id) REFERENCES clientes(id);

Você já vai ter também tenants.default_empresa_id (emissor padrão).
Então a mensalidade fica 100% resolvida: emissor e tomador.

2) Fluxo de NFS-e para Subscription (recorrente)

Entrada: subscriptions.id

2.1 Resolver emissor e tomador

empresa_id = tenants.default_empresa_id (obrigatório)

cliente_id = tenants.ca_cliente_id (obrigatório)

Validações mínimas antes de enfileirar:

empresa.municipio_ibge preenchido

clientes.municipio_ibge preenchido

empresa.im preenchido (NFS-e costuma exigir)

empresa.aliquota_iss ou uma alíquota definida para a emissão

certificado A1 presente e válido (do jeito que você já armazena em empresa)

2.2 Criar nfse_invoices

Campos:

origin_type='SUBSCRIPTION'

origin_id=subscriptions.id

tenant_id=subscriptions.tenant_id

empresa_id (default)

cliente_id (CA)

municipio_prestacao_ibge = empresa.municipio_ibge

data_competencia = subscriptions.period_start (ou mês do período)

valor_servicos = subscriptions.valor_mensal_centavos/100

descricao_servico = "Mensalidade {plano_codigo} - {period_start} a {period_end}"

aliquota_iss = empresa.aliquota_iss (padrão; pode permitir override)

status='QUEUED'

Idempotência:

UNIQUE (tenant_id, origin_type, origin_id) evita duplicar notas do mesmo período/ciclo.

3) Telas/config necessárias (bem objetivas)
3.1 Config Fiscal do CA (uma vez)

Na área do CA:

Selecionar Empresa emissora padrão (tenants.default_empresa_id)

Selecionar Cliente CA (tomador padrão) (tenants.ca_cliente_id)

Validar IBGE preenchido em ambos

3.2 Assistente de preenchimento do IBGE (para empresa e cliente)

Como você tem cidade e uf, você pode:

sugerir o IBGE automaticamente

mas guardar em municipio_ibge e travar emissão se vazio

4) Ajustes que eu aplicaria agora (resumo de migrações)
ALTER TABLE empresa ADD COLUMN municipio_ibge INT NULL;
ALTER TABLE clientes ADD COLUMN municipio_ibge INT NULL;

ALTER TABLE tenants ADD COLUMN default_empresa_id BIGINT NULL;
ALTER TABLE tenants ADD COLUMN ca_cliente_id BIGINT NULL;

ALTER TABLE ordem_servico ADD COLUMN empresa_id BIGINT NULL;
5) Regras rápidas de bloqueio (evitam “nota quebrada”)

Bloquear emissão de subscription se:

tenants.default_empresa_id IS NULL

tenants.ca_cliente_id IS NULL

empresa.im IS NULL OR empresa.im=''

empresa.municipio_ibge IS NULL

cliente.municipio_ibge IS NULL

certificado inexistente/expirado (se você for emitir de verdade)

Mostrar mensagem direta:

“Configure empresa emissora padrão e cliente CA, e preencha o código IBGE do município do emissor e do tomador.”

### Mapeamento: ordem_servico → nfse_invoices

Regra:

ordem_servico.empresa_id (novo campo) é o emissor.

ordem_servico.cliente_id é o tomador.

valor_servicos = SUM(ordem_servico_itens.valor_total) (calcular no momento da geração).

data_competencia = DATE(ordem_servico.data_conclusao) (se nulo, usar data_abertura).

descricao_servico = ordem_servico.observacoes + resumo dos itens (concat).

aliquota_iss = empresa.aliquota_iss (com override manual se necessário).

iss_retido = regra por município / contrato (por enquanto, usar empresa.iss_retencao_default se existir; senão false).

Campos resultantes a preencher em nfse_invoices:

tenant_id = ordem_servico.tenant_id (propague se disponível; caso contrário derive pela empresa)

origin_type = 'OS'

origin_id = ordem_servico.id

empresa_id = ordem_servico.empresa_id

cliente_id = ordem_servico.cliente_id

municipio_prestacao_ibge = empresa.municipio_ibge

data_competencia = COALESCE(ordem_servico.data_conclusao::date, ordem_servico.data_abertura::date)

valor_servicos = SUM(ordem_servico_itens.valor_total)

valor_deducoes = 0 (padrão; parametrizável)

base_iss = valor_servicos - valor_deducoes

aliquota_iss, valor_iss = base_iss * aliquota_iss

iss_retido/valor_iss_retido conforme regras

descricao_servico texto gerado

status = 'QUEUED'

2) Migrações SQL (prontas para executar)
-- 1) campos mínimos
ALTER TABLE empresa ADD COLUMN municipio_ibge INT NULL;
ALTER TABLE clientes ADD COLUMN municipio_ibge INT NULL;

ALTER TABLE tenants ADD COLUMN default_empresa_id BIGINT NULL;
ALTER TABLE tenants ADD COLUMN ca_cliente_id BIGINT NULL;

ALTER TABLE ordem_servico ADD COLUMN empresa_id BIGINT NULL;

-- 2) índice/constraint opcionais (aplique conforme política de FKs)
ALTER TABLE ordem_servico ADD CONSTRAINT fk_os_empresa FOREIGN KEY (empresa_id) REFERENCES empresa(id);
ALTER TABLE tenants ADD CONSTRAINT fk_tenants_default_empresa FOREIGN KEY (default_empresa_id) REFERENCES empresa(id);
ALTER TABLE tenants ADD CONSTRAINT fk_tenants_ca_cliente FOREIGN KEY (ca_cliente_id) REFERENCES clientes(id);

Aconselho aplicar FK em ambiente de homologação primeiro. Se usar migrations Alembic, coloque como nullable e rode migração de dados separada para popular empresa_id nas OS existentes.

---

## PARTE VII — Referência técnica e checklists

### 3. Funções utilitárias (SQL) — cálculo do total da OS

```sql
-- total da OS
SELECT os.id,
       COALESCE(SUM(osi.valor_total),0) AS total_os
FROM ordem_servico os
LEFT JOIN ordem_servico_itens osi ON osi.ordem_servico_id = os.id
WHERE os.id = :ordem_servico_id
GROUP BY os.id;
```

### 4. Contratos (Pydantic) — modelos mínimos

```python
# models/nfse.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class NfseInvoiceCreate(BaseModel):
    tenant_id: int
    empresa_id: int
    cliente_id: Optional[int]
    origin_type: str  # 'SUBSCRIPTION' | 'OS' | 'MANUAL'
    origin_id: Optional[int]
    municipio_prestacao_ibge: int
    data_competencia: date
    descricao_servico: Optional[str]
    item_lista_servico: Optional[str]
    cnae: Optional[str]
    valor_servicos: float
    valor_deducoes: Optional[float] = 0.0
    aliquota_iss: float
    iss_retido: bool = False
```

### 5. Exemplo rápido SQLAlchemy model (esqueleto)

```python
# models.py (SQLAlchemy declarative)
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, DECIMAL, Enum, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class NfseInvoice(Base):
    __tablename__ = "nfse_invoices"
    id = Column(BigInteger, primary_key=True)
    tenant_id = Column(BigInteger, index=True, nullable=False)
    empresa_id = Column(BigInteger, nullable=False)
    cliente_id = Column(BigInteger, nullable=True)
    origin_type = Column(String(20), nullable=False)
    origin_id = Column(BigInteger, nullable=True)
    municipio_prestacao_ibge = Column(Integer, nullable=False)
    data_competencia = Column(DateTime, nullable=False)
    descricao_servico = Column(Text)
    valor_servicos = Column(DECIMAL(15,2), default=0)
    base_iss = Column(DECIMAL(15,2), default=0)
    aliquota_iss = Column(DECIMAL(9,4), default=0)
    valor_iss = Column(DECIMAL(15,2), default=0)
    iss_retido = Column(Boolean, default=False)
    status = Column(String(20), default='DRAFT')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 6. Worker / Jobs — pseudocódigo (FastAPI + Celery / RQ style)
6.1 Resumo dos jobs

job_issue_nfse(invoice_id)

job_poll_nfse(invoice_id)

job_cancel_nfse(invoice_id, reason)

job_generate_pdf(invoice_id)

6.2 Pseudocódigo job_issue_nfse
def job_issue_nfse(invoice_id):
    with db.session.begin():
        invoice = db.get(NfseInvoice, invoice_id, lock_for_update=True)
        if invoice.status not in ('QUEUED','DRAFT'):
            return
        # validar pré-requisitos
        empresa = db.get(Empresa, invoice.empresa_id)
        if not empresa.municipio_ibge:
            invoice.status = 'REJECTED'
            invoice.last_error_msg = 'Empresa sem municipio_ibge'
            db.commit()
            return
        # credential check
        if not empresa.certificado_a1_blob or empresa.certificado_validade < today:
            invoice.status = 'REJECTED'
            invoice.last_error_msg = 'Certificado inexistente ou expirado'
            return
        # reservar RPS (transação)
        rps = reserve_rps(tenant_id=invoice.tenant_id, empresa_id=invoice.empresa_id)
        invoice.status = 'SENT'
        db.flush()

    # fora da transação: montar XML/payload e assinar
    try:
        payload = provider.build_payload(invoice, empresa, rps)
        signed = sign_payload(payload, empresa.certificado_a1_blob, empresa.senha_certificado)
        resp = provider.issue(signed, config=provider_config)
        log_request_response(invoice_id, payload, resp)
        if resp.is_sync_authorized:
            invoice.status = 'AUTHORIZED'
            invoice.numero_nfse = resp.numero
            invoice.codigo_verificacao = resp.codigo
            invoice.data_emissao = resp.data_emissao
        else:
            invoice.status = 'SENT'
            schedule_job(job_poll_nfse, invoice_id, delay=30)  # poll later
    except TransientNetworkError as e:
        # retry policy: exponential backoff (3 attempts)
        retry_job(job_issue_nfse, invoice_id)
    except ValidationError as e:
        invoice.status = 'REJECTED'
        invoice.last_error_msg = str(e)
6.3 Pseudocódigo job_poll_nfse
def job_poll_nfse(invoice_id):
    invoice = db.get(NfseInvoice, invoice_id)
    if invoice.status not in ('SENT',):
        return
    resp = provider.query(invoice.external_id or invoice.numero_nfse)
    log_request_response(invoice_id, 'POLL', resp)
    if resp.status == 'AUTHORIZED':
        invoice.status = 'AUTHORIZED'
        invoice.numero_nfse = resp.numero
        invoice.codigo_verificacao = resp.codigo
        invoice.data_emissao = resp.data_emissao
    elif resp.status == 'REJECTED':
        invoice.status = 'REJECTED'
        invoice.last_error_msg = resp.message
    else:
        # ainda pendente, re-agendar com backoff
        schedule_job(job_poll_nfse, invoice_id, delay=next_backoff())
7) Máquina de estados (state machine)

Estados permitidos e transições:

DRAFT → QUEUED (usuário ou fluxo automático)

QUEUED → SENT (worker reserva RPS e envia)

SENT → AUTHORIZED (autorizado pelo provedor)

SENT → REJECTED (rejeição fiscal)

REJECTED → QUEUED (se erro corrigido e reemitir) — somente manual ou via UI

AUTHORIZED → CANCELED (cancelamento dentro do prazo permitido)

AUTHORIZED → SUBSTITUTED (se o município suportar substituição) — opcional

8) Códigos de erro padrão (para last_error_code)

Sugestão curta (padronize em enum):

MUN_IBGE_MISSING — município IBGE ausente

CERT_EXPIRED — certificado expirado

CERT_MISSING — certificado não encontrado

RPS_UNAVAILABLE — falha ao reservar RPS

NETWORK_ERROR — erro de rede/transiente

SCHEMA_INVALID — payload inválido (validação XML)

REJEICAO_XXXX — código de rejeição vindo do provedor (mantém código original)

9) Política de retry

Erros transientes (NETWORK, 5xx): re-tentar 3 vezes com backoff exponencial (ex.: 30s, 2m, 10m).

RPS reservation falha: retry 1-2x.

Erros de validação (schema/tributo): não re-tentar — mover para REJECTED e notificar suporte.

Polling: poll a cada 30s até 5 vezes, depois 5m, 15m, 1h (ou até limite de 24h) — parametrizável por tenant.

10) RBAC (resumo prático)

tenant_admin / ca_admin

configura issuer (empresa), carrega certificado, define ca_cliente_id, default_empresa_id

pode emitir/cancelar/reprocessar

fiscal_user

pode emitir/cancelar/reprocessar notas para empresas que pertence ao tenant

user_operacional

pode ver NFSe e baixar XML/PDF

support_readonly

visualizar logs e mensagens (mas não baixar pfx)

Sempre filtrar por tenant_id e empresa_id pertencente.

11) Checklist de testes (mínimos)

Unitários:

criação de nfse_invoices a partir de subscriptions e ordem_servico (cobrir idempotência)

reserva de RPS (concorrência simulada)

validação de pré-requisitos (IBGE, IM, certificado)

Integração (homolog):

emissão completa contra ambiente homolog do provider nacional (fluxo sync + async)

rejeição fiscal simulada (ex.: invalid NCM/custom field)

cancelamento autorizado e cancelamento rejeitado

E2E:

ciclo de mensalidade: gerar invoice, enviar, autorizar, gerar PDF, reconciliar com pagamento

Observabilidade:

testar logs redigidos (payloads com dados pessoais devem ser redigidos)

alertas de expiração de certificado (30/15/7 dias)

12) Checklist de deploy (prático)

Migration DB aplicadas (backup antes)

Worker scaling: mínimo 1 worker com fila dedicada nfse_issue

Secrets: pfx senha em Vault / KMS

Monitor: Sentry/Prometheus + alertas para REJECTED > threshold

Dashboard operacional: fila depth, authorized rate, rejected rate, avg latency

13) Artefatos que eu posso gerar agora (se quiser)

Se você quiser que eu gere agora (copie/cole comando):

Alembic migration SQL completa

Arquivos Pydantic/SQLAlchemy prontos (arquivos .py)

Pseudo-implementação do provider ProviderNacional (métodos stub)

Tela de administração (HTML/JS) para upload A1 e validação

---

## Resumo da organização do documento

| Parte | Foco |
|-------|------|
| **I** | Contexto: tipos de documentos fiscais no Brasil (NF-e, NFS-e, NFC-e), Nota Fiscal Paulista, panorama 2026. |
| **II** | Estrutura por esfera (Federal/Estadual/Municipal) e programas de incentivo por estado. |
| **III** | Arquitetura técnica: camadas do sistema, certificados, contingência, reforma CBS/IBS, checklist integração. |
| **IV** | Módulo NFS-e: core + providers + worker, modelo de dados, roteamento, diferenças SP/PR/MG/RS. |
| **V** | Implementação: DDL MySQL, contratos Pydantic, interface do provider, jobs, RBAC. |
| **VI** | Adequações no sistema atual: IBGE, emissor OS/subscription, migrações SQL, fluxo subscription e OS. |
| **VII** | Referência: funções SQL, modelos Pydantic/SQLAlchemy, pseudocódigo jobs, máquina de estados, códigos de erro, checklists de teste e deploy. |