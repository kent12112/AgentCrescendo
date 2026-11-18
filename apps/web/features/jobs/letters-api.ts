import { call } from "./api";
import type { Pick } from "./types";

export type ResearchFact = { topic: string; claim: string; quote: string; url: string };
export type CompanyResearch = {
  status: "done" | "failed"; model: string; error?: string; researched_at?: string;
  facts: ResearchFact[]; excluded: (ResearchFact & { reason: string })[]; open_questions: string[];
};
export type LetterPosting = Pick & { description: string; company_notes: string; company_research?: CompanyResearch };
// One Thinker/Worker/Verifier step, saved by the API as soon as it finishes.
export type Turn = {
  turn: number; role: "thinker" | "worker" | "verifier"; status: "done" | "failed"; seconds: number; summary: string;
  detail: { text?: string; words?: number; accepted?: boolean; issues?: { sentence: number; problem: string; fix: string }[]; host_checks?: string[] };
};
export type SourceQuote = { source: string; quote: string; quote_found: boolean };
export type SourceCheck = SourceQuote & { text: string; flags: string[]; supporting_quotes?: SourceQuote[] };
export type Letter = {
  id: string; session_id: string; posting: LetterPosting;
  status: "pending" | "generating" | "failed" | "draft" | "approved";
  text: string; checks: SourceCheck[]; turns: Turn[]; error: string | null; version: number;
  created_at: string; updated_at: string;
};
export type LetterSession = {
  id: string; input_digest: string; confirmed_at: string | null; created_at: string;
  inputs: { model: string; resume: string; jobs: LetterPosting[] }; letters: Letter[];
};

const json = (method: string, data: unknown) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
export const listLetters = () => call<{ letters: Letter[] }>("/api/jobs/letters");
export const getLetter = (id: string) => call<Letter>(`/api/jobs/letters/${encodeURIComponent(id)}`);
export const getSession = (id: string) => call<LetterSession>(`/api/jobs/letter-sessions/${encodeURIComponent(id)}`);
export const prepare = (name: string, picks: Pick[], notes: Record<string, string>) => call<LetterSession>("/api/jobs/letter-sessions", json("POST", {
  name, picks: picks.map(p => ({ source: p.source, posting_id: p.posting_id, company_notes: notes[`${p.source}:${p.posting_id}`] ?? "" })),
}));
export const research = (s: LetterSession) => call<LetterSession>(`/api/jobs/letter-sessions/${s.id}/research`, { method: "POST" });
export const confirm = (s: LetterSession) => call<LetterSession>(`/api/jobs/letter-sessions/${s.id}/confirm`, json("POST", { input_digest: s.input_digest }));
export const generate = (id: string) => call<Letter>(`/api/jobs/letters/${id}/generate`, { method: "POST" });
export const draftLive = (letter: Letter) => call(`/api/jobs/letters/${letter.id}/draft-writer`, json("POST", { version: letter.version }));
export const writerState = (id: string) => call<{ export: { status: string } | null }>(`/api/jobs/letters/${id}/writer`);
export const save = (letter: Letter, text: string, approve: boolean, reviewed: boolean) => call<Letter>(`/api/jobs/letters/${letter.id}`, json("PUT", {
  text, version: letter.version, approve, reviewed,
}));

export const STATUS: Record<Letter["status"], string> = {
  pending: "Ready to draft", generating: "Drafting", failed: "Needs retry", draft: "Review answer", approved: "Ready to paste",
};
