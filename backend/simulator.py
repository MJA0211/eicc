"""Local protocol fixtures. No user-controlled host, command, script or outbound transport."""

import asyncio
import json
import time
import xml.etree.ElementTree as ET

import httpx
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import Field, StrictStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import models as m
from backend.auth import current_session
from backend.db import get_db
from backend.schemas import Scenario, Strict

router = APIRouter(
    prefix="/simulator", tags=["Local integration simulators"], dependencies=[Depends(current_session)]
)
SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ERRORS = {"bad_request": 400, "unauthorized": 401, "not_found": 404, "conflict": 409, "server_error": 500}


class CasePayload(Strict):
    case_id: StrictStr = Field(min_length=1, max_length=80)
    status: StrictStr = Field(min_length=1, max_length=30)
    recipient: StrictStr = Field(default="owner@example.test", max_length=200)


async def controlled(scenario):
    if scenario == "timeout":
        await asyncio.sleep(0.15)
        return JSONResponse({"error": "Controlled simulator timeout"}, status_code=504)
    if scenario in ERRORS:
        return JSONResponse(
            {"error": f"Controlled {scenario.replace('_', ' ')}"}, status_code=ERRORS[scenario]
        )
    return None


@router.post("/cases")
async def create_case(payload: CasePayload, scenario: Scenario = "success", db: Session = Depends(get_db)):
    failure = await controlled(scenario)
    if failure:
        return failure
    existing = db.scalar(select(m.SimulatorCase).where(m.SimulatorCase.case_id == payload.case_id))
    if existing:
        if existing.payload == payload.model_dump():
            return JSONResponse(
                {"case_id": existing.case_id, "status": existing.status, "idempotent": True}, status_code=201
            )
        raise HTTPException(409, "Case ID already exists with different content")
    db.add(m.SimulatorCase(case_id=payload.case_id, status=payload.status, payload=payload.model_dump()))
    db.commit()
    return JSONResponse(
        {"case_id": payload.case_id, "status": payload.status, "created": True}, status_code=201
    )


@router.get("/cases/{case_id}")
async def get_case(case_id: str, scenario: Scenario = "success", db: Session = Depends(get_db)):
    failure = await controlled(scenario)
    if failure:
        return failure
    record = db.scalar(select(m.SimulatorCase).where(m.SimulatorCase.case_id == case_id))
    if not record:
        raise HTTPException(404, "Case not found")
    return {"case_id": record.case_id, "status": record.status}


@router.post("/notifications")
async def notification(payload: CasePayload, scenario: Scenario = "success", asynchronous: bool = False):
    failure = await controlled(scenario)
    if failure:
        return failure
    if "@" not in payload.recipient or not payload.recipient.endswith(".test"):
        raise HTTPException(400, "Simulator recipient must be an example .test address")
    return JSONResponse(
        {
            "case_id": payload.case_id,
            "status": "QUEUED" if asynchronous else "DELIVERED",
            "recipient": payload.recipient,
            "simulated": True,
        },
        status_code=202 if asynchronous else 201,
    )


def soap_response(body, status=200):
    envelope = ET.Element(f"{{{SOAP}}}Envelope")
    ET.SubElement(envelope, f"{{{SOAP}}}Body").append(body)
    return Response(ET.tostring(envelope, encoding="unicode"), status_code=status, media_type="text/xml")


def fault(message):
    body = ET.Element(f"{{{SOAP}}}Fault")
    ET.SubElement(body, "faultcode").text = "Client.Validation"
    ET.SubElement(body, "faultstring").text = message
    return soap_response(body, 500)


@router.post("/soap")
async def soap(request: Request, scenario: Scenario = "success"):
    if scenario == "timeout":
        await asyncio.sleep(0.15)
        return fault("Controlled legacy timeout")
    if scenario != "success":
        return fault(f"Controlled legacy {scenario}")
    try:
        root = fromstring(await request.body())
        if root.tag != f"{{{SOAP}}}Envelope":
            return fault("SOAP 1.1 Envelope is required")
        body = root.find(f"{{{SOAP}}}Body/CreateCase")
        if body is None:
            return fault("CreateCase action is required")
        case = body.find("case_id")
        if case is None or not case.text or case.get(f"{{{XSI}}}type") != "xsd:string":
            return fault(
                "case_id must be xsd:string; integer identifiers are rejected by the legacy contract"
            )
        result = ET.Element("CreateCaseResponse")
        ET.SubElement(result, "case_id").text = case.text
        ET.SubElement(result, "status").text = "CREATED"
        return soap_response(result)
    except (ET.ParseError, DefusedXmlException):
        return fault("Malformed or unsafe XML")


