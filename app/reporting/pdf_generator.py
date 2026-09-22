import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.schemas.investigation import (
    InvestigationSummarySchema,
    FindingSchema,
    EvidenceGraphItemSchema,
)
from app.schemas.trace import TraceResultResponse
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.vasp import VASPAttributionResponse
from app.sources.registry import source_registry

logger = logging.getLogger("specter.reporting.pdf_generator")


class PDFReportGenerator:
    """
    Generates professional, multi-page PDF reports titled:
    INVESTIGATION-READY BLOCKCHAIN INTELLIGENCE REPORT
    """

    def generate_pdf_report(
        self,
        output_path: str,
        summary: InvestigationSummarySchema,
        findings: List[FindingSchema],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
        risk_resp: RiskIndicatorResponse,
        vasp_resp: Optional[VASPAttributionResponse] = None,
    ) -> str:
        """
        Builds and saves the investigation PDF report to output_path.
        Returns the absolute file path.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom Paragraph Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1A365D"),
            fontName="Helvetica-Bold",
            alignment=0,
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4A5568"),
            fontName="Helvetica-Bold",
            spaceAfter=12,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1A365D"),
            fontName="Helvetica-Bold",
            spaceBefore=10,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=4,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2D3748"),
        )

        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1A365D"),
            fontName="Helvetica-Bold",
        )

        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#718096"),
            fontName="Helvetica-Oblique",
        )

        story = []

        # Header Title
        story.append(Paragraph("INVESTIGATION-READY BLOCKCHAIN INTELLIGENCE REPORT", title_style))
        story.append(Paragraph("SPECTER HIGH-VELOCITY MULTI-HOP FUND TRACING & RISK ENGINE", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2B6CB0"), spaceAfter=10))

        # 1. Executive Summary & Case Metadata
        story.append(Paragraph("1. EXECUTIVE SUMMARY & CASE METADATA", section_heading))
        meta_data = [
            [Paragraph("Case ID:", table_cell_bold), Paragraph(summary.case_id, table_cell_style),
             Paragraph("Job ID:", table_cell_bold), Paragraph(summary.job_id, table_cell_style)],
            [Paragraph("Target Wallet:", table_cell_bold), Paragraph(summary.target_wallet, table_cell_style),
             Paragraph("Network / Asset:", table_cell_bold), Paragraph(f"{summary.chain} ({summary.asset})", table_cell_style)],
            [Paragraph("Status:", table_cell_bold), Paragraph(summary.investigation_status, table_cell_style),
             Paragraph("Completed At:", table_cell_bold), Paragraph(str(summary.completed_at), table_cell_style)],
            [Paragraph("Wallets Traced:", table_cell_bold), Paragraph(str(summary.total_wallets_traced), table_cell_style),
             Paragraph("Transactions Analyzed:", table_cell_bold), Paragraph(str(summary.total_transactions_analyzed), table_cell_style)],
        ]
        meta_table = Table(meta_data, colWidths=[1.1 * inch, 2.4 * inch, 1.1 * inch, 2.4 * inch])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 8))

        # 2. Risk Indicator Breakdown
        story.append(Paragraph("2. TRANSACTION-FLOW RISK INDICATOR BREAKDOWN", section_heading))
        if risk_resp and risk_resp.risk_score is not None:
            risk_color = "#E53E3E" if risk_resp.risk_level in ["HIGH", "VERY HIGH", "CRITICAL"] else ("#DD6B20" if risk_resp.risk_level == "MODERATE" else "#38A169")
            risk_summary_text = (
                f"<b>Contextual Risk Score:</b> <font color='{risk_color}'><b>{risk_resp.risk_score:.1f} / 100.0 ({risk_resp.risk_level})</b></font><br/>"
                f"<b>Raw Transaction-Flow Score:</b> {(risk_resp.raw_risk_score or 0.0):.1f} / 100.0<br/>"
                f"<b>Service Entity Context:</b> {risk_resp.service_entity_context}<br/>"
                f"<b>Contextual Interpretation:</b> {risk_resp.contextual_interpretation}"
            )
        else:
            risk_summary_text = (
                f"<b>Assessment Status:</b> <font color='#718096'><b>INSUFFICIENT_EVIDENCE (N/A)</b></font><br/>"
                f"<b>Contextual Interpretation:</b> {risk_resp.contextual_interpretation if risk_resp else 'Insufficient history'}"
            )
        story.append(Paragraph(risk_summary_text, body_style))
        story.append(Spacer(1, 4))


        # Risk Breakdown Table
        risk_comp_data = [
            [Paragraph("Risk Component", table_header_style), Paragraph("Points Contributed", table_header_style), Paragraph("Description", table_header_style)]
        ]
        for comp, val in risk_resp.component_contributions.items():
            risk_comp_data.append([
                Paragraph(comp.replace("_", " ").title(), table_cell_bold),
                Paragraph(f"{val:.1f} pts", table_cell_style),
                Paragraph(f"Contribution of {comp.replace('_', ' ')} to transaction-flow risk score.", table_cell_style),
            ])
        comp_table = Table(risk_comp_data, colWidths=[2.2 * inch, 1.2 * inch, 3.6 * inch])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(comp_table)

        if risk_resp.false_positive_mitigations:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>False-Positive Mitigations & Safety Rules Applied:</b>", body_style))
            for mit in risk_resp.false_positive_mitigations:
                story.append(Paragraph(f"• {mit}", body_style))

        story.append(Spacer(1, 8))

        # 3. High-Velocity Movement & Rapid Successive Transfer Analysis
        story.append(Paragraph("3. HIGH-VELOCITY MOVEMENT ANALYSIS", section_heading))
        vel_text = (
            f"<b>High-Velocity Movement Flag:</b> {velocity_resp.has_high_velocity_pattern}<br/>"
            f"<b>Summary:</b> {velocity_resp.summary}"
        )
        story.append(Paragraph(vel_text, body_style))

        if velocity_resp.alerts:
            story.append(Spacer(1, 4))
            alert_table_data = [
                [Paragraph("Alert ID", table_header_style), Paragraph("Severity", table_header_style), Paragraph("Score", table_header_style), Paragraph("Transfers", table_header_style), Paragraph("Min Δt", table_header_style), Paragraph("Explanation", table_header_style)]
            ]
            for a in velocity_resp.alerts:
                alert_table_data.append([
                    Paragraph(a.alert_id[:12], table_cell_style),
                    Paragraph(a.severity, table_cell_bold),
                    Paragraph(f"{a.velocity_score:.1f}", table_cell_style),
                    Paragraph(str(a.transfer_count), table_cell_style),
                    Paragraph(f"{a.minimum_delta_t:.1f}s" if a.minimum_delta_t is not None else "N/A", table_cell_style),
                    Paragraph(a.explanation, table_cell_style),
                ])
            alert_table = Table(alert_table_data, colWidths=[1.0 * inch, 0.9 * inch, 0.6 * inch, 0.7 * inch, 0.7 * inch, 3.1 * inch])
            alert_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(alert_table)

        story.append(Spacer(1, 8))

        # 4. Structural Transaction Typologies
        story.append(Paragraph("4. STRUCTURAL TRANSACTION TYPOLOGY ANALYSIS", section_heading))
        story.append(Paragraph(f"<b>Typologies Summary:</b> {typology_resp.summary}", body_style))

        if typology_resp.typologies:
            story.append(Spacer(1, 4))
            typ_table_data = [
                [Paragraph("Typology Pattern", table_header_style), Paragraph("Severity", table_header_style), Paragraph("Confidence", table_header_style), Paragraph("Description", table_header_style)]
            ]
            for t in typology_resp.typologies:
                typ_table_data.append([
                    Paragraph(t.typology_name.replace("_", " "), table_cell_bold),
                    Paragraph(t.severity, table_cell_style),
                    Paragraph(f"{t.confidence:.2f}", table_cell_style),
                    Paragraph(t.description, table_cell_style),
                ])
            typ_table = Table(typ_table_data, colWidths=[1.8 * inch, 0.9 * inch, 0.8 * inch, 3.5 * inch])
            typ_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(typ_table)

        story.append(Spacer(1, 8))

        # 5. VASP Attribution & Endpoint Resolution
        story.append(Paragraph("5. VIRTUAL ASSET SERVICE PROVIDER (VASP) ATTRIBUTION", section_heading))
        if vasp_resp and vasp_resp.status == "RESOLVED" and vasp_resp.candidates:
            top_v = vasp_resp.candidates[0]
            vasp_text = (
                f"<b>Likely Attributed VASP:</b> {top_v.candidate_name} ({top_v.entity_role})<br/>"
                f"<b>Attribution Score:</b> {top_v.attribution_confidence:.1f}/100 | <b>Confidence Band:</b> {top_v.confidence_band}<br/>"
                f"<b>Matched Endpoint Address:</b> {top_v.endpoint_address} ({top_v.match_position})<br/>"
                f"<b>Hop Distance:</b> {top_v.endpoint_hop_distance} hop(s) | <b>Classification:</b> {top_v.attribution_type}<br/>"
                f"<b>Note:</b> Evidence-backed analytical attribution based on transfer flow continuity; does not constitute legal proof of beneficial ownership."
            )
            story.append(Paragraph(vasp_text, body_style))
            if getattr(top_v, "why_this_vasp", None):
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Why This VASP Match:</b>", body_style))
                for wtv in top_v.why_this_vasp[:5]:
                    story.append(Paragraph(f"• {wtv}", body_style))
        else:
            wallets_cnt = vasp_resp.wallets_traced_count if vasp_resp else len(trace_result.paths)
            tx_cnt = vasp_resp.transactions_traced_count if vasp_resp else 0
            cand_cnt = vasp_resp.candidates_considered_count if vasp_resp else 0
            neg_reason = vasp_resp.negative_reason if (vasp_resp and vasp_resp.negative_reason) else "Traced fund flow endpoints did not match known high-confidence custodial VASP clusters."
            neg_text = (
                f"<b>STATUS: NO HIGH-CONFIDENCE VASP IDENTIFIED</b><br/>"
                f"The traced fund flow did not provide sufficient evidence to associate the endpoint with a known VASP.<br/>"
                f"<b>Investigation Context:</b> {wallets_cnt} wallets traced | {tx_cnt} transactions analyzed | {cand_cnt} candidate entities evaluated.<br/>"
                f"<b>Assessment:</b> {neg_reason}<br/>"
                f"<i>This is a valid investigation result.</i>"
            )
            story.append(Paragraph(neg_text, body_style))

        story.append(Spacer(1, 8))

        # 6. Multi-Hop Fund Tracing Path Ledger
        story.append(Paragraph("6. MULTI-HOP FUND TRACING PATH LEDGER", section_heading))
        path_table_data = [
            [Paragraph("Path ID", table_header_style), Paragraph("Hops", table_header_style), Paragraph("Initial Amt", table_header_style), Paragraph("Final Amt", table_header_style), Paragraph("Retention %", table_header_style), Paragraph("Time", table_header_style), Paragraph("Relevance", table_header_style)]
        ]
        for p in trace_result.paths:
            path_table_data.append([
                Paragraph(p.path_id, table_cell_bold),
                Paragraph(str(p.hop_count), table_cell_style),
                Paragraph(f"${p.initial_amount:,.2f}", table_cell_style),
                Paragraph(f"${p.final_amount:,.2f}", table_cell_style),
                Paragraph(f"{p.value_retention_percent:.1f}%", table_cell_style),
                Paragraph(f"{p.elapsed_time_seconds:.1f}s", table_cell_style),
                Paragraph(f"{p.relevance_score:.1f}", table_cell_style),
            ])
        path_table = Table(path_table_data, colWidths=[1.1 * inch, 0.6 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch, 0.8 * inch, 1.3 * inch])
        path_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(path_table)

        story.append(Spacer(1, 8))

        # 7. Evidence Graph & Source Attribution Ledger
        story.append(Paragraph("7. VERIFIABLE EVIDENCE LEDGER & SOURCE REGISTRY ATTRIBUTION", section_heading))
        ev_table_data = [
            [Paragraph("Evidence ID", table_header_style), Paragraph("Finding / Evidence Summary", table_header_style), Paragraph("Source Name", table_header_style), Paragraph("Confidence", table_header_style)]
        ]
        for e in evidence_items:
            ev_table_data.append([
                Paragraph(e.evidence_id[:12], table_cell_bold),
                Paragraph(e.finding, table_cell_style),
                Paragraph(e.source_name, table_cell_style),
                Paragraph(f"{e.confidence:.2f}", table_cell_style),
            ])
        ev_table = Table(ev_table_data, colWidths=[1.1 * inch, 3.7 * inch, 1.5 * inch, 0.7 * inch])
        ev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(ev_table)

        story.append(Spacer(1, 14))

        # 8. Disclaimer & Legal Safeguards
        disclaimer_box = [
            Paragraph("<b>LEGAL SAFEGUARDS & INVESTIGATIVE DISCLAIMERS:</b>", ParagraphStyle("DiscHead", parent=body_style, fontName="Helvetica-Bold", fontSize=8)),
            Paragraph(
                "1. <b>Non-Criminal Labeling Safeguard:</b> Specter analytical scores, velocity alerts, and typologies reflect objective mathematical and graph structural features of fund movements. They do NOT constitute automated legal findings of criminality or guilt.<br/>"
                "2. <b>No Automatic Freezing:</b> This intelligence report is generated for investigative decision support only. Specter does NOT execute automatic asset freezing or seizure.<br/>"
                "3. <b>Authorised Integration Only:</b> Export packages generated by Specter are formatted for authorised API portal integration (e.g. SAHYOG). Specter performs NO automated external portal submissions without human law enforcement authorisation.<br/>"
                "4. <b>Chain of Custody:</b> All transaction hashes and explorer URLs reference immutable Layer-1 TRON blockchain ledger state.",
                disclaimer_style,
            )
        ]
        disc_table = Table([[disclaimer_box]], colWidths=[7.0 * inch])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(disc_table)

        doc.build(story)
        logger.info(f"PDF Report generated successfully at: {output_path}")
        return os.path.abspath(output_path)
