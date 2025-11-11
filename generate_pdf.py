"""
Script to convert documentation.md to PDF
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re

def create_pdf():
    """Create PDF from markdown documentation"""
    
    # Read markdown file
    with open('documentation.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create PDF document
    pdf_filename = 'Employee_Progress_Tracker_Documentation.pdf'
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for the 'Flowable' objects
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#1a1a1a',
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#2c3e50',
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#333333',
        spaceAfter=12,
        leading=16,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#333333',
        spaceAfter=12,
        leading=16,
        alignment=TA_LEFT,
        fontName='Helvetica',
        leftIndent=20,
        rightIndent=20
    )
    
    # Parse markdown content
    lines = content.split('\n')
    
    # Add title
    story.append(Paragraph("Employee Progress Tracker", title_style))
    story.append(Paragraph("Project Documentation", ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor='#666666',
        spaceAfter=30,
        alignment=TA_CENTER
    )))
    story.append(Spacer(1, 0.3*inch))
    
    current_section = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and markdown headers
        if not line or line.startswith('#'):
            if line.startswith('## Summary'):
                # Process accumulated text if any
                if current_section and current_text:
                    story.append(Paragraph(current_section, heading_style))
                    for text in current_text:
                        story.append(Paragraph(text, body_style))
                    story.append(Spacer(1, 0.2*inch))
                    current_text = []
                
                # Add summary section
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph("Summary", heading_style))
                continue
            continue
        
        # Check for image sections (## Image X:)
        if line.startswith('## Image'):
            # Save previous section if exists
            if current_section and current_text:
                story.append(Paragraph(current_section, heading_style))
                for text in current_text:
                    story.append(Paragraph(text, body_style))
                story.append(Spacer(1, 0.2*inch))
            
            # Extract section title
            current_section = line.replace('## ', '')
            current_text = []
        elif line.startswith('---'):
            # Skip horizontal rules
            continue
        elif current_section:
            # Add text to current section
            if line:
                # Clean up markdown formatting
                line = line.replace('**', '<b>').replace('**', '</b>')
                line = line.replace('*', '').replace('`', '')
                current_text.append(line)
    
    # Add last section
    if current_section and current_text:
        story.append(Paragraph(current_section, heading_style))
        for text in current_text:
            story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Add summary if found
    summary_started = False
    summary_lines = []
    for i, line in enumerate(lines):
        if '## Summary' in line:
            summary_started = True
            continue
        if summary_started and line.strip():
            if line.startswith('##'):
                break
            summary_lines.append(line.strip())
    
    if summary_lines:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Summary", heading_style))
        summary_text = ' '.join(summary_lines)
        summary_text = summary_text.replace('**', '<b>').replace('**', '</b>')
        story.append(Paragraph(summary_text, summary_style))
    
    # Build PDF
    doc.build(story)
    print(f"PDF created successfully: {pdf_filename}")

if __name__ == "__main__":
    try:
        create_pdf()
    except Exception as e:
        print(f"Error creating PDF: {e}")
        import traceback
        traceback.print_exc()



