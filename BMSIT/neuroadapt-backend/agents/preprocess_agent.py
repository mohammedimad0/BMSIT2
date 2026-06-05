"""
Preprocessing Agent: Structure raw text into semantic blocks.

Detects headings, lists, and paragraphs.
Fixes hyphenation breaks across line breaks.
Returns list of blocks: [{"type": "heading"|"paragraph"|"list", "text": "..."}]

No inter-agent imports. All exceptions caught and logged locally.
"""

import logging
import re
from models import PipelineState

logger = logging.getLogger(__name__)


def _fix_hyphenation(text: str) -> str:
    """
    Fix broken hyphenation: rejoin words split across line breaks.
    
    Handles: "photo-\nsynthesis" → "photosynthesis"
    """
    # Match word- followed by newline(s) followed by word
    text = re.sub(r'(\w+)-\n+(\w+)', r'\1\2', text)
    return text


def _is_heading(text: str, next_text: str = "") -> bool:
    """
    Heuristic to detect heading-like lines.
    
    Return True if:
    - ALL CAPS and < 60 chars
    - Ends without period and < 60 chars and followed by blank line
    - ALL CAPS or title case and very short (< 40 chars)
    """
    text = text.strip()
    if not text:
        return False
    
    # Too long to be a heading
    if len(text) > 80:
        return False
    
    # ALL CAPS is a strong signal
    if text.isupper() and len(text) > 3:
        return True
    
    # Ends without period, short, followed by content = heading
    if (len(text) < 60 and
        not text.endswith(('.', '!', '?')) and
        next_text and
        len(next_text.strip()) > 10):
        return True
    
    return False


def _is_list_item(text: str) -> bool:
    """
    Detect bullet points and numbered lists.
    """
    text = text.strip()
    if not text:
        return False
    
    # Bullet patterns
    if text[0] in ('•', '◦', '○', '-', '*', '+'):
        return True
    
    # Numbered: 1. 2) i. etc.
    if re.match(r'^(\d+\.|\d+\)|\w\.)\s', text):
        return True
    
    return False


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on double newlines."""
    # Normalize newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split on 2+ newlines
    paragraphs = re.split(r'\n{2,}', text)
    
    # Filter empty
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    return paragraphs


def run(state: PipelineState) -> PipelineState:
    """
    Main preprocessing agent entry point.
    
    Returns:
        Updated PipelineState with cleaned_text and transformed_chunks
    """
    logger.info("[AGENT:preprocess] Starting")
    
    raw_text = state.raw_text
    if not raw_text.strip():
        logger.warning("[AGENT:preprocess] No raw text to process")
        state.cleaned_text = ""
        state.transformed_chunks = []
        return state
    
    try:
        # Fix hyphenation
        text = _fix_hyphenation(raw_text)
        
        # Split into paragraphs
        paragraphs = _split_paragraphs(text)
        
        # Classify each paragraph
        blocks = []
        for i, para in enumerate(paragraphs):
            # Get next paragraph for context
            next_para = paragraphs[i + 1] if i + 1 < len(paragraphs) else ""
            
            if _is_heading(para, next_para):
                block_type = "heading"
            elif _is_list_item(para):
                block_type = "list"
            else:
                block_type = "paragraph"
            
            blocks.append({
                "type": block_type,
                "text": para
            })
        
        # Reconstruct cleaned text
        cleaned_lines = [block["text"] for block in blocks]
        cleaned_text = "\n\n".join(cleaned_lines)
        
        state.cleaned_text = cleaned_text
        state.transformed_chunks = blocks
        
        logger.info(
            f"[AGENT:preprocess] Complete: {len(blocks)} blocks "
            f"({sum(1 for b in blocks if b['type']=='heading')} headings, "
            f"{sum(1 for b in blocks if b['type']=='list')} lists, "
            f"{sum(1 for b in blocks if b['type']=='paragraph')} paragraphs)"
        )
        
        return state
    
    except Exception as e:
        logger.error(f"[AGENT:preprocess] Fallback: simple split", exc_info=True)
        
        # Fallback: simple split on double newlines
        try:
            paragraphs = _split_paragraphs(raw_text)
            blocks = [{"type": "paragraph", "text": p} for p in paragraphs]
            
            state.cleaned_text = "\n\n".join(paragraphs)
            state.transformed_chunks = blocks
            
            logger.info(f"[AGENT:preprocess] Fallback complete: {len(blocks)} paragraphs")
            return state
        
        except Exception as fallback_err:
            logger.error(f"[AGENT:preprocess] Fallback also failed: {str(fallback_err)}")
            state.degraded = True
            state.errors.append(f"preprocess: {str(e)}")
            return state
