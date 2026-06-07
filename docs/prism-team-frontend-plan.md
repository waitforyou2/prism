# Prism Team Frontend Design & Development Plan

## 1. Positioning

Prism Team Frontend MVP is a no-login, no-permission team knowledge workspace.

All users can:

- View team knowledge bases.
- Upload documents.
- Submit links.
- Write notes.
- Trigger backend jobs.
- View compile plans, audit reports, raw sources, pages, and query results.

The frontend is not a document website. It is an operational console for team knowledge assets.

Core workflow:

```text
View team knowledge bases
  -> Upload material / submit link / write note
  -> Backend creates job
  -> User watches job progress
  -> User checks raw / compile plan / audit
  -> User queries knowledge base
```

Out of scope for MVP:

- Login.
- Member management.
- Role-based access control.
- Complex approval workflow.
- Real-time collaborative editing.
- Knowledge graph visualization.

## 2. Tech Stack

Recommended stack:

```text
Vue 3
Vite
TypeScript
Vue Router
Pinia
Naive UI
TanStack Query for Vue
Markdown-it
Monaco Editor
ECharts
SSE
```

Responsibilities:

- Vue 3 + Composition API: application framework.
- Vite: development/build tool.
- TypeScript: type safety.
- Vue Router: page routing.
- Pinia: lightweight global UI/workspace state.
- TanStack Query: server data fetching, cache, loading, error, mutation refresh.
- Naive UI: dashboard/workbench components.
- Markdown-it: render `WIKI.md`, pages, raw records, compile plan, audit reports.
- Monaco Editor: note editor and future Markdown editing.
- ECharts: status charts and knowledge-base distribution.
- SSE: job logs and progress updates.

Pinia should not store most API data. API data should be managed by TanStack Query.

## 3. Information Architecture

Primary navigation:

```text
Dashboard
Knowledge Bases
Contributions
Jobs
Query
Settings
```

Routes:

```text
/
/dashboard

/kbs
/kbs/:kbId
/kbs/:kbId/overview
/kbs/:kbId/pages
/kbs/:kbId/raw
/kbs/:kbId/compile-plan
/kbs/:kbId/audit
/kbs/:kbId/activity
/kbs/:kbId/settings

/contributions
/contributions/:contributionId

/jobs
/jobs/:jobId

/query

/settings
```

`/` redirects to `/dashboard`.

## 4. Page Design

### 4.1 Dashboard

Purpose: team knowledge overview.

Show:

- Knowledge base count.
- Page count.
- Raw source count.
- Pending raw count.
- Submitted contribution count.
- Running job count.
- Recent failed job count.
- Latest audit status.

Sections:

- Metric strip.
- Recently active knowledge bases.
- Submitted contributions.
- Running jobs.
- Audit failure alerts.
- Knowledge health trend.

Interactions:

- Open knowledge base detail.
- Open failed job detail.
- Open contribution detail.
- Open upload material dialog.

### 4.2 Knowledge Base List

Purpose: scan, search, and enter team knowledge bases.

Fields:

- Name.
- Description.
- Tags.
- Page count.
- Raw count.
- Pending raw count.
- Last updated time.
- Audit status.
- Health status.
- Running job count.

Actions:

- Create knowledge base.
- Search knowledge bases.
- Filter by tag.
- Filter by status.
- Open detail.
- Upload material.
- Run compile.
- Run audit.
- Run health check.

Default view: dense table.

Health states:

```text
healthy
warning
failed
stale
empty
compiling
auditing
```

### 4.3 Knowledge Base Detail

Purpose: central workspace for one knowledge base.

Header:

- Name.
- Description.
- Tags.
- Updated time.
- Page count.
- Raw count.
- Health status.
- Latest audit status.

Primary actions:

- Upload document.
- Submit link.
- Write note.
- Run compile.
- Run audit.
- Query this KB.

Tabs:

```text
Overview
Pages
Raw Sources
Compile Plan
Audit
Activity
Settings
```

### 4.4 KB Overview

Show:

