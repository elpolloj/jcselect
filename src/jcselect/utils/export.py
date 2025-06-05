"""Export utilities for results data to CSV and PDF formats."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    logger.warning("Arabic text support not available - install arabic-reshaper and python-bidi")


def format_arabic_text(text: str) -> str:
    """Format Arabic text for proper display in PDFs."""
    if not ARABIC_SUPPORT or not text:
        return text
        
    try:
        # Reshape Arabic text and apply bidirectional algorithm
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        logger.warning(f"Failed to format Arabic text '{text}': {e}")
        return text


def export_results_csv(results_data: dict[str, Any], file_path: str) -> bool:
    """
    Export results data to CSV format.

    Args:
        results_data: Dictionary containing party_totals, candidate_totals, winners, and metadata
        file_path: Path where the CSV file should be saved

    Returns:
        True if export successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write metadata header
            metadata = results_data.get("metadata", {})
            writer.writerow(["JCSELECT Results Export"])
            writer.writerow(["Exported at:", metadata.get("exported_at", "")])
            writer.writerow(["Pen filter:", metadata.get("pen_filter", "")])
            writer.writerow(["Total ballots:", metadata.get("total_ballots", 0)])
            writer.writerow(["Completion %:", f"{metadata.get('completion_percent', 0):.1f}%"])
            writer.writerow([])  # Empty row

            # Write party totals section
            writer.writerow(["PARTY TOTALS"])
            writer.writerow(["Party ID", "Party Name", "Total Votes", "Candidate Count"])

            party_totals = results_data.get("party_totals", [])
            for party in party_totals:
                writer.writerow([
                    party.get("party_id", ""),
                    party.get("party_name", ""),
                    party.get("total_votes", 0),
                    party.get("candidate_count", 0)
                ])

            writer.writerow([])  # Empty row

            # Write candidate totals section
            writer.writerow(["CANDIDATE TOTALS"])
            writer.writerow(["Candidate ID", "Candidate Name", "Party Name", "Total Votes"])

            candidate_totals = results_data.get("candidate_totals", [])
            for candidate in candidate_totals:
                writer.writerow([
                    candidate.get("candidate_id", ""),
                    candidate.get("candidate_name", ""),
                    candidate.get("party_name", ""),
                    candidate.get("total_votes", 0)
                ])

            writer.writerow([])  # Empty row

            # Write winners section
            writer.writerow(["WINNERS"])
            writer.writerow(["Rank", "Candidate Name", "Party Name", "Total Votes", "Elected"])

            winners = results_data.get("winners", [])
            for winner in winners:
                writer.writerow([
                    winner.get("rank", 0),
                    winner.get("candidate_name", ""),
                    winner.get("party_name", ""),
                    winner.get("total_votes", 0),
                    "Yes" if winner.get("is_elected", False) else "No"
                ])

        logger.info(f"CSV export completed successfully: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        return False


def export_party_totals_csv(party_totals: List[Dict[str, Any]], file_path: str) -> bool:
    """
    Export party totals to CSV format.
    
    Args:
        party_totals: List of party total dictionaries
        file_path: Output file path
        
    Returns:
        True if export successful, False otherwise
        
    Raises:
        ValueError: If data is invalid
        IOError: If file cannot be written
    """
    try:
        if not party_totals:
            raise ValueError("No party totals data provided for export")
            
        # Convert to DataFrame
        df = pd.DataFrame(party_totals)
        
        # Ensure required columns exist
        required_columns = ['party_name', 'total_votes']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        # Add metadata columns
        df['export_timestamp'] = datetime.now().isoformat()
        df['export_type'] = 'party_totals'
        
        # Reorder columns for better readability
        column_order = ['party_name', 'total_votes', 'candidate_count', 'export_timestamp', 'export_type']
        available_columns = [col for col in column_order if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in available_columns]
        final_columns = available_columns + remaining_columns
        
        df = df[final_columns]
        
        # Export to CSV with UTF-8 encoding for Arabic support
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"Exported {len(party_totals)} party totals to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export party totals CSV: {e}")
        raise


