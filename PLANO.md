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

Implementação **incremental**. Cada fase entrega algo funcional e tem **checkpoints de validação**. Só avançamos para a próxima fase quando **todos** os checkpoints da fase atual estiverem marcados com `[x]`.

---

### Fase 0 — Preparação do ambiente

**Objetivo**: deixar o projeto pronto para receber código.

**O que será feito:**
1. Criar `requirements.txt` com as dependências congeladas: `flet`, `edge-tts`, `pypdf`, `python-docx`, `ebooklib`, `pysbd`, `just_playback`, `loguru`, `pytest`, `pytest-asyncio`, `pyinstaller`.
2. Criar a estrutura completa de pastas conforme a seção **Arquitetura** (`core/`, `core/extractors/`, `ui/`, `ui/components/`, `tests/fixtures/docs/`, `tests/fixtures/audio/`, `packaging/`).
3. Criar `README.md` mínimo (nome do projeto + como instalar e rodar).
4. Criar arquivos `__init__.py` vazios onde forem necessários para reconhecer pacotes Python.
5. Configurar `venv` local (`python -m venv .venv`) e instalar dependências (`pip install -r requirements.txt`).

**Checkpoints:**
- [ ] `requirements.txt` existe e instala sem erros em ambiente limpo
- [ ] Estrutura de pastas confere com o diagrama da seção Arquitetura
- [ ] `python -c "import flet, edge_tts, pypdf, docx, ebooklib, pysbd, just_playback, loguru"` roda sem erro
- [ ] `README.md` tem instruções básicas de instalação

---

### Fase 1 — MVP funcional (núcleo do app)

**Objetivo**: conseguir colar um texto na janela, escolher uma voz fixa e ouvir o áudio dentro do app.

**O que será feito:**
1. **`core/logger.py`**: configura o loguru uma única vez (detecta `sys.frozen` pra escolher INFO vs WARNING; cria pasta `~/FizzyBee/logs/` se não existir; rotação diária).
2. **`core/storage.py`**: lê/escreve `~/FizzyBee/config.json` (apenas `default_voice` e `default_rate` no MVP); retorna defaults se o arquivo não existir.
3. **`core/tts_engine.py`**: função `async synthesize(text, voice, rate) -> bytes` que chama `edge-tts` e retorna o MP3 completo do texto curto (sem chunking ainda).
4. **`core/audio_player.py`**: classe `AudioPlayer` com `play(mp3_bytes)`, `pause()`, `stop()`, estado protegido por `asyncio.Lock`. Internamente usa `just_playback` em `run_in_executor`.
5. **UI mínima Flet (`ui/app.py`)**: janela com área de texto, dropdown com 3 vozes pt-BR hardcoded (Francisca, Antonio, Brenda), botão "▶ Reproduzir", botão "⏹ Parar", botão "💾 Salvar MP3".
6. **`main.py`**: ponto de entrada que inicializa logger e roda o Flet app em modo asyncio.
7. **Validação empírica** (parte essencial da fase, não pode ser pulada):
   - Sintetizar o mesmo texto 3 vezes e checar com `ffprobe` (ou módulo `mutagen`) se sample rate e canais batem entre as 3 amostras → valida hipótese da concatenação binária
   - Fazer PyInstaller experimental do MVP e abrir o `.app` em macOS limpo → confirma que `just_playback`/`miniaudio` empacotam

**Checkpoints:**
- [ ] Cola-se texto, clica play, ouve o áudio com a voz selecionada
- [ ] Botão Stop interrompe a reprodução na hora
- [ ] Botão "Salvar MP3" gera arquivo que toca corretamente em outro player do SO
- [ ] Logs aparecem em `~/FizzyBee/logs/fizzy_bee.log`
- [ ] **Validação empírica 1**: três síntese consecutivas têm mesmo sample rate/canais (anotar no commit)
- [ ] **Validação empírica 2**: PyInstaller gera `.app` funcional (sem testes de UI extensivos, só confirma que abre e toca)
- [ ] `pytest` roda os testes unitários de `tts_engine` (com mock) e `audio_player` (métodos puros) sem falhas

---

### Fase 2 — Importação de arquivos

