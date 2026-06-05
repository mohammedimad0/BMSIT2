"""
PDF Export Utility: Generate PDF from chapter chunks and metadata.

Uses reportlab for professional PDF generation with formatting.
"""

import logging
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def generate_chapter_pdf(
    title: str,
    subject: str,
    class_level: int,
    board: str,
    chunks: List[Dict[str, Any]],
    include_original: bool = True,
    include_glossary: bool = True,
    include_objectives: bool = True
) -> Optional[bytes]:
    """
    Generate a PDF from chapter chunks.
    
    Args:
        title: Chapter title
        subject: Subject name
        class_level: Grade level
        board: Board name (NCERT, SCERT, etc.)
        chunks: List of chunk dicts with simplified_text, glossary, etc.
        include_original: Whether to include original text
        include_glossary: Whether to include glossary
        include_objectives: Whether to include learning objectives
    
    Returns:
        PDF bytes or None on failure
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    except ImportError:
        logger.error("[PDF_EXPORT] reportlab not installed")
        return None
    
    try:
        # Create PDF in memory
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1e40af'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=HexColor('#666666'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'ChunkHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#1e40af'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        
        objective_style = ParagraphStyle(
            'Objective',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#4b5563'),
            spaceAfter=6,
            leftIndent=0.25*inch,
            fontName='Helvetica-Oblique'
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#1a202c'),
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        glossary_heading_style = ParagraphStyle(
            'GlossaryHeading',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=HexColor('#2d3748'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )
        
        glossary_term_style = ParagraphStyle(
            'GlossaryTerm',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#2d3748'),
            spaceAfter=2,
            leftIndent=0.2*inch,
            fontName='Helvetica-Bold'
        )
        
        glossary_def_style = ParagraphStyle(
            'GlossaryDef',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#4a5568'),
            spaceAfter=6,
            leftIndent=0.4*inch,
            fontName='Helvetica'
        )
        
        # Build story (content list)
        story = []
        
        # ════════════════════════════════════════════════════════════════
        # TITLE PAGE
        # ════════════════════════════════════════════════════════════════
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.1*inch))
        
        meta_text = f"<b>Subject:</b> {subject} | <b>Class:</b> {class_level} | <b>Board:</b> {board}<br/><b>Generated:</b> {datetime.now().strftime('%d %B %Y')}"
        story.append(Paragraph(meta_text, subtitle_style))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(PageBreak())
        
        # ════════════════════════════════════════════════════════════════
        # TABLE OF CONTENTS
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("Table of Contents", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        toc_items = []
        for i, chunk in enumerate(chunks, 1):
            objective = chunk.get("objective", "Section")[:60]
            toc_items.append(f"{i}. {objective}")
        
        for toc_item in toc_items:
            story.append(Paragraph(toc_item, content_style))
        
        story.append(PageBreak())
        
        # ════════════════════════════════════════════════════════════════
        # CONTENT CHAPTERS
        # ════════════════════════════════════════════════════════════════
        all_glossaries = {}
        
        for chunk_num, chunk in enumerate(chunks, 1):
            # Chunk heading with number
            chunk_title = chunk.get("objective", f"Section {chunk_num}")
            story.append(Paragraph(f"{chunk_num}. {chunk_title}", heading_style))
            
            # Learning objective
            if include_objectives and chunk.get("objective"):
                story.append(Paragraph(f"<b>Learning Objective:</b> {chunk['objective']}", objective_style))
            
            # Core facts highlight
            if chunk.get("core_facts"):
                story.append(Paragraph("<b>Key Points:</b>", objective_style))
                for fact in chunk["core_facts"]:
                    story.append(Paragraph(f"• {fact}", content_style))
            
            story.append(Spacer(1, 0.08*inch))
            
            # Simplified text (dyslexia-friendly version)
            simplified = chunk.get("simplified_text", "")
            if simplified:
                story.append(Paragraph("<i><b>Simplified Text (Dyslexia-Friendly):</b></i>", objective_style))
                story.append(Paragraph(simplified, content_style))
            
            story.append(Spacer(1, 0.1*inch))
            
            # Original text (if included)
            if include_original:
                original = chunk.get("original_text", "")
                if original and original != simplified:
                    story.append(Paragraph("<i><b>Original Text:</b></i>", objective_style))
                    story.append(Paragraph(original, content_style))
            
            # Glossary for this chunk
            glossary = chunk.get("glossary", {})
            if include_glossary and glossary:
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph("<b>Vocabulary:</b>", glossary_heading_style))
                for term, definition in glossary.items():
                    all_glossaries[term] = definition
                    story.append(Paragraph(f"<b>{term}</b>", glossary_term_style))
                    story.append(Paragraph(definition, glossary_def_style))
            
            story.append(PageBreak())
        
        # ════════════════════════════════════════════════════════════════
        # MASTER GLOSSARY
        # ════════════════════════════════════════════════════════════════
        if include_glossary and all_glossaries:
            story.append(Paragraph("Master Glossary", heading_style))
            story.append(Spacer(1, 0.1*inch))
            
            for term in sorted(all_glossaries.keys()):
                definition = all_glossaries[term]
                story.append(Paragraph(f"<b>{term}</b>", glossary_term_style))
                story.append(Paragraph(definition, glossary_def_style))
        
        # ════════════════════════════════════════════════════════════════
        # BUILD PDF
        # ════════════════════════════════════════════════════════════════
        doc.build(story)
        pdf_bytes = pdf_buffer.getvalue()
        logger.info(f"[PDF_EXPORT] Generated PDF: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"[PDF_EXPORT] Failed to generate PDF: {str(e)}", exc_info=True)
        return None
