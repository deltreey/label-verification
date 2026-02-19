from logic.ocr import OCR
from logic.required_text import RequiredText


def check_rules(ocr: OCR, fields: dict):
    try:
        # @TODO: we should start by checking that the application is actually what we want to test.

        if ocr.processed_img is None:
            response = {
                "decision": "Human Review",
                "confidence": 0.0,
                "full_text": "",
                "findings": ocr.findings
            }
        # Given this exact text must appear always, let's check for it and reject if it's not there
        basic_check = ocr.has_text('GOVERNMENT WARNING')
        if not basic_check['ok']:
            ocr.findings.append('GOVERNMENT WARNING header not found')
            response = {
                "decision": "Reject",
                "confidence": basic_check['confidence'],
                "full_text": ocr.text,
                "findings": ocr.findings
            }
        else:
            ocr.findings.append('GOVERNMENT WARNING header found')
            # read the form and determine what fields we need to check for
            bevg_type = fields["Product Type"]
            if bevg_type:
                requirements = RequiredText(type=bevg_type.lower())
            else:
                requirements = RequiredText(type="all")
            # for now, we're just reading the required fields
            for item in requirements.as_required_list():
                found = ocr.has_text(item)
                if found:
                    ocr.findings.append(f"Required text '{item}' found")
                else:
                    ocr.findings.append(f"Required text '{item}' not found")
                    response = {
                        "decision": "Reject",
                        "confidence": found['confidence'],
                        "full_text": ocr.text,
                        "findings": ocr.findings
                    }
                    return response
            # Get type designation
            type = None
            for item in requirements.as_type_list():
                found = ocr.has_text(item)
                print(f"Checking for '{item}': {found}")
                if found:
                    type = item
                    ocr.findings.append(f"Type Designation '{type}' found")
                    break
            if type is None:
                ocr.findings.append(f"Type Designation not found")
                response = {
                    "decision": "Reject",
                    "confidence": 0.0,
                    "full_text": ocr.text,
                    "findings": ocr.findings
                }
            else:
                response = {
                    "decision": "Human Review",
                    "confidence": 0.0,
                    "full_text": ocr.text,
                    "findings": ocr.findings
                }
            # @TODO: continue testing other requirements here
    except Exception as err:
        response = {
            "decision": "Human Review",
            "confidence": 0.0,
            "full_text": "",
            "findings": ["Error Occurred", f"Exception: {err}"]
        }
    return response
