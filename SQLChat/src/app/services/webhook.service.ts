import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';

export interface WebhookRequest {
  query?: string;
  userId?: string;
  timestamp?: string;
  data?: any;
}

export interface WebhookResponse {
  success: boolean;
  message?: string;
  data?: any;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class WebhookService {
  //private webhookUrl = 'http://localhost:5678/webhook-test/my-webhook';
  //private webhookUrl = 'http://localhost:5678/webhook/my-webhook';

     //private webhookUrl = 'http://localhost:5678/webhook-test/ask-db';
     private webhookUrl = 'http://localhost:8000/chat';

  constructor(private http: HttpClient) { }

  /**
   * Send data to n8n webhook using POST method
   * @param payload - Data to send to the webhook
   * @returns Observable with webhook response
   */
  sendToWebhook(payload: WebhookRequest): Observable<WebhookResponse> {
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    });

    const requestBody = {
      ...payload,
      timestamp: new Date().toISOString(),
      source: 'ues-analytics-hub'
    };

    return this.http.post<WebhookResponse>(this.webhookUrl, requestBody, { headers })
      .pipe(
        catchError(this.handleError)
      );
  }

  /**
   * Send search query to n8n webhook
   * @param query - Search query string
   * @returns Observable with webhook response
   */
  sendSearchQuery(query: string): Observable<WebhookResponse> {
    const payload: WebhookRequest = {
      query: query,
      userId: 'user-' + Math.random().toString(36).substr(2, 9),
      data: {
        type: 'search',
        source: 'analytics-hub'
      }
    };

    return this.sendToWebhook(payload);
  }

  /**
   * Send chart data request to n8n webhook
   * @param chartType - Type of chart requested
   * @returns Observable with webhook response
   */
  requestChartData(chartType: string): Observable<WebhookResponse> {
    const payload: WebhookRequest = {
      query: `Get ${chartType} data`,
      data: {
        type: 'chart-request',
        chartType: chartType,
        requestedAt: new Date().toISOString()
      }
    };

    return this.sendToWebhook(payload);
  }

  /**
   * Test webhook connection
   * @returns Observable with webhook response
   */
  testConnection(): Observable<WebhookResponse> {
    const payload: WebhookRequest = {
      query: 'test connection',
      data: {
        type: 'connection-test',
        message: 'Testing webhook connection from UES Analytics Hub'
      }
    };

    return this.sendToWebhook(payload);
  }

  /**
   * Handle HTTP errors
   * @param error - HTTP error response
   * @returns Observable error
   */
  private handleError(error: any): Observable<never> {
    let errorMessage = 'An unknown error occurred';
    
    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Client Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = `Server Error Code: ${error.status}\nMessage: ${error.message}`;
    }
    
    console.error('Webhook Service Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