**Objetivo**: abrir arquivos TXT/PDF/DOCX/EPUB e ouvir textos longos (com chunking).

**O que será feito:**
1. **`core/extractors/__init__.py`**: função `extract(path: Path) -> str` que escolhe o extractor certo pela extensão e devolve texto puro.
2. **`core/extractors/txt.py`**: lê com `pathlib` respeitando encoding (UTF-8 com fallback para latin-1).
3. **`core/extractors/pdf.py`**: usa `pypdf` para concatenar texto de todas as páginas.
4. **`core/extractors/docx.py`**: usa `python-docx` para extrair parágrafos.
5. **`core/extractors/epub.py`**: usa `ebooklib` + `BeautifulSoup` para extrair texto de cada item HTML do EPUB.
6. **`core/text_chunker.py`**: função `chunk(text, language, max_chars=3000) -> list[str]` usando `pysbd`. Junta frases até chegar perto do limite, fecha o chunk, abre o próximo.
7. **`tts_engine.py`** ganha modo "sintetiza por chunks": função `async synthesize_chunks(chunks: list[str], voice, rate) -> AsyncIterator[bytes]` que retorna os MP3s de cada chunk (ainda **sem** streaming progressivo — Fase 1.5 do player junta tudo em memória antes de tocar).
8. **`audio_player.py`** ganha capacidade de tocar uma fila de MP3s em sequência.
9. **UI**: botão "📁 Abrir arquivo" com diálogo do SO. Tentar implementar drag-and-drop e validar; se não funcionar bem no Flet em macOS, deixar só o botão.
10. **Calibração empírica do limite de chunk**: testar com texto de 5000, 10000, 20000 chars; medir tempo de resposta do edge-tts; ajustar `max_chars` se preciso.

**Checkpoints:**
- [ ] Abrir um `.txt` longo (>10k chars) e ouvir do início ao fim sem erro
- [ ] Abrir um `.pdf` de pelo menos 3 páginas e ouvir
- [ ] Abrir um `.docx` simples e ouvir
- [ ] Abrir um `.epub` (qualquer livro pequeno em domínio público) e ouvir
- [ ] `pysbd` divide texto com abreviações ("Sr. Silva foi ao Dr. Mendes.") em **uma única frase**, não duas
- [ ] Drag-and-drop funciona OU está documentado como desabilitado no README
- [ ] Limite ideal de `max_chars` calibrado e anotado no `text_chunker.py`
- [ ] Testes de `extractors/` passam com fixtures em `tests/fixtures/docs/`

---

### Fase 3 — Controles avançados de voz

**Objetivo**: deixar o usuário escolher qualquer voz do edge-tts e ajustar velocidade/volume.

**O que será feito:**
1. **`tts_engine.py`** ganha função `async list_voices() -> list[Voice]` que chama `edge_tts.list_voices()` e cacheia o resultado em memória durante a sessão.
2. **Fallback offline**: voz padrão hardcoded (`pt-BR-FranciscaNeural`) usada se `list_voices()` falhar (sem internet na primeira execução).
3. **`ui/components/voice_controls.py`**: componente Flet com dois dropdowns (idioma → voz) + dois sliders (velocidade -50%/+100%, volume 0-100%).
4. **Filtro de idioma**: extrai locales únicos da lista de vozes (`pt-BR`, `en-US`, `es-ES`, etc.), ordena alfabeticamente, mostra no primeiro dropdown.
5. **Filtro de voz**: ao escolher idioma, segundo dropdown popula com as vozes daquele locale.
6. **Aplicar parâmetros**: rate e volume vão como `rate=+10%`, `volume=-5%` na chamada do `edge_tts.Communicate` (formato exigido pela biblioteca).
7. **Persistência**: voz, idioma, rate e volume escolhidos são salvos em `config.json` ao mudar, e restaurados na próxima abertura.

**Checkpoints:**
- [ ] Lista completa de vozes carrega (>30 vozes em pt-BR/en-US disponíveis)
- [ ] Trocar idioma filtra as vozes corretamente
- [ ] Slider de velocidade muda o ritmo (testar -25%, 0%, +25%, +50%)
- [ ] Slider de volume muda o nível do áudio audivelmente
- [ ] Sem internet na primeira execução, app abre e usa Francisca como fallback (validar matando rede temporariamente)
- [ ] Preferências persistem entre reinicializações do app

