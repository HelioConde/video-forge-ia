# Personagens — VideoForge AI

Um personagem por diretório, independentemente do canal. Exemplo:
- \`personagens/alex/profile.json\`: descrição visual e movimentos.
- \`output/pixellab/alex/\`: exportações PNG/ZIP geradas (não versionadas).

O perfil contém as regras visuais, os movimentos animados e as poses/estados usados pela API do PixelLab. Não guarda token, ID privado do personagem, histórico de jobs ou imagens pagas.

Para preservar **exatamente** um personagem existente no PixelLab, configure seu UUID em \`PIXELLAB_CHARACTER_ID\` no GitHub Actions Secrets e execute \`animate\` ou \`ensure-and-animate\`. Se não houver um UUID configurado, \`ensure-and-animate\` cria um novo personagem com base na descrição e depois anima. A identidade visual pode variar quando criada de novo.

Se preferir importar um sprite PNG south-facing, coloque-o em uma pasta privada/local de um personagem e defina \`reference_file\` no perfil. Em repositórios públicos, **não suba imagens privadas ao Git**.

O processo de integração e o comando GitHub Actions estão em [docs/PIXELLAB.md](../docs/PIXELLAB.md).
