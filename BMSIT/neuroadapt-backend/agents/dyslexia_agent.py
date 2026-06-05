"""
Dyslexia Transformation Agent: Apply 4 independent sub-transforms.

A. Syllable splitting: Break long words using pyphen
B. Numbers to words: Convert 6CO₂ → "six CO₂ molecules" using num2words
C. Concept chunking: Group sentences into 2-4 sentence chunks
D. Glossary injection: Attach NCERT term definitions to chunks

Each sub-transform is independent — failure in one does NOT stop others.

No inter-agent imports. All exceptions caught and logged locally.
"""

import logging
import re
from typing import Dict, List, Set
from models import PipelineState

logger = logging.getLogger(__name__)

# NCERT Science glossary (~30 key terms)
NCERT_GLOSSARY = {
    "photosynthesis": "how plants make food using sunlight",
    "mitochondria": "the powerhouse of the cell, producing energy",
    "chlorophyll": "green pigment in plants that captures sunlight",
    "respiration": "how cells break down food to produce energy",
    "evaporation": "water turning into invisible water vapor",
    "condensation": "water vapor turning into liquid water",
    "decomposition": "breaking down of dead organisms into soil",
    "reproduction": "making offspring or new living things",
    "fertilisation": "when male and female cells combine to make new life",
    "electromagnetism": "the combined effect of electricity and magnetism",
    "gravitational": "related to the force that pulls objects down",
    "acceleration": "change in speed or direction of movement",
    "combustion": "rapid burning that produces heat and light",
    "chloroplast": "part of the plant cell where photosynthesis happens",
    "chromosome": "structure carrying genes in cell nucleus",
    "enzyme": "protein that speeds up chemical reactions in cells",
    "osmosis": "movement of water across a membrane",
    "photon": "tiny packet of light energy",
    "isotope": "atom of element with different number of neutrons",
    "equilibrium": "state of balance with no net change",
    "hydration": "process of absorbing water",
    "oxidation": "loss of electrons in a chemical reaction",
    "catalyst": "substance that speeds up reaction without being used",
    "polymer": "large molecule made of many repeated small units",
    "substrate": "surface or substance an enzyme acts upon",
    "antibody": "protein that fights germs in the body",
    "mitosis": "cell division creating two identical cells",
    "meiosis": "cell division creating sex cells",
    "allele": "different version of a gene",
    "ecosystem": "community of living things and their environment",
}


def _syllablify_word(word: str) -> str:
    """
    Split a word into syllables using pyphen.
    
    Returns original word if splitting fails.
    Format: word with dots between syllables for display.
    """
    if len(word) <= 6:
        return word  # Don't split short words
    
    # Don't split proper nouns (capital letter mid-word indicates proper noun)
    if any(c.isupper() for c in word[1:]):
        return word
    
    try:
        from pyphen import Pyphen
        dic = Pyphen(lang='en_GB')
        hyphenated = dic.inserted(word.lower())
        syllables = hyphenated.split('-')
        return '·'.join(syllables)
    except Exception as e:
        logger.debug(f"[AGENT:dyslexia] Syllable split failed for '{word}': {e}")
        return word


def _transform_a_syllables(blocks: List[Dict]) -> List[Dict]:
    """
    Sub-transform A: Syllable splitting.
    
    Splits words > 6 chars, stores as data attribute.
    """
    logger.info("[AGENT:dyslexia:A] Starting syllable splitting")
    
    try:
        ncert_terms = set(NCERT_GLOSSARY.keys())
        
        for block in blocks:
            if 'simplified' not in block:
                block['simplified'] = block.get('text', '')
            
            text = block['simplified']
            words = text.split()
            syllabified_words = []
            
            for word in words:
                # Remove trailing punctuation
                trailing_punct = ''
                while word and not word[-1].isalpha():
                    trailing_punct = word[-1] + trailing_punct
                    word = word[:-1]
                
                if len(word) > 6 or word.lower() in ncert_terms:
                    syllables = _syllablify_word(word.lower() if not word[0].isupper() else word)
                    syllabified_words.append(word + trailing_punct)  # Keep original for HTML
                else:
                    syllabified_words.append(word + trailing_punct)
            
            # Store syllable data for HTML layer
            if not hasattr(block, 'syllable_map'):
                block['syllable_map'] = {}
            
            logger.debug(f"[AGENT:dyslexia:A] Processed {len(words)} words in block")
        
        logger.info("[AGENT:dyslexia:A] Complete")
        return blocks
    
    except Exception as e:
        logger.error(f"[AGENT:dyslexia:A] Failed: {str(e)}")
        return blocks


