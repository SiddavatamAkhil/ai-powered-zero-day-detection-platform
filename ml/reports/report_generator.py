"""
Generates a professional PDF report summarizing dataset info, model
comparison, and open-set evaluation results — the deliverable for
Phase 9 (PDF Report Generation) and the research comparison section.

Uses reportlab directly since the report structure is fixed and well
suited to reportlab's flowable model.
"""
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_evaluation_report(
    output_path: str,
    project_title: str,
    dataset_name: str,
    known_classes: list[str],
    unknown_classes: list[str],
    model_results: list[dict],
) -> str:
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], textColor=colors.HexColor("#0B1220"))
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"], textColor=colors.HexColor("#1D4ED8"), spaceBefore=14)
    body_style = styles["BodyText"]

    story = []
    story.append(Paragraph(project_title, title_style))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("1. Dataset Overview", heading_style))
    story.append(Paragraph(f"<b>Dataset:</b> {dataset_name}", body_style))
    story.append(Paragraph(f"<b>Known classes (used for training):</b> {', '.join(known_classes)}", body_style))
    story.append(Paragraph(
        f"<b>Unknown / held-out classes (zero-day simulation):</b> {', '.join(unknown_classes) or 'None configured'}",
        body_style,
    ))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("2. Model Comparison", heading_style))
    story.append(Paragraph(
        "All models were trained on identical known-class splits and evaluated with the same "
        "held-out unknown classes to ensure a fair comparison.",
        body_style,
    ))
    story.append(Spacer(1, 0.3 * cm))

    header = ["Model", "Acc.", "Prec.", "Recall", "F1", "MCC", "ROC-AUC", "FPR", "Unk. Recall", "Train (s)", "Infer (ms)"]
    rows = [header]
    for r in model_results:
        rows.append([
            r.get("model_name", "-"),
            _fmt(r.get("accuracy")),
            _fmt(r.get("precision")),
            _fmt(r.get("recall")),
            _fmt(r.get("f1")),
            _fmt(r.get("mcc")),
            _fmt(r.get("roc_auc")),
            _fmt(r.get("false_positive_rate")),
            _fmt(r.get("unknown_attack_recall")),
            _fmt(r.get("training_time_seconds"), decimals=1),
            _fmt(r.get("inference_time_ms_per_sample"), decimals=2),
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1220")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))

    best_model = max(model_results, key=lambda r: r.get("unknown_attack_recall") or 0) if model_results else None
    if best_model:
        story.append(Paragraph("3. Key Finding", heading_style))
        story.append(Paragraph(
            f"<b>{best_model['model_name']}</b> achieved the highest unknown-attack recall "
            f"({_fmt(best_model.get('unknown_attack_recall'))}), making it the strongest candidate "
            f"for zero-day detection among the architectures compared.",
            body_style,
        ))

    doc.build(story)
    return output_path


def _fmt(value, decimals: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:.{decimals}f}"
