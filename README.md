# Apollo + JEV lead classifier

Turn an Apollo export into a list you can review by customer fit, relevant offer and message mismatch.

This starter uses JEV for structured decisions. You define what a good customer looks like, import an Apollo CSV and get the model's labels and confidence for each prospect. Uncertain records go into a review queue.

**Status:** starter implementation. Offline tests and request preview are available. Live JEV classification, speed, cost and accuracy still need verification with your account. The sample data is fictional.

Start with the [plain-English walkthrough](docs/resource.md).

## What you get

| Output | Meaning |
| --- | --- |
| `fit` | `good_fit`, `poor_fit` or `unknown`, based on your offer |
| `angle` | Which configured automation the evidence supports, or `unknown` |
| `message_check` | `match`, `mismatch` or `unknown`; skipped if you supply no message |
| Individual confidence values | JEV's reported certainty for each decision |
| `next_step` | Research/review, deprioritize, revise message or review for outreach |

The included example targets service-business owners and operations buyers. Edit `config/offer.json` to use a different offer. The suggested confidence threshold of 0.8 is a starting rule, not a validated accuracy target.

The tool does not predict conversion rates, write messages, fetch web pages, enrich contacts or send outreach. It works with the evidence you supply. An `unknown` is useful when the export lacks a fact needed for a decision.

## Try it without an API key

Install [Python](https://www.python.org/downloads/) version 3.10 or newer if needed. Download this repository using GitHub's **Code > Download ZIP**, unzip it and open a terminal in that folder. You can also open the folder in your coding assistant and ask it to run the command.

On macOS or Linux:

```sh
python3 lead_classifier.py --preview --output output-preview
```

On Windows, replace `python3` with `py` in these commands.

Open `output-preview/requests.jsonl`. It shows exactly which selected fields would be sent to JEV and the questions it would answer. Preview mode makes no API calls and produces no predicted labels. The five example records include a plausible fit, a mismatched pitch, a clear exclusion and missing information.

Each run requires a new output directory so it cannot overwrite a previous run.

## Connect your Apollo data

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

This version connects through CSV. Direct Apollo API ingestion is not implemented. Apollo's [People API Search](https://docs.apollo.io/reference/people-api-search) is an option for a later integration, but it does not return email addresses or phone numbers. Search data also needs enough business context to support your criteria.

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

The included `.env.example` documents the variable name. The script does not load `.env` files.

For a larger run, set `--limit 700` or another explicit cap. The default is 10 rows and four concurrent requests. Set `--workers 1` for serial requests, or up to 16 after checking your rate limits. Each lead uses one request containing its applicable questions. There is no dollar spending cap and retries may add charges.

## Read your results

Open `classified.csv` in your spreadsheet app. Each decision has its own confidence. The code sends any unknown or below-threshold decision to `research_or_review`. Otherwise it deprioritizes poor fits, flags mismatched messages for revision and queues remaining records for outreach review. It never sends anything.

Other output files:

- `requests.jsonl`: input sent to TypeSafe, linked to local lead IDs.
- `responses.jsonl`: returned responses or per-record errors.
- `config-used.json`: a snapshot of your criteria.
- `summary.json`: row counts, elapsed processing time, returned model IDs and reported usage. Cost remains blank until checked against provider billing.

Use the [benchmark worksheet](docs/validation.md) before publishing performance claims. Classification confidence is not the probability that someone replies or buys. TypeSafe explains the distinction in its [confidence guide](https://docs.typesafe.ai/confidence).

## Data and keys

Preview runs locally. Live mode sends company, role, business context, supplied research and message text to TypeSafe. Dedicated name, email, phone and personal profile columns are excluded, but anything you put inside notes or messages still goes to the provider.

Input files in `data/`, output folders named `output*` and environment files are ignored by Git. Keep real prospect files there. Custom output paths outside `output*` are not automatically ignored. Requests and responses can contain sensitive business information; review files before sharing. Synthetic examples are the only lead data intended for the repository.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `python3` not found | Install Python, then reopen your terminal. Use `py` on Windows. |
| Output directory already exists | Choose a new `--output` name. |
| Missing company column or extra cells | Check your export headers and CSV quoting. Do not hand-edit commas inside quoted text. |
| Too many `unknown` results | Inspect missing fields or narrow the criteria. Add sourced facts instead of lowering the threshold to hide uncertainty. |
| JEV HTTP 401 | Check that your TypeSafe key is active and set in the same terminal. |
| JEV HTTP 422 | Inspect request structure and edited criteria. Reduce oversized notes. |
| JEV HTTP 429 or 529 | The tool retries these responses with backoff, up to four attempts. Reduce `--workers` if it persists. |
| Connection timeout | Check provider status and your connection. The request might have been billed; it is not automatically retried. |
| Some records failed | `classified.csv` marks them `error_review`; the process exits with a failure status. Fix the cause and create a CSV containing only failed rows before rerunning. There is no automatic resume. |

Run the offline checks with `python3 -m unittest discover -s tests -v`. These check data handling and routing with simulated API responses; they do not measure JEV accuracy.
