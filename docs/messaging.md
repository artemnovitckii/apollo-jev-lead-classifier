# From a qualified lead to a personal message

The pipeline is: Apollo contacts → JEV qualification and service selection → company-specific draft → JEV relevance check → your review and sending process.

JEV makes structured decisions. The code writes from templates you control, using the company name and selected service. This gives you actual draft text without another AI provider or writing API key. It does not invent a compliment, claim to have visited a website or repeat raw research notes in a pitch.

## Set your offer and message together

1. Update `config/offer.json` with your customer criteria and evidence requirements.
2. Update `config/messages.json`. Each known angle needs its own `subject` and `body`. Supported placeholders are `{company}` and `{title}`. Keep factual claims about your own offer accurate.
3. Set `call_to_action` to your invitation to talk. Add your own `booking_url` and `sender_name` if you want them. Both can stay blank.
4. Use `python3 lead_classifier.py --doctor --draft-messages` to check configuration and key presence. This does not call either provider.

For example, a reporting template can say what you build and ask whether it is useful. It should not claim that the prospect is losing money or that their reporting is broken.

If you prefer private settings, copy the config to `config/messages.local.json` and use `--messages-config config/messages.local.json`. That file is ignored by Git.

## Run the complete workflow

```sh
python3 lead_classifier.py --source apollo --live --draft-messages --limit 10 --output output-outreach-drafts
```

Or reuse a previously imported snapshot:

```sh
python3 lead_classifier.py --input output-apollo-preview/imported-leads.csv --live --draft-messages --limit 10 --output output-outreach-drafts
```

Only confident good fits with a known service angle and company name receive drafts. An uncertain existing message does not block writing a replacement if the fit and angle themselves qualify. The replacement gets a fresh check. The original is preserved.

## Review the output

`classified.csv` holds the original lead decisions. `message_drafts.csv` holds the draft and its separate status. It includes every input row so you can see why some leads were skipped. Filter `status` to `review_before_sending` for the drafts that passed the model check, then read them yourself. A mismatch means revise; an unknown means research or review; a failed check stays flagged as an error.

Review the company, intended recipient, service relevance, every factual claim and your booking link. Then use your existing email or messaging tool. The project does not send messages, create campaigns, update Apollo or confirm appointments. It preserves Apollo IDs for matching with your own contacts and excludes dedicated email, phone and personal-name fields.

Editing a draft changes what was checked. To check edited messages, put them in your CSV's `Outreach Message` column and classify that CSV with `--live` **without** `--draft-messages`. This evaluates the edited text instead of generating another template draft.

## What it costs and what is tested

Draft creation is local. Each draft adds a separate JEV request containing the selected business data, subject, body and optional booking URL. Those checks run sequentially after classification. Usage and failures are recorded separately under `messaging` in the summary. Preview mode never calls JEV and produces no drafts because it has no qualification results.

Offline tests cover generation, eligibility, checks, errors and output files with simulated provider responses. A real account-to-account run and actual campaign results still need verification. The 700-lead, 40-second and $0.09 figures are not measurements of this implementation.
