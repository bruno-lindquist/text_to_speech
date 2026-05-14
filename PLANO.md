# 🐝 Fizzy Bee — Leitor de Texto de Alta Qualidade

> Aplicativo desktop Python com Flet, usando edge-tts para síntese de voz de alta qualidade.

---

## Contexto

Este projeto nasce do desejo de ter um **leitor de texto pessoal** com narração natural e visual moderno, evitando os leitores genéricos do sistema operacional (que costumam ter vozes robóticas) e os serviços online (que têm limites e custos). Usando **edge-tts** (que acessa as vozes neurais da Microsoft Edge gratuitamente), conseguimos qualidade comparável a serviços pagos sem nenhum custo.

O app servirá para:
- Ouvir artigos, textos longos e livros em PDF/EPUB enquanto faz outras tarefas
- Estudar com ritmo personalizado (controle de velocidade)
- Salvar áudios para ouvir offline depois
- Aprender Python na prática construindo algo útil

---

## Visão Geral

**Fizzy Bee** é um leitor de texto desktop (Python + Flet) que usa **edge-tts** para gerar narração com alta qualidade. O usuário cola texto ou abre arquivos (TXT/PDF/DOCX/EPUB), escolhe voz e parâmetros, ouve dentro do app com acompanhamento visual (texto destacado conforme é lido na Fase 5) e pode salvar como MP3.

### Stack técnica

| Componente | Biblioteca | Função |
|---|---|---|
| Linguagem | Python 3.11+ | Base do projeto |
| GUI | **Flet** | Interface gráfica moderna (Material Design) |
| Síntese de voz | **edge-tts** | Vozes neurais da Microsoft Edge (grátis) |
| Leitura de PDF | **pypdf** | Extração de texto de PDF |
| Leitura de DOCX | **python-docx** | Extração de texto de Word |
| Leitura de EPUB | **ebooklib** | Extração de texto de ebooks |
| Segmentação de frases | **pysbd** | Quebra texto em frases respeitando abreviações |
| Player de áudio | **just_playback** | Player MP3 com seek (wrapper sobre miniaudio) |
| Logging | **loguru** | Logs estruturados e simples |
| Concorrência | **asyncio** (nativo) | Alinhado com edge-tts e Flet |
| Empacotamento (macOS) | **PyInstaller** + **create-dmg** | Gera `.app` e instalador `.dmg` |

> **Por que `just_playback`?** Escolhido por não exigir dependência externa (como o VLC). Tem seek nativo e suporta MP3.
>
> ⚠️ **Riscos aceitos conscientemente:**
> - `just_playback` está com manutenção parada desde ~2018. Plano B: trocar por `miniaudio` direto se aparecerem bugs em macOS recente.
> - Como `just_playback` é wrapper sobre `miniaudio` (C-extension), PyInstaller pode ter atrito no embalo. Validar empiricamente na Fase 1.

### Tema visual

Dark mode moderno (estilo Spotify/Discord), com accent color **âmbar/amarelo** combinando com o tema "abelha" 🐝.

---

## Não-objetivos (escopo fechado)

Listado explicitamente para evitar escopo crescer (YAGNI):

- **Não suporta vozes locais/offline** — só edge-tts (precisa de internet)
- **Não tem edição ou anotação de texto** — é leitor, não editor
- **Não tem fila de múltiplas leituras** — uma leitura por vez
- **Não tem sincronização entre dispositivos** — tudo local
- **Não tem login, conta ou nuvem**
- **Não tem cache persistente de áudios** — chunks ficam em memória apenas durante a sessão (invalidados ao trocar texto, voz ou velocidade) e são descartados ao fechar o app
- **Não tem internacionalização da UI** — interface sempre em pt-BR, mesmo quando a voz selecionada é de outro idioma
- **Não tem tradução de texto**
- **Não tem OCR de imagens/PDFs escaneados**

---

## Arquitetura

Código separado em **módulos com responsabilidades claras** (princípio SOLID — cada peça faz uma coisa só):

