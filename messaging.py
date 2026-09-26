"""Company-specific drafts from editable templates, checked by JEV before review."""
import json
from pathlib import Path
from string import Formatter
from urllib.parse import urlsplit


def load_config(path, offer):
    config = json.loads(Path(path).read_text())
    if not isinstance(config, dict):
        raise ValueError("Messaging config must be an object.")
    for field in ("sender_name", "booking_url", "call_to_action"):
        if not isinstance(config.get(field), str):
            raise ValueError(f"Messaging config needs a {field} string.")
    if not config["call_to_action"].strip():
        raise ValueError("Set a call_to_action in the messaging config.")
    if config["booking_url"]:
        url = urlsplit(config["booking_url"])
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or any(c.isspace() for c in config["booking_url"])):
            raise ValueError("booking_url must be a public HTTPS link, or blank.")
    templates = config.get("templates")
    angles = set(offer["criteria"]["angle"]) - {"unknown"}
    if not isinstance(templates, dict) or set(templates) != angles:
        raise ValueError("Provide one message template for each known service angle.")
    for angle, template in templates.items():
        for field in ("subject", "body"):
            value = template.get(field) if isinstance(template, dict) else None
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Template {angle} needs {field} text.")
            for _, name, spec, conversion in Formatter().parse(value):
                if name is not None and (name not in {"company", "title"} or spec or conversion):
                    raise ValueError("Templates support only {company} and {title}, without formatting.")
    return config


def prepare(lead, classification, config, threshold):
    """Preserve all rows; only confident fits with a supported angle get drafts."""
    row = {"lead_id": lead["lead_id"], "company": lead["company"],
           "angle": classification["angle"], "subject": "", "message": "",
           "draft_check": "not_checked", "draft_check_confidence": "",
           "status": "", "error": "", "original_message": lead["message"],
           "research_source": lead["research_source"], "research_date": lead["research_date"]}
    if classification["error"]:
        row["status"] = "skipped_classification_error"
    elif classification["fit"] == "poor_fit":
        row["status"] = "skipped_poor_fit"
    elif (classification["fit"] != "good_fit" or classification["angle"] == "unknown"
          or any(classification[f"{field}_confidence"] < threshold for field in ("fit", "angle"))):
        row["status"] = "skipped_uncertain"
    elif not lead["company"].strip():
        row["status"] = "skipped_missing_company"
    else:
        # Research notes choose the angle via JEV; they are not pasted into a pitch.
        values = {field: " ".join(lead[field].split()) for field in ("company", "title")}
        template = config["templates"][classification["angle"]]
        row["subject"] = template["subject"].format_map(values)
        parts = [template["body"].format_map(values), config["call_to_action"].strip()]
        if config["booking_url"]:
            parts.append(config["booking_url"])
        if config["sender_name"].strip():
            parts.append(config["sender_name"].strip())
        row["message"] = "\n\n".join(parts)
        row["status"] = "pending_check"
    return row


def check(row, lead, offer, model, key, make_request, post, validate):
    """Check the exact subject and body without overwriting the original decisions."""
    body = make_request({**lead, "message": f"Subject: {row['subject']}\n\n{row['message']}"}, offer, model)
    body["questions"] = {"message_check": body["questions"]["message_check"]}
    response = None
    try:
        response = post(body, key)
        answer = validate(response, body)["message_check"]
        row["draft_check"] = answer["choice"]
        row["draft_check_confidence"] = answer["confidence"]
        if answer["choice"] == "unknown" or answer["confidence"] < offer["review_threshold"]:
            row["status"] = "research_or_review"
        elif answer["choice"] == "mismatch":
            row["status"] = "revise_message"
        else:
            row["status"] = "review_before_sending"
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        row.update(status="error_review", error=str(error))
        if response is None:
            response = {"error": str(error)}
    return body, response
