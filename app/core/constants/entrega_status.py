# PDV Ibix - Status de entrega (logística local)
# Usar constantes em model, schema e services para evitar strings soltas.

AGUARDANDO_PUBLICACAO = "aguardando_publicacao"
DISPONIVEL = "disponivel"
ACEITA = "aceita"
EM_RETIRADA = "em_retirada"
RETIRADA = "retirada"
EM_ROTA = "em_rota"
ENTREGUE = "entregue"
CANCELADA = "cancelada"
EXPIRADA = "expirada"
FALHA_ENTREGA = "falha_entrega"

STATUS_VALIDOS = (
    AGUARDANDO_PUBLICACAO,
    DISPONIVEL,
    ACEITA,
    EM_RETIRADA,
    RETIRADA,
    EM_ROTA,
    ENTREGUE,
    CANCELADA,
    EXPIRADA,
    FALHA_ENTREGA,
)

# Vocabulário tipo_veiculo (entregador)
TIPO_VEICULO_MOTO = "moto"
TIPO_VEICULO_CARRO = "carro"
TIPO_VEICULO_UTILITARIO = "utilitario"
TIPO_VEICULO_AMBOS = "ambos"
TIPOS_VEICULO = (TIPO_VEICULO_MOTO, TIPO_VEICULO_CARRO, TIPO_VEICULO_UTILITARIO, TIPO_VEICULO_AMBOS)

# Vocabulário tipo_veiculo_aceito (entrega)
TIPO_VEICULO_ACEITO_QUALQUER = "qualquer"
TIPOS_VEICULO_ACEITO = (TIPO_VEICULO_MOTO, TIPO_VEICULO_CARRO, TIPO_VEICULO_UTILITARIO, TIPO_VEICULO_ACEITO_QUALQUER)