- `index.md` summary.
- Overview page list.
- Page type distribution.
- Recently updated pages.
- Recently added raw sources.
- Latest compile result.
- Latest audit result.

Page type distribution:

```text
overview
concept
entity
synthesis
other
```

### 4.5 Pages

Purpose: browse compiled Prism pages.

Fields:

- Title.
- Type.
- Path.
- Tags.
- Updated time.
- Citation count.
- Raw citation count.

Filters:

- Page type.
- Title search.
- Tags.

Detail layout:

```text
Left: page list or page tree
Center: Markdown viewer
Right: citation panel
```

MVP can start with table/list + Markdown viewer.

### 4.6 Raw Sources

Purpose: manage and inspect source layer.

Fields:

- Title.
- Source.
- Keyword.
- Importance.
- Relevance.
- Compiled.
- Word count.
- Contributor.
- Created time.
- Citation count.
- Path.

States:

```text
compiled
uncompiled
signal
manual
failed
```

Filters:

- Compiled true/false.
- Importance.
- Source.
- Keyword.
- Manual/harvested.

Actions:

- View raw content.
- Change priority.
- Trigger compile.
- View cited pages.

### 4.7 Compile Plan

Purpose: make `compile_plan.md` visible and operational.

Sections:

- Raw Coverage Checklist.
- Extraction Table.
- Overview Coverage.

Raw Coverage Checklist fields:

- Raw path.
- Title.
- Importance.
- Relevance.
- Status.
- Target pages.

Extraction Table fields:

- Raw Source.
- Entity.
- Concept.
- Claim / Detail.
- Target Page.
- Status.

Overview Coverage fields:

- High-value raw.
- Covered by overview.
- Linked overview page.

MVP can render Markdown first, with basic parsed tables later.

Actions:

- Regenerate compile plan.
- Run compile.
- Open raw source.
- Open target page.

### 4.8 Audit

Purpose: show compile quality report.

Audit states:

```text
pass
fail
warning
not_run
```

Fields:

- `total_raw_records`
- `compiled_raw_records`
- `pending_raw_records`
- `page_count`
- `uncited_compiled_raw`
- `high_value_missing_from_overview`
- `pages_without_raw_citations`

Interactions:

- Click raw issue -> raw source detail.
- Click page issue -> page detail.
- Run audit.
- Run compile.
- Export report.

### 4.9 Contributions

Purpose: team contribution inbox.

There is no permission or approval gate in MVP. Everyone can submit material.

Contribution types:

```text
document
link
note
meeting_note
chat_summary
```

Contribution states:

```text
submitted
ingesting
accepted
rejected
compiled
failed
```

Fields:

- Title.
- Type.
- Target knowledge base.
- Submitter name.
- Status.
- Created time.
- Summary.
- Related job.

Submit dialog fields:

- Target knowledge base.
- Contribution type.
- Title.
- Submitter name.
- File / URL / note body.
- Remark.

Submit result:

```text
Create contribution
Create ingest job
Navigate to job detail or contribution detail
```

### 4.10 Contribution Detail

Show:

- Original content.
- Attachment or URL.
- Target KB.
- Submitter name.
- AI summary.
- Current status.
- Related jobs.
- Raw sources created after ingestion.

Actions:

- Re-ingest.
- Move to another knowledge base.
- Delete contribution.

### 4.11 Jobs

Purpose: make backend workflows observable.

Job types:

```text
harvest
ingest
normalize_raw
compile_plan
compile
audit
health_check
route_query
query
```

Job states:

```text
queued
running
succeeded
failed
cancelled
```

Fields:

- Job ID.
- Type.
- Target.
- Status.
- Progress.
- Created time.
- Started time.
- Finished time.
- Duration.
- Created by.
- Error message.

Job detail:

- Basic metadata.
- Step timeline.
- Real-time logs.
- Artifact links.
- Error details.

SSE endpoint:

```text
GET /api/jobs/:jobId/events
```

### 4.12 Query

Purpose: query team knowledge.

Modes:

