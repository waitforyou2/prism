# Prism Team Backend API Draft

## 1. Scope

This document defines the MVP backend API contract for Prism Team.

MVP assumptions:

- No login.
- No permission model.
- All users can view knowledge bases.
- All users can upload documents, submit links, and write notes.
- Submitter identity is a plain text field: `submitterName`.
- Long-running operations are represented as jobs.
- The backend can store Markdown-native Prism wiki files while exposing structured API responses.

## 2. API Conventions

Base path:

```text
/api
```

JSON response envelope:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

Error response:

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "kb_not_found",
    "message": "Knowledge base not found",
    "details": {}
  }
}
```

Common status codes:

```text
200 OK
201 Created
202 Accepted
400 Bad Request
404 Not Found
409 Conflict
422 Unprocessable Entity
500 Internal Server Error
```

Timestamps use ISO 8601 strings.

Pagination query:

```text
?page=1&pageSize=20
```

Paginated meta:

```json
{
  "page": 1,
  "pageSize": 20,
  "total": 120
}
```

## 3. Data Models

### 3.1 KnowledgeBase

```ts
interface KnowledgeBase {
  id: string
  name: string
  description: string
  tags: string[]
  pageCount: number
  rawCount: number
  pendingRawCount: number
  lastUpdatedAt: string | null
  healthStatus: 'healthy' | 'warning' | 'failed' | 'stale' | 'empty'
  auditStatus: 'pass' | 'fail' | 'warning' | 'not_run'
  runningJobCount: number
  wikiPath: string
}
```

### 3.2 KnowledgePage

```ts
interface KnowledgePage {
  id: string
  kbId: string
  title: string
  type: 'overview' | 'concept' | 'entity' | 'synthesis' | 'other'
  path: string
  tags: string[]
  updatedAt: string | null
  citationCount: number
  rawCitationCount: number
  markdown?: string
}
```

### 3.3 RawSource

```ts
interface RawSource {
  id: string
  kbId: string
  title: string
  path: string
  source: string
  keyword: string
  importance: 'low' | 'medium' | 'high' | 'urgent'
  relevance: number
  compiled: boolean
  wordCount: number
  contributor?: string
  createdAt: string
  citationCount: number
  markdown?: string
}
```

### 3.4 Contribution

```ts
interface Contribution {
  id: string
  title: string
  type: 'document' | 'link' | 'note' | 'meeting_note' | 'chat_summary'
  targetKbId: string
  submitterName: string
  status: 'submitted' | 'ingesting' | 'accepted' | 'rejected' | 'compiled' | 'failed'
  summary?: string
  remark?: string
  url?: string
  fileName?: string
  createdAt: string
  updatedAt: string
  relatedJobId?: string
  rawSourceIds?: string[]
}
```

### 3.5 Job

```ts
interface Job {
  id: string
  type: 'harvest' | 'ingest' | 'normalize_raw' | 'compile_plan' | 'compile' | 'audit' | 'health_check' | 'route_query' | 'query'
  targetType: 'kb' | 'contribution' | 'workspace'
  targetId: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  progress: number
  createdAt: string
  startedAt?: string
  finishedAt?: string
  createdBy?: string
  errorMessage?: string
  artifacts: ArtifactRef[]
}
```

### 3.6 JobEvent

```ts
interface JobEvent {
  id: string
  jobId: string
  type: 'status' | 'progress' | 'log' | 'artifact' | 'error'
  message: string
  progress?: number
  createdAt: string
  payload?: Record<string, unknown>
}
```

### 3.7 ArtifactRef

```ts
interface ArtifactRef {
  type: 'compile_plan' | 'audit_report' | 'raw_source' | 'page' | 'log' | 'file'
  id?: string
  path?: string
  url?: string
  title?: string
}
```

### 3.8 AuditReport

```ts
interface AuditReport {
  kbId: string
  status: 'pass' | 'fail' | 'warning' | 'not_run'
  generatedAt: string | null
  totalRawRecords: number
  compiledRawRecords: number
  pendingRawRecords: number
  pageCount: number
  uncitedCompiledRaw: string[]
  highValueMissingFromOverview: string[]
  pagesWithoutRawCitations: string[]
  markdown?: string
}
```

### 3.9 QueryResult

```ts
interface QueryResult {
  answer: string
  confidence: 'high' | 'medium' | 'low'
  mode: 'single_kb' | 'cross_kb'
  scope: 'official' | 'include_uncompiled_raw' | 'include_contributions'
  matchedKbs: KnowledgeBaseMatch[]
  citations: Citation[]
  relatedPages: KnowledgePage[]
  relatedRawSources: RawSource[]
  generatedAt: string
}
```

## 4. Knowledge Base APIs

### 4.1 List Knowledge Bases

```text
GET /api/kbs
```

Query params:

```text
q?: string
tag?: string
healthStatus?: string
auditStatus?: string
page?: number
pageSize?: number
```

Response:

```json
{
  "data": [
    {
      "id": "claude-code",
      "name": "Claude Code",
      "description": "Claude Code knowledge base",
      "tags": ["ai-coding", "anthropic"],
      "pageCount": 24,
      "rawCount": 110,
      "pendingRawCount": 12,
      "lastUpdatedAt": "2026-06-07T10:00:00Z",
      "healthStatus": "healthy",
      "auditStatus": "pass",
      "runningJobCount": 0,
      "wikiPath": "knowledge/claude-code/wiki"
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  },
  "error": null
}
```

### 4.2 Create Knowledge Base

```text
POST /api/kbs
```

Request:

```json
{
  "id": "claude-code",
  "name": "Claude Code",
  "description": "Claude Code team knowledge base",
  "tags": ["ai-coding", "anthropic"]
}
```

Response: `201 Created`

```json
{
  "data": {
    "id": "claude-code",
    "name": "Claude Code",
    "description": "Claude Code team knowledge base",
    "tags": ["ai-coding", "anthropic"],
    "pageCount": 0,
    "rawCount": 0,
    "pendingRawCount": 0,
    "lastUpdatedAt": null,
    "healthStatus": "empty",
    "auditStatus": "not_run",
    "runningJobCount": 0,
    "wikiPath": "knowledge/claude-code/wiki"
  },
  "meta": {},
  "error": null
}
```

Backend behavior:

- Create KB directory.
- Create `wiki/WIKI.md`.
- Create `wiki/index.md`.
- Create `wiki/log.md`.
- Create `wiki/raw/`, `wiki/signals/`, `wiki/pages/*`.

### 4.3 Get Knowledge Base

```text
GET /api/kbs/:kbId
```

Response:

```json
{
  "data": {
    "id": "claude-code",
    "name": "Claude Code",
    "description": "Claude Code team knowledge base",
    "tags": ["ai-coding", "anthropic"],
    "pageCount": 24,
    "rawCount": 110,
    "pendingRawCount": 12,
    "lastUpdatedAt": "2026-06-07T10:00:00Z",
    "healthStatus": "healthy",
    "auditStatus": "pass",
    "runningJobCount": 0,
    "wikiPath": "knowledge/claude-code/wiki"
  },
  "meta": {},
  "error": null
}
```

### 4.4 Update Knowledge Base

```text
PATCH /api/kbs/:kbId
```

Request:

```json
{
  "name": "Claude Code",
  "description": "Updated description",
  "tags": ["ai-coding", "anthropic", "cli"]
}
```

Response: updated `KnowledgeBase`.

### 4.5 Get KB Overview

```text
GET /api/kbs/:kbId/overview
```

Response:

```json
{
  "data": {
    "kb": {},
    "indexMarkdown": "# Prism Wiki...",
    "overviewPages": [],
    "pageTypeCounts": {
      "overview": 3,
      "concept": 10,
      "entity": 8,
      "synthesis": 3,
      "other": 0
    },
    "recentPages": [],
    "recentRawSources": [],
    "latestCompileJob": null,
    "latestAuditReport": null
  },
  "meta": {},
  "error": null
}
```

## 5. Page APIs

### 5.1 List Pages

```text
GET /api/kbs/:kbId/pages
```

Query params:

```text
q?: string
type?: overview|concept|entity|synthesis|other
tag?: string
page?: number
pageSize?: number
```

Response:

```json
{
  "data": [
    {
      "id": "pages-overview-main",
      "kbId": "claude-code",
      "title": "Claude Code Overview",
      "type": "overview",
      "path": "pages/overview/claude-code-overview.md",
      "tags": ["claude-code"],
      "updatedAt": "2026-06-07T10:00:00Z",
      "citationCount": 12,
      "rawCitationCount": 8
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  },
  "error": null
}
```

### 5.2 Get Page

```text
GET /api/kbs/:kbId/pages/:pageId
```

Response:

```json
{
  "data": {
    "id": "pages-overview-main",
    "kbId": "claude-code",
    "title": "Claude Code Overview",
    "type": "overview",
    "path": "pages/overview/claude-code-overview.md",
    "tags": ["claude-code"],
    "updatedAt": "2026-06-07T10:00:00Z",
    "citationCount": 12,
    "rawCitationCount": 8,
    "markdown": "# Claude Code Overview\n\n..."
  },
  "meta": {},
  "error": null
}
```

### 5.3 Get Page Citations

```text
GET /api/kbs/:kbId/pages/:pageId/citations
```

Response:

```json
{
  "data": {
    "pageId": "pages-overview-main",
    "rawSources": [],
    "pageLinks": []
  },
  "meta": {},
  "error": null
}
```

## 6. Raw Source APIs

### 6.1 List Raw Sources

```text
GET /api/kbs/:kbId/raw
```

Query params:

```text
q?: string
compiled?: boolean
importance?: low|medium|high|urgent
source?: string
keyword?: string
kind?: manual|harvested|signal
page?: number
pageSize?: number
```

Response:

```json
{
  "data": [
    {
      "id": "raw-20260607-example",
      "kbId": "claude-code",
      "title": "Example Raw Source",
      "path": "raw/20260607/topic/example.md",
      "source": "manual",
      "keyword": "claude-code",
      "importance": "medium",
      "relevance": 0,
      "compiled": false,
      "wordCount": 1200,
      "contributor": "Alice",
      "createdAt": "2026-06-07T10:00:00Z",
      "citationCount": 0
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  },
  "error": null
}
```

### 6.2 Get Raw Source

```text
GET /api/kbs/:kbId/raw/:rawId
```

Response:

```json
{
  "data": {
    "id": "raw-20260607-example",
    "kbId": "claude-code",
    "title": "Example Raw Source",
    "path": "raw/20260607/topic/example.md",
    "source": "manual",
    "keyword": "claude-code",
    "importance": "medium",
    "relevance": 0,
    "compiled": false,
    "wordCount": 1200,
    "contributor": "Alice",
    "createdAt": "2026-06-07T10:00:00Z",
    "citationCount": 0,
    "markdown": "---\ntitle: Example Raw Source\n---\n\n# Example\n"
  },
  "meta": {},
  "error": null
}
```

### 6.3 Update Raw Source Metadata

```text
PATCH /api/kbs/:kbId/raw/:rawId
```

Request:

```json
{
  "importance": "high",
  "compiled": false
}
```

Response: updated `RawSource`.

## 7. Compile Plan APIs

### 7.1 Get Compile Plan

```text
GET /api/kbs/:kbId/compile-plan
```

Response:

```json
{
  "data": {
    "kbId": "claude-code",
    "generatedAt": "2026-06-07T10:00:00Z",
    "markdown": "# Prism Compile Plan\n\n...",
    "rawCoverage": [],
    "extractionRows": [],
    "overviewCoverage": []
  },
  "meta": {},
  "error": null
}
```

### 7.2 Regenerate Compile Plan

```text
POST /api/kbs/:kbId/regenerate-compile-plan
```

Response: `202 Accepted`

```json
{
  "data": {
    "jobId": "job_01",
    "status": "queued"
  },
  "meta": {},
  "error": null
}
```

Backend behavior:

- Create a `compile_plan` job.
- Run existing Prism compile plan generation in worker.
- Update `wiki/compile_plan.md`.

## 8. Audit APIs

### 8.1 Get Audit Report

```text
GET /api/kbs/:kbId/audit
```

Response:

```json
{
  "data": {
    "kbId": "claude-code",
    "status": "pass",
    "generatedAt": "2026-06-07T10:00:00Z",
    "totalRawRecords": 110,
    "compiledRawRecords": 98,
    "pendingRawRecords": 12,
    "pageCount": 24,
    "uncitedCompiledRaw": [],
    "highValueMissingFromOverview": [],
    "pagesWithoutRawCitations": [],
    "markdown": "# Prism Compile Audit: PASS\n\n..."
  },
  "meta": {},
  "error": null
}
```

### 8.2 Run Audit

```text
POST /api/kbs/:kbId/audit
```

Response: `202 Accepted`

```json
{
  "data": {
    "jobId": "job_02",
    "status": "queued"
  },
  "meta": {},
  "error": null
}
```

## 9. KB Operation APIs

### 9.1 Run Compile

```text
POST /api/kbs/:kbId/compile
```

Request:

```json
{
  "mode": "incremental",
  "createdBy": "Alice"
}
```

Response: `202 Accepted`

```json
{
  "data": {
    "jobId": "job_03",
    "status": "queued"
  },
  "meta": {},
  "error": null
}
```

### 9.2 Run Health Check

```text
POST /api/kbs/:kbId/health-check
```

Response: `202 Accepted`

```json
{
  "data": {
    "jobId": "job_04",
    "status": "queued"
  },
  "meta": {},
  "error": null
}
```

## 10. Contribution APIs

### 10.1 List Contributions

```text
GET /api/contributions
```

Query params:

```text
q?: string
targetKbId?: string
type?: string
status?: string
submitterName?: string
page?: number
pageSize?: number
```

Response:

```json
{
  "data": [
    {
      "id": "contrib_01",
      "title": "Claude Code meeting notes",
      "type": "note",
      "targetKbId": "claude-code",
      "submitterName": "Alice",
      "status": "submitted",
      "summary": "Notes about Claude Code workflow.",
      "createdAt": "2026-06-07T10:00:00Z",
      "updatedAt": "2026-06-07T10:00:00Z",
      "relatedJobId": "job_05",
      "rawSourceIds": []
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  },
  "error": null
}
```

### 10.2 Submit Document Contribution

```text
POST /api/contributions/document
```

Content type:

```text
multipart/form-data
```

Fields:

```text
targetKbId: string
title: string
submitterName: string
remark?: string
file: File
```

Response: `202 Accepted`

```json
{
  "data": {
    "contribution": {
      "id": "contrib_02",
      "title": "Uploaded document",
      "type": "document",
      "targetKbId": "claude-code",
      "submitterName": "Alice",
      "status": "submitted",
      "createdAt": "2026-06-07T10:00:00Z",
      "updatedAt": "2026-06-07T10:00:00Z",
      "relatedJobId": "job_06",
      "rawSourceIds": []
    },
    "jobId": "job_06"
  },
  "meta": {},
  "error": null
}
```

Backend behavior:

- Save uploaded file.
- Create contribution record.
- Create ingest job.
- Worker normalizes file into target KB raw layer.

### 10.3 Submit Link Contribution

```text
POST /api/contributions/link
```

Request:

```json
{
  "targetKbId": "claude-code",
  "title": "Article about Claude Code",
  "submitterName": "Alice",
  "url": "https://example.com/article",
  "remark": "Looks useful for the team."
}
```

Response: `202 Accepted`

```json
{
  "data": {
    "contribution": {},
    "jobId": "job_07"
  },
  "meta": {},
  "error": null
}
```

Backend behavior:

- Create contribution.
- Create fetch/ingest job.
- Worker fetches URL, creates raw or signal.

### 10.4 Submit Note Contribution

```text
POST /api/contributions/note
```

Request:

```json
{
  "targetKbId": "claude-code",
  "title": "Internal Claude Code usage note",
  "submitterName": "Alice",
  "body": "# Usage note\n\n...",
  "remark": "From today's discussion."
}
```

Response: `202 Accepted`

```json
{
  "data": {
    "contribution": {},
    "jobId": "job_08"
  },
  "meta": {},
  "error": null
}
```

Backend behavior:

- Create contribution.
- Create ingest job.
- Worker writes note as manual raw.

### 10.5 Get Contribution

```text
GET /api/contributions/:id
```

Response:

```json
{
  "data": {
    "id": "contrib_01",
    "title": "Claude Code meeting notes",
    "type": "note",
    "targetKbId": "claude-code",
    "submitterName": "Alice",
    "status": "submitted",
    "summary": "Notes about Claude Code workflow.",
    "remark": "From team meeting.",
    "createdAt": "2026-06-07T10:00:00Z",
    "updatedAt": "2026-06-07T10:00:00Z",
    "relatedJobId": "job_05",
    "rawSourceIds": [],
    "content": "# Meeting notes\n\n..."
  },
  "meta": {},
  "error": null
}
```

### 10.6 Update Contribution

```text
PATCH /api/contributions/:id
```

Request:

```json
{
  "title": "Updated title",
  "targetKbId": "codex",
  "status": "submitted"
}
```

Response: updated `Contribution`.

### 10.7 Delete Contribution

```text
DELETE /api/contributions/:id
```

Response:

```json
{
  "data": {
    "deleted": true
  },
  "meta": {},
  "error": null
}
```

## 11. Job APIs

### 11.1 List Jobs

```text
GET /api/jobs
```

Query params:

```text
type?: string
status?: string
targetType?: string
targetId?: string
page?: number
pageSize?: number
```

Response:

```json
{
  "data": [
    {
      "id": "job_01",
      "type": "compile",
      "targetType": "kb",
      "targetId": "claude-code",
      "status": "running",
      "progress": 45,
      "createdAt": "2026-06-07T10:00:00Z",
      "startedAt": "2026-06-07T10:01:00Z",
      "createdBy": "Alice",
      "artifacts": []
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  },
  "error": null
}
```

### 11.2 Get Job

```text
GET /api/jobs/:jobId
```

Response:

```json
{
  "data": {
    "id": "job_01",
    "type": "compile",
    "targetType": "kb",
    "targetId": "claude-code",
    "status": "running",
    "progress": 45,
    "createdAt": "2026-06-07T10:00:00Z",
    "startedAt": "2026-06-07T10:01:00Z",
    "createdBy": "Alice",
    "artifacts": []
  },
  "meta": {},
  "error": null
}
```

### 11.3 Get Job Events

```text
GET /api/jobs/:jobId/events
```

MVP transport: Server-Sent Events.

Event example:

```text
event: progress
data: {"jobId":"job_01","progress":45,"message":"Compiling raw sources"}
```

Supported event names:

```text
status
progress
log
artifact
error
done
```

### 11.4 Get Job Event History

```text
GET /api/jobs/:jobId/event-history
```

Response:

```json
{
  "data": [
    {
      "id": "event_01",
      "jobId": "job_01",
      "type": "log",
      "message": "Started compile",
      "createdAt": "2026-06-07T10:01:00Z"
    }
  ],
  "meta": {},
  "error": null
}
```

### 11.5 Cancel Job

```text
POST /api/jobs/:jobId/cancel
```

Response:

```json
{
  "data": {
    "id": "job_01",
    "status": "cancelled"
  },
  "meta": {},
  "error": null
}
```

## 12. Query APIs

### 12.1 Query Knowledge

```text
POST /api/query
```

Request:

```json
{
  "mode": "single_kb",
  "kbId": "claude-code",
  "question": "Claude Code 最近的能力变化对团队开发有什么影响？",
  "scope": "official"
}
```

Response:

```json
{
  "data": {
    "answer": "Claude Code recently...",
    "confidence": "high",
    "mode": "single_kb",
    "scope": "official",
    "matchedKbs": [
      {
        "kbId": "claude-code",
        "score": 999,
        "confidence": 1
      }
    ],
    "citations": [
      {
        "type": "page",
        "id": "pages-overview-main",
        "title": "Claude Code Overview",
        "path": "pages/overview/claude-code-overview.md"
      }
    ],
    "relatedPages": [],
    "relatedRawSources": [],
    "generatedAt": "2026-06-07T10:00:00Z"
  },
  "meta": {},
  "error": null
}
```

### 12.2 Route Query

```text
POST /api/route-query
```

Request:

```json
{
  "question": "Codex 和 Claude Code 哪个更适合团队自动化开发？",
  "scope": "official"
}
```

Response:

```json
{
  "data": {
    "answer": "...",
    "confidence": "medium",
    "mode": "cross_kb",
    "scope": "official",
    "matchedKbs": [
      {
        "kbId": "codex",
        "score": 12.4,
        "confidence": 0.9
      },
      {
        "kbId": "claude-code",
        "score": 11.8,
        "confidence": 0.86
      }
    ],
    "citations": [],
    "relatedPages": [],
    "relatedRawSources": [],
    "generatedAt": "2026-06-07T10:00:00Z"
  },
  "meta": {},
  "error": null
}
```

## 13. Activity APIs

### 13.1 Get KB Activity

```text
GET /api/kbs/:kbId/activity
```

Query params:

```text
page?: number
pageSize?: number
```

Response:

```json
{
  "data": [
    {
      "id": "activity_01",
      "type": "compile",
      "message": "Compile completed",
      "createdAt": "2026-06-07T10:00:00Z",
      "actor": "Alice",
      "jobId": "job_01"
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  },
  "error": null
}
```

## 14. Settings APIs

### 14.1 Get Settings

```text
GET /api/settings
```

Response:

```json
{
  "data": {
    "workspacePath": "/data/prism-team",
    "defaultQueryScope": "official",
    "defaultUploadTargetKbId": null,
    "jobRefreshIntervalMs": 3000,
    "sseEnabled": true,
    "markdown": {
      "enableWikiLinks": true
    }
  },
  "meta": {},
  "error": null
}
```

### 14.2 Update Settings

```text
PATCH /api/settings
```

Request:

```json
{
  "defaultQueryScope": "official",
  "jobRefreshIntervalMs": 5000,
  "sseEnabled": true
}
```

Response: updated settings.

## 15. Suggested Backend Job Pipeline

### 15.1 Document Contribution

```text
POST /api/contributions/document
  -> create contribution
  -> create ingest job
  -> worker saves file
  -> worker normalizes raw
  -> worker updates raw index
  -> worker emits artifact raw_source
  -> job succeeds
```

### 15.2 Link Contribution

```text
POST /api/contributions/link
  -> create contribution
  -> create fetch/ingest job
  -> worker fetches URL
  -> worker extracts content
  -> worker writes raw or signal
  -> worker updates raw/signals index
  -> job succeeds
```

### 15.3 Note Contribution

```text
POST /api/contributions/note
  -> create contribution
  -> create ingest job
  -> worker writes note as manual raw
  -> worker updates raw index
  -> job succeeds
```

### 15.4 Compile

```text
POST /api/kbs/:kbId/compile
  -> create compile job
  -> normalize raw
  -> scan raw
  -> generate compile plan
  -> compile pages
  -> update index
  -> run audit
  -> publish artifacts
  -> job succeeds or fails
```

### 15.5 Audit

```text
POST /api/kbs/:kbId/audit
  -> create audit job
  -> run compile_audit
  -> persist audit report
  -> update KB auditStatus
  -> job succeeds
```

## 16. Backend Storage Notes

The backend can combine:

- Filesystem for Prism Markdown wiki files.
- Database for metadata, jobs, contributions, activity, and indexes.
- Object storage or local storage for uploaded files.

Suggested workspace layout:

```text
workspace/
  knowledge/
    {kbId}/
      wiki/
        WIKI.md
        index.md
        log.md
        compile_plan.md
        raw/
        signals/
        pages/
  contributions/
    {contributionId}/
      original/
      metadata.json
  jobs/
    {jobId}/
      logs.jsonl
      artifacts/
```

## 17. MVP Implementation Priority

Backend can be implemented in this order:

1. KB CRUD.
2. Page/raw read APIs.
3. Contribution create/list/detail.
4. Job create/list/detail/event APIs.
5. Document and note ingestion jobs.
6. Compile plan and audit jobs.
7. Compile job.
8. Query and route-query APIs.
9. Settings and activity APIs.

