# Which Apollo leads actually fit your offer?

A practical guide to qualifying your lead list and preparing personalized outreach with JEV.

An Apollo search gives you people who match your filters. You still need to decide whether your offer makes sense for them and whether your message says anything unsupported.

This project adds those checks to saved Apollo contacts or an exported list. You write down your criteria, give JEV the available evidence and get a CSV with a decision for each prospect. The useful part is being able to review a whole list using the same criteria.

If you want an AI to handle setup, start with the [clone-and-configure guide](setup-with-ai.md). It includes a prompt you can paste into your coding assistant and instructions for connecting Apollo directly. The CSV route below works too.

## The example

Suppose you sell AI automations to service businesses. Your customers usually have 5 to 100 employees, and you work with founders or people responsible for operations.

You offer three things: faster enquiry follow-up, simpler client onboarding and less manual reporting.

A company being an agency does not tell you which one it needs. A research note saying that its team copies numbers into a weekly client report gives you a more specific reason to investigate reporting automation.

The starter asks JEV:

1. Does this prospect fit the customer criteria?
2. Which of the configured services has support in the available evidence?
3. If there is a message, does it match the prospect and stick to supported facts?

Each question allows an unknown answer. That matters when your export contains little more than a job title and company name.

## 1. Write down your offer

Open `config/offer.json`. Replace the example with what you actually sell.

Be specific about the buyer, business type and exclusions. "Businesses that want to grow" gives the classifier almost nothing to work with. "Founders or operations leads at service businesses with 5 to 100 employees" is a useful starting point.

Define what would support each service. If you sell onboarding automation, look for evidence of repeated intake or document collection. Having a CRM does not establish that onboarding is broken.

You can ask your coding assistant to help edit the file:

> Help me adapt config/offer.json to my business. Ask what I sell, who buys it, who is a poor fit and what evidence supports each service. Keep an unknown option. Do not invent buying signals. Preserve the labels required by the README.

## 2. Export your Apollo list

In Apollo, open your people search or list, select the contacts and export a CSV. Check the export settings for the fields you need. Apollo documents the process in its [export guide](https://knowledge.apollo.io/hc/en-us/articles/4409237712141-Export-Contacts-to-a-CSV).

Save the file in this project's `data` folder. Include company name, job title and whatever company context is available. The tool accepts the common Apollo headers described in the README.

If you already researched a prospect, add the evidence in `Research Notes`, with its source and date in `Research Source` and `Research Date`. Add an existing message under `Outreach Message` to check it too.

These research columns are additions you supply. The starter does not automatically research operational pain points or visit source links. Direct API import can optionally enrich company facts such as industry and headcount; those facts alone do not prove a specific need.

## 3. Look at what JEV would receive

Follow the README setup and run preview mode on ten records. You do not need an API key for this step.

Open the generated request file. Check whether the importer picked up the columns you expected. Check the offer and criteria too. A classifier cannot recover facts that never reached it.

The repository includes fictional leads for trying this step before you use your own data. Preview does not produce model results.

## 4. Classify a small batch

Set your TypeSafe key privately using the README instructions. Run live mode with a limit of ten records.

Open the resulting CSV and compare each result with the original evidence. If a record is uncertain, inspect what is missing. If it is wrong despite clear evidence, revise the criteria and test again.

JEV returns a label and confidence for each of these Choice questions. Confidence describes the model's certainty about that classification. It does not establish how likely the lead is to reply or buy. See TypeSafe's [confidence explanation](https://docs.typesafe.ai/confidence).

## 5. Use the list to decide what to review

The starter produces four next steps:

| Next step | What you do |
| --- | --- |
| Research or review | Fill a material gap or check an uncertain decision. |
| Deprioritize | Check the stated exclusion before removing the prospect from this campaign. |
| Revise message | Fix the wrong angle or unsupported personalization. |
| Review for outreach | Check the message and your normal contact rules before sending through your existing process. |

You can filter the CSV by service to review one group together. Keep the original decisions and confidence values visible while you work.

For example, a reporting offer may make sense for a prospect whose supplied brief describes manual client reports. A warehouse-inventory pitch to that same prospect would deserve a mismatch flag. These are illustrations of the criteria, not measured model results.

## 6. Draft a message for each qualified lead

Configure `config/messages.json` with your real services, call invitation, optional booking link and signature. Add `--draft-messages` to the live command. JEV selects the service angle; the code fills a company-specific template and JEV checks the resulting subject and message.

Open `message_drafts.csv`. Confident good fits with a known angle get a draft. Poor fits and uncertain records are skipped. A confident message match is marked `review_before_sending`; mismatches, uncertainty and API errors remain flagged. Original messages and classifications stay available.

The [messaging guide](messaging.md) shows the command, settings, example and review steps. This is template personalization by company and service, not free-form writing or automatic sending. A booking link is an invitation, not a booked meeting.

## 7. Measure it on your own list

Once the small batch looks sensible, test a larger list against decisions you have reviewed manually. Track errors and unknowns as well as speed.

The project saves row counts, elapsed processing time, model details and reported usage. Confirm money spent in the provider's billing records. Apollo export costs and research time are separate from JEV inference.

Use the included validation worksheet to record what you actually ran. You can then describe your result precisely: how many records you processed, how long the run took, what it cost and how the classifications compared with your review.

The next useful experiment is checking whether those groups differ in actual campaign results. Until that is measured, call the output customer fit and message relevance.
