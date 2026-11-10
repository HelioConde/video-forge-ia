# Execução autorizada de animações do personagem base

Em 10/11/2026, o usuário autorizou a geração das animações do personagem existente.

- Identificação do personagem: hash SHA-256 do UUID capturado pelo próprio proprietário, sem copiar UUID para o Git público.
- `.github/workflows/pixellab-launch.yml` iniciou o primeiro lote com no máximo 4 direções de animação.
- `.github/workflows/pixellab-complete.yml` faz a continuação sequencial depois de verificar a conclusão **bem-sucedida** do primeiro lote no GitHub.
- O programa não recria o personagem base, não envia vídeos ao YouTube e não publica spritesheet/ZIP; apenas relatório saneado do número de tarefas.
- A API PixelLab é consultada novamente antes de cada POST, e entre rodadas.
- O total de chamadas pagas da continuação é limitado a 44, com no máximo 8 por rodada e sem reenvio automático de POSTs em erro/timeout.
- Se houver falha, 409, dados ambíguos ou ausência de progresso após geração, a continuação para. Não repetir automaticamente.
- A biblioteca PixelLab continua a ser o armazenamento original das imagens geradas. O GitHub Actions guarda somente relatórios temporários de 7 dias.

Fluxo disparado por alterações explícitas aos arquivos do workflow (sem cron).
Não editar nem renomear o arquivo da execução sem revisar se isso causará um novo disparo pago.
