import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface FeedbackPayload {
  name: string;
  email: string;
  rating: number;
  comments: string;
}

@Injectable({ providedIn: 'root' })
export class FeedbackService {
  private readonly http = inject(HttpClient);

  submit(payload: FeedbackPayload): Observable<{ status: string }> {
    return this.http.post<{ status: string }>('/api/v1/feedback', payload);
  }
}
