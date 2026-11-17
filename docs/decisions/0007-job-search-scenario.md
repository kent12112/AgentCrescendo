# Decision: job search replaces the weekend trip as the primary scenario

Date: November 17, 2026. Decided by the user. First slice: JOB-F01 (offer finder).
Changes the primary acceptance scenario in [architecture](../architecture.md);
no network, permission, or orchestration rule changes.

## Context

The weekend trip was chosen as a neutral first scenario. The user wants a
scenario where watching agents work on real desktops is the product's main
appeal, and chose an end-to-end job search modeled on a common multi-agent
pattern: parse a resume → find offers → user chooses → research the company →
write a cover letter.

Most of that pattern maps onto parts already planned: the coordinator assigns
work, worker desktops browse public boards, the user's choice is an intervention
point, and the cover letter is the sourced deliverable. Roles stay data; this is
an acceptance scenario, not a hard-coded pipeline.

## Decision

1. **Primary scenario.** Job search is the primary acceptance scenario. The
   weekend trip becomes a generality check, alongside product comparison.
2. **No application typing or submitting, for now.** The user chose to skip form
   filling. Submission is also structurally impossible today: the request filter
   passes only GET Document/Stylesheet requests and page scripts are off
   ([0005](0005-open-browsing.md)), so a POST application form cannot be sent.
   Typing personal data into third-party pages needs its own decision first.
3. **Public company boards only.** No login-only sites (LinkedIn, Indeed
   accounts). Supported boards must render with page scripts disabled. Probed
   November 17, 2026 (local Edge, scripts off, Document/Stylesheet only):
   - Greenhouse (`job-boards.greenhouse.io`) and Lever (`jobs.lever.co`) render
     listings; both are used by many companies, so they come first.
   - HN jobs and python.org jobs render; not company boards.
   - Ashby and Work at a Startup render nothing ("enable JavaScript").
   - WeWorkRemotely and RemoteOK showed only navigation on the first screen.
4. **Offers come from the browser, not the model.** The model finishes with link
   IDs only. The host resolves each ID in the current browser snapshot and accepts
   it only when the link's real destination is a posting on the same company
   board, and its label is not a button word. Title and URL come from the page;
   the model's reason is stored as `why_untrusted`. This prevents invented jobs or
   URLs, the main way an offer list could mislead a user.
5. **The resume stays off desktops** (for the next slice). Parse it on the host into a
   profile the user reviews, kept out of Git; agents receive only the fields a
   task needs.

## Alternatives considered

- **Model writes titles and URLs, host checks visit history.** The model could
  still misstate a title it read, and the host can only check URLs it visited,
  not postings it saw on a list. Rejected.
- **Allow page scripts to support Ashby and others.** This is a far larger
  change ([0005](0005-open-browsing.md)): scripts can send data with
  `fetch` and could post forms. Deferred until a scenario needs it.
- **Use job-board APIs.** Originally rejected because nothing would happen on the
  desktop. Superseded the same day; see the update below.

## Update, November 17, 2026: discovery uses ATS APIs (JOB-F00)

The user asked for a search agent that finds the best match for a resume, not
just browsing one board. Two facts changed the design:

- **No search engine works for automated queries.** Probed with local Edge, scripts
  off, GET Document/Stylesheet only:
  - DuckDuckGo html/lite gave a bot challenge, and its form is POST.
  - Google required JavaScript.
  - Brave returned 429 "suspicious".
  - Mojeek returned 403 "automated queries".
  - Startpage showed a blocked page.
  - Bing loaded but ignored `site:`.

  Google's Custom Search JSON API is closed to new customers and ends January 1,
  2027. Google's terms also prohibit scraping its results from the host.
- **ATS public APIs work and are made for this.** Job boards commonly aggregate
  postings through them. Live, keyless:
  - Greenhouse: `boards-api.greenhouse.io/v1/boards/<co>/jobs?content=true`
    (659 postings for one company).
  - Lever: `api.lever.co/v0/postings/<co>?mode=json` (301 postings).
  - Ashby: `api.ashbyhq.com/posting-api/job-board/<co>` (840 postings).

  Responses reach about 15 MB.

So the work splits:

1. **Discovery on the host** from ATS APIs over a company list the user controls.
   Ashby is included: its API works even though its pages need scripts.
2. **Matching on the host** against the reviewed resume profile, on full posting text.
3. **The desktop is for the visible part**: opening the top postings on the real
   board pages. JOB-F01's browser lookup still applies there, so it covers
   Greenhouse and Lever pages only. Ashby postings can be matched but not shown on
   the desktop until page scripts are allowed.

Posting URLs are rebuilt from the validated board name and a checked ID, never
taken from the response. For example, Greenhouse's `absolute_url` can point to a
company's own careers site. Searching all companies (no list) needs a paid search
API; this is deferred.

## Update, November 17, 2026: companies from Common Crawl (JOB-F06)

HN "Who is hiring?" gave 281 boards over 12 months and 12 relevant roles for the user's
resume; coverage was the limit. The user pointed to jobs.whatrunsindia.com (135k
postings, 4,066 companies). Its open-source repo (`rishilahoti/ashbyhq-scraper`)
showed how it finds companies: the public **Common Crawl URL index**, queried per ATS
host, with each slug checked against the ATS API.

Decided:

1. **Use Common Crawl, not that site.** Its robots.txt disallows `/?`, `/api/`, and
   `/jobs/` for automated clients, so its search and data are not used.
2. **Write our own code.** The repo is MIT + Commons Clause, which forbids redistributing
   its components "alone, in a bundle, or as a ported version". Only the general
   technique (query a public index, then verify) is reused.
3. **Ashby first, several crawls.** One crawl (CC-MAIN-2026-43) had a single index page,
   ~3,800 Ashby URLs, ~944 companies; each crawl samples different pages, so the
   latest 6 are combined. Greenhouse can follow; Lever blocks Common Crawl's crawler.
4. **Cache locally.** The index server returned 502/504 within minutes of a 200, so the
   company list is cached ~30 days (stale list reused if a refresh fails) and each board
   ~24 hours. A search never needs the index to be up.
5. **Country from structured data.** A 150-company Ashby sample passed Toronto, London,
   and "Remote – UK" through a text-only "remote" filter. Ashby's
   `address.postalAddress.addressCountry` (plus place names in location text for
   other sources) now lets `--country` drop roles abroad; postings naming no country
   are kept and marked. `isRemote` is true on Hybrid jobs, so `workplaceType` wins.

Measured before building: 150 random Ashby companies from one crawl fetched in 3 s
(141 live, 9 gone) and gave 15 filtered matches, more than all of HN.

Rejected for now: the Wayback Machine CDX index as a fallback (answered in ~23 s with
junk-heavy, alphabetical output; the stale cache covers outages), VC portfolio job
boards (Getro), and more ATS platforms (Workable, SmartRecruiters).

## Consequences

- Lever's APPLY button links to the same posting URL as the title, so the destination
  alone cannot tell them apart. Button-word labels are refused (smoke check).
- An offer must be cited from the *current* screen (the model sees only the
  latest link list), so one run returns at most what fits on its final screen.
- One run covers one board and one results page in at most 10 steps and 120
  seconds (existing loop limits). Multiple boards are a coordinator concern.
- Week 4's benchmark (W4-F07) becomes the job-search benchmark.
