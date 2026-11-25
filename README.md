# Nightreign Seed Reader

Identifica a **seed do mapa** do *Elden Ring Nightreign* sozinho, lendo a tela do jogo. Mostra o mapa completo da seed (chefes de cada dia, evento especial, fortes, igrejas, ruínas, chefes de campo, castelo…) numa janela escura no estilo do jogo, feita pra ficar aberta no **segundo monitor**.

Faz o mesmo que o [nightreign-seed-finder.com](https://nightreign-seed-finder.com/), mas sem você clicar em nada: abriu o mapa no jogo, a seed aparece.

## Como funciona

1. Você abre o mapa no jogo (tecla **M**).
2. O app tira "prints" da região do mapa (igual ao OBS), espera a imagem estabilizar e:
   - reconhece o **tipo de mapa** (Normal, Mountaintop, Crater, Rotted Woods, Noklateo, Great Hollow);
   - reconhece o **Nightlord** pelo retrato no canto do mapa;
   - reconhece os **ícones dos POIs** (rede neural pequena, roda na CPU);
   - compara com as **520 seeds** (jogo base + DLC) e mostra a melhor.
3. **Nightlord desconhecido/oculto?** Sem problema: ele monta a seed só pelos POIs do mapa. Se duas seeds empatarem, avisa "confira candidatos" e você troca com um clique (ou **F10**).

Leva cerca de 1 segundo por leitura. A cada vez que o mapa é aberto de novo, ele confere outra vez (então uma partida nova é detectada sozinha).

## Segurança (ban)

- Só lê **pixels da tela**, do mesmo jeito que OBS, Discord ou a ferramenta de captura do Windows.
- **Não** lê a memória do jogo, **não** injeta nada, **não** abre nem altera arquivos do jogo, **não** mexe no Easy Anti-Cheat.
- É o mesmo método usado por overlays populares da comunidade. Mesmo assim, nenhuma ferramenta de terceiros tem garantia oficial da FromSoftware.

## Instalação

**Opção A, instalador pronto:** baixe o `NightreignSeedReader-Setup.exe` e dê dois cliques. A janela de instalação pergunta se você quer o atalho na Área de Trabalho e cria o atalho no Menu Iniciar. Não precisa de administrador nem de nenhum outro programa.

**Opção B, gerar o instalador:** com Python 3.11+ instalado, dê dois cliques em `build.bat`. O `NightreignSeedReader-Setup.exe` aparece na própria pasta, do lado do `build.bat`.

**Opção C, rodar do código (sem instalar):** dois cliques em `run.bat`.

Para desinstalar: Configurações do Windows → Aplicativos → Nightreign Seed Reader → Desinstalar.

## Uso

- Deixe o jogo em **janela sem bordas** (Borderless). Em tela cheia exclusiva a captura pode sair preta.
- A região do mapa é calculada sozinha para janelas **16:9** (1080p, 1440p, 4K…). Se usar outra proporção ou HUD diferente: menu **☰ → Calibrar região do mapa**, abra o mapa e arraste um quadrado em volta dele.
- Mova a janela pro segundo monitor: ela lembra a posição.
- Por padrão ele só lê quando o jogo está em primeiro plano (dá pra mudar no menu ☰).

| Tecla | Ação |
|---|---|
| **F8** | Ler agora (força nova leitura na próxima vez que o mapa estiver aberto) |
| **F9** | Liga/desliga o overlay com os nomes por cima do mapa dentro do jogo |
| **F10** | Próximo candidato |
| Roda do mouse / arrastar / duplo clique | Zoom / mover / ajustar o mapa |

As teclas funcionam com o jogo em foco.

### Busca manual (igual ao site)

Na aba **Busca manual**: escolha o Nightlord (ou "desconhecido"), o tipo de mapa e clique nos círculos para marcar o que você vê (igreja, forte, ruína, com o elemento se houver). Dourado = POI, vermelho = chefe de campo, azul = castelo. Botão direito remove a marcação. Quando sobrar uma seed, ela abre sozinha.

### Overlay no jogo (opcional)

Com **F9** ligado, os nomes de chefes e locais aparecem por cima do mapa dentro do jogo. O overlay fica **invisível para capturas** (não atrapalha a próxima leitura e não vaza spoiler na live).

### Ler a partir de um print

Menu **☰ → Reconhecer a partir de um print…** aceita um print da tela inteira (16:9) ou só do mapa.

## Observações

- A numeração das seeds do jogo base (0–319) é a mesma do site, então o botão "Abrir no site" leva direto à mesma seed. As seeds do DLC usam a numeração interna dos dados (1000+) e não têm link.
- Nomes de chefes e locais aparecem em inglês, como na maioria dos guias.

## Créditos e licença

- Motor de reconhecimento, modelo CNN dos POIs e dados das seeds: [nightreign-overlay-helper](https://github.com/NeuraXmy/nightreign-overlay-helper) de NeuraXmy (AGPL-3.0), com dados extraídos pela comunidade (thefifthmatt e outros).
- Fonte Cinzel: Natanael Gama (SIL Open Font License).
- Este projeto também é distribuído sob a **GNU AGPL-3.0** (veja `LICENSE`).
- Projeto de fã, sem afiliação com FromSoftware ou Bandai Namco.
