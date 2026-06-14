"""
Lab result importers: HL7 v2 ORU^R01 and FHIR R4 DiagnosticReport.

Both parsers are deliberately zero-dependency and tolerant: in-house veterinary
analyzers (IDEXX, Heska, Abaxis) emit slightly divergent HL7, so we extract the
fields LabResult needs (panel, date, analyte map) and ignore everything else.

Output shape (consumed by LabResultViewSet import actions):
    {
        'panel_name': str,
        'result_date': 'YYYY-MM-DD',
        'result_type': str,           # inferred from panel name, default 'other'
        'lab_name': str,
        'result_data': {analyte: {value, unit, ref_low, ref_high, flag}},
    }
"""

from datetime import date, datetime

# Keyword → LabResult.result_type inference (case-insensitive substring match).
_RESULT_TYPE_KEYWORDS = [
    (('cbc', 'hemogram', 'hematol', 'blood count'), 'hematology'),
    (('chem', 'biochem', 'metabolic', 'electrolyte'), 'biochemistry'),
    (('urin',), 'urinalysis'),
    (('cytol',), 'cytology'),
    (('serol', 'antibod', 'titer', 'elisa'), 'serology'),
    (('culture', 'microb', 'sensitivity'), 'microbiology'),
]


def _infer_result_type(panel_name):
    low = (panel_name or '').lower()
    for keywords, rtype in _RESULT_TYPE_KEYWORDS:
        if any(k in low for k in keywords):
            return rtype
    return 'other'


def _parse_hl7_ts(value):
    """HL7 TS (YYYYMMDD[HHMMSS...]) → ISO date string; today on failure."""
    digits = (value or '')[:8]
    try:
        return datetime.strptime(digits, '%Y%m%d').date().isoformat()
    except ValueError:
        return date.today().isoformat()


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# HL7 v2 ORU^R01
# ---------------------------------------------------------------------------

def parse_hl7_oru(message):
    """
    Parse a raw HL7 v2 ORU^R01 message into the LabResult import dict.

    Handles the segments that matter (MSH, OBR, OBX); component separator and
    field separator are read from MSH per spec. Raises ValueError on messages
    that are not parseable HL7.
    """
    if not message or not message.strip():
        raise ValueError('Empty HL7 message.')

    segments = [s for s in message.replace('\r\n', '\r').replace('\n', '\r').split('\r') if s.strip()]
    msh = next((s for s in segments if s.startswith('MSH')), None)
    if msh is None or len(msh) < 8:
        raise ValueError('No MSH segment found — not an HL7 message.')

    field_sep = msh[3]                      # char right after 'MSH'
    comp_sep = msh[4] if len(msh) > 4 else '^'

    def fields(segment):
        return segment.split(field_sep)

    def comp(field_value, index=1):
        """1-based component from a ^-composite field; '' when absent."""
        parts = (field_value or '').split(comp_sep)
        return parts[index - 1] if len(parts) >= index else ''

    msh_fields = fields(msh)
    # MSH-4 sending facility (index 3 after the segment name token split)
    lab_name = comp(msh_fields[3]) if len(msh_fields) > 3 else ''

    panel_name = ''
    result_date = date.today().isoformat()
    analytes = {}

    for seg in segments:
        seg_fields = fields(seg)
        seg_type = seg_fields[0]

        if seg_type == 'OBR':
            # OBR-4 universal service identifier: code^text^system
            if len(seg_fields) > 4:
                panel_name = comp(seg_fields[4], 2) or comp(seg_fields[4], 1)
            # OBR-7 observation date/time
            if len(seg_fields) > 7 and seg_fields[7]:
                result_date = _parse_hl7_ts(seg_fields[7])

        elif seg_type == 'OBX':
            # OBX-3 identifier, OBX-5 value, OBX-6 units, OBX-7 ref range, OBX-8 flag
            name = comp(seg_fields[3], 2) or comp(seg_fields[3], 1) if len(seg_fields) > 3 else ''
            if not name:
                continue
            value = _num(seg_fields[5]) if len(seg_fields) > 5 else None
            unit = comp(seg_fields[6]) if len(seg_fields) > 6 else ''
            ref_low = ref_high = None
            if len(seg_fields) > 7 and '-' in (seg_fields[7] or ''):
                lo, _, hi = seg_fields[7].partition('-')
                ref_low, ref_high = _num(lo), _num(hi)
            flag = (seg_fields[8] or 'N').strip() if len(seg_fields) > 8 and seg_fields[8] else 'N'
            analytes[name] = {
                'value': value if value is not None else (seg_fields[5] if len(seg_fields) > 5 else ''),
                'unit': unit,
                'ref_low': ref_low,
                'ref_high': ref_high,
                'flag': flag,
            }

    if not analytes:
        raise ValueError('No OBX result segments found in the HL7 message.')

    panel_name = panel_name or 'Imported HL7 panel'
    return {
        'panel_name': panel_name,
        'result_date': result_date,
        'result_type': _infer_result_type(panel_name),
        'lab_name': lab_name,
        'result_data': analytes,
    }


# ---------------------------------------------------------------------------
# FHIR R4 DiagnosticReport
# ---------------------------------------------------------------------------

def parse_fhir_diagnostic_report(payload):
    """
    Parse a FHIR R4 DiagnosticReport (with contained Observation resources)
    into the LabResult import dict. Raises ValueError for non-conformant input.
    """
    if not isinstance(payload, dict) or payload.get('resourceType') != 'DiagnosticReport':
        raise ValueError("Payload must be a FHIR resource with resourceType 'DiagnosticReport'.")

    code = payload.get('code') or {}
    panel_name = (
        code.get('text')
        or next((c.get('display') for c in code.get('coding', []) if c.get('display')), '')
        or 'Imported FHIR panel'
    )

    effective = payload.get('effectiveDateTime') or payload.get('issued') or ''
    result_date = effective[:10] if len(effective) >= 10 else date.today().isoformat()

    performer = payload.get('performer') or []
    lab_name = performer[0].get('display', '') if performer and isinstance(performer[0], dict) else ''

    analytes = {}
    for resource in payload.get('contained', []):
        if resource.get('resourceType') != 'Observation':
            continue
        obs_code = resource.get('code') or {}
        name = (
            obs_code.get('text')
            or next((c.get('display') for c in obs_code.get('coding', []) if c.get('display')), '')
        )
        if not name:
            continue

        quantity = resource.get('valueQuantity') or {}
        ref_low = ref_high = None
        for rr in resource.get('referenceRange', []):
            ref_low = (rr.get('low') or {}).get('value', ref_low)
            ref_high = (rr.get('high') or {}).get('value', ref_high)

        flag = 'N'
        for interp in resource.get('interpretation', []):
            for coding in interp.get('coding', []):
                if coding.get('code'):
                    flag = coding['code']
                    break

        analytes[name] = {
            'value': quantity.get('value', resource.get('valueString', '')),
            'unit': quantity.get('unit', ''),
            'ref_low': ref_low,
            'ref_high': ref_high,
            'flag': flag,
        }

    if not analytes:
        raise ValueError('No contained Observation resources found in the DiagnosticReport.')

    return {
        'panel_name': panel_name,
        'result_date': result_date,
        'result_type': _infer_result_type(panel_name),
        'lab_name': lab_name,
        'result_data': analytes,
    }
