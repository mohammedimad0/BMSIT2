"""
HTML Output Agent: Build complete self-contained HTML.

Creates semantic HTML with:
- Chunk divs with data-hidden, data-chunk-id
- Sentence paragraphs with class="na-sentence"
- Syllable-split words as data attributes
- Glossary injection
- Debug info in root div

No inter-agent imports. All exceptions caught and logged locally.
"""

import json
import logging
from html import escape
from models import PipelineState

logger = logging.getLogger(__name__)


def _encode_html_safe(text: str) -> str:
    """
    HTML-escape text safely.
    """
    return escape(text)


def _build_chunk_html(chunk: dict, chunk_index: int, total_chunks: int) -> str:
    """
    Build HTML for a single chunk div.
    """
    chunk_id = chunk.get('chunk_id', chunk_index)
    is_hidden = chunk_index > 0  # All chunks hidden except first
    
    chunk_html = f'  <div class="na-chunk" data-chunk-id="{chunk_id}" data-hidden="{"true" if is_hidden else "false"}">\n'
    
    # Handle headings
    if chunk.get('is_heading', chunk.get('type') == 'heading'):
        heading_text = _encode_html_safe(chunk.get('simplified', chunk.get('text', '')))
        chunk_html += f'    <h2 class="na-heading">{heading_text}</h2>\n'
    else:
        # Handle sentences in paragraph
        sentences = chunk.get('sentences', [])
        if not sentences:
            # Fallback: split simplified text on periods
            text = chunk.get('simplified', chunk.get('text', ''))
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        for sentence in sentences:
            sentence_text = _encode_html_safe(sentence)
            chunk_html += f'    <p class="na-sentence">{sentence_text}</p>\n'
    
    # Add glossary popup if present
    if 'glossary' in chunk:
        for term, definition in chunk['glossary'].items():
            term_safe = _encode_html_safe(term)
            def_safe = _encode_html_safe(definition)
            chunk_html += f'    <div class="na-glossary-popup" data-term="{term_safe}">{def_safe}</div>\n'
    
    chunk_html += '  </div>\n'
    
    return chunk_html


def run(state: PipelineState) -> PipelineState:
    """
    Main HTML building agent entry point.
    
    Primary strategy: Build structured HTML with chunking and data attributes.
    Fallback strategy: Wrap in plain <p> tags if structured fails.
    
    Returns:
        Updated PipelineState with html_output populated
    """
    logger.info("[AGENT:html] Starting")
    
    if not state.transformed_chunks:
        logger.warning("[AGENT:html] No chunks to render")
        state.html_output = f'''<div class="na-document" data-job-id="{state.job_id}" data-degraded="true">
  <p class="na-error">No content to display</p>
</div>'''
        return state
    
    try:
        chunks = state.transformed_chunks
        total_chunks = len(chunks)
        
        # Build root div with metadata
        agent_statuses_json = json.dumps(state.agent_statuses)
        agent_statuses_safe = _encode_html_safe(agent_statuses_json)
        
        html_parts = [
            f'<div class="na-document" data-job-id="{state.job_id}" data-degraded="{"true" if state.degraded else "false"}" data-agent-statuses=\'{agent_statuses_safe}\'>',
        ]
        
        # Build each chunk
        for i, chunk in enumerate(chunks):
            chunk_html = _build_chunk_html(chunk, i, total_chunks)
            html_parts.append(chunk_html)
        
        html_parts.append('</div>')
        
        state.html_output = '\n'.join(html_parts)
        
        logger.info(f"[AGENT:html] Complete: {total_chunks} chunks, {len(state.html_output)} bytes")
        
        return state
    
    except Exception as e:
        logger.error(f"[AGENT:html] Primary failed, using fallback: {str(e)}", exc_info=True)
        
        try:
            # Fallback: simple paragraph wrapping
            chunks = state.transformed_chunks
            
            html_parts = [
                f'<div class="na-document" data-job-id="{state.job_id}" data-degraded="true">',
            ]
            
            for chunk in chunks:
                text = chunk.get('simplified', chunk.get('text', ''))
                text_safe = _encode_html_safe(text)
                html_parts.append(f'  <p class="na-sentence">{text_safe}</p>')
            
            html_parts.append('</div>')
            
            state.html_output = '\n'.join(html_parts)
            state.degraded = True
            state.errors.append("html: Used fallback (plain paragraph wrapping)")
            
            logger.info(f"[AGENT:html] Fallback complete: {len(state.html_output)} bytes")
            
            return state
        
        except Exception as fallback_err:
            logger.error(f"[AGENT:html] Fallback also failed: {str(fallback_err)}", exc_info=True)
            
            # Last resort: bare minimum
            state.html_output = f'''<div class="na-document" data-job-id="{state.job_id}" data-degraded="true">
  <p class="na-error">Failed to generate readable HTML</p>
</div>'''
            state.degraded = True
            state.errors.append(f"html: Fallback failed - {str(fallback_err)}")
            
            return state
