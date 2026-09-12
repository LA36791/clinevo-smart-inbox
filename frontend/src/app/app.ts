import { Component } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';

interface EmailItem {
  id: string;
  sender: string;
  subject: string;
  date: string;
  body: string;
  attachments: string[];
}

interface AuditEntry {
  action: string;
  emailId: string;
  timestamp: string;
  details: string;
}

@Component({
  selector: 'app-root',
  imports: [DecimalPipe],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {

  selectedFile: File | null = null;
  analysis: any = null;
  loading = false;
  error = '';

  selectedEmail: EmailItem | null = null;
  reviewStatus = '';
  auditLog: AuditEntry[] = [];

  emails: EmailItem[] = [
    {
      id: 'MSG-001',
      sender: 'safety@example.test',
      subject: 'Adverse event report - Product A',
      date: '2026-09-08 09:12',
      body: 'Patient P-001 received Product A and developed nausea. Severity was non-serious. Batch BATCH-001. Reporter is Dr. Smith.',
      attachments: ['synthetic_case.pdf']
    },
    {
      id: 'MSG-002',
      sender: 'quality@example.test',
      subject: 'Complaint regarding Product B packaging',
      date: '2026-09-08 09:25',
      body: 'We received a complaint that Product B packaging was damaged on arrival. Lot LOT-2045. Please investigate the quality issue.',
      attachments: []
    },
    {
      id: 'MSG-003',
      sender: 'medical@example.test',
      subject: 'Medical information request - Product C',
      date: '2026-09-08 09:41',
      body: 'Please provide information about the recommended dosage and administration of Product C for adult patients.',
      attachments: []
    },
    {
      id: 'MSG-004',
      sender: 'safety2@example.test',
      subject: 'Serious reaction reported',
      date: '2026-09-08 10:03',
      body: 'Patient P-014 experienced severe dizziness after receiving Product D. The event required hospitalization. Reporter: Dr. Kumar.',
      attachments: ['case_014.pdf']
    },
    {
      id: 'MSG-005',
      sender: 'quality2@example.test',
      subject: 'Product defect complaint',
      date: '2026-09-08 10:17',
      body: 'The customer reports that Product E tablets were broken inside the package. Batch B-7788.',
      attachments: ['product_photo.pdf']
    },
    {
      id: 'MSG-006',
      sender: 'medical2@example.test',
      subject: 'Question about Product F',
      date: '2026-09-08 10:31',
      body: 'Can you confirm whether Product F has any known interaction with common antihypertensive medicines?',
      attachments: []
    },
    {
      id: 'MSG-007',
      sender: 'newsletter@example.test',
      subject: 'Monthly company newsletter',
      date: '2026-09-08 10:46',
      body: 'Please find attached our monthly internal newsletter containing company updates and employee announcements.',
      attachments: ['newsletter.pdf']
    },
    {
      id: 'MSG-008',
      sender: 'safety3@example.test',
      subject: 'Patient reaction follow-up',
      date: '2026-09-08 11:02',
      body: 'Follow-up for patient P-021. Product G caused headache and vomiting. Severity: serious. Reporter: Dr. Rao.',
      attachments: []
    },
    {
      id: 'MSG-009',
      sender: 'quality3@example.test',
      subject: 'Wrong label on Product H',
      date: '2026-09-08 11:19',
      body: 'A customer reported an incorrect label on Product H. Lot number LOT-9981. No patient reaction was reported.',
      attachments: []
    },
    {
      id: 'MSG-010',
      sender: 'medical3@example.test',
      subject: 'Product I clinical information',
      date: '2026-09-08 11:36',
      body: 'Could you provide the clinical information and indications available for Product I?',
      attachments: ['product_i_info.pdf']
    }
  ];

  constructor(private http: HttpClient) {
    this.selectedEmail = this.emails[0];
  }

  selectEmail(email: EmailItem): void {
    this.selectedEmail = email;
    this.analysis = null;
    this.error = '';
    this.loading = false;
    this.reviewStatus = '';
    this.selectedFile = null;
  }

  analyzeSelectedEmail(): void {
    if (!this.selectedEmail) return;

    this.loading = true;
    this.error = '';
    this.analysis = null;
    this.reviewStatus = '';

    const start = performance.now();

    const request = {
      messageId: this.selectedEmail.id,
      sender: this.selectedEmail.sender,
      subject: this.selectedEmail.subject,
      date: this.selectedEmail.date,
      body: this.selectedEmail.body,
      attachments: this.selectedEmail.attachments
    };

    this.http.post<any>('/api/analyze', request).subscribe({
      next: (result) => {
        const elapsed = Math.round(performance.now() - start);

        this.analysis = {
          ...result,
          processing_time_ms: result.processing_time_ms ?? elapsed
        };

        this.loading = false;

        this.addAudit(
          'AI_ANALYSIS',
          `AI analyzed ${this.selectedEmail?.id} in ${this.analysis.processing_time_ms} ms`
        );
      },
      error: (err) => {
        console.error('ANALYSIS ERROR:', err);
        this.loading = false;
        this.error = `Analysis failed: HTTP ${err.status || 'unknown'}`;
      }
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) return;

    this.selectedFile = file;
    this.analysis = null;
    this.error = '';
    this.reviewStatus = '';
    this.loading = true;

    const start = performance.now();
    const formData = new FormData();
    formData.append('file', file);

    this.http.post<any>('/api/analyze-document', formData).subscribe({
      next: (result) => {
        const elapsed = Math.round(performance.now() - start);

        this.analysis = {
          ...result,
          processing_time_ms: result.processing_time_ms ?? elapsed
        };

        this.loading = false;

        this.addAudit(
          'PDF_ANALYSIS',
          `PDF ${file.name} processed in ${this.analysis.processing_time_ms} ms`
        );
      },
      error: (err) => {
        console.error('PDF ANALYSIS ERROR:', err);
        this.loading = false;
        this.error = `PDF analysis failed: HTTP ${err.status || 'unknown'}`;
      }
    });
  }

  acceptDecision(): void {
    if (!this.analysis || !this.selectedEmail) return;

    this.reviewStatus = 'ACCEPTED';

    this.addAudit(
      'REVIEW_ACCEPTED',
      `Human reviewer accepted AI decision for ${this.selectedEmail.id}`
    );
  }

  overrideDecision(): void {
    if (!this.analysis || !this.selectedEmail) return;

    this.reviewStatus = 'OVERRIDDEN';

    this.addAudit(
      'REVIEW_OVERRIDDEN',
      `Human reviewer overrode AI decision for ${this.selectedEmail.id}`
    );
  }

  addAudit(action: string, details: string): void {
    this.auditLog.unshift({
      action,
      emailId: this.selectedEmail?.id || 'DOCUMENT',
      timestamp: new Date().toISOString(),
      details
    });
  }

  getConfidenceClass(value: number | undefined): string {
    if (value === undefined || value === null) return 'confidence-low';

    if (value >= 0.85) return 'confidence-high';
    if (value >= 0.60) return 'confidence-medium';

    return 'confidence-low';
  }

  getCategoryLabel(category: string): string {
    const labels: Record<string, string> = {
      SAFETY_REPORT_ICSR: 'Safety Report / ICSR',
      QUALITY_COMPLAINT_PQC: 'Quality Complaint / PQC',
      INFO_REQUEST_MI: 'Info Request / MI',
      NOT_RELEVANT: 'Not Relevant'
    };

    return labels[category] || category;
  }
}