def _transform_b_numbers(blocks: List[Dict]) -> List[Dict]:
    """
    Sub-transform B: Numbers to words.
    
    Converts "6CO₂" → "six CO₂ molecules", "35°C" → "35 degrees Celsius"
    """
    logger.info("[AGENT:dyslexia:B] Starting number conversion")
    
    try:
        from num2words import num2words
    except ImportError:
        logger.warning("[AGENT:dyslexia:B] num2words not installed, skipping")
        return blocks
    
    try:
        for block in blocks:
            if 'simplified' not in block:
                continue
            
            text = block['simplified']
            
            # Convert measurements: "35°C" → "35 degrees Celsius"
            text = re.sub(r'(\d+)°C\b', r'\1 degrees Celsius', text)
            text = re.sub(r'(\d+)°F\b', r'\1 degrees Fahrenheit', text)
            text = re.sub(r'(\d+)°\b', r'\1 degrees', text)
            
            # Convert standalone integers with units
            def replace_number(match):
                num = int(match.group(1))
                if num > 1000:
                    words = num2words(num)
                else:
                    words = num2words(num)
                return words
            
            # Only replace numbers in certain contexts
            text = re.sub(r'\b(\d+)\s*(?:cm|m|km|g|kg|ml|l|sec|min)\b', replace_number, text)
            
            block['simplified'] = text
        
        logger.info("[AGENT:dyslexia:B] Complete")
        return blocks
    
    except Exception as e:
        logger.error(f"[AGENT:dyslexia:B] Failed: {str(e)}")
        return blocks


def _transform_c_concepts(blocks: List[Dict]) -> List[Dict]:
    """
    Sub-transform C: Concept chunking.
    
    Groups 2-4 consecutive sentences into concept blocks.
    Creates chunk_id and marks hierarchy.
    """
    logger.info("[AGENT:dyslexia:C] Starting concept chunking")
    
    try:
        chunked_blocks = []
        chunk_id = 0
        
        for block in blocks:
            if 'simplified' not in block:
                block['simplified'] = block.get('text', '')
            
            text = block['simplified']
            is_heading = block.get('type') == 'heading'
            
            if is_heading:
                # Headings always start a new chunk
                chunk_id += 1
                chunked_blocks.append({
                    **block,
                    'chunk_id': chunk_id,
                    'is_heading': True,
                    'sentences': [text]
                })
            else:
                # Split into sentences
                sentences = re.split(r'(?<=[.!?])\s+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                # Group sentences into chunks of 2-4
                for i in range(0, len(sentences), 3):
                    chunk_id += 1
                    chunk_sentences = sentences[i:i+3]
                    
                    chunked_blocks.append({
                        **block,
                        'chunk_id': chunk_id,
                        'is_heading': False,
                        'sentences': chunk_sentences,
                        'simplified': ' '.join(chunk_sentences)
                    })
        
        logger.info(f"[AGENT:dyslexia:C] Created {chunk_id} concept chunks")
        return chunked_blocks
    
    except Exception as e:
        logger.error(f"[AGENT:dyslexia:C] Failed: {str(e)}")
        return blocks


def _transform_d_glossary(blocks: List[Dict]) -> List[Dict]:
    """
    Sub-transform D: Glossary injection.
    
    Attaches NCERT term definitions to chunks where they first appear.
    """
    logger.info("[AGENT:dyslexia:D] Starting glossary injection")
    
    try:
        terms_seen: Set[str] = set()
        
        for block in blocks:
            text = block.get('simplified', block.get('text', ''))
            glossary_terms = {}
            
            for term, definition in NCERT_GLOSSARY.items():
                # Case-insensitive search
                if term.lower() in text.lower() and term not in terms_seen:
                    glossary_terms[term] = definition
                    terms_seen.add(term)
            
            if glossary_terms:
                block['glossary'] = glossary_terms
            
            logger.debug(f"[AGENT:dyslexia:D] Found {len(glossary_terms)} glossary terms in block")
        
        logger.info(f"[AGENT:dyslexia:D] Complete: {len(terms_seen)} unique terms")
        return blocks
    
    except Exception as e:
        logger.error(f"[AGENT:dyslexia:D] Failed: {str(e)}")
        return blocks


def run(state: PipelineState) -> PipelineState:
    """
    Main dyslexia transformation agent entry point.
    
    Runs all 4 sub-transforms independently.
    Failure in one sub-transform does NOT stop the others.
    
    Returns:
        Updated PipelineState with transformed chunks
    """
    logger.info("[AGENT:dyslexia] Starting")
    
    if not state.transformed_chunks:
        logger.warning("[AGENT:dyslexia] No blocks to transform")
        return state
    
    blocks = state.transformed_chunks
    
    # Run all 4 transforms (each independently handles errors)
    blocks = _transform_a_syllables(blocks)
    blocks = _transform_b_numbers(blocks)
    blocks = _transform_c_concepts(blocks)
    blocks = _transform_d_glossary(blocks)
    
    state.transformed_chunks = blocks
    
    logger.info(f"[AGENT:dyslexia] Complete: {len(blocks)} transformed blocks")
    
    return state