```
fizzy_bee/
├── main.py                    # Ponto de entrada (inicia o Flet app)
├── core/                      # Lógica de negócio (Python puro, sem GUI)
│   ├── tts_engine.py          # Wrapper do edge-tts (síntese + word boundaries)
│   ├── audio_player.py        # Player com play/pause/stop/seek (just_playback)
│   ├── text_chunker.py        # Divide texto em frases (pysbd)
│   ├── extractors/            # Um arquivo por formato (Open/Closed)
│   │   ├── __init__.py        # Função pública extract(path) que escolhe extractor
│   │   ├── txt.py
│   │   ├── pdf.py
│   │   ├── docx.py
│   │   └── epub.py
│   ├── storage.py             # Persistência JSON (histórico e config)
│   └── logger.py              # Configuração centralizada do loguru
├── ui/                        # Camada visual
│   ├── app.py                 # Estrutura principal da janela
│   ├── components/
│   │   ├── text_area.py       # Área de texto com highlight
│   │   ├── voice_controls.py  # Dropdowns e sliders de voz
│   │   ├── player_controls.py # Play/pause/seek/salvar
│   │   └── side_panel.py      # Painel lateral de histórico
│   └── theme.py               # Cores e estilos do dark mode
├── tests/                     # Testes (focados em core/)
│   └── fixtures/              # Arquivos de exemplo
│       ├── docs/              # TXT, PDF, DOCX, EPUB para extractors
│       └── audio/             # MP3s curtos pré-gerados (mock do edge-tts)
├── packaging/                 # Scripts de empacotamento macOS
│   ├── fizzy_bee.spec         # Config PyInstaller
│   └── build_dmg.sh           # Gera .app + .dmg
├── requirements.txt
└── README.md
```

> **Dados do usuário ficam em `~/FizzyBee/`**, fora do repositório. Veja seção **Armazenamento**.

### Por que essa separação

- **`core/`** é Python puro — funciona sem GUI, pode até virar CLI futuramente sem retrabalho
- **`ui/`** só desenha a tela e chama o `core/` — se um dia trocar Flet por outra GUI, o `core/` continua intacto
- **`extractors/`** isolado por formato — adicionar novo formato (RTF, ODT...) = criar novo arquivo, sem tocar nos outros (Open/Closed)
- **`storage.py` único** — toda persistência JSON num só lugar (DRY)
- **Componentes pequenos** = cada arquivo cabe na cabeça enquanto edita (KISS)

---

## Funcionalidades

### Entrada de texto

- Colar/digitar texto direto na área central
- Abrir arquivo via diálogo do sistema operacional
- Arrastar arquivo (drag-and-drop) direto na janela ⚠️ suporte de drop de arquivos do SO no Flet é parcial — validar em macOS na Fase 2; se não funcionar, manter apenas o diálogo do SO
- Formatos suportados: **TXT, PDF, DOCX, EPUB**

### Controles de voz

- **Filtro por idioma** (dropdown 1): pt-BR, en-US, es-ES, etc.
- **Escolha de voz** (dropdown 2): lista filtrada pelo idioma (ex: Francisca, Antonio, Brenda...)
- **Velocidade (rate)**: slider de -50% a +100%
- **Volume**: slider de ajuste

> **Pitch fora do MVP**: vozes neurais do edge-tts frequentemente ignoram ou distorcem o ajuste de pitch. Avaliar inclusão depois, com base na experiência real.

### Reprodução de áudio

- Player embutido com **play / pause / parar**
- **Stop cancela tanto a reprodução quanto qualquer síntese em andamento** (player atual + tasks asyncio em background)
- **Barra de progresso com seek** (Fase 5)
- **Highlight de palavra sendo lida** (Fase 5)
- **Salvar como MP3** — concatena os chunks por anexação binária. Funciona porque edge-tts entrega MP3s com parâmetros consistentes (a validar na Fase 1; se variarem, plano B é re-encodar com `pydub`+`ffmpeg`)

### Estratégia de reprodução: streaming progressivo

Em vez de esperar todos os chunks serem sintetizados antes de tocar:

1. Sintetiza o **chunk 1** → começa a tocar assim que pronto
2. Enquanto o **chunk 1 toca**, sintetiza o **chunk 2** em paralelo (`asyncio.create_task`)
3. Quando o **chunk N termina**, o **chunk N+1** já está pronto na fila
4. Latência inicial percebida = tempo de síntese de **um** chunk, não do texto todo

*Caso o N+1 ainda não esteja pronto quando o N terminar (rede lenta), player pausa brevemente — UI mostra um spinner discreto até o próximo chunk chegar.*

> Os chunks sintetizados ficam na fila em memória só durante a sessão (não é cache persistente — ver Não-objetivos).

### Funcionalidades extras

- **Histórico de leituras**: lista de textos lidos recentemente, com reabrir/reouvir
- **Divisão automática de texto em chunks** — detalhes na seção **Segmentação de texto**

---

## Fluxo de uso

1. **Abre o app** — janela dark mode com:
   - Painel lateral esquerdo: histórico de leituras
   - Centro: área de texto grande
   - Painel direito: controles de voz
   - Rodapé: player + botão "Salvar MP3"

2. **Insere texto** (colar, abrir arquivo, ou arrastar)

3. **Configura voz** (filtro idioma → voz → sliders)

4. **Clica em ▶ Reproduzir**:
   - App divide texto em chunks (pysbd)
   - edge-tts sintetiza com streaming progressivo
   - Player toca; na Fase 5, destaca palavras sendo lidas

