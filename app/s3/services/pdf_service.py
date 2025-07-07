import json
import io
from typing import Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
    def generate_report_pdf(self, report_data: Dict[str, Any]) -> bytes:
        """JSON 리포트를 PDF로 변환"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # 제목
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # 중앙 정렬
        )
        
        metadata = report_data.get('metadata', {})
        title = metadata.get('youtube_title', 'YouTube 분석 리포트')
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # 메타데이터 테이블
        if metadata:
            story.append(Paragraph("영상 정보", self.styles['Heading2']))
            meta_data = [
                ['채널', metadata.get('youtube_channel', 'N/A')],
                ['재생시간', metadata.get('youtube_duration', 'N/A')],
                ['URL', metadata.get('youtube_url', 'N/A')],
                ['분석일시', metadata.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
            ]
            
            meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 20))
        
        # 요약
        summary = report_data.get('summary', '')
        if summary:
            story.append(Paragraph("요약", self.styles['Heading2']))
            story.append(Paragraph(summary, self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        # 주요 포인트
        key_points = report_data.get('key_points', [])
        if key_points:
            story.append(Paragraph("주요 포인트", self.styles['Heading2']))
            for i, point in enumerate(key_points, 1):
                story.append(Paragraph(f"{i}. {point}", self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        # 전체 내용
        content = report_data.get('content', '')
        if content:
            story.append(Paragraph("상세 내용", self.styles['Heading2']))
            # 긴 텍스트를 단락으로 나누기
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), self.styles['Normal']))
                    story.append(Spacer(1, 12))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

pdf_service = PDFService()