# Apollo + JEV lead qualification and messaging

Turn saved Apollo contacts or a CSV export into qualified leads and personalized message drafts with a call invitation.

This starter uses JEV for structured decisions. You define what a good customer looks like, import from Apollo and get the model's labels and confidence for each prospect. Uncertain records go into a review queue. With `--draft-messages`, confident fits get a company-specific draft for the selected service, then JEV checks the draft against the supplied evidence.

**Status:** direct Apollo saved-contact import, JEV classification and template-based messaging are implemented and tested offline. A live Apollo-to-JEV run, speed, cost and accuracy still need verification with your accounts. The sample data is fictional.

Start with the [plain-English walkthrough](docs/resource.md).

## Set it up with your AI

Clone this repository, open it in your coding assistant and give it the [setup prompt](docs/setup-with-ai.md). `AGENTS.md` tells the assistant how to configure your offer, connect Apollo and check the results. You supply your own account keys privately:

```sh
git clone https://github.com/artemnovitckii/apollo-jev-lead-classifier.git
cd apollo-jev-lead-classifier
python3 configure.py
python3 lead_classifier.py --doctor
```

Once your offer, message templates and keys are configured, this imports up to 10 saved contacts, classifies them and prepares checked drafts for confident fits:

```sh
python3 lead_classifier.py --source apollo --live --draft-messages --limit 10 --output output-first-live
```

Use `--preview` instead of `--live` to fetch Apollo contacts and inspect the JEV requests first. Apollo preview contacts Apollo but makes no JEV calls. The guide covers list filters, optional company enrichment and adding research or messages. Python 3.10+ is the only local dependency. On Windows use `py` instead of `python3`.

## What you get

| Output | Meaning |
| --- | --- |
| `fit` | `good_fit`, `poor_fit` or `unknown`, based on your offer |
| `angle` | Which configured automation the evidence supports, or `unknown` |
| `message_check` | `match`, `mismatch` or `unknown`; skipped if you supply no message |
| Individual confidence values | JEV's reported certainty for each decision |
| `next_step` | Research/review, deprioritize, revise message or review for outreach |

The included example targets service-business owners and operations buyers. Edit `config/offer.json` to use a different offer. The suggested confidence threshold of 0.8 is a starting rule, not a validated accuracy target.

Drafts use editable templates personalized by company and the evidence-supported service angle. JEV selects and checks; it does not generate free-form prose. The tool does not predict conversion rates, fetch web pages, reveal personal contact details, send outreach or book calls automatically. It can optionally enrich company data through Apollo. An `unknown` is useful when a record lacks a fact needed for a decision.

## Turn qualified leads into message drafts

Edit `config/messages.json` alongside your offer:

- `templates`: one subject and body for each service angle in `config/offer.json`, excluding `unknown`. Use `{company}` and optionally `{title}`. Write only what your business actually offers.
- `call_to_action`: your invitation to talk. The default asks whether a quick call would be useful.
- `booking_url`: optionally add your own HTTPS booking link. Blank means no link is included.
- `sender_name`: optionally add your signature.

Then add `--draft-messages` to your live command. For an existing CSV:

```sh
python3 lead_classifier.py --input data/apollo.csv --live --draft-messages --limit 10 --output output-with-messages
```

The tool drafts only when fit is `good_fit`, the selected angle is known, both confidence values meet your threshold and a company name is present. It can draft a replacement for an existing mismatched message while preserving the original message and classification. It does not rank by reply probability or manufacture a personal observation from research notes.

Open `message_drafts.csv`. It contains a subject, message, original message, evidence references, a separate JEV message check and a status for every input row:

| Status | Meaning |
| --- | --- |
| `review_before_sending` | JEV returned a confident match. You still review and send through your normal process. |
| `revise_message` | JEV flagged a mismatch in the generated subject or body. |
| `research_or_review` | The draft check was unknown or below your threshold. |
| `error_review` | The draft check failed. The draft stays available, but is not cleared for outreach review. |
| `skipped_*` | No draft: poor fit, uncertain fit/angle, missing company or failed classification. |

