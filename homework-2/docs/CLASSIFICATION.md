# How Ticket Classification Works

This document explains, in plain language, how the support system automatically figures out what
kind of problem a ticket is about (its **category**) and how urgent it is (its **priority**).

## The basic idea

When a ticket comes in, the system reads the subject line and description and looks for certain
"trigger words" or phrases. Based on which words it finds, it decides:

- **What category** the ticket belongs to (e.g. a login problem vs. a billing problem)
- **How urgent** it is (urgent, high, medium, or low)
- **How confident** it is in that decision
- **Why** it made that decision, in a short readable explanation

This is a simple, rule-based system — it does not use artificial intelligence to "understand"
the ticket the way a human would. It just checks for known keywords, similar to how a spam filter
looks for suspicious words in an email.

## How the category is chosen

Categories aren't fixed in the code anymore — they live in an editable list (see "Managing
categories" below) that starts out with five built-in ones:

1. **Bug Report** — words like "steps to reproduce" or "regression".
2. **Account Access** — words like "login", "password", "2FA", "locked out".
3. **Billing Question** — words like "invoice", "refund", "charge", "subscription".
4. **Feature Request** — words like "enhancement", "suggestion", "would be nice".
5. **Technical Issue** — more general words like "bug", "error", "crash", "not working".

For every ticket, the system checks **all** categories and counts how many of each category's
trigger words show up in the ticket text. Whichever category has the **most** matching words
wins. If nothing matches at all, the ticket is labeled **Other**.

**Why "most matches" instead of "first match"?** Some words overlap between categories — for
example, "bug" could show up in both a bug report and a general technical issue. Counting matches
means a ticket packed with clearly technical language ("bug", "error", "crash") is correctly
called a Technical Issue even if it also happens to contain one bug-report-style word, instead of
always defaulting to whichever category happens to be checked first.

**What if two categories tie** with the same number of matching words? The tie goes to whichever
category has been around longer — the five built-in categories are checked before any custom
category, and custom categories are checked in the order they were added. So a brand-new category
only "wins" a ticket when it genuinely has more matching words than everything else; on a tie, an
older/more established category keeps the edge.

## How the priority is chosen

Separately from the category, the system also scans for urgency words, again stopping at the
first match:

1. **Urgent** — phrases like "can't access", "critical", "production down", "security".
2. **High** — words like "important", "blocking", "asap".
3. **Low** — words like "minor", "cosmetic", "suggestion".
4. If none of the above are found, the priority defaults to **Medium**.

## How the confidence score works

The confidence score (shown as a number between 0 and 1) is a simple estimate of how sure the
system is, based on how many trigger words it found in total:

- More matching keywords → higher confidence (up to a maximum of 1.0, i.e. 100%)
- If no keywords matched at all for either category or priority (everything defaulted), the
  system reports a low, fixed confidence of 0.3 (30%), since it's really just guessing.

This is not a "true" measure of accuracy — it's a rough, transparent stand-in so a human reviewer
can see when the system was fairly sure versus when it was just falling back on defaults.

## Why the system explains itself

Every classification comes with a short, plain-English explanation (the "reasoning") that says
exactly which words led to the category and which words led to the priority. This makes it easy
for a support agent to double-check the system's decision at a glance, rather than trusting a
black box.

Every classification decision is also written to a log file behind the scenes, so there's always
a record of what the system decided and why, for later review or troubleshooting.

## When can classification happen?

There are two ways a ticket gets classified:

1. **Automatically when it's created** — if the person creating the ticket chooses to turn this
   on (it's optional, off by default).
2. **On demand, at any time** — a support agent can ask the system to (re-)classify any existing
   ticket whenever they want.

## Managing categories

Since categories and their trigger words are no longer hardcoded, there's a small set of
endpoints for viewing and editing them:

- **See one category's trigger words** — `GET /category/{key}` (e.g. `GET /category/billing_question`)
  shows that category's current list of trigger words. Asking for a category that doesn't exist
  gives a clear "not found" response.
- **See every category at once** — `GET /category/list` shows all categories and their trigger
  words, in the order they're checked when classifying a ticket.
- **Add a brand-new category** — `POST /category` lets you create one, giving it a short
  lowercase name (like `shipping_delay`) and, optionally, a starting list of trigger words. New
  categories are always added at the *end* of the checking order, so they start out with the
  lowest priority (see the tie-breaking rule above) until they build up a strong set of trigger
  words of their own. Calling this twice with the same name is safe — it won't create a
  duplicate, it just adds any new trigger words you give it.
- **Add more trigger words to an existing category** — `PUT /category/{key}` lets you extend a
  category (built-in or custom) with additional trigger words. It only *adds* words; it never
  removes or replaces the ones already there. If you try to add a word that's already on that
  category's list, it's simply skipped rather than duplicated.
- **The catch-all "Other" category is untouchable** — it's the built-in fallback for tickets that
  don't match anything, and isn't managed through this API (you can't create, view as a
  manageable entry, or add trigger words to it directly).

The same word can be a trigger for more than one category — the "most matches wins" rule
described above is exactly what handles that overlap sensibly.

## What happens if a human disagrees?

If a support agent manually changes a ticket's category or priority themselves, the system
remembers that this ticket was "manually overridden." From that point on, if someone asks the
system to auto-classify that ticket again, it will still tell you what *it* thinks the category
and priority should be — but it will **not** silently overwrite the human's decision. The human's
judgment always wins once they've stepped in.
