# Arquitetura proposta — VideoForge AI

## Meta
Automatizar: pauta > roteiro > planejamento de cenas > geração de imagens e camadas > animação > narração > montagem > validação > upload no YouTube.

## Módulos (e responsabilidades)
1. **Content Planner**: recebe o tema, canal e duração. Cria roteiro e storyboard com identidade de personagens.
2. **Scene Composer**: gera primeiro a composição visual de referência; depois produz cenário, personagens e objetos em camadas transparentes, respeitando a aparência original.
3. **Animator**: anima separadamente personagens, objetos e câmera; preserva enquadramento e continuidade.
4. **Audio Studio**: cria narração e trilha/efeitos licenciados, sincronizando com as cenas.
5. **Renderer**: combina camadas, legendas e áudio usando FFmpeg, exportando vídeo vertical ou horizontal.
6. **Quality Gate**: verifica duração, resolução, áudio, consistência dos personagens, arquivos e duplicatas.
7. **YouTube Publisher**: usa OAuth e YouTube Data API; começa com modo privado e só publica quando explicitamente habilitado.
8. **Scheduler / Observability**: GitHub Actions, logs, reexecuções seguras e resumo de cada envio.

## Sequência segura de entrega
- [x] Fundamentos: configuração de vídeo, storyboard JSON, validação local e GitHub Actions de teste.
- [ ] Gerador real de roteiros com provedor de IA configurável.
- [ ] Compositor de imagens e extração de camadas transparentes.
- [ ] Animação por camadas e renderização FFmpeg.
- [ ] Voz, trilha, legendas e mixagem.
- [ ] Teste completo: vídeo local de 10 segundos.
- [ ] Autenticação OAuth do YouTube e upload **privado** de teste.
- [ ] Publicação e agendamento automático por canal, com autorização.
- [ ] Métricas e comparação de resultados por vídeo.

## Segurança e custo
- Nenhuma credencial deve entrar no Git.
- Segredos devem ficar em GitHub Actions Secrets.
- Antes de usar APIs pagas, permitir configuração de orçamento, cotas e provedores.
- Em falhas, não publicar um vídeo incompleto.
- Controlar idempotência por identificador de vídeo para impedir uploads duplicados.
- A pipeline atual só gera **um JSON de storyboard**. Ainda não gera imagem, voz, MP4 nem envia ao YouTube.

## Organização futura de múltiplos canais
Cada canal terá configuração própria (tema, idioma, formato, agendamento, conta do YouTube, prompts e limites) sem misturar personagens nem assets.