Each draft adds one JEV request, including the subject, full message and booking link if supplied. Draft checks run sequentially after classification and use API credits. The summary records their usage separately. Preview mode validates the templates but produces no drafts because it has no JEV fit results. No additional writing-provider key is required.

See an [illustrative message](examples/message-draft.md) and the [messaging walkthrough](docs/messaging.md). Booked calls depend on actual sending and prospect responses; they are not an output of this tool.

## Try it without an API key

Install [Python](https://www.python.org/downloads/) version 3.10 or newer if needed. Download this repository using GitHub's **Code > Download ZIP**, unzip it and open a terminal in that folder. You can also open the folder in your coding assistant and ask it to run the command.

On macOS or Linux:

```sh
python3 lead_classifier.py --preview --output output-preview
```

On Windows, replace `python3` with `py` in these commands.

Open `output-preview/requests.jsonl`. It shows exactly which selected fields would be sent to JEV and the questions it would answer. Preview mode makes no API calls and produces no predicted labels. The five example records include a plausible fit, a mismatched pitch, a clear exclusion and missing information.

Each run requires a new output directory so it cannot overwrite a previous run.

## Use an Apollo CSV instead

1. In Apollo, open **Search > People**, filter to your list and select the contacts.
2. Choose **Export** and check the CSV field settings. Include company name, title, industry, employee count and useful keywords or company information when available.
3. Download the export and place it at `data/apollo.csv` inside this project. Create the `data` folder first.
4. Optionally add `Research Notes`, `Research Source`, `Research Date` and `Outreach Message` columns. Notes should contain the actual evidence; a URL alone is not evidence the program can read. The script does not browse URLs.
5. Check the first ten records:

```sh
python3 lead_classifier.py --input data/apollo.csv --preview --output output-my-preview
```

Apollo's export permissions and credit usage depend on your account. Field availability varies. See the [official export instructions](https://knowledge.apollo.io/hc/en-us/articles/4409237712141-Export-Contacts-to-a-CSV).

Headers are case-insensitive. Accepted aliases are listed in `ALIASES` inside `lead_classifier.py`. Unknown columns are ignored. A company column is required; missing details stay blank. Rows with duplicate Apollo IDs stop the import. If IDs are absent, the tool assigns IDs from CSV row numbers, which are only stable within that file.

For direct API import, follow the [Apollo setup guide](docs/setup-with-ai.md). It reads saved contacts through Apollo's Contacts Search endpoint. It does not search the entire Apollo prospect database.

## Make it fit your offer

Open `config/offer.json` and change:

- `offer`: what you sell, who buys it and any exclusions.
- `criteria.fit`: observable facts that establish a fit or exclusion.
- `criteria.angle`: the services or messages you want to choose between, with evidence requirements.
- `criteria.message_check`: what makes personalization supported or mismatched.

Keep `good_fit`, `poor_fit` and `unknown` in the fit options. Keep `match`, `mismatch` and `unknown` in the message options. You can rename the specific angle options. All decisions use JEV Choice questions, which support a defined answer set and confidence. The implementation follows the [official TypeSafe API](https://docs.typesafe.ai/api).

## Run JEV

Get a TypeSafe API key through the [official quickstart](https://docs.typesafe.ai/introduction/quickstart). Access and billing depend on your account. Never paste a key into source files, screenshots or an assistant conversation.

On macOS/Linux, this prompts privately for the key without putting it in shell history:

```sh
printf 'TypeSafe API key: '
read -r -s TYPESAFE_API_KEY
export TYPESAFE_API_KEY
printf '\n'
python3 lead_classifier.py --input data/apollo.csv --live --limit 10 --output output-live-10
unset TYPESAFE_API_KEY
```

On Windows PowerShell:

```powershell
$jevSecret = Read-Host 'TypeSafe API key' -AsSecureString
$env:TYPESAFE_API_KEY = [System.Net.NetworkCredential]::new('', $jevSecret).Password
py lead_classifier.py --input data/apollo.csv --live --limit 10 --output output-live-10
Remove-Item Env:TYPESAFE_API_KEY
```

Alternatively, run `python3 configure.py` to save both keys privately in the ignored `.env` file. The classifier loads that file automatically; nonempty environment variables take precedence. Clearing an environment variable does not remove a saved key from `.env`.

For a larger run, set `--limit 700` or another explicit cap. The default is 10 rows and four concurrent requests. Set `--workers 1` for serial requests, or up to 16 after checking your rate limits. Each lead uses one classification request containing its applicable questions. `--draft-messages` adds one request per generated draft. There is no dollar spending cap and retries may add charges.

## Read your results

Open `classified.csv` in your spreadsheet app. Each decision has its own confidence. The code sends any unknown or below-threshold decision to `research_or_review`. Otherwise it deprioritizes poor fits, flags mismatched messages for revision and queues remaining records for outreach review. It never sends anything.

Other output files:

- `requests.jsonl`: input sent to TypeSafe, linked to local lead IDs.
- `responses.jsonl`: returned responses or per-record errors.
- `config-used.json`: a snapshot of your criteria.
- `summary.json`: row counts, elapsed processing time, returned model IDs and reported usage. Cost remains blank until checked against provider billing.
- `source-summary.json`: import source, time and Apollo completeness information.
- With `--draft-messages`: `message_drafts.csv`, `message-requests.jsonl`, `message-responses.jsonl` and `messages-config-used.json`. Draft checks, errors and usage appear under `messaging` in `summary.json`; classification and draft-check usage must both be included when calculating total cost.
- In Apollo mode, `imported-leads.csv` and `apollo-config-used.json`: the selected business fields and search settings. Reuse the CSV to classify the same snapshot without fetching or enriching again.

Use the [benchmark worksheet](docs/validation.md) before publishing performance claims. Classification confidence is not the probability that someone replies or buys. TypeSafe explains the distinction in its [confidence guide](https://docs.typesafe.ai/confidence).

## Data and keys

CSV preview runs locally. Apollo preview reads from Apollo; optional company enrichment can consume Apollo credits. Live mode also sends company, role, business context, supplied research and message text to TypeSafe. Dedicated name, email, phone and personal profile fields are excluded from saved imports and JEV payloads, but anything you put inside notes or messages still goes to the provider. Apollo's response may contain contact details in memory before the importer selects its business fields; it does not save the raw response.

Input files in `data/`, output folders named `output*` and environment files are ignored by Git. Keep real prospect files there. Custom output paths outside `output*` are not automatically ignored. Requests and responses can contain sensitive business information; review files before sharing. Synthetic examples are the only lead data intended for the repository.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `python3` not found | Install Python, then reopen your terminal. Use `py` on Windows. |
| Output directory already exists | Choose a new `--output` name. |
| Missing company column or extra cells | Check your export headers and CSV quoting. Do not hand-edit commas inside quoted text. |
| Too many `unknown` results | Inspect missing fields or narrow the criteria. Add sourced facts instead of lowering the threshold to hide uncertainty. |
| JEV HTTP 401 | Check that your TypeSafe key is active and set in the same terminal. |
| Apollo HTTP 401 or 403 | Check your Apollo key and access to Contacts Search, plus Organization Enrichment if enabled. See the setup guide. |
| JEV HTTP 422 | Inspect request structure and edited criteria. Reduce oversized notes. |
| JEV HTTP 429 or 529 | The tool retries these responses with backoff, up to four attempts. Reduce `--workers` if it persists. |
| Connection timeout | Check provider status and your connection. The request might have been billed; it is not automatically retried. |
| Some records failed | `classified.csv` marks them `error_review`; the process exits with a failure status. Fix the cause and create a CSV containing only failed rows before rerunning. There is no automatic resume. |

Run the offline checks with `python3 -m unittest discover -s tests -v`. These check data handling and routing with simulated API responses; they do not measure JEV accuracy.
