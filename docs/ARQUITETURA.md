# Arquitetura proposta — VideoForge AI

## Organização por canal e por modelo

```text
canal/
  <canal-id>/
    canal.json
    videos/
      <video-id>/
        video.json
modelos/
  <modelo-id>/
    modelo.json
videoforge/
  config.py     # resolve a receita do canal/vídeo
  pipeline.py   # prepara e valida storyboard (dry-run)
tests/
.github/workflows/
output/         # gerados localmente, fora do Git
```

- **Canal**: define idioma, configurações de publicação e `modelo_padrao`.
- **Vídeo**: guarda duração, roteiro/cenas e `modelo` opcional. Quando existe, substitui o modelo padrão do canal.
- **Modelo de produção**: receita independente do canal para etapas de roteiro, imagem, animação, voz e montagem.
- **Modelo de IA**: provedor e identificação configuráveis para cada etapa (`provedor` e `modelo_ia`), ainda não integrados.

## Meta

Automatizar: pauta > roteiro > planejamento de cenas > geração de imagens e camadas > animação > narração > montagem > validação > upload no YouTube.

## Módulos planejados

1. **Content Planner**: tema, canal, vídeo, roteiro, storyboard e continuidade dos personagens.
2. **Scene Composer**: imagem completa de referência; extração de cenário, personagens e objetos transparentes.
3. **Animator**: anima os elementos separadamente, preservando enquadramento e identidade.
4. **Audio Studio**: vozes e efeitos licenciados, com sincronização.
5. **Renderer**: renderização FFmpeg com legendas e áudio.
6. **Quality Gate**: duração, consistência, assets ausentes e duplicatas.
7. **YouTube Publisher**: OAuth/YouTube Data API, teste privado antes de liberar publicação.
8. **Scheduler / Observability**: GitHub Actions, logs, recuperações e status de cada canal.

## Etapas de entrega

- [x] Organização de pastas por canal, vídeo e modelo reutilizável.
- [x] Herança de modelo do canal com sobrescrita por vídeo, com testes.
- [x] Storyboard JSON de exemplo e validação no GitHub Actions.
- [ ] Integração real de IA para roteiros, imagens, animação e voz.
- [ ] Renderização de um MP4 de 10 segundos.
- [ ] Upload privado de teste no YouTube.
- [ ] Agendamento automático e monitoramento.

## Segurança e limites atuais

- O protótipo **não gera imagens, áudio ou MP4 e não realiza uploads**.
- Credenciais devem ficar em Actions Secrets, nunca em `canal/` ou `modelos/`.
- Testar em privado primeiro, impedir uploads repetidos, validar qualidade e controlar custo das APIs.
