# core/extractors/__init__.py
# Função pública extract(path) escolhe o extractor certo pela extensão.
# Adicionar novo formato = criar novo arquivo no pacote, sem mexer aqui (Open/Closed).

from pathlib import Path

from loguru import logger

from . import docx as docx_extractor
from . import epub as epub_extractor
from . import pdf as pdf_extractor
from . import txt as txt_extractor


class ExtractorError(Exception):
    # Erro genérico de extração — UI captura e mostra dialog.
    pass


class UnsupportedFormatError(ExtractorError):
    pass


# Mapeia extensão -> função extractor
_EXTRACTORS = {
    ".txt": txt_extractor.extract,
    ".pdf": pdf_extractor.extract,
    ".docx": docx_extractor.extract,
    ".epub": epub_extractor.extract,
}

SUPPORTED_EXTENSIONS = tuple(_EXTRACTORS.keys())


def extract(path: Path | str) -> str:
    # Lê o arquivo e devolve texto puro pronto para o chunker.
    # Levanta UnsupportedFormatError se a extensão não for conhecida.
    # Levanta ExtractorError se o arquivo for inválido/corrompido.
    path = Path(path)
    if not path.exists():
        raise ExtractorError(f"Arquivo não encontrado: {path}")

    ext = path.suffix.lower()
    extractor_fn = _EXTRACTORS.get(ext)
    if extractor_fn is None:
        raise UnsupportedFormatError(
            f"Formato não suportado: {ext}. "
            f"Suportados: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    logger.info(f"Extraindo texto de {path.name} ({ext})")
    try:
        text = extractor_fn(path)
    except ExtractorError:
        raise
    except Exception as exc:
        # Qualquer erro inesperado da lib subjacente vira ExtractorError
        logger.error(f"Falha ao extrair {path.name}: {exc}")
        raise ExtractorError(f"Não foi possível ler {path.name}: {exc}") from exc

    logger.info(f"Extraídos {len(text)} caracteres de {path.name}")
    return text
