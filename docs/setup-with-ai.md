# Clone it and let your AI help set it up

Give your coding assistant this repository and the prompt below. It contains the Apollo importer, JEV classifier, editable criteria, message templates, key setup and checks. You supply your own accounts and tell it what a good prospect looks like.

## Copy this prompt

> Set up this Apollo + JEV lead classifier for me. Read AGENTS.md and docs/setup-with-ai.md. Ask about my offer, target buyer, exclusions and the services I want to match to prospects, then configure the criteria and message templates. Ask for my call invitation, optional booking URL and sender name. Update config/messages.json with one truthful template per service angle. Help me connect either my saved Apollo contacts or an Apollo CSV. Show me how to enter my API keys privately with configure.py, and never ask me to paste keys into this conversation. Run the local checks, then import a preview of 10 contacts once Apollo is configured. Tell me which fields are missing and whether company enrichment would help. I want the setup ready to qualify my list and create personalized message drafts with --draft-messages. Explain which drafts need revision or research and which are ready for my review before sending. Do not send messages. Clearly distinguish offline checks from a successful live run.

## What you need

- Python 3.10 or newer. Windows users can substitute `py` for `python3`.
- A TypeSafe account with JEV API access for live classification.
- For direct import: an Apollo key allowed to use `api/v1/contacts/search`, and contacts already saved in your Apollo account. Follow [Apollo's key instructions](https://docs.apollo.io/docs/create-api-key).
- If you opt into company enrichment, the key also needs `api/v1/organizations/enrich`. This can consume Apollo credits. Check your account's current access and costs.

An AI cannot supply those accounts or keys for you. CSV preview works without either account.

## First run

```sh
git clone https://github.com/artemnovitckii/apollo-jev-lead-classifier.git
cd apollo-jev-lead-classifier
python3 configure.py
python3 lead_classifier.py --doctor
python3 -m unittest discover -s tests -v
```

Run `configure.py` yourself in a terminal. It hides input and writes `.env`, which Git ignores. It preserves an existing file instead of overwriting it. Both keys can also be set as environment variables. The doctor checks whether values exist; it does not validate them with either provider.

Configure your offer before processing real leads. Then read up to 10 saved Apollo contacts and prepare their JEV requests:

```sh
python3 lead_classifier.py --source apollo --preview --limit 10 --output output-apollo-preview
```

This calls Apollo. It makes no JEV calls. Inspect `imported-leads.csv`, `source-summary.json` and `requests.jsonl`. The default Apollo config has no filters, so it reads the first saved contacts returned by Apollo.

If the imported records have enough context, classify that exact saved snapshot without fetching Apollo again:

```sh
python3 lead_classifier.py --input output-apollo-preview/imported-leads.csv --live --draft-messages --limit 10 --output output-first-results
```

Or fetch and classify in one command:

```sh
python3 lead_classifier.py --source apollo --live --draft-messages --limit 10 --output output-direct-results
```

Open message_drafts.csv alongside classified.csv. Confident fits with a supported service get a company-specific template draft, call invitation and optional booking link, followed by a separate JEV check. Review the status before using any message. See [messaging setup](messaging.md).

Live mode uses JEV API credits. Each generated draft adds a JEV check. Increase the row limit only when ready. Use a new output folder for every run.

## Choose the saved contacts

Copy `config/apollo.json` to `config/apollo.local.json` and edit `filters`. Local config files are ignored by Git.

For example, this searches saved contacts for the keyword `agency`:

```json
{
  "filters": { "q_keywords": "agency" },
  "custom_fields": {}
}
```

Add `--apollo-config config/apollo.local.json` to Apollo commands. For lists, use `contact_label_ids` with actual Apollo label IDs. `contact_stage_ids`, `sort_by_field` and `sort_ascending` are also supported. These use Apollo's [saved-contact search API](https://docs.apollo.io/reference/search-for-contacts). Full-database People Search is not implemented.

The importer paginates, deduplicates by contact ID and caps the number of imported rows at `--limit`. Apollo's search display limit still applies. Partial-result responses are recorded in the source summary.

## Missing company details

Saved-contact search may return a role and company name without industry, headcount or a description. The source summary counts records missing basic fit fields.

To look up company data, opt in explicitly:

```sh
python3 lead_classifier.py --source apollo --enrich-organizations --preview --limit 10 --output output-enriched-preview
```

This calls Apollo's [organization enrichment endpoint](https://docs.apollo.io/reference/organization-enrichment) and may consume credits even though JEV is in preview mode. Within one run, contacts at the same domain share one enrichment request. A new run may incur charges again. The importer skips companies without a domain, leaves unavailable values blank and stops on an enrichment error or a mismatched returned domain.

Use the resulting `imported-leads.csv` for later JEV runs so you do not pay to enrich the same snapshot again.

Company data helps establish customer fit. It does not establish a specific operational problem. The service angle may still be `unknown` until you provide relevant research.

## Bring existing research or messages

The importer can read these values from Apollo contact custom fields. In `custom_fields`, map `research_notes`, `research_source`, `research_date` or `message` to the actual field ID in your workspace. Unmapped fields remain blank; the tool does not guess IDs or download sequences.

Alternatively, edit `imported-leads.csv` to add your evidence and message, then run the CSV classification command. Plain text, numeric or list custom-field values are supported. Source URLs are references only; the program does not browse them.

## Connection problems

Apollo 401 usually means the key is invalid or absent. Apollo 403 can mean the endpoint is outside the key's scope or account access. Check the key in Apollo rather than posting it into your AI chat. A 429 triggers limited retries; reduce frequency if it persists.

If Apollo returns no contacts, confirm they are saved in the account that owns the key and check your filters. If enrichment fails, retry without the enrichment flag or use a CSV that already contains the company data you need.

The integration has offline tests using simulated HTTP responses. A real Apollo-to-JEV run still needs verification with your accounts. Template drafting and JEV message checks are included with --draft-messages. Account creation, optional enrichment and web research need their own setup; sending and booking calls happen through your existing process.
