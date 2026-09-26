# Before you publish the demo

The 700-lead / 40-second / $0.09 example is a third-party claim, not a benchmark from this repository. Do not use those numbers as this project's results.

## Review quality

Create a small evaluation set of at least 30 records covering clear fits, explicit exclusions, missing facts, unsupported personalization and valid messages. Label it manually before looking at JEV results. Include ordinary records from your actual list, not only easy examples.

Record expected fit, supported service and message relevance separately. Save your reasons and the exact source facts. Have someone else review ambiguous cases if possible.

After the run, report agreement separately for each question. Also count unknown answers, below-threshold decisions and confident mistakes. Check whether a higher confidence threshold actually reduces errors on your data. If you edit the criteria after reviewing mistakes, test again on fresh records.

An offline test with a simulated response verifies the software's handling of that response. It cannot establish the model's classification accuracy.

## Run record

| Item | Fill in from your own run |
| --- | --- |
| Date and input source | |
| Model returned | |
| Configuration hash | |
| Rows attempted / succeeded / failed | |
| Questions per row | |
| Concurrent requests | |
| Processing wall time | |
| Reported token usage | |
| Provider-confirmed JEV cost | |
| Separate Apollo / enrichment costs | |
| Manually reviewed records | |
| Fit / service / message agreement | |
| Unknown or review rate | |
| Confident errors and examples | |

`summary.json` measures the processing portion of the program. For an end-to-end workflow claim, separately time export, research and human review. Retry costs and failed requests may not appear in returned usage, so reconcile billing before quoting a price.

## What a campaign experiment would add

Fit labels alone do not measure response or conversion probability. To investigate campaign performance, record actual replies and qualified outcomes. Compare sufficiently similar groups and keep message, audience and sending conditions documented. A small or selected sample does not establish that JEV caused a lift.

Publish anonymized or fictional examples. Keep real prospect files, keys and private outreach out of the public repository.