---

### Fase 4 — Persistência e histórico

**Objetivo**: lembrar das últimas leituras e deixar o usuário voltar nelas com um clique.

**O que será feito:**
1. **`core/storage.py`** ganha `save_history_entry(text, voice, timestamp)` e `load_history() -> list[Entry]`. Limite **FIFO de 50 entradas** — a entrada mais antiga é descartada quando uma nova passa do limite.
2. **Cada entrada** guarda: snippet do texto (primeiros 80 chars), texto completo, voz usada, rate, timestamp ISO 8601.
3. **`ui/components/side_panel.py`**: painel lateral à esquerda com lista de cartões (snippet + data + voz). Clicar reabre o texto e os controles na janela principal.
4. **Salvamento automático**: cada vez que o play é acionado, a entrada é adicionada ao histórico (após começar a tocar, não antes).
5. **Botão "🗑 Limpar histórico"** no rodapé do painel, com diálogo de confirmação.
6. **Shutdown limpo**: histórico é salvo na sequência definida em **Concorrência → Shutdown limpo**.

**Checkpoints:**
- [ ] Após 3 leituras, o painel mostra 3 cartões na ordem do mais recente para o mais antigo
- [ ] Clicar num cartão reabre o texto na área principal com a mesma voz/rate
- [ ] Histórico para de crescer ao chegar em 50 entradas (FIFO funcionando)
- [ ] Fechar e reabrir o app preserva o histórico
- [ ] "Limpar histórico" zera a lista após confirmação
- [ ] Teste de `storage.py` valida limite FIFO e defaults

---

### Fase 5 — Player avançado + atalhos

**Objetivo**: dar ao player capacidades profissionais — barra de progresso navegável, palavra destacada e atalhos de teclado.

**O que será feito:**
1. **Streaming progressivo** (substitui o "tocar fila inteira" da Fase 2): chunk N+1 começa a sintetizar assim que chunk N inicia a reprodução. Implementação com `asyncio.Queue` entre `tts_engine` e `audio_player`.
2. **Barra de progresso (`ui/components/player_controls.py`)**: mostra tempo decorrido / tempo total da fila completa de chunks (soma das durações conhecidas + estimativa para chunks ainda não sintetizados).
3. **Seek**: clicar na barra calcula em qual chunk + offset cair, e pula. Pode exigir resintetizar chunks à frente se ainda não estiverem em memória.
4. **Highlight de palavra**: cada chunk recebe `offset_ms` acumulado. Os `WordBoundary` events do edge-tts (relativos ao chunk) são somados ao offset para virar timestamp absoluto. Um `Timer` Flet roda em ~50ms tickando e destacando a palavra atual em `text_area.py`. Ressincronizar com posição real do player a cada transição de chunk pra evitar deriva.
5. **Atalhos de teclado** (via `on_keyboard_event` do Flet):
   - **Espaço**: play / pause
   - **Esc**: stop
   - **← →**: seek ± 5s
   - **↑ ↓**: volume ± 5%

**Checkpoints:**
- [ ] Texto longo começa a tocar antes de toda a síntese terminar (latência inicial < 3s)
- [ ] Barra de progresso avança suavemente, com tempo correto no fim de cada chunk
- [ ] Clicar na barra pula pra posição certa (testar pulando entre chunks)
- [ ] Palavra atual fica destacada e acompanha o áudio sem deriva visível (validar com texto de 30s)
- [ ] Todos os 5 atalhos de teclado funcionam (com janela em foco)
- [ ] Race entre Stop + síntese paralela não trava o app (executar Stop 10x rapidamente em sequência durante uma leitura)
- [ ] Teste de integração com `pytest-asyncio` cobre o `asyncio.Lock` do player

---

### Fase 6 — Polimento visual

**Objetivo**: deixar o app com cara de produto, não de protótipo.

