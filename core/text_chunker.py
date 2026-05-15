# core/text_chunker.py
# Divide texto em chunks respeitando frases (pysbd) e um limite de caracteres.
# Todo texto passa pelo chunker — textos curtos viram 1 chunk só.

import pysbd
from loguru import logger

# Limite calibrado empiricamente na Fase 2 (sample_long.txt, 11k chars, pt-BR FranciscaNeural):
# - 3000 chars/chunk: latência ~12-18s por chunk no edge-tts → estourava timeout de 10s
# - 2000 chars/chunk: latência ~6-10s por chunk → seguro com timeout de 20s
# Trade-off: chunks menores = mais requisições ao edge-tts, mas latência inicial menor
# (importante para o streaming progressivo da Fase 5).
DEFAULT_MAX_CHARS = 2000

# pysbd não suporta 'pt' nativamente. Italiano é o melhor fallback para PT
# porque reconhece abreviações latinas como "Sr.", "Dr.", "Sra." sem cortar.
# (Testado: 'en' e 'es' quebram em "Sr. " + "Silva...", 'it' mantém "Sr. Silva...")
_PYSBD_LANG_MAP = {
    "pt": "it",
    "pt-BR": "it",
    "pt-PT": "it",
}


def chunk(text: str, language: str = "pt", max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    # Divide texto em chunks de até ~max_chars cada.
    # Estratégia: pysbd quebra em frases respeitando abreviações; juntamos
    # frases consecutivas até chegar perto do limite, então fechamos o chunk.
    #
    # Frase única maior que max_chars passa inteira (não corta no meio).
    if not text or not text.strip():
        return []

    pysbd_lang = _PYSBD_LANG_MAP.get(language, language)
    try:
        seg = pysbd.Segmenter(language=pysbd_lang, clean=False)
    except ValueError:
        # Idioma desconhecido pelo pysbd — fallback para inglês
        logger.warning(f"pysbd não suporta '{language}', usando 'en' como fallback")
        seg = pysbd.Segmenter(language="en", clean=False)
    sentences = seg.segment(text)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence_len = len(sentence)

        # Se a frase sozinha já estoura o limite, fecha o que tem e manda ela inteira
        if sentence_len > max_chars:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            chunks.append(sentence)
            continue

        # Se adicionar essa frase passar do limite, fecha o chunk atual primeiro
        if current_len + sentence_len + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = sentence_len
        else:
            current.append(sentence)
            current_len += sentence_len + 1  # +1 do espaço entre frases

    if current:
        chunks.append(" ".join(current))

    logger.info(f"Texto de {len(text)} chars dividido em {len(chunks)} chunks")
    return chunks
