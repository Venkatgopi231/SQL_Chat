# Webhook Integration Test Guide

## Overview
The UES Analytics Hub now includes a webhook service that connects to n8n using POST requests.

## Webhook Service Features

### 1. **WebhookService Methods:**
- `sendToWebhook(payload)` - Generic POST method to send data
- `sendSearchQuery(query)` - Send search queries from the UI
- `requestChartData(chartType)` - Request specific chart data
- `testConnection()` - Test webhook connectivity

### 2. **Webhook URL:**
```
http://localhost:5678/webhook-test/my-webhook
```

### 3. **Request Format:**
```json
{
  "query": "user search query",
  "userId": "generated-user-id",
  "timestamp": "2026-01-19T07:30:00.000Z",
  "source": "ues-analytics-hub",
  "data": {
    "type": "search|chart-request|connection-test",
    "additional": "metadata"
  }
}
```

### 4. **Expected Response Format:**
```json
{
  "success": true,
  "message": "Response message",
  "data": {
    "any": "response data"
  }
}
```

## How to Test

### 1. **Start n8n (if not running):**
```bash
# Make sure n8n is running on localhost:5678
# Create a webhook node with URL: /webhook-test/my-webhook
```

### 2. **Test in the Application:**
1. Open the app at `http://localhost:4200/`
2. Type a query in the search box (e.g., "show revenue circle chart")
3. Press Enter or click Send
4. Check the browser console for webhook requests/responses
5. View the response in the UI below the search bar

### 3. **Automatic Tests:**
- Connection test runs automatically when the app loads
- Check browser console for connection status

## Integration Points

### 1. **Search Functionality:**
- User types in search box
- Triggers `sendSearchQuery()` method
- Sends POST request to n8n webhook
- Displays response in UI

### 2. **Chart Data Requests:**
- When user searches for "revenue", automatically requests chart data
- Uses `requestChartData()` method
- Can be extended to update charts with real data

### 3. **Error Handling:**
- Network errors are caught and displayed
- CORS issues are handled gracefully
- User-friendly error messages

## n8n Webhook Setup

### Basic Webhook Node Configuration:
1. **HTTP Method:** POST
2. **Path:** `/webhook-test/my-webhook`
3. **Response Mode:** Respond to Webhook
4. **Response Data:** JSON

### Sample n8n Response:
```json
{
  "success": true,
  "message": "Query received successfully",
  "data": {
    "processedQuery": "{{ $json.query }}",
    "timestamp": "{{ new Date().toISOString() }}",
    "chartData": [25, 20, 20, 20, 15]
  }
}
```

## Troubleshooting

### Common Issues:
1. **CORS Errors:** Make sure n8n allows cross-origin requests
2. **Connection Refused:** Verify n8n is running on port 5678
3. **404 Errors:** Check webhook path configuration in n8n

### Debug Steps:
1. Check browser console for detailed error messages
2. Verify n8n webhook is active and accessible
3. Test webhook directly with curl or Postman
4. Check network tab in browser dev tools

## Next Steps

### Potential Enhancements:
1. **Authentication:** Add API keys or tokens
2. **Real-time Updates:** Implement WebSocket connections
3. **Data Caching:** Cache webhook responses
4. **Retry Logic:** Implement automatic retry for failed requests
5. **Chart Updates:** Use webhook data to update charts dynamically