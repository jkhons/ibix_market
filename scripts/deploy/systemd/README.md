# Systemd – PDV Ibix

Serviços **Ibix**: PDV Ibix e Auto Ibix são produtos distintos. Este repositório e estes units são do **PDV Ibix**.

## Units (este repositório)

| Unit | Descrição | Porta |
|------|-----------|--------|
| `pdv_solumatica.service` | Aplicação web (Gunicorn/Uvicorn) | 8000 |
| `pdv_solumatica-celery.service` | Celery worker + beat (tarefas + agendamento: billing 03:00, reconciliação MP a cada 10min) | — |
| `pdv_solumatica-beat.service` | Celery beat separado (opcional; não use se celery já roda com `--beat`) | — |

**Auto Ibix** é outro produto; se for instalado no mesmo servidor, use outro unit e outra porta (ex.: 8001).

## Instalação no servidor

```bash
sudo cp pdv_solumatica.service pdv_solumatica-celery.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pdv_solumatica pdv_solumatica-celery
```

Ou use `COPIAR-PARA-SERVIDOR.sh` (executar com sudo no servidor).