5. **Salva MP3** (opcional) — escolhe destino no diálogo, app concatena chunks

6. **Sai do app** — histórico é salvo na ordem: parar player → salvar histórico → cancelar tasks pendentes → flush dos logs → sair

---

## Tratamento de erros e casos especiais

| Caso | Comportamento |
|---|---|
| Texto vazio ao clicar play | Botão **desabilitado** quando não há texto |
| Falha de rede / rate limit do edge-tts | Timeout de 10s na requisição + retry com backoff exponencial (1s, 2s, 4s — máx 3 tentativas). Após falha definitiva: dialog com mensagem clara e botão "Tentar novamente". |
| Arquivo corrompido / formato não suportado | Dialog: "Não foi possível ler este arquivo. Formatos suportados: TXT, PDF, DOCX, EPUB." |
| edge-tts falha em uma voz | Mensagem específica: "Voz X indisponível, tente outra" |
| Usuário clica Stop durante síntese | Task `asyncio` de síntese é cancelada **e** player atual é parado, sob proteção do `asyncio.Lock` do player (ver Concorrência) |
| Primeira execução sem internet | App abre, mas usa **voz padrão hardcoded** (ex: `pt-BR-FranciscaNeural`) — listagem dinâmica de vozes só funciona quando houver rede |
| Operações longas (livro inteiro) | Streaming progressivo evita espera inicial; indicador de progresso por chunk |

---

## Armazenamento

- **Pasta padrão**: `~/FizzyBee/` (criada na primeira execução)
  - `~/FizzyBee/history.json` — histórico de leituras (limitado a **50 entradas mais recentes**, FIFO; entradas antigas descartadas ao salvar)
  - `~/FizzyBee/config.json` — configurações do usuário (idioma padrão, voz padrão, etc.)
  - `~/FizzyBee/logs/` — logs do loguru com rotação diária e retenção de 7 dias
- **Áudios MP3 exportados**: usuário escolhe destino via diálogo do SO ao clicar em "Salvar"
- Toda persistência JSON é centralizada em `core/storage.py` (DRY)

---

## Concorrência

Todo o app usa **`asyncio`** (não `threading`), pelos motivos:

- **edge-tts é assíncrono nativo** (`async/await`) — usar threading só pra "esconder" o async cria complexidade desnecessária
- **Flet suporta asyncio** via `ft.app(target=main, ...)` com função `async`
- **just_playback** expõe API síncrona — usamos `loop.run_in_executor()` quando chamadas forem bloqueantes

**Regra prática:**
- I/O (edge-tts, leitura de arquivo grande) → `async`
- CPU/biblioteca síncrona pesada (extração de PDF longo) → `run_in_executor`
- UI nunca bloqueia a janela
- **Tasks de síntese são canceláveis** (`asyncio.Task.cancel()`) — Stop interrompe na hora

### Sincronização do player

Estado do player (`playing`, `paused`, `position`, fila de chunks) é protegido por **`asyncio.Lock`** em `audio_player.py`. Chamadas via `run_in_executor` adquirem o lock antes de mutar estado, evitando race entre Stop, seek, fim de chunk e síntese em paralelo do próximo chunk (streaming progressivo).

### Shutdown limpo

Handler de `SIGINT` (Ctrl+C) e evento `on_close` da janela Flet executam, **nesta ordem**:

1. Parar player atual
2. Salvar histórico em `history.json`
3. Cancelar todas as tasks pendentes (`asyncio.all_tasks()`)
4. Flush dos logs do loguru
5. Sair

---

## Segmentação de texto

Usamos **`pysbd`** (Python Sentence Boundary Disambiguation) para quebrar todo texto em frases — não há limite mágico de "texto curto":

- Todo texto passa pelo chunker — textos pequenos viram 1 chunk só (KISS: uma única regra)
- Lida com **abreviações** ("Sr.", "Dr.", "etc.") sem cortar errado
- Suporta múltiplos idiomas (pt, en, es...) — passamos o idioma escolhido
- **Limite inicial: ~3000 caracteres/chunk** — valor a calibrar empiricamente na Fase 2 (edge-tts não documenta limite oficial; ajustar conforme testes reais)
- Estratégia: junta frases consecutivas até chegar perto do limite, depois fecha o chunk

---

## Logging

`core/logger.py` configura o **loguru** uma única vez:

- **Detecção de modo**: se `sys.frozen` (PyInstaller) → produção (nível `WARNING`); senão → desenvolvimento (nível `INFO`). Variável de ambiente `FIZZYBEE_LOG_LEVEL` sobrescreve.
- Arquivo: `~/FizzyBee/logs/fizzy_bee.log` com rotação diária e retenção de 7 dias
- Formato: timestamp + nível + módulo + mensagem
- Demais módulos só importam `from loguru import logger` e usam — sem configuração espalhada

