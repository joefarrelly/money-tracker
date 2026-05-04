import email as email_lib
import imaplib
import logging
import os
import re
from datetime import datetime
from email.header import decode_header as _decode_header
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

EMAIL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "email"))


def _env(key: str) -> str:
    return os.environ.get(key, "")


def _decode_str(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    parts = _decode_header(str(value))
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return "".join(out)


def _classify_subject(subject: str) -> str | None:
    lower = subject.lower()
    if "payslip" in lower:
        return "payslip"
    if "bank" in lower:
        return "bank_statement"
    return None


def poll_emails(db) -> int:
    """Check inbox for new PDF emails and create pending EmailImport records."""
    address = _env("EMAIL_ADDRESS")
    password = _env("EMAIL_APP_PASSWORD")
    label = _env("EMAIL_LABEL") or "INBOX"

    if not address or not password:
        logger.warning("Email credentials not configured — skipping poll")
        return 0

    from models import EmailImport

    os.makedirs(EMAIL_DIR, exist_ok=True)

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(address, password)
        mail.select(label)
    except Exception as exc:
        logger.error("IMAP connection failed: %s", exc)
        raise RuntimeError(f"Could not connect to Gmail: {exc}") from exc

    _, barr = mail.search(None, '(OR SUBJECT "payslip" SUBJECT "bank")')
    message_nums = barr[0].split() if barr and barr[0] else []

    new_count = 0
    for num in message_nums:
        try:
            _, data = mail.fetch(num, "(RFC822)")
            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)

            message_id = msg.get("Message-ID", "").strip()
            if not message_id:
                continue

            subject = _decode_str(msg.get("Subject", ""))
            import_type = _classify_subject(subject)
            if not import_type:
                continue

            sender = _decode_str(msg.get("From", ""))
            try:
                received_at = parsedate_to_datetime(msg.get("Date", ""))
                received_at = received_at.replace(tzinfo=None)
            except Exception:
                received_at = datetime.utcnow()

            pdfs = _extract_pdfs(msg)
            if not pdfs:
                continue

            for filename, payload in pdfs:
                uid = f"{message_id}::{filename}"
                if db.query(EmailImport).filter_by(message_id=uid).first():
                    continue

                safe = re.sub(r"[^\w\-.]", "_", f"{re.sub(r'[<>]', '', message_id)}_{filename}")[:120]
                save_path = os.path.join(EMAIL_DIR, safe)
                with open(save_path, "wb") as f:
                    f.write(payload)

                raw_data, error = _parse_pdf(save_path, import_type, db)
                db.add(EmailImport(
                    message_id=uid,
                    subject=subject,
                    sender=sender,
                    received_at=received_at,
                    filename=filename,
                    import_type=import_type,
                    status="pending" if raw_data else "failed",
                    error_message=error,
                    file_path=save_path,
                    raw_data=raw_data,
                ))
                new_count += 1

        except Exception as exc:
            logger.error("Error processing message %s: %s", num, exc)
            continue

    if new_count:
        db.commit()
    mail.logout()
    return new_count


def _extract_pdfs(msg) -> list[tuple[str, bytes]]:
    pdfs = []
    for part in msg.walk():
        ct = part.get_content_type()
        fname = part.get_filename()
        if fname:
            fname = _decode_str(fname)
        if ct == "application/pdf" or (fname and fname.lower().endswith(".pdf")):
            payload = part.get_payload(decode=True)
            if payload:
                pdfs.append((fname or "attachment.pdf", payload))
    return pdfs


def _parse_pdf(file_path: str, import_type: str, db) -> tuple[dict | None, str | None]:
    if import_type == "payslip":
        return _parse_payslip(file_path)
    return _parse_bank_statement(file_path, db)


def _parse_payslip(file_path: str) -> tuple[dict | None, str | None]:
    try:
        from parsers.payslip import parse_payslip_pdf
        p = parse_payslip_pdf(file_path)
        if p["date"] is None:
            return None, "Could not extract date from payslip"
        return {
            "date": str(p["date"]),
            "employer": p["employer"],
            "ni_number": p.get("ni_number"),
            "net_pay": p["net_pay"],
            "gross_pay": p["gross_pay"],
            "line_items": p["line_items"],
        }, None
    except Exception as exc:
        return None, str(exc)


def _parse_bank_statement(file_path: str, db) -> tuple[dict | None, str | None]:
    try:
        from models import StatementFormat
        from parsers import universal

        formats = db.query(StatementFormat).all()
        preview = universal.extract_preview(
            file_path, filename=os.path.basename(file_path), saved_formats=formats
        )

        mapping = preview["proposed_mapping"]
        year = preview.get("detected_year") if not preview.get("needs_year") else None
        df = universal.parse_with_mapping(file_path, mapping, year=year, skip_patterns=[])

        if df.empty:
            return None, "No transactions could be parsed — upload manually via the Upload page"

        text = universal._extract_text(file_path)
        account_number = universal.detect_account_number(text) or "unknown"
        fmt = preview.get("matched_format")

        txns = []
        for _, row in df.iterrows():
            bal = row.get("balance")
            txns.append({
                "date": str(row["date"].date()),
                "description": str(row["description"]),
                "amount": round(float(row["amount"]), 2),
                "balance": round(float(bal), 2) if bal and bal == bal else None,
            })

        return {
            "account_number": account_number,
            "bank_name": fmt.name.lower() if fmt else "unknown",
            "format_id": fmt.id if fmt else None,
            "format_name": fmt.name if fmt else None,
            "transaction_count": len(txns),
            "transactions": txns,
        }, None
    except Exception as exc:
        return None, str(exc)