```text
single_kb
cross_kb
```

Scopes:

```text
official
include_uncompiled_raw
include_contributions
```

Default scope: `official`.

Layout:

```text
Top: query input
Left: scope and KB selector
Center: answer
Right: citations
Bottom: related pages and raw sources
```

Answer fields:

- Answer.
- Confidence.
- Matched KBs.
- Citations.
- Related pages.
- Related raw sources.
- Generated time.

Actions:

- Copy answer.
- Open citation.
- Mark stale.
- Save as contribution.
- Request recompile.

### 4.13 Settings

MVP settings only. No permissions.

Workspace settings:

- Workspace path.
- Default query scope.
- Default upload target.
- Job refresh interval.
- SSE enabled/disabled.
- Markdown render options.

KB settings:

- Name.
- Description.
- Tags.
- View `WIKI.md`.

MVP can make `WIKI.md` read-only.

## 5. Component Structure

```text
src/
  main.ts
  App.vue

  app/
    router.ts
    query.ts
    naive.ts

  layouts/
    AppLayout.vue
    MainSidebar.vue
    TopBar.vue
    PageShell.vue

  pages/
    DashboardPage.vue
    KbListPage.vue
    KbDetailPage.vue
    KbOverviewPage.vue
    KbPagesPage.vue
    KbRawPage.vue
    KbCompilePlanPage.vue
    KbAuditPage.vue
    KbActivityPage.vue
    ContributionsPage.vue
    ContributionDetailPage.vue
    JobsPage.vue
    JobDetailPage.vue
    QueryPage.vue
    SettingsPage.vue

  components/
    common/
      PageHeader.vue
      StatusBadge.vue
      MetricCard.vue
      EmptyState.vue
      LoadingBlock.vue
      ErrorBlock.vue
      MarkdownViewer.vue
      SplitPane.vue

    kb/
      KbTable.vue
      KbStatusBadge.vue
      KbHealthBadge.vue
      KbActionBar.vue
      KbSummaryPanel.vue
      PageTypeBadge.vue
      PageList.vue
      PageViewer.vue
      RawSourceTable.vue
      RawSourceDetailDrawer.vue
      CompilePlanView.vue
      AuditReportView.vue
      CitationPanel.vue

    contribution/
      ContributionTable.vue
      ContributionSubmitDialog.vue
      ContributionDetailPanel.vue
      UploadDocumentForm.vue
      SubmitLinkForm.vue
      SubmitNoteForm.vue

    job/
      JobTable.vue
      JobStatusBadge.vue
      JobTimeline.vue
      JobLogViewer.vue
      JobProgress.vue

    query/
      QueryComposer.vue
      QueryScopeSelector.vue
      AnswerView.vue
      QueryCitationPanel.vue
      RelatedSources.vue

  stores/
    layout.store.ts
    workspace.store.ts
    query.store.ts

  api/
    client.ts
    kbs.api.ts
    pages.api.ts
    raw.api.ts
    contributions.api.ts
    jobs.api.ts
    query.api.ts
    settings.api.ts

  queries/
    useKbs.ts
    useKb.ts
    usePages.ts
    useRawSources.ts
    useCompilePlan.ts
    useAuditReport.ts
    useContributions.ts
    useJobs.ts
    useQueryKnowledge.ts

  types/
    kb.ts
    page.ts
    raw.ts
    contribution.ts
    job.ts
    query.ts
    audit.ts

  utils/
    format.ts
    markdown.ts
    status.ts
```

## 6. State Management

Pinia stores:

```text
layout.store.ts
  sidebarCollapsed
  theme
  activeMenu

workspace.store.ts
  workspaceName
  currentKbId
  recentKbIds

query.store.ts
  lastQuery
  queryMode
  selectedKbIds
  scope
```

TanStack Query hooks:

```text
useKbs()
useKb(kbId)
useKbPages(kbId)
useRawSources(kbId)
useCompilePlan(kbId)
useAuditReport(kbId)
useContributions()
useJobs()
useJob(jobId)
```