def export_candidate_results_csv(candidate_totals: List[Dict[str, Any]], file_path: str) -> bool:
    """
    Export candidate results to CSV format.
    
    Args:
        candidate_totals: List of candidate total dictionaries
        file_path: Output file path
        
    Returns:
        True if export successful, False otherwise
        
    Raises:
        ValueError: If data is invalid
        IOError: If file cannot be written
    """
    try:
        if not candidate_totals:
            raise ValueError("No candidate totals data provided for export")
            
        # Convert to DataFrame
        df = pd.DataFrame(candidate_totals)
        
        # Ensure required columns exist
        required_columns = ['candidate_name', 'total_votes']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        # Add metadata columns
        df['export_timestamp'] = datetime.now().isoformat()
        df['export_type'] = 'candidate_results'
        
        # Reorder columns for better readability
        column_order = ['candidate_name', 'party_name', 'total_votes', 'rank', 'export_timestamp', 'export_type']
        available_columns = [col for col in column_order if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in available_columns]
        final_columns = available_columns + remaining_columns
        
        df = df[final_columns]
        
        # Export to CSV with UTF-8 encoding for Arabic support
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"Exported {len(candidate_totals)} candidate results to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export candidate results CSV: {e}")
        raise


def export_results_pdf(results_data: Dict[str, Any], file_path: str) -> bool:
    """
    Export results to PDF format with Arabic text support.
    
    Args:
        results_data: Dictionary containing results data with keys:
                     - party_totals: List of party totals
                     - candidate_totals: List of candidate results  
                     - winners: List of winners (optional)
                     - metadata: Additional metadata (optional)
        file_path: Output file path
        
    Returns:
        True if export successful, False otherwise
        
    Raises:
        ValueError: If data is invalid
        IOError: If file cannot be written
    """
    try:
        if not results_data:
            raise ValueError("No results data provided for export")
            
        # Create the PDF document
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        
        # Build the content
        story = []
        styles = getSampleStyleSheet()
        
        # Create custom styles for Arabic text
        title_style = ParagraphStyle(
            'ArabicTitle',
            parent=styles['Title'],
            fontSize=18,
            alignment=1,  # Center alignment
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'ArabicHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            alignment=2  # Right alignment for Arabic
        )
        
        # Add title
        title_text = format_arabic_text("تقرير النتائج الانتخابية")
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 20))
        
        # Add export timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp_text = f"تاريخ التصدير: {timestamp}"
        story.append(Paragraph(format_arabic_text(timestamp_text), styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add party totals section
        party_totals = results_data.get('party_totals', [])
        if party_totals:
            story.append(Paragraph(format_arabic_text("إجمالي الأصوات حسب الحزب"), heading_style))
            story.append(Spacer(1, 10))
            
            # Create party totals table
            party_table_data = [
                [format_arabic_text("الحزب"), format_arabic_text("إجمالي الأصوات"), format_arabic_text("النسبة المئوية")]
            ]
            
            total_votes = sum(party.get('total_votes', 0) for party in party_totals)
            
            for party in party_totals:
                party_name = format_arabic_text(party.get('party_name', ''))
                votes = party.get('total_votes', 0)
                percentage = f"{(votes / total_votes * 100):.1f}%" if total_votes > 0 else "0%"
                party_table_data.append([party_name, str(votes), percentage])
            
            party_table = Table(party_table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            party_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(party_table)
            story.append(Spacer(1, 20))
        
        # Add candidate results section
        candidate_totals = results_data.get('candidate_totals', [])
        if candidate_totals:
            story.append(Paragraph(format_arabic_text("نتائج المرشحين"), heading_style))
            story.append(Spacer(1, 10))
            
            # Create candidate results table
            candidate_table_data = [
                [format_arabic_text("المرشح"), format_arabic_text("الحزب"), 
                 format_arabic_text("الأصوات"), format_arabic_text("الترتيب")]
            ]
            
            for candidate in candidate_totals:
                candidate_name = format_arabic_text(candidate.get('candidate_name', ''))
                party_name = format_arabic_text(candidate.get('party_name', ''))
                votes = candidate.get('total_votes', 0)
                rank = candidate.get('rank', '-')
                candidate_table_data.append([candidate_name, party_name, str(votes), str(rank)])
            
            candidate_table = Table(candidate_table_data, colWidths=[2*inch, 2*inch, 1*inch, 1*inch])
            candidate_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(candidate_table)
            story.append(Spacer(1, 20))
        
        # Add winners section if available
        winners = results_data.get('winners', [])
        if winners:
            story.append(Paragraph(format_arabic_text("الفائزون"), heading_style))
            story.append(Spacer(1, 10))
            
            # Create winners table
            winners_table_data = [
                [format_arabic_text("المرشح"), format_arabic_text("الحزب"), 
                 format_arabic_text("الأصوات"), format_arabic_text("المركز")]
            ]
            
            for winner in winners:
                if winner.get('is_elected', False):
                    candidate_name = format_arabic_text(winner.get('candidate_name', ''))
                    party_name = format_arabic_text(winner.get('party_name', ''))
                    votes = winner.get('total_votes', 0)
                    rank = winner.get('rank', '-')
                    winners_table_data.append([candidate_name, party_name, str(votes), str(rank)])
            
            if len(winners_table_data) > 1:  # More than just header
                winners_table = Table(winners_table_data, colWidths=[2*inch, 2*inch, 1*inch, 1*inch])
                winners_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(winners_table)
        
        # Add metadata if available
        metadata = results_data.get('metadata', {})
        if metadata:
            story.append(Spacer(1, 20))
            story.append(Paragraph(format_arabic_text("معلومات إضافية"), heading_style))
            
            for key, value in metadata.items():
                if isinstance(value, str):
                    formatted_key = format_arabic_text(str(key))
                    formatted_value = format_arabic_text(str(value))
                    story.append(Paragraph(f"{formatted_key}: {formatted_value}", styles['Normal']))
        
        # Build the PDF
        doc.build(story)
        
        logger.info(f"Exported results PDF to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export results PDF: {e}")
        raise


def generate_summary_report_pdf(pen_id: str, file_path: str) -> bool:
    """
    Generate a summary report PDF for a specific pen.

    Args:
        pen_id: Pen ID to generate report for
        file_path: Path where the PDF file should be saved

    Returns:
        True if export successful, False otherwise
    """
    try:
        # Import DAO functions
        from jcselect.dao_results import (
            get_pen_completion_status,
            get_pen_voter_turnout,
            get_totals_by_candidate,
            get_totals_by_party,
        )
        from jcselect.utils.db import get_session

        # Gather data for the pen
        with get_session() as session:
            party_totals = get_totals_by_party(pen_id, session)
            candidate_totals = get_totals_by_candidate(pen_id, session)
            turnout = get_pen_voter_turnout(pen_id, session)
            completion_status = get_pen_completion_status(pen_id, session)

        # Prepare summary data
        summary_data = {
            "pen_id": pen_id,
            "completion_status": completion_status,
            "voter_turnout": turnout,
            "party_totals": party_totals,
            "candidate_totals": candidate_totals,
            "generated_at": str(Path(file_path).stem)
        }

        # Use the main export function
        return export_results_pdf(summary_data, file_path)

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}")
        return False


def get_export_filename(export_type: str, extension: str, base_name: str = "results") -> str:
    """
    Generate a filename for export with timestamp.
    
    Args:
        export_type: Type of export (e.g., "party_totals", "candidate_results")
        extension: File extension (e.g., "csv", "pdf")
        base_name: Base name for the file
        
    Returns:
        Formatted filename with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{export_type}_{timestamp}.{extension}"


def validate_export_path(file_path: str) -> bool:
    """
    Validate that the export path is writable.
    
    Args:
        file_path: Path to validate
        
    Returns:
        True if path is writable, False otherwise
    """
    try:
        # Check if directory exists and is writable
        directory = Path(file_path).parent
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            
        # Test write access by creating a temporary file
        test_file = directory / f"test_write_{os.getpid()}.tmp"
        test_file.write_text("test")
        test_file.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Export path validation failed: {e}")
        return False
