// Shapes returned by the job search API (services/api/crescendo_api/routes/jobs.py, JOB-F08).
// All posting text is untrusted page data from job boards; React renders it as text, never HTML.

export type JobRow = {
  source: string;
  posting_id: string;
  score: number;
  title: string;
  company: string;
  url: string;
  locations: string[];
  countries: string[];
  country_known: boolean;
  workplace: string | null;
  compensation: string | null;
  department: string | null;
  posted: string | null;
  age_days: number | null;
  first_seen: string | null;
  title_match: number;
  skill_coverage: number;
  matched_skills: string[];
  missing_skills: string[];
  years_asked: number | null;
  other_postings: number;
  picked: boolean;
  application: { status: ApplicationStatus; applied_on: string | null } | null;
};

export type HiddenCounts = { country: number; location: number; senior: number; years: number; age: number };

export type Crawl = { id: number; status: string; started_at: string | null; finished_at: string | null };

export type SearchPage = {
  total: number;
  offset: number;
  limit: number;
  hidden: HiddenCounts;
  postings_searched: number;
  crawl: Crawl | null;
  results: JobRow[];
};

export type Segment = { text: string; skill?: string; kind?: "have" | "gap" };

export type JobDetail = {
  description: string;
  segments: Segment[];
  locations: string[];
  countries: string[];
  employment_type: string | null;
  first_seen: string | null;
  last_seen: string | null;
  closed_at: string | null;
  years_asked: number | null;
};

export type Pick = { source: string; posting_id: string; title: string; company: string; url: string; closed: boolean };

export type ResumeInfo = { filename: string; uploaded_at: string; skills: string[]; characters: number };

// What the search form edits. maxYears "" means no limit.
export type Filters = {
  q: string;
  country: string;
  cities: string;
  remote: boolean;
  noSenior: boolean;
  maxYears: string;
  maxAgeDays: string;
  hideApplied: boolean;
};

export const APPLICATION_STATUS = {
  ready: "Ready", applied: "Applied", interviewing: "Interviewing", offer: "Offer",
  rejected: "Rejected", withdrawn: "Withdrawn",
} as const;
export type ApplicationStatus = keyof typeof APPLICATION_STATUS;
export type Application = {
  source: string; posting_id: string;
  posting: { title: string; company: string; url: string; description: string; locations: string[] };
  status: ApplicationStatus; applied_on: string | null; follow_up_on: string | null;
  notes: string; version: number; created_at: string; updated_at: string;
  posting_state: "open" | "closed" | "expired";
};

export const MAX_PICKS = 3;