**O que será feito:**
1. **`ui/theme.py`**: definir paleta completa (background níveis 1/2/3, accent âmbar `#FFB300`, texto primário/secundário, vermelhos/verdes para erro/sucesso).
2. **Tipografia**: fonte principal (Inter ou Roboto), tamanhos consistentes para títulos, corpo, controles.
3. **Ícones**: usar `Material Icons` do Flet (`PLAY_ARROW`, `PAUSE`, `STOP`, `FOLDER_OPEN`, `SAVE`, `DELETE`).
4. **Logo da abelha 🐝**: criar ícone PNG simples (256x256) para o app + ícone do `.dmg` da Fase 7.
5. **Layout responsivo**: a janela tem tamanho mínimo (ex: 900x600) e os painéis se adaptam ao redimensionar.
6. **Estados visuais**: hover/pressed em botões, cor diferente para botão Play ativo, loading spinners durante síntese.
7. **Validação de Acessibilidade** (ver seção dedicada):
   - Rodar `colour-contrast-checker` ou similar para validar contraste WCAG AA
   - Testar com VoiceOver ativo

**Checkpoints:**
- [ ] Paleta de cores consistente em todos os componentes
- [ ] Ícone do app visível no Dock do macOS (após Fase 7)
- [ ] Botões reagem visualmente a hover/click
- [ ] Spinner aparece durante síntese (não fica trancado parecendo travado)
- [ ] Contraste WCAG AA validado em texto sobre todos os fundos
- [ ] VoiceOver lê os labels dos botões corretamente

---

### Fase 7 — Empacotamento macOS (uso pessoal)

**Objetivo**: gerar um `.dmg` instalável.

**O que será feito:**
1. **`packaging/fizzy_bee.spec`**: arquivo de configuração do PyInstaller — entrypoint `main.py`, ícone, hidden imports para `just_playback`/`miniaudio`/`edge_tts`, builds universal arm64+x86_64.
2. **`packaging/build_dmg.sh`**: script que roda `pyinstaller`, depois `create-dmg` para gerar `Fizzy Bee.dmg` com janela customizada (ícone do app à esquerda, atalho para `/Applications` à direita).
3. **Documentação no `README.md`**: passo de primeira execução (autorizar em "Privacidade e Segurança" porque o `.dmg` não é assinado).
4. **Teste em macOS limpo**: copiar o `.dmg` pra outra máquina (ou VM) e validar fluxo completo do zero.

**Checkpoints:**
- [ ] `bash packaging/build_dmg.sh` gera `Fizzy Bee.dmg` sem erros
- [ ] O `.dmg` abre uma janela com o ícone e o atalho de Aplicações
- [ ] Arrastar pra Aplicações instala normalmente
- [ ] Na primeira execução, macOS pede autorização em "Privacidade e Segurança" (esperado)
- [ ] Após autorizar, app abre e funciona em macOS limpo (sem Python instalado pelo usuário)
- [ ] Bundle final dentro de 80–250MB

---

### Fase 8 (futura/opcional) — Presets de voz

Adiada até validar uso real da Fase 4. Presets seriam combinações nomeadas de (voz + velocidade), salvas em `presets.json`, exibidas como segunda aba do painel lateral.

**Checkpoints (quando/se for implementada):**
- [ ] Criar preset a partir das configurações atuais
- [ ] Aplicar preset com 1 clique restaura voz + rate
- [ ] Renomear e excluir preset
- [ ] Persistência em `~/FizzyBee/presets.json`

---

## Regras de execução

- **Avanço sequencial**: só começar a Fase N+1 depois que **todos** os checkpoints da Fase N estiverem marcados com `[x]`.
- **Marcação dos checkpoints**: ao validar um checkpoint, alterar `[ ]` para `[x]` neste arquivo e fazer commit.
- **Falha em checkpoint**: se algum não puder ser validado, **não pular** — corrigir o problema antes de seguir. Se for impossível corrigir, registrar o motivo neste arquivo e decidir se a fase precisa ser revisada.
- **Commits por fase**: ao fechar uma fase com todos os checkpoints `[x]`, fazer um commit com mensagem `feat(faseN): descrição curta` (ou `chore(fase0): ...` para a preparação).

---

## Próximos passos

1. ✅ Plano aprovado e salvo
2. ⏭️ Iniciar **Fase 0 (Preparação do ambiente)**
3. ⏭️ Iterar pelas fases seguintes, marcando checkpoints conforme validados
