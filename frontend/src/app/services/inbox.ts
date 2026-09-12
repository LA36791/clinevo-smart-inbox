import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class InboxService {

  private readonly apiUrl = '/api';

  async analyzeDocument(file: File): Promise<any> {
    const form = new FormData();
    form.append('file', file);

    const response = await fetch(
      `${this.apiUrl}/analyze-document`,
      {
        method: 'POST',
        body: form
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }
}