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

**Fizzy Bee** é um leitor de texto desktop (Python + Flet) que usa **edge-tts** para gerar narração com alta qualidade. O usuário cola texto ou abre arquivos (TXT/PDF/DOCX/EPUB), escolhe voz e parâmetros, ouve dentro do app com acompanhamento visual (texto destacado conforme é lido) e pode salvar como MP3.

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
| Player de áudio | **just_playback** | Player MP3 self-contained com seek (sem dependência externa) |
| Logging | **loguru** | Logs estruturados e simples |
| Concorrência | **asyncio** (nativo) | Alinhado com edge-tts e Flet |
| Empacotamento (macOS) | **PyInstaller** + **create-dmg** | Gera `.app` e instalador `.dmg` |

> **Por que `just_playback`?** Foi escolhido sobre `python-vlc` porque é **self-contained** (não exige VLC instalado no sistema), simplificando muito o empacotamento `.dmg` para macOS. Tem seek nativo e suporta MP3 diretamente.

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
- **Não tem cache de áudios sintetizados** — cada reprodução gera nova síntese
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
│   ├── storage.py             # Persistência JSON (histórico, presets, config)
│   └── logger.py              # Configuração centralizada do loguru
├── ui/                        # Camada visual
│   ├── app.py                 # Estrutura principal da janela
│   ├── components/
│   │   ├── text_area.py       # Área de texto com highlight
│   │   ├── voice_controls.py  # Dropdowns e sliders de voz
│   │   ├── player_controls.py # Play/pause/seek/salvar
│   │   └── side_panel.py      # Painel lateral com abas (Histórico / Presets)
│   └── theme.py               # Cores e estilos do dark mode
├── tests/                     # Testes (focados em core/)
│   └── fixtures/              # Arquivos de exemplo (TXT, PDF, DOCX, EPUB)
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
- Arrastar arquivo (drag-and-drop) direto na janela
- Formatos suportados: **TXT, PDF, DOCX, EPUB**

### Controles de voz

- **Filtro por idioma** (dropdown 1): pt-BR, en-US, es-ES, etc.
- **Escolha de voz** (dropdown 2): lista filtrada pelo idioma (ex: Francisca, Antonio, Brenda...)
- **Velocidade (rate)**: slider de -50% a +100%
- **Volume**: slider de ajuste

> **Pitch fora do MVP**: vozes neurais do edge-tts frequentemente ignoram ou distorcem o ajuste de pitch. Avaliar inclusão depois, com base na experiência real.

### Reprodução de áudio

- Player embutido com **play / pause / parar**
- **Stop cancela síntese em andamento** (não só o áudio que está tocando)
- **Barra de progresso com seek** (clicar para pular trecho)
- **Highlight de palavra sendo lida** (usando word boundaries do edge-tts)
- **Salvar como MP3** — concatena os chunks em um único arquivo (concatenação binária de MP3, suportada nativamente pelo formato)

### Funcionalidades extras

- **Histórico de leituras**: lista de textos lidos recentemente, com reabrir/reouvir
- **Presets de voz**: salvar combinações (voz + velocidade) nomeadas (ex: "Estudo lento", "Notícia rápida")
- **Divisão automática de texto em chunks**: todo texto passa pelo chunker (textos curtos viram 1 chunk só), sem regra mágica de tamanho mínimo

---

## Fluxo de uso

1. **Abre o app** — janela dark mode com:
   - Painel lateral esquerdo: abas Histórico / Presets
   - Centro: área de texto grande
   - Painel direito: controles de voz
   - Rodapé: player + botão "Salvar MP3"

2. **Insere texto** (colar, abrir arquivo, ou arrastar)

3. **Configura voz** (filtro idioma → voz → sliders) ou aplica preset

4. **Clica em ▶ Reproduzir**:
   - App divide texto em chunks
   - edge-tts sintetiza
   - Player toca e destaca palavras sendo lidas

5. **Salva MP3** (opcional) — escolhe destino no diálogo, app concatena chunks

6. **Sai do app** — histórico é salvo automaticamente

---

## Tratamento de erros e casos especiais

| Caso | Comportamento |
|---|---|
| Texto vazio ao clicar play | Botão **desabilitado** quando não há texto |
| Sem internet | Mensagem clara: "Sem conexão — edge-tts precisa de internet" |
| Texto longo | `text_chunker.py` divide em frases (pysbd), sintetiza em sequência, junta no player |
| Arquivo corrompido / formato não suportado | Dialog: "Não foi possível ler este arquivo. Formatos suportados: TXT, PDF, DOCX, EPUB." |
| edge-tts falha em uma voz | Mensagem específica: "Voz X indisponível, tente outra" |
| Usuário clica Stop durante síntese | Task `asyncio` é cancelada (não fica gerando em background); áudio atual para |
| Operações longas (livro inteiro) | Rodam em tarefas `asyncio` com indicador de progresso, **sem travar a janela** |

---

## Armazenamento

- **Pasta padrão**: `~/FizzyBee/` (criada na primeira execução)
  - `~/FizzyBee/history.json` — histórico de leituras
  - `~/FizzyBee/presets.json` — presets salvos
  - `~/FizzyBee/config.json` — configurações do usuário (idioma padrão, voz padrão, etc.)
  - `~/FizzyBee/logs/` — logs do loguru com rotação diária
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

---

## Segmentação de texto

Usamos **`pysbd`** (Python Sentence Boundary Disambiguation) para quebrar todo texto em frases — não há limite mágico de "texto curto":

- Todo texto passa pelo chunker — textos pequenos viram 1 chunk só (KISS: uma única regra)
- Lida com **abreviações** ("Sr.", "Dr.", "etc.") sem cortar errado
- Suporta múltiplos idiomas (pt, en, es...) — passamos o idioma escolhido
- Limite alvo de chunk: **~3000 caracteres por requisição** ao edge-tts (margem de segurança)
- Estratégia: junta frases consecutivas até chegar perto do limite, depois fecha o chunk

---

## Logging

`core/logger.py` configura o **loguru** uma única vez:

- Console: nível `INFO` em desenvolvimento, `WARNING` em produção
- Arquivo: `~/FizzyBee/logs/fizzy_bee.log` com rotação diária e retenção de 7 dias
- Formato: timestamp + nível + módulo + mensagem
- Demais módulos só importam `from loguru import logger` e usam — sem configuração espalhada

---

## Testes (validação)

Testes focados em `core/` usando `pytest`:

- `core/extractors/`: arquivos exemplo em `tests/fixtures/` (TXT, PDF, DOCX, EPUB) → verificar extração correta
- `core/text_chunker.py`: garantir que `pysbd` divide corretamente respeitando abreviações e limite de caracteres
- `core/storage.py`: salvar/ler histórico, presets e config sem perda (inclui defaults quando arquivo não existe)
- `core/tts_engine.py`: com **mock do edge-tts** (não bate na rede em CI) + 1 teste manual real
- `core/audio_player.py`: métodos puros (cálculo de progresso, formatação de tempo) — player real é validação manual
- **UI**: validação manual

---

## Roadmap de fases

Implementação **incremental**, cada fase entregando algo funcional:

### Fase 1 — MVP funcional (núcleo do app)
- `core/logger.py` (loguru configurado)
- `core/storage.py` (config básica em JSON)
- `core/tts_engine.py` (síntese básica via edge-tts)
- `core/audio_player.py` (play/pause/stop com just_playback)
- UI mínima Flet (asyncio): área de texto, dropdown de voz, botão play, salvar MP3
- ✅ **Resultado: ouvir texto colado**

### Fase 2 — Importação de arquivos
- `core/extractors/` (TXT, PDF, DOCX, EPUB)
- `core/text_chunker.py` (pysbd + limite de ~3000 chars)
- Botão "Abrir arquivo" + drag-and-drop

### Fase 3 — Controles avançados de voz
- Filtro de idioma + lista completa de vozes
- Sliders de velocidade e volume

### Fase 4 — Persistência e UX
- Histórico de leituras em `core/storage.py`
- Painel lateral (`side_panel.py`) com abas Histórico / Presets
- Sistema de presets nomeados

### Fase 5 — Player avançado + atalhos
- Barra de progresso com seek
- Highlight de palavra sendo lida (word boundaries do edge-tts, com offset entre chunks)
- **Atalhos de teclado**: espaço (play/pause), setas (seek ±5s), Esc (stop)

### Fase 6 — Polimento visual
- Tema dark mode refinado
- Ícones e tipografia caprichada

### Fase 7 — Empacotamento macOS
- `packaging/fizzy_bee.spec` (PyInstaller)
- `packaging/build_dmg.sh` (gera `.app` + `.dmg` com `create-dmg`)
- Ícone do app, assinatura (opcional), testes em macOS limpo
- ✅ **Resultado: instalador `.dmg` distribuível**

---

## Próximos passos

1. ✅ Plano aprovado e salvo
2. ⏭️ Criar `requirements.txt` com dependências
3. ⏭️ Criar estrutura de pastas
4. ⏭️ Implementar **Fase 1 (MVP)** — síntese básica + player + UI mínima
5. ⏭️ Iterar pelas fases seguintes
