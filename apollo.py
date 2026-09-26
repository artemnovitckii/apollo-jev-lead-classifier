"""Read saved Apollo contacts and optionally enrich their companies."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

BASE = "https://api.apollo.io/api/v1"


def api_request(path, key, payload=None, query=None):
    url = BASE + path + ("?" + urlencode(query) if query else "")
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"X-Api-Key": key, "Content-Type": "application/json", "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=45) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                raise ValueError("Apollo returned an invalid response object.")
            return data
        except HTTPError as error:
            status = error.code
            retry = error.headers.get("Retry-After", "")
            error.close()
            if status == 429 and attempt < 3:
                time.sleep(min(30, max(2 ** attempt, int(retry))) if retry.isdigit() else 2 ** attempt)
                continue
            raise ValueError(f"Apollo HTTP {status}; check your key, endpoint access and rate limit. See docs/setup-with-ai.md.") from None
        except (URLError, OSError, TimeoutError):
            raise ValueError("Apollo connection failed. Check your connection; no JEV requests were sent.") from None


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("Apollo config must be an object.")
    filters = config.get("filters", {})
    allowed = {"q_keywords", "contact_stage_ids", "contact_label_ids", "sort_by_field", "sort_ascending"}
    if not isinstance(filters, dict) or set(filters) - allowed:
        raise ValueError("Unsupported Apollo filter. Use the saved-contact filters documented in config/apollo.json.")
    if "q_keywords" in filters and not isinstance(filters["q_keywords"], str):
        raise ValueError("Apollo q_keywords must be text.")
    for name in ("contact_stage_ids", "contact_label_ids"):
        if name in filters and (not isinstance(filters[name], list) or not all(isinstance(x, str) and x for x in filters[name])):
            raise ValueError(f"Apollo {name} must be a list of IDs.")
    fields = config.get("custom_fields", {})
    if not isinstance(fields, dict) or set(fields) - {"research_notes", "research_source", "research_date", "message"}:
        raise ValueError("Unsupported Apollo custom-field mapping.")
    if not all(isinstance(v, str) and v for v in fields.values()):
        raise ValueError("Custom-field mappings must contain Apollo field IDs.")
    return filters, fields


def text(value):
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if isinstance(v, (str, int, float)))
    return str(value) if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


def organization_for(contact):
    account = contact.get("account") or {}
    organization = contact.get("organization") or {}
    if not isinstance(account, dict) or not isinstance(organization, dict):
        raise ValueError("Apollo returned malformed company data.")
    return {**account, **{k: v for k, v in organization.items() if v is not None and v != ""}}


def domain_for(organization):
    value = organization.get("primary_domain") or organization.get("domain") or organization.get("website_url")
    if not isinstance(value, str) or not value:
        return ""
    parsed = urlparse(value if "://" in value else "https://" + value)
    domain = (parsed.hostname or "").lower()
    return domain.removeprefix("www.")


def normalize(contact, organization, fields):
    custom = contact.get("typed_custom_fields") or {}
    if not isinstance(custom, dict):
        custom = {}
    return {
        "lead_id": str(contact["id"]), "title": text(contact.get("title")),
        "company": text(organization.get("name") or contact.get("organization_name")),
        "company_domain": domain_for(organization),
        "industry": text(organization.get("industry")),
        "employees": text(organization.get("estimated_num_employees")),
        "description": text(organization.get("short_description")),
        "keywords": text(organization.get("keywords")),
        "technologies": text(organization.get("technology_names")),
        "company_country": text(organization.get("country")),
        **{name: text(custom.get(fields.get(name, "")))
           for name in ("research_notes", "research_source", "research_date", "message")},
    }


def fetch_leads(config, key, limit, enrich=False):
    filters, fields = validate_config(config)
    # Keep page size constant: changing it on the final page would change the offset.
    per_page = min(limit, 100)
    contacts, seen = [], set()
    meta = {"source": "apollo_saved_contacts", "pages_fetched": 0,
            "company_enrichments": 0, "companies_without_domain": 0,
            "partial_results_only": False, "enrichment_enabled": enrich}
    for page in range(1, 501):
        response = api_request("/contacts/search", key, payload={**filters, "page": page, "per_page": per_page})
        meta["pages_fetched"] += 1
        meta["partial_results_only"] |= bool(response.get("partial_results_only"))
        rows = response.get("contacts")
        if not isinstance(rows, list):
            raise ValueError("Apollo response is missing the contacts list.")
        added = 0
        for contact in rows:
            if not isinstance(contact, dict) or not isinstance(contact.get("id"), str) or not contact["id"]:
                raise ValueError("Apollo contact is missing a valid ID.")
            if contact["id"] not in seen:
                seen.add(contact["id"])
                contacts.append(contact)
                added += 1
                if len(contacts) >= limit:
                    break
        pagination = response.get("pagination") or {}
        total_pages = pagination.get("total_pages") if isinstance(pagination, dict) else None
        if len(contacts) >= limit or not rows or (isinstance(total_pages, int) and page >= total_pages):
            break
        if added == 0:
            raise ValueError("Apollo repeated a page without new contacts. Narrow the search and retry.")
        if not pagination and len(rows) < per_page:
            break
    if not contacts:
        raise ValueError("No saved Apollo contacts matched. Check your filters or use a CSV export.")
    cache, leads = {}, []
    for contact in contacts:
        organization = organization_for(contact)
        domain = domain_for(organization)
        if enrich and domain:
            if domain not in cache:
                response = api_request("/organizations/enrich", key, query={"domain": domain})
                enriched = response.get("organization")
                if not isinstance(enriched, dict):
                    raise ValueError("Apollo enrichment returned no organization. Retry without enrichment or check the domain.")
                returned_domain = domain_for(enriched)
                if returned_domain and returned_domain != domain:
                    raise ValueError("Apollo enrichment returned a different domain. Review the company match before proceeding.")
                cache[domain] = enriched
                meta["company_enrichments"] += 1
            organization.update({k: v for k, v in cache[domain].items() if v is not None and v != ""})
        elif enrich:
            meta["companies_without_domain"] += 1
        leads.append(normalize(contact, organization, fields))
    meta["rows_imported"] = len(leads)
    meta["rows_missing_fit_context"] = sum(not all(lead[f] for f in ("title", "company", "industry", "employees")) for lead in leads)
    return leads, meta
