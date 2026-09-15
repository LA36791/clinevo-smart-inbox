import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {

  // Production-safe: override with window.__BACKEND_URL__ (env-injected at
  // serve time) or localStorage 'clinevo_backend_url'; falls back to
  // same-origin '' for deployed frontend+backend, then localhost for dev.
  private backendUrl(): string {
    const w = window as any;
    const configured: string =
      w.__BACKEND_URL__ ||
      localStorage.getItem('clinevo_backend_url') ||
      '';
    if (configured) {
      return configured.replace(/\/$/, '');
    }
    if (window.location.port === '4200') {
      return 'http://localhost:8080';
    }
    if (/\.onrender\.com$/.test(window.location.hostname)) {
      // Static-hosted frontend: same origin serves no backend; use the deployed API.
      return 'https://clinevo-smart-inbox.onrender.com';
    }
    return '';
  }

  backendLabel(): string {
    return this.backendUrl() || '(same origin)';
  }

  selectedFile: File | null = null;
  analysis: any = null;
  activeTab: string = 'inbox';
  selectedInboxItem: number | null = null;

  analyzing = false;
  reviewing = false;
  backendOnline: boolean | null = null;

  message = 'Ready for review';

  reviewer = 'Human Reviewer';
  reviewNotes = '';

  overrideCategory = '';

  reviewCompleted = false;
  reviewAction = '';

  auditEntries: any[] = null;
  auditLoading = false;

  loadAudit() {
    if (!this.analysis?.analysisId) {
      this.message = 'Audit requires a saved analysis (analysisId).';
      return;
    }
    this.auditLoading = true;
    this.http
      .get<any[]>(`${this.backendUrl()}/api/audit?analysisId=${Number(this.analysis.analysisId)}`)
      .subscribe({
        next: (rows) => {
          this.auditEntries = rows || [];
          this.auditLoading = false;
        },
        error: () => {
          this.auditEntries = [];
          this.auditLoading = false;
          this.message = 'Audit history could not be loaded.';
        },
      });
  }

  // Dashboard metrics
  dashboard = {
    totalProcessed: 0,
    safetyCount: 0,
    pqcCount: 0,
    miCount: 0,
    notRelevantCount: 0,
    reviewRequired: 0,
    avgProcessingTime: 0,
  };

  inbox = [
    {
      id: 1,
      subject: 'Adverse event report – Product A',
      sender: 'clinical@synthetic-health.test',
      receivedAt: '2026-09-12T09:30:00Z',
      category: 'SAFETY_REPORT_ICSR',
      categoryLabel: 'Safety Report / ICSR',
      confidence: 0.92,
      status: 'Needs Review',
      priority: 'high',
      attachment: 'safety_case.pdf',
      summary: 'Patient P-100 reported severe headache after Product A.',
    },
    {
      id: 2,
      subject: 'Complaint: damaged package – Product B',
      sender: 'quality@synthetic-health.test',
      receivedAt: '2026-09-12T10:15:00Z',
      category: 'QUALITY_COMPLAINT_PQC',
      categoryLabel: 'Quality Complaint / PQC',
      confidence: 0.89,
      status: 'Needs Review',
      priority: 'medium',
      attachment: 'complaint_batch99.pdf',
      summary: 'Batch BATCH-99 reported with damaged packaging and broken tablets.',
    },
    {
      id: 3,
      subject: 'Question regarding Product C dosage',
      sender: 'medical@synthetic-health.test',
      receivedAt: '2026-09-12T11:00:00Z',
      category: 'INFO_REQUEST_MI',
      categoryLabel: 'Info Request / MI',
      confidence: 0.94,
      status: 'Reviewed',
      priority: 'low',
      attachment: 'dosage_question.pdf',
      summary: 'Inquiry about recommended dosage for Product C in elderly patients.',
    },
    {
      id: 4,
      subject: 'Conference registration confirmation',
      sender: 'events@synthetic-health.test',
      receivedAt: '2026-09-12T12:00:00Z',
      category: 'NOT_RELEVANT',
      categoryLabel: 'Not Relevant',
      confidence: 0.98,
      status: 'Reviewed',
      priority: 'low',
      attachment: null,
      summary: 'Annual Healthcare Conference 2026 registration confirmed.',
    },
    {
      id: 5,
      subject: 'Quality issue: discoloration in Product D batch',
      sender: 'qc@synthetic-health.test',
      receivedAt: '2026-09-12T13:45:00Z',
      category: 'QUALITY_COMPLAINT_PQC',
      categoryLabel: 'Quality Complaint / PQC',
      confidence: 0.91,
      status: 'Needs Review',
      priority: 'medium',
      attachment: 'discoloration_batch50.pdf',
      summary: 'Discoloration and unusual odor detected in Batch BATCH-50.',
    },
  ];

  constructor(private http: HttpClient) {
    this.checkBackendHealth();
    this.computeDashboardMetrics();
  }

  ngOnInit(): void {
    this.computeDashboardMetrics();
  }

  checkBackendHealth() {
    this.http.get<any>(`${this.backendUrl()}/api/health`).subscribe({
      next: () => (this.backendOnline = true),
      error: () => (this.backendOnline = false),
    });
  }

  priorityClass(priority: string): string {
    return 'priority-' + priority;
  }

  categoryClass(category: string): string {
    return 'cat-' + category.toLowerCase().replace(/_/g, '-');
  }

  computeDashboardMetrics(): void {
    const items = this.inbox;
    this.dashboard.totalProcessed = items.length;
    this.dashboard.safetyCount = items.filter(i => i.category === 'SAFETY_REPORT_ICSR').length;
    this.dashboard.pqcCount = items.filter(i => i.category === 'QUALITY_COMPLAINT_PQC').length;
    this.dashboard.miCount = items.filter(i => i.category === 'INFO_REQUEST_MI').length;
    this.dashboard.notRelevantCount = items.filter(i => i.category === 'NOT_RELEVANT').length;
    this.dashboard.reviewRequired = items.filter(i => i.status === 'Needs Review').length;
    const confidences = items.map(i => i.confidence).filter(c => c > 0);
    this.dashboard.avgProcessingTime = confidences.length > 0
      ? Math.round(confidences.reduce((a, b) => a + b, 0) / confidences.length * 100) / 100
      : 0;
  }

  selectInboxItem(index: number): void {
    this.selectedInboxItem = index;
    const item = this.inbox[index];
    this.analysis = {
      categories: [{ category: item.category, confidence: item.confidence, reason: item.summary }],
      summary: item.summary,
      document_type: 'EMAIL',
      human_review_required: item.status === 'Needs Review',
      processing_time_ms: 0,
      timestamp_utc: item.receivedAt,
    };
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;

    this.selectedFile = input.files?.[0] ?? null;
    this.analysis = null;
    this.reviewCompleted = false;
    this.reviewAction = '';
    this.overrideCategory = '';
    this.reviewNotes = '';

    this.message = this.selectedFile
      ? `Selected: ${this.selectedFile.name}`
      : 'Ready for review';
  }

  analyze() {

    if (!this.selectedFile) {
      this.message = 'Please select a PDF first.';
      return;
    }

    this.analyzing = true;
    this.analysis = null;
    this.reviewCompleted = false;
    this.reviewAction = '';

    this.message = 'AI is analyzing document...';

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http.post<any>(
      `${this.backendUrl()}/api/analyze`,
      formData
    ).subscribe({

      next: (result) => {

        console.log('ANALYSIS RESULT:', result);

        if (typeof result === 'string') {
          try {
            this.analysis = JSON.parse(result);
          } catch {
            this.analysis = { summary: result };
          }
        } else {
          this.analysis = result;
        }

        this.overrideCategory =
          this.primaryCategory();

        this.analyzing = false;

        this.message =
          'Analysis completed – human review required.';
      },

      error: (error) => {

        console.error('ANALYSIS ERROR:', error);

        this.analyzing = false;

        this.message =
          `Analysis failed: ${error.status || ''} ${
            error.statusText || error.message || ''
          }`;
      }
    });
  }

  primaryCategory(): string {

    const category =
      this.analysis?.categories?.[0]?.category;

    return category || 'NOT_RELEVANT';
  }

  categoryLabel(category: string): string {

    const labels: Record<string, string> = {
      SAFETY_REPORT_ICSR: 'Safety Report / ICSR',
      QUALITY_COMPLAINT_PQC: 'Quality Complaint / PQC',
      INFO_REQUEST_MI: 'Info Request / MI',
      NOT_RELEVANT: 'Not Relevant'
    };

    return labels[category] || category;
  }

  confidence(value: number): number {
    return Math.round((value ?? 0) * 100);
  }

  evidenceCount(): number {

    const facts = this.analysis?.facts || [];

    return facts.filter(
      (fact: any) =>
        fact.evidence &&
        fact.evidence.length > 0
    ).length;
  }

  totalFactCount(): number {
    return this.analysis?.facts?.length || 0;
  }

  evidenceCoverage(): number {
    const coverage = this.analysis?.evidence_summary?.evidence_coverage;

    if (coverage && typeof coverage.coverage_percent === 'number') {
      return Math.round(coverage.coverage_percent);
    }

    const facts = this.analysis?.facts || [];
    const applicable = facts.filter(
      (fact: any) => fact?.value && fact.value !== 'Not stated'
    );

    if (!applicable.length) return 0;

    const supported = applicable.filter(
      (fact: any) => Array.isArray(fact?.evidence) && fact.evidence.length > 0
    ).length;

    return Math.round((supported / applicable.length) * 100);
  }

  lowConfidenceCount(): number {

    const facts = this.analysis?.facts || [];

    return facts.filter(
      (fact: any) =>
        (fact.confidence ?? 0) < 0.75
    ).length;
  }

  reviewPriority(): string {

    if (!this.analysis) {
      return ' ';
    }

    const categories =
      this.analysis.categories?.length || 0;

    const lowConfidence =
      this.lowConfidenceCount();

    const coverage =
      this.evidenceCoverage();

    if (
      categories > 1 ||
      lowConfidence > 0 ||
      coverage < 75
    ) {
      return 'HIGH';
    }

    if (
      this.analysis.human_review_required
    ) {
      return 'MEDIUM';
    }

    return 'LOW';
  }

  reviewPriorityClass(): string {

    const priority = this.reviewPriority();

    return priority.toLowerCase();
  }

  whyFlagged(): string {

    if (!this.analysis) {
      return '';
    }

    const reasons: string[] = [];

    if (this.analysis.human_review_required) {
      reasons.push('Human verification is required');
    }

    if (this.analysis.categories?.length > 1) {
      reasons.push('Multiple relevant categories detected');
    }

    if (this.lowConfidenceCount() > 0) {
      reasons.push(
        'One or more extracted facts have low confidence'
      );
    }

    if (this.evidenceCoverage() < 75) {
      reasons.push('Evidence coverage is incomplete');
    }

    if (!reasons.length) {
      return 'No major review risk detected.';
    }

    return reasons.join('. ') + '.';
  }

  missingInformation(): string[] {

    if (!this.analysis?.facts) {
      return [];
    }

    return this.analysis.facts
      .filter(
        (fact: any) =>
          fact.value === 'Not stated'
      )
      .map(
        (fact: any) =>
          fact.field
      );
  }

  acceptDecision() {

    this.submitReview(
      'ACCEPT',
      this.primaryCategory()
    );
  }

  overrideDecision() {

    if (!this.overrideCategory) {
      this.message =
        'Select the final category before overriding.';
      return;
    }

    this.submitReview(
      'OVERRIDE',
      this.overrideCategory
    );
  }

  private submitReview(
    action: string,
    finalCategory: string
  ) {

    if (!this.analysis?.analysisId) {

      this.message =
        'Review cannot be saved because analysisId is missing.';

      return;
    }

    this.reviewing = true;
    this.message = 'Saving reviewer decision...';

    const payload = {

      analysisId:
        Number(this.analysis.analysisId),

      action,

      originalCategory:
        this.primaryCategory(),

      finalCategory,

      reviewer:
        this.reviewer || 'Human Reviewer',

      notes:
        this.reviewNotes || ''
    };

    this.http.post<any>(
      `${this.backendUrl()}/api/review`,
      payload
    ).subscribe({

      next: (result) => {

        console.log('REVIEW SAVED:', result);

        this.reviewing = false;
        this.reviewCompleted = true;
        this.reviewAction = action;

        this.message =
          action === 'ACCEPT'
            ? '✓ AI decision accepted – reviewer action recorded.'
            : '↻ Decision overridden – reviewer action recorded.';
      },

      error: (error) => {

        console.error('REVIEW ERROR:', error);

        this.reviewing = false;

        this.message =
          `Review save failed: ${
            error.status || ''
          } ${
            error.error?.message ||
            error.statusText ||
            error.message ||
            ''
          }`;
      }
    });
  }
}