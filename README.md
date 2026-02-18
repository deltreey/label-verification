# Label Verification

> This is a tool to assist for TTB Label Verification.

# Prerequisites



# Tools and Licenses

- Python uses a GPL-compatible license
- Docker has a robust CE and Enterprise options

# Goals

Alright, so here's the reality.  Humans can do this stupidly fast.  After various tests,
we're clearly never going to outperform humans with AI, at least not at current tech
levels without tying into expensive external models that we won't have access to from
govt infrastructure.  So, if we're going to be useful, we need to be fast and reliable.
We need to provide them with something useful.  An early rejection of clearly bad
applications is very useful, especially when facing batch uploads.  If the majority of
applications are flagged for human review, that's fine.  If we can occasionally confirm
a fully passing application: that's gravy.  So, we optimize for failure first.

- Default: send to human for review
- Goal: find a way to reject
- Rare exception: an application passes all filters and looks 100% valid