def apply_mappings(payload, mappings):
    if not mappings:
        return dict(payload)
    transformed = {}
    for mapping in mappings:
        value = payload.get(mapping.source_field)
        if value is None:
            if mapping.required:
                raise ValueError(f"Required source field {mapping.source_field} is missing")
            continue
        transform = mapping.transformation
        if transform == "to_string":
            value = str(value)
        elif transform == "to_integer":
            value = int(value)
        elif transform == "uppercase":
            value = str(value).upper()
        elif transform == "lowercase":
            value = str(value).lower()
        elif transform != "identity":
            raise ValueError("Unknown mapping transformation")
        if mapping.validation_rule == "non_empty" and not str(value).strip():
            raise ValueError(f"{mapping.source_field} cannot be empty")
        if mapping.validation_rule == "positive" and float(value) <= 0:
            raise ValueError(f"{mapping.source_field} must be positive")
        if mapping.validation_rule == "email" and "@" not in str(value):
            raise ValueError(f"{mapping.source_field} must be an email address")
        transformed[mapping.target_field] = value
    return transformed


async def execute_local(request, db, test, actor):
    integration = db.get(m.Integration, test.integration_id) if test.integration_id else None
    if not integration:
        raise HTTPException(
            422,
            "Automated tests require a linked local integration; use manual evidence for functional tests",
        )
    mappings = list(db.scalars(select(m.FieldMapping).where(m.FieldMapping.integration_id == integration.id)))
    start = time.perf_counter()
    try:
        payload = apply_mappings(test.payload, mappings)
    except (ValueError, TypeError, OverflowError) as exc:
        return m.TestExecution(
            test_case_id=test.id,
            executed_by=actor,
            status="BLOCKED",
            actual_result=str(exc),
            evidence="Local field-mapping validation stopped the request",
            request_body=json.dumps(test.payload),
            response_body="",
        )
    endpoint = integration.endpoint
    if endpoint not in {
        "/simulator/cases",
        "/simulator/cases/{id}",
        "/simulator/notifications",
        "/simulator/soap",
    }:
        raise HTTPException(422, "Only registered local simulator routes are executable")
    headers = {"X-CSRF-Token": request.headers.get("X-CSRF-Token", "")}
    params = {"scenario": test.scenario}
    if integration.protocol == "SOAP":
        envelope = ET.Element(f"{{{SOAP}}}Envelope", {"xmlns:xsd": "http://www.w3.org/2001/XMLSchema"})
        body = ET.SubElement(ET.SubElement(envelope, f"{{{SOAP}}}Body"), "CreateCase")
        for name, value in payload.items():
            ET.SubElement(
                body, name, {f"{{{XSI}}}type": "xsd:string" if isinstance(value, str) else "xsd:int"}
            ).text = str(value)
        request_body = ET.tostring(envelope, encoding="unicode")
        headers.update({"Content-Type": "text/xml", "SOAPAction": "CreateCase"})
        kwargs = {"content": request_body}
        method = "POST"
    else:
        request_body = json.dumps(payload, indent=2)
        kwargs = {"json": payload}
        method = integration.method
        if endpoint.endswith("{id}"):
            from urllib.parse import quote

            endpoint = endpoint.replace("{id}", quote(str(payload.get("case_id", "")), safe=""))
            kwargs = {}
        if integration.mode == "ASYNCHRONOUS":
            params["asynchronous"] = "true"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=request.app),
        base_url="http://eicc.local",
        cookies=dict(request.cookies),
        headers=headers,
    ) as client:
        try:
            response = await asyncio.wait_for(
                client.request(method, endpoint, params=params, **kwargs),
                timeout=0.08 if test.scenario == "timeout" else 5,
            )
            code, response_body = response.status_code, response.text
            schema_valid = True
            if code < 300:
                if integration.protocol == "SOAP":
                    parsed = fromstring(response.text)
                    schema_valid = parsed.find(f"{{{SOAP}}}Body/CreateCaseResponse/case_id") is not None
                else:
                    data = response.json()
                    schema_valid = isinstance(data.get("case_id"), str) and isinstance(
                        data.get("status"), str
                    )
            passed = code == test.expected_status and schema_valid
            actual = f"Expected HTTP {test.expected_status}; received HTTP {code}. Response schema {'valid' if schema_valid else 'invalid'}."
        except TimeoutError:
            code, response_body, passed = (
                504,
                "Local simulator exceeded the controlled 80 ms deadline",
                test.expected_status == 504,
            )
            actual = "Timed out waiting for the local simulator (80 ms deadline)."
    return m.TestExecution(
        test_case_id=test.id,
        executed_by=actor,
        status="PASS" if passed else "FAIL",
        actual_result=actual,
        evidence="Captured from an actual in-process HTTP exchange with the local simulator",
        request_body=request_body,
        response_body=response_body,
        response_status=code,
        duration_ms=round((time.perf_counter() - start) * 1000),
    )
