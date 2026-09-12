import { Component } from '@angular/core';
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
export class App {

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
    return '';
  }

  backendLabel(): string {
    return this.backendUrl() || '(same origin)';
  }

  selectedFile: File | null = null;
  analysis: any = null;

  analyzing = false;
  reviewing = false;
  backendOnline: boolean | null = null;

  message = 'Ready for review';

  reviewer = 'Human Reviewer';
  reviewNotes = '';

  overrideCategory = '';

  reviewCompleted = false;
  reviewAction = '';

  inbox = [
    {
      subject: 'Adverse event report – Product A',
      sender: 'clinical@synthetic-health.test',
      category: 'Safety Report / ICSR',
      confidence: 0.92,
      status: 'Needs Review'
    },
    {
      subject: 'Complaint: damaged package – Product B',
      sender: 'quality@synthetic-health.test',
      category: 'Quality Complaint / PQC',
      confidence: 0.89,
      status: 'Needs Review'
    },
    {
      subject: 'Question regarding Product C dosage',
      sender: 'medical@synthetic-health.test',
      category: 'Info Request / MI',
      confidence: 0.94,
      status: 'Reviewed'
    },
    {
      subject: 'Conference registration confirmation',
      sender: 'events@synthetic-health.test',
      category: 'Not Relevant',
      confidence: 0.98,
      status: 'Reviewed'
    }
  ];

  constructor(private http: HttpClient) {
    this.checkBackendHealth();
  }

  checkBackendHealth() {
    this.http.get<any>(`${this.backendUrl()}/api/health`).subscribe({
      next: () => (this.backendOnline = true),
      error: () => (this.backendOnline = false),
    });
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

    const total = this.totalFactCount();

    if (!total) {
      return 0;
    }

    return Math.round(
      (this.evidenceCount() / total) * 100
    );
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