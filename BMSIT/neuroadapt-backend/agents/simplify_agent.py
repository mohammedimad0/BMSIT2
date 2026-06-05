"""
Simplification Agent: Use Ollama to run Qwen2.5-1.5B-Instruct locally.

Ollama is a simple, reliable local LLM server that runs on localhost:11434.

Primary strategy: Call Ollama API to simplify paragraphs.
Fallback strategy: Pass paragraphs through unchanged if Ollama unavailable.

No inter-agent imports. All exceptions caught and logged locally.
"""

import logging
import os
import requests
from typing import Optional
from models import PipelineState

logger = logging.getLogger(__name__)

# Ollama API endpoint (default localhost:11434)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')

SYSTEM_PROMPT = """You are a reading assistant for dyslexic school students in India.
Rewrite the given text following ALL these rules:
1. Use only short sentences. Maximum 12 words per sentence.
2. Use simple, common English words. Replace technical jargon with plain equivalents but KEEP subject-specific terms (e.g. photosynthesis, mitosis) — just define them.
3. Use active voice. Never passive voice.
4. One idea per sentence.
5. Do NOT add new information. Do NOT remove key facts.
6. Do NOT use bullet points or lists. Write in plain sentences only.
7. Output ONLY the rewritten text. No preamble, no explanation."""


def _check_ollama_available() -> bool:
    """
    Check if Ollama server is running and model is available.
    """
    try:
        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=2
        )
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"[AGENT:simplify] Ollama not available: {str(e)}")
        return False


def _simplify_paragraph(paragraph: str, wpm: Optional[int] = None, profile: Optional[str] = None, temperature: float = 0.5) -> str:
    """
    Simplify a single paragraph using Ollama API.
    
    Args:
        paragraph: Text to simplify
        wpm: Optional reading speed in words per minute
        profile: Optional student profile string
        temperature: Model temperature (0.0-1.0)
    
    Returns:
        Simplified text or original if fails
    """
    if not paragraph.strip():
        return paragraph
    
    system_prompt = SYSTEM_PROMPT
    custom_rules = []
    
    if profile:
        profile_lower = profile.lower()
        if "adhd" in profile_lower:
            custom_rules.append("Break content into very small, action-oriented segments with vivid, engaging examples.")
        elif "dyslexia" in profile_lower or "dyslexic" in profile_lower:
            custom_rules.append("Use direct, clear sentence structures, avoiding passive voice and complex clauses.")
        elif "autism" in profile_lower or "autistic" in profile_lower:
            custom_rules.append("Use logical progressions, highly literal explanations, and avoid idioms, metaphors, or ambiguous language.")
            
    if wpm is not None and wpm > 0:
        if wpm < 120:
            system_prompt = system_prompt.replace("Maximum 12 words per sentence.", "Maximum 8 words per sentence. Use extremely basic, simplified vocabulary.")
        elif wpm < 180:
            system_prompt = system_prompt.replace("Maximum 12 words per sentence.", "Maximum 10 words per sentence.")
            
    if custom_rules:
        system_prompt += "\n" + "\n".join(f"{i+8}. {rule}" for i, rule in enumerate(custom_rules))
    
    try:
        prompt = f"{system_prompt}\n\nText to rewrite:\n{paragraph}\n\nRewritten text:"
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
            },
            timeout=60
        )
        
        if response.status_code != 200:
            logger.warning(f"[AGENT:simplify] Ollama error: {response.status_code}")
            return paragraph
        
        output_text = response.json().get('response', '').strip()
        
        # Validate: non-empty and not too long (< 3x input)
        if output_text and len(output_text) < len(paragraph) * 3:
            return output_text
        
        logger.warning(
            f"[AGENT:simplify] Output validation failed, retrying with lower temp"
        )
        
        # Retry with lower temperature
        if temperature > 0.2:
            return _simplify_paragraph(paragraph, wpm=wpm, profile=profile, temperature=temperature - 0.1)
        
        return paragraph
    
    except requests.Timeout:
        logger.error("[AGENT:simplify] Ollama request timeout")
        return paragraph
    except Exception as e:
        logger.error(f"[AGENT:simplify] Inference failed: {str(e)}")
        return paragraph


def _estimate_tokens(text: str) -> int:
    """
    Rough token estimation: ~4 chars per token for English.
    """
    return len(text) // 4 + 1


def _chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """
    Split text into chunks on sentence boundaries to avoid context limits.
    """
    if not text or len(text) <= max_chars:
        return [text]
    
    sentences = text.split('. ')
    chunks = []
    current_chunk = []
    current_len = 0
    
    for sentence in sentences:
        sentence_len = len(sentence)
        
        if current_len + sentence_len > max_chars and current_chunk:
            # Start new chunk
            chunks.append('. '.join(current_chunk) + '.')
            current_chunk = [sentence]
            current_len = sentence_len
        else:
            current_chunk.append(sentence)
            current_len += sentence_len + 2  # +2 for '. '
    
    if current_chunk:
        chunks.append('. '.join(current_chunk))
    
    return chunks


def run(state: PipelineState) -> PipelineState:
    """
    Main simplification agent entry point.
    
    Processes only paragraph blocks via Ollama API.
    Passes headings/lists through unchanged.
    
    Fallback: If Ollama unavailable, passes all text through unchanged.
    
    Returns:
        Updated PipelineState with simplified_text
    """
    logger.info("[AGENT:simplify] Starting")
    
    if not state.transformed_chunks:
        logger.warning("[AGENT:simplify] No blocks to simplify")
        state.simplified_text = state.cleaned_text
        return state
    
    # Check if Ollama is available
    if not _check_ollama_available():
        logger.warning(
            f"[AGENT:simplify] Ollama not available at {OLLAMA_BASE_URL}, "
            f"passing text through unchanged"
        )
        state.simplified_text = state.cleaned_text
        return state
    
    logger.info(f"[AGENT:simplify] Using Ollama model: {OLLAMA_MODEL}")
    
    wpm = getattr(state, 'wpm', None)
    profile = getattr(state, 'profile', None)
    
    simplified_blocks = []
    
    for block in state.transformed_chunks:
        if block['type'] == 'paragraph':
            # Chunk large paragraphs
            text = block['simplified'] if 'simplified' in block else block['text']
            chunks = _chunk_text(text, max_chars=1000)
            simplified_chunks = []
            
            for chunk in chunks:
                simplified = _simplify_paragraph(chunk, wpm=wpm, profile=profile)
                simplified_chunks.append(simplified)
            
            simplified_text = ' '.join(simplified_chunks)
        else:
            # Pass headings and lists through unchanged
            simplified_text = block['text']
        
        simplified_blocks.append({
            **block,
            'simplified': simplified_text
        })
    
    # Reconstruct simplified text
    simplified_lines = [block['simplified'] for block in simplified_blocks]
    simplified_text = '\n\n'.join(simplified_lines)
    
    state.simplified_text = simplified_text
    state.transformed_chunks = simplified_blocks
    
    logger.info(f"[AGENT:simplify] Complete: {len(simplified_blocks)} blocks")
    
    return state
