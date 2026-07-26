import io
from datetime import datetime, timezone
import pytz
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def format_currency(val):
    if val is None:
        return "₹0.00"
    return f"₹{val:,.2f}"

def generate_report_pdf(report, branch, performances, top_perf_exec) -> io.BytesIO:
    buffer = io.BytesIO()
    
    # A4 dimensions: 595.27 x 841.89 points
    # Margins: 0.5 inch (36 pt)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom colors
    gold = colors.HexColor('#D4AF37')
    navy = colors.HexColor('#0B0B0E')
    light_gold = colors.HexColor('#F9F6E6')
    text_color = colors.HexColor('#121217')
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=navy,
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.gray,
        alignment=1,
        spaceAfter=25
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=navy,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=text_color
    )
    
    body_bold = ParagraphStyle(
        'BodyTextBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_bold,
        textColor=colors.white,
        alignment=0
    )
    
    story = []
    
    # Header Section
    story.append(Paragraph("POTHYS SWARNA MAHAL", title_style))
    story.append(Paragraph(f"DAILY OPERATIONS REPORT — {branch.name.upper()}", subtitle_style))
    
    # Convert report.uploaded_at (or created_at) to IST
    tz_kolkata = pytz.timezone('Asia/Kolkata')
    report_time = report.uploaded_at if getattr(report, 'uploaded_at', None) is not None else report.created_at
    if report_time.tzinfo is None:
        report_created_utc = report_time.replace(tzinfo=timezone.utc)
    else:
        report_created_utc = report_time.astimezone(timezone.utc)
    
    created_ist = report_created_utc.astimezone(tz_kolkata)
    formatted_date_time = created_ist.strftime("%d %b %Y • %I:%M %p")
    
    # Metadata Table
    meta_data = [
        [Paragraph("Report Date:", body_bold), Paragraph(str(report.date), body_style), 
         Paragraph("Submitted At (IST):", body_bold), Paragraph(formatted_date_time, body_style)],
        [Paragraph("Branch Manager:", body_bold), Paragraph(report.sub_manager_name or "N/A", body_style),
         Paragraph("Overall Status:", body_bold), Paragraph(report.status, body_bold)]
    ]
    meta_table = Table(meta_data, colWidths=[120, 140, 120, 140])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_gold),
        ('GRID', (0,0), (-1,-1), 0.5, gold),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # Revenue / Sales
    story.append(Paragraph("Revenue & Sales Breakdown", h2_style))
    rev_data = [
        [Paragraph("Category", table_header_style), Paragraph("Amount / Achievement", table_header_style)],
        [Paragraph("Total Revenue", body_bold), Paragraph(format_currency(report.total_revenue), body_style)],
        [Paragraph("Gold Sales", body_style), Paragraph(format_currency(report.gold_sales), body_style)],
        [Paragraph("Silver Sales", body_style), Paragraph(format_currency(report.silver_sales), body_style)],
        [Paragraph("Platinum Sales", body_style), Paragraph(format_currency(report.platinum_sales), body_style)],
        [Paragraph("Diamond Sales", body_style), Paragraph(format_currency(report.diamond_sales), body_style)],
        [Paragraph("Target Achievement", body_bold), Paragraph(f"{report.target_achievement:.1f}%", body_bold)],
    ]
    rev_table = Table(rev_data, colWidths=[260, 260])
    rev_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(rev_table)
    story.append(Spacer(1, 15))
    
    # Schemes & Attendance
    story.append(Paragraph("Digital Schemes & Attendance", h2_style))
    
    digigold_total = report.scheme_summary.digigold_total if report.scheme_summary else report.digigold_enrollments
    digisilver_total = report.scheme_summary.digisilver_total if report.scheme_summary else report.digisilver_enrollments
    
    scheme_data = [
        [Paragraph("Metric", table_header_style), Paragraph("Details", table_header_style)],
        [Paragraph("DigiGold Enrollments", body_style), Paragraph(str(digigold_total), body_style)],
        [Paragraph("DigiSilver Enrollments", body_style), Paragraph(str(digisilver_total), body_style)],
        [Paragraph("Employees Present", body_style), Paragraph(str(report.employees_present), body_style)],
        [Paragraph("Employees Absent", body_style), Paragraph(str(report.employees_absent), body_style)],
        [Paragraph("Total Staff Attendance Count", body_style), Paragraph(str(report.attendance_count), body_style)],
    ]
    scheme_table = Table(scheme_data, colWidths=[260, 260])
    scheme_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(scheme_table)
    story.append(Spacer(1, 15))
    
    # Feedback & Remarks
    story.append(Paragraph("Operations & Feedback", h2_style))
    feedback_data = [
        [Paragraph("Section", table_header_style), Paragraph("Content", table_header_style)],
        [Paragraph("Operational Issues", body_bold), Paragraph(report.operational_issues or report.issues or "None", body_style)],
        [Paragraph("Customer Complaints", body_bold), Paragraph(report.customer_complaints or "None", body_style)],
        [Paragraph("Manager Remarks", body_bold), Paragraph(report.remarks or "None", body_style)]
    ]
    feedback_table = Table(feedback_data, colWidths=[150, 370])
    feedback_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(feedback_table)
    
    # Employee Performance Section
    if performances:
        story.append(PageBreak())
        story.append(Paragraph("Individual Employee Performance", h2_style))
        
        perf_data = [
            [
                Paragraph("Employee Name", table_header_style),
                Paragraph("Gold Grams (Val)", table_header_style),
                Paragraph("Silver Grams (Val)", table_header_style),
                Paragraph("Platinum Val", table_header_style),
                Paragraph("Diamond Val", table_header_style),
                Paragraph("Enrollments", table_header_style),
            ]
        ]
        for p in performances:
            perf_data.append([
                Paragraph(p.employee.name, body_bold),
                Paragraph(f"{p.gold_grams_sold:.3f}g<br/>({format_currency(p.gold_amount)})", body_style),
                Paragraph(f"{p.silver_grams_sold:.3f}g<br/>({format_currency(p.silver_amount)})", body_style),
                Paragraph(format_currency(p.platinum_amount), body_style),
                Paragraph(format_currency(p.diamond_amount), body_style),
                Paragraph(f"Gold: {p.digigold_enrollments}<br/>Silver: {p.digisilver_enrollments}", body_style),
            ])
            
        perf_table = Table(perf_data, colWidths=[110, 85, 85, 80, 80, 80])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), navy),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(perf_table)
        story.append(Spacer(1, 15))
        
        if top_perf_exec:
            story.append(Paragraph("Top Performing Executive", h2_style))
            exec_data = [
                [Paragraph("Name", table_header_style), Paragraph("Total Individual Sales Today", table_header_style)],
                [Paragraph(top_perf_exec[1].name, body_bold), Paragraph(format_currency(top_perf_exec[0]), body_bold)]
            ]
            exec_table = Table(exec_data, colWidths=[260, 260])
            exec_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), gold),
                ('GRID', (0,0), (-1,-1), 0.5, gold),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(exec_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