Mutations:

```text
createKb()
uploadContribution()
submitLink()
submitNote()
runCompile()
runAudit()
runHealthCheck()
queryKnowledge()
```

## 7. Core Types

```ts
export interface KnowledgeBase {
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
}

export interface KnowledgePage {
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

export interface RawSource {
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
}

export interface Contribution {
  id: string
  title: string
  type: 'document' | 'link' | 'note' | 'meeting_note' | 'chat_summary'
  targetKbId: string
  submitterName: string
  status: 'submitted' | 'ingesting' | 'accepted' | 'rejected' | 'compiled' | 'failed'
  summary?: string
  createdAt: string
  relatedJobId?: string
}

export interface Job {
  id: string
  type: 'harvest' | 'ingest' | 'normalize_raw' | 'compile_plan' | 'compile' | 'audit' | 'health_check' | 'query'
  targetType: 'kb' | 'contribution' | 'workspace'
  targetId: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  progress: number
  createdAt: string
  startedAt?: string
  finishedAt?: string
  errorMessage?: string
}
```

## 8. Interaction Principles

- Every long-running operation creates a job.
- No page should block while compile/audit/ingest runs.
- Every failed job must expose the error reason.
- Every raw source should be traceable to pages.
- Every page should expose raw citations.
- Every audit failure should link to the object that needs attention.
- Uploading material should be simple and fast.

Upload document flow:

```text
Click upload
Select target KB
Fill submitter name
Select file
Submit
Create contribution
Create ingest job
Navigate to job detail
```

Submit link flow:

```text
Click submit link
Select target KB
Fill submitter name
Paste URL
Optional remark
Submit
Create fetch/ingest job
```

Write note flow:

```text
Click write note
Select target KB
Fill submitter name
Fill title and body
Submit
Create manual raw
Create compile-plan job
```

## 9. Visual Direction

Style:

```text
Workbench
Restrained
Clear
Medium-high information density
Similar to Linear / GitHub / Notion database / Vercel dashboard
```

Layout:

- Left sidebar.
- Top operation bar.
- Main content region.
- Right-side drawer for details.

Avoid:

- Marketing hero.
- Decorative illustration-heavy layout.
- Gradient backgrounds.
- Low-density card-only pages.

Status colors:

```text
healthy / pass      green
warning / stale     amber
failed / fail       red
running             blue
queued              gray
compiled            green
uncompiled          amber
```

## 10. MVP Development Order

### Phase 1: Project Skeleton

- Vite + Vue 3 + TypeScript.
- Vue Router.
- Pinia.
- Naive UI.
- TanStack Query.
- API client.

### Phase 2: Layout

- AppLayout.
- Sidebar.
- TopBar.
- PageHeader.
- Route frame.

### Phase 3: Mock Data

- KB mock.
- Raw mock.
- Page mock.
- Audit mock.
- Job mock.
- Contribution mock.

### Phase 4: Knowledge Base Module

- Knowledge base list.
- KB detail.
- Overview.
- Pages.
- Raw Sources.

### Phase 5: Prism-Specific Module

- Compile Plan.
- Audit Report.
- Citation Panel.

### Phase 6: Contribution Module

- Upload document dialog.
- Submit link dialog.
- Write note dialog.
- Contribution list/detail.

### Phase 7: Job Center

- Job list.
- Job detail.
- Job timeline.
- SSE log viewer.

### Phase 8: Query

- Query composer.
- Answer view.
- Citation panel.
- Single-KB and cross-KB modes.

### Phase 9: Real Backend Integration

- Replace mock APIs.
- Add loading/error/empty states.
- Add mutation refresh strategy.

## 11. MVP Acceptance Criteria

The frontend is ready when users can:

- View all knowledge bases.
- Create a knowledge base.
- Open a knowledge base detail page.
- View pages/raw/compile plan/audit.
- Upload a document.
- Submit a link.
- Write a note.
- View contribution records.
- View backend job progress.
- Trigger compile and audit.
- Query knowledge bases.
- See answer citations.