---

## Acessibilidade

- **Contraste WCAG AA** validado no dark mode (testar com ferramenta como `colour-contrast-checker`)
- **Atalhos de teclado completos** — ver Fase 5
- **Foco visual visível** em todos os controles interativos (default do Flet costuma cobrir, validar)
- **Labels semânticos** nos componentes Flet para leitores de tela (VoiceOver no macOS)

---

## Testes (validação)

Testes focados em `core/` usando `pytest`:

- `core/extractors/`: arquivos exemplo em `tests/fixtures/docs/` (TXT, PDF, DOCX, EPUB) → verificar extração correta
- `core/text_chunker.py`: garantir que `pysbd` divide corretamente respeitando abreviações e limite de caracteres
- `core/storage.py`: salvar/ler histórico e config sem perda (inclui defaults quando arquivo não existe, e limite FIFO de 50 entradas)
- `core/tts_engine.py`: usa MP3s pré-gerados em `tests/fixtures/audio/` para simular respostas do edge-tts (sem rede em CI). Teste com edge-tts real existe, mas marcado com `@pytest.mark.network` e excluído do CI por padrão.
- `core/audio_player.py`:
  - métodos puros (cálculo de progresso, formatação de tempo) → testes de unidade
  - estado mutável e lock (race conditions entre Stop/seek/fim-de-chunk) → testes de integração com `pytest-asyncio`
  - reprodução real → validação manual
- **UI**: validação manual

---

## Roadmap de fases

Implementação **incremental**, cada fase entregando algo funcional:

### Fase 1 — MVP funcional (núcleo do app)
- `core/logger.py` (loguru configurado)
- `core/storage.py` (config básica em JSON)
- `core/tts_engine.py` (síntese básica via edge-tts)
- `core/audio_player.py` (play/pause/stop com just_playback + `asyncio.Lock`)
- UI mínima Flet (asyncio): área de texto, dropdown de voz, botão play, salvar MP3
- **Validação empírica**: confirmar que MP3s do edge-tts têm parâmetros consistentes (concatenação binária funciona) e que PyInstaller embala bem o `just_playback`/`miniaudio`
- ✅ **Resultado: ouvir texto colado**

### Fase 2 — Importação de arquivos
- `core/extractors/` (TXT, PDF, DOCX, EPUB)
- `core/text_chunker.py` (pysbd; calibrar limite real do edge-tts)
- Botão "Abrir arquivo" + drag-and-drop (validar suporte do Flet em macOS; fallback para só diálogo se necessário)

### Fase 3 — Controles avançados de voz
- Filtro de idioma + lista completa de vozes (com voz padrão hardcoded como fallback offline)
- Sliders de velocidade e volume

### Fase 4 — Persistência e histórico
- Histórico de leituras em `core/storage.py` (FIFO de 50)
- Painel lateral (`side_panel.py`) com lista de histórico

### Fase 5 — Player avançado + atalhos
- Barra de progresso com seek
- Highlight de palavra sendo lida (cada chunk guarda `offset_ms` acumulado; word boundaries do edge-tts são relativos ao chunk e somados a esse offset para obter posição absoluta; ressincronizar a cada transição de chunk com a posição real do player evita deriva)
- **Atalhos de teclado**: espaço (play/pause), setas (seek ±5s), Esc (stop)

### Fase 6 — Polimento visual
- Tema dark mode refinado
- Ícones e tipografia caprichada

### Fase 7 — Empacotamento macOS (uso pessoal)
- `packaging/fizzy_bee.spec` (PyInstaller, build universal arm64+x86_64)
- `packaging/build_dmg.sh` (gera `.app` + `.dmg` com `create-dmg`)
- Bundle esperado: 80–200MB (Flet + Python + edge-tts)
- **`.dmg` não-assinado**: ao abrir pela 1ª vez, usuário precisa autorizar em `Ajustes → Privacidade e Segurança` (decisão consciente — sem Apple Developer ID)
- Documentar passo de "primeira execução" no README
- ✅ **Resultado: instalador `.dmg` para uso pessoal/restrito**

### Fase 8 (futura/opcional) — Presets de voz
Adiada até validar uso real da Fase 4. Presets seriam combinações nomeadas de (voz + velocidade), salvas em `presets.json`, exibidas como segunda aba do painel lateral.

---

## Próximos passos

1. ✅ Plano aprovado e salvo
2. ⏭️ Criar `requirements.txt` com dependências
3. ⏭️ Criar estrutura de pastas
4. ⏭️ Implementar **Fase 1 (MVP)** — síntese básica + player + UI mínima
5. ⏭️ Iterar pelas fases seguintes
