import base64
import binascii
import hashlib
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import models as m
from backend.auth import current_session, require_role, writer
from backend.db import get_db
from backend.schemas import Strict
from backend.services import audit

router = APIRouter(prefix="/api", tags=["Evidence attachments"])


class AttachmentInput(Strict):
    filename: str = Field(min_length=1, max_length=150)
    media_type: Literal["text/plain", "image/png", "image/jpeg", "application/pdf"]
    content_base64: str = Field(min_length=1, max_length=2796204)


def attachment_info(record):
    return {
        "id": record.id,
        "filename": record.filename,
        "media_type": record.media_type,
        "size": len(record.content),
        "sha256": record.sha256,
        "actor": record.actor,
        "timestamp": record.timestamp.isoformat(),
    }


def add_attachment(db, data, session, execution_id=None, result_id=None):
    try:
        content = base64.b64decode(data.content_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, "Attachment must be valid base64") from exc
    if not content or len(content) > 2 * 1024 * 1024:
        raise HTTPException(422, "Evidence attachments must be between 1 byte and 2 MiB")
    signatures = {
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
        "application/pdf": b"%PDF-",
    }
    if data.media_type in signatures and not content.startswith(signatures[data.media_type]):
        raise HTTPException(422, "The attachment signature does not match its media type")
    if data.media_type == "text/plain":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, "Text evidence must use UTF-8") from exc
    filename = re.sub(r"[^a-zA-Z0-9._ -]", "_", data.filename).strip(". ") or "evidence"
    attachment = m.EvidenceAttachment(
        execution_id=execution_id,
        uat_result_id=result_id,
        filename=filename,
        media_type=data.media_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        actor=session.actor,
    )
    db.add(attachment)
    db.flush()
    return attachment


@router.post("/test-executions/{execution_id}/attachments", status_code=201)
def upload_test(
    execution_id: int, data: AttachmentInput, session=Depends(writer), db: Session = Depends(get_db)
):
    require_role(session, "analyst", "tester", "manager")
    execution = db.get(m.TestExecution, execution_id)
    if not execution:
        raise HTTPException(404, "Execution not found")
    attachment = add_attachment(db, data, session, execution_id=execution_id)
    info = attachment_info(attachment)
    audit(db, session.actor, "evidence_attached", db.get(m.TestCase, execution.test_case_id), after=info)
    db.commit()
    return info


@router.post("/uat-results/{result_id}/attachments", status_code=201)
def upload_uat(result_id: int, data: AttachmentInput, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "analyst", "tester", "stakeholder", "manager")
    result = db.get(m.UATResult, result_id)
    if not result:
        raise HTTPException(404, "UAT result not found")
    attachment = add_attachment(db, data, session, result_id=result_id)
    info = attachment_info(attachment)
    audit(db, session.actor, "uat_evidence_attached", db.get(m.UATScenario, result.scenario_id), after=info)
    db.commit()
    return info


@router.get("/attachments")
def list_attachments(
    execution_id: int | None = None,
    uat_result_id: int | None = None,
    session=Depends(current_session),
    db: Session = Depends(get_db),
):
    if (execution_id is None) == (uat_result_id is None):
        raise HTTPException(422, "Supply exactly one execution or UAT result ID")
    query = select(m.EvidenceAttachment)
    query = (
        query.where(m.EvidenceAttachment.execution_id == execution_id)
        if execution_id
        else query.where(m.EvidenceAttachment.uat_result_id == uat_result_id)
    )
    return [attachment_info(a) for a in db.scalars(query)]


@router.get("/attachments/{attachment_id}/download")
def download(attachment_id: int, session=Depends(current_session), db: Session = Depends(get_db)):
    record = db.get(m.EvidenceAttachment, attachment_id)
    if not record:
        raise HTTPException(404, "Attachment not found")
    return Response(
        record.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{record.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
