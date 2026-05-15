# 🐝 Fizzy Bee

> Leitor de texto desktop para macOS com vozes neurais de alta qualidade (edge-tts).

Aplicativo Python + Flet que sintetiza texto em fala usando as vozes neurais da Microsoft Edge (gratuitas via `edge-tts`). Suporta TXT, PDF, DOCX e EPUB.

## Status

🚧 **Em desenvolvimento — Fase 2 (importação de arquivos)**. Veja [`PLANO.md`](PLANO.md) para o roadmap completo.

### Limitações conhecidas

- **Drag-and-drop de arquivos do SO está desabilitado.** Limitação arquitetural do Flet: o app Python e a janela nativa (`flet-desktop-full`) rodam em processos separados, comunicando-se via UDS. A `NSWindow` que aceitaria o drop está no processo filho — fora do alcance do nosso processo Python (PyObjC inclusive). Para abrir arquivos, use o botão **"📁 Abrir arquivo"**.

## Requisitos

- macOS (Apple Silicon ou Intel)
- Python 3.11 ou superior
- Conexão com a internet (o edge-tts depende de servidores da Microsoft)

## Instalação (modo desenvolvimento)

```bash
# Clone o repositório
git clone https://github.com/bruno-lindquist/text_to_speech.git
cd text_to_speech

# Crie e ative um ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

## Como rodar

```bash
python main.py
```

## Como rodar os testes

```bash
pytest
```

## Estrutura do projeto

Veja a seção **Arquitetura** do [`PLANO.md`](PLANO.md) para o layout completo. Resumo:

- `core/` — lógica de negócio em Python puro (sem GUI)
- `ui/` — camada visual em Flet
- `tests/` — testes unitários e de integração
- `packaging/` — scripts de empacotamento `.dmg` para macOS

## Licença

Pessoal/educacional — sem licença pública definida ainda.
