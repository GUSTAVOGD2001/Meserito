"""Ticket rendering and printing helpers for Meserito."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Optional

from PyQt6.QtCore import QMarginsF, QSizeF
from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo


def ensure_ticket_output_path(
    timestamp: datetime, order_id: int, *, ensure_closed: bool = True
) -> Path:
    """Create the ticket folder structure and return the target PDF path."""

    safe_timestamp = timestamp or datetime.utcnow()
    date_folder = safe_timestamp.strftime("%Y-%m-%d")
    output_dir = Path("tickets") / date_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    if ensure_closed:
        filename = f"ticket_{order_id}.pdf"
    else:
        filename = f"ticket_{order_id}_preview.pdf"
    return output_dir / filename


def render_ticket_html(
    *,
    restaurant_name: str,
    receipt_title: str,
    mesa: Optional[str],
    mesero: Optional[str],
    items: Iterable[Mapping[str, object]],
    subtotal_cents: int,
    discount_cents: int,
    tax_cents: int,
    total_cents: int,
    payment_type: Optional[str],
    card_last4: Optional[str],
    created_at: datetime,
    message: str = "¡Gracias por su visita!",
) -> str:
    """Generate a rich HTML representation for an 80mm ticket."""

    created_display = created_at.strftime("%d/%m/%Y %H:%M")
    mesa_text = mesa or "-"
    mesero_text = mesero or "-"
    payment_display = (payment_type or "Pendiente").title()
    if payment_display.lower() == "tarjeta" and card_last4:
        payment_display = f"Tarjeta (**** {card_last4})"

    def _format_amount(cents: int) -> str:
        return f"${cents / 100:.2f}"

    lines: list[str] = []
    for item in items:
        qty = int(item.get("qty", 0))
        name = str(item.get("name", ""))
        total_cents = int(item.get("total_cents", 0))
        lines.append(
            """
            <tr>
                <td class="qty">{qty}x</td>
                <td class="desc">{name}</td>
                <td class="amount">{amount}</td>
            </tr>
            """.format(qty=qty, name=name, amount=_format_amount(total_cents))
        )

    items_html = "\n".join(lines) or "<tr><td colspan='3'>Sin productos</td></tr>"

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{ font-family: 'DejaVu Sans Mono', monospace; font-size: 10pt; margin: 0; color: #0F1216; }}
          .ticket {{ width: 100%; padding: 4px 0; color: #0F1216; }}
          h1 {{ font-size: 16pt; margin: 0; text-align: center; text-transform: uppercase; }}
          h3 {{ font-size: 12pt; margin: 4px 0 12px; text-align: center; letter-spacing: 1px; }}
          .meta {{ font-size: 9pt; margin-bottom: 10px; }}
          .meta div {{ margin-bottom: 2px; }}
          table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
          th, td {{ padding: 2px 0; text-align: left; }}
          .qty {{ width: 18%; }}
          .desc {{ width: 52%; }}
          .amount {{ width: 30%; text-align: right; }}
          .totals {{ margin-top: 8px; border-top: 1px dashed #161A20; padding-top: 6px; }}
          .totals div {{ display: flex; justify-content: space-between; margin-bottom: 2px; }}
          .totals .grand {{ font-size: 12pt; font-weight: 700; margin-top: 6px; }}
          .footer {{ margin-top: 12px; text-align: center; font-size: 9pt; }}
        </style>
      </head>
      <body>
        <div class="ticket">
          <h1>{restaurant_name}</h1>
          <h3>{receipt_title}</h3>
          <div class="meta">
            <div><strong>Mesa:</strong> {mesa_text}</div>
            <div><strong>Mesero:</strong> {mesero_text}</div>
            <div><strong>Fecha:</strong> {created_display}</div>
          </div>
          <table>
            <thead>
              <tr>
                <th class="qty">Cant</th>
                <th class="desc">Descripción</th>
                <th class="amount">Importe</th>
              </tr>
            </thead>
            <tbody>
              {items_html}
            </tbody>
          </table>
          <div class="totals">
            <div><span>Subtotal</span><span>{_format_amount(subtotal_cents)}</span></div>
            <div><span>Descuento</span><span>{_format_amount(discount_cents)}</span></div>
            <div><span>Impuestos</span><span>{_format_amount(tax_cents)}</span></div>
            <div class="grand"><span>Total</span><span>{_format_amount(total_cents)}</span></div>
          </div>
          <div class="meta" style="margin-top: 8px;">
            <div><strong>Forma de pago:</strong> {payment_display}</div>
          </div>
          <div class="footer">{message}</div>
        </div>
      </body>
    </html>
    """
    return html


def print_ticket_document(
    payload: Mapping[str, object],
    output_path: Path,
    *,
    printer_name: Optional[str] = None,
) -> Optional[Path]:
    """Render the given ticket payload and print it on an 80mm layout."""

    html = render_ticket_html(
        restaurant_name=str(payload.get("restaurant_name", "Meserito")).upper(),
        receipt_title=str(payload.get("receipt_title", "RECIBO DE COBRO")).upper(),
        mesa=str(payload.get("mesa", "")) if payload.get("mesa") is not None else None,
        mesero=str(payload.get("mesero", "")) if payload.get("mesero") else None,
        items=payload.get("items", []) or [],
        subtotal_cents=int(payload.get("subtotal_cents", 0)),
        discount_cents=int(payload.get("discount_cents", 0)),
        tax_cents=int(payload.get("tax_cents", 0)),
        total_cents=int(payload.get("total_cents", 0)),
        payment_type=payload.get("payment_type"),
        card_last4=payload.get("card_last4"),
        created_at=payload.get("created_at") or datetime.utcnow(),
    )

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    page_size = QPageSize(QSizeF(80.0, 2000.0), QPageSize.Unit.Millimeter)
    printer.setPageSize(page_size)
    printer.setPageMargins(QMarginsF(3, 3, 3, 3), QPageLayout.Unit.Millimeter)
    printer.setColorMode(QPrinter.ColorMode.GrayScale)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if printer_name:
        printer.setPrinterName(printer_name)
    else:
        default_printer = QPrinterInfo.defaultPrinter()
        if default_printer.isNull():
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(output_path))
        else:
            printer.setPrinterName(default_printer.printerName())

    if printer.outputFormat() == QPrinter.OutputFormat.NativeFormat and not printer.isValid():
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))
    elif printer.outputFormat() == QPrinter.OutputFormat.PdfFormat:
        printer.setOutputFileName(str(output_path))

    document = QTextDocument()
    document.setDefaultFont(QFont("DejaVu Sans Mono", 10))
    document.setHtml(html)
    document.setPageSize(page_size.sizePoints())
    # TODO: Incorporar impresión directa a múltiples impresoras configurables.
    document.print_(printer)

    if printer.outputFormat() == QPrinter.OutputFormat.PdfFormat:
        return Path(printer.outputFileName()) if printer.outputFileName() else output_path
    return None
