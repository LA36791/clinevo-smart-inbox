import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  selectedFile: File | null = null;
  analysis: any = null;
  analyzing = false;
  message = 'Ready for review';

  inbox = [
    { subject: 'Adverse event report – Product A', sender: 'clinical@synthetic-health.test', category: 'Safety Report / ICSR', confidence: 0.92, status: 'Needs Review' },
    { subject: 'Complaint: damaged package – Product B', sender: 'quality@synthetic-health.test', category: 'Quality Complaint / PQC', confidence: 0.89, status: 'Needs Review' },
    { subject: 'Question regarding Product C dosage', sender: 'medical@synthetic-health.test', category: 'Info Request / MI', confidence: 0.94, status: 'Reviewed' },
    { subject: 'Conference registration confirmation', sender: 'events@synthetic-health.test', category: 'Not Relevant', confidence: 0.98, status: 'Reviewed' }
  ];

  constructor(private http: HttpClient) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0] ?? null;
    this.analysis = null;
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
    this.message = 'AI is analyzing document...';

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http.post<any>(
      'https://clinevo-smart-inbox-backend.onrender.com/api/analyze',
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

        this.analyzing = false;
        this.message = 'Analysis completed — human review required.';
      },
      error: (error) => {
        console.error('ANALYSIS ERROR:', error);
        this.analyzing = false;
        this.message =
          `Analysis failed: ${error.status || ''} ${error.statusText || error.message || ''}`;
      }
    });
  }

  acceptDecision() {
    this.message = '✓ AI decision accepted — reviewer action recorded.';
  }

  overrideDecision() {
    this.message = '↻ Override recorded — reviewer action logged.';
  }

  confidence(value: number) {
    return Math.round((value ?? 0) * 100);
  }
}
