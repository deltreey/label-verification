# Label Verification

> This is a tool to assist for TTB Label Verification.

# Prerequisites

- we're using [uv](https://docs.astral.sh/uv/) to manage python here
- we're using [docker](https://docs.docker.com/engine/) to build and deploy
- we're using [make](https://www.gnu.org/software/make/#download) for basic dev functionality
- we're using [git](https://git-scm.com/downloads) for version control

# Tools and Licenses

- Python uses a GPL-compatible license
- Docker has a robust CE and Enterprise options

# Assumptions

1. One image per label.  I know this is probably unrealistic, but for PoC it seems like a decent start.
2. For bulk upload, we're only supporting zip files with 2 files, one form and one image.  We can easily alter this to support the JSON fields, multiple images, or a manifest file later.
3. We're supporting only the exact PDF form from the website, filled in digitally.  We can parse the form in future phases.
4. We assume the optimal use case is to reject applications to save the humans' time parsing obviously invalid applications.
5. We're assuming the form is filled out correctly, and for the moment, we're assuming only actual applications even though the form supports renewals and whatnot.
6. We're assuming access to some sort of Azure AI capable box, like a GPU.  On my CPU-only workstation, this runs at ~10 seconds.  Faster AI processing is a requirement, not an option.
6. We're assuming there is more work to do!

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
