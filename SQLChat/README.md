# UES Analytics Hub

A sample Angular application that replicates the UES Analytics Hub dashboard interface.

## Features

- **Navigation Tabs**: Multiple department tabs (Strategic, Executive, Financials, etc.)
- **Interactive Dashboard**: Strategic section with search functionality
- **Revenue Chart**: Pie chart showing "Revenue by Service Line" using Chart.js
- **Responsive Design**: Mobile-friendly layout

## Technologies Used

- Angular 19
- Chart.js for data visualization
- TypeScript
- CSS3 with modern styling
- Responsive design principles

## Getting Started

### Prerequisites

- Node.js (v20 or higher)
- npm (v11 or higher)
- Angular CLI

### Installation

1. Clone or download the project
2. Navigate to the project directory:
   ```bash
   cd ues-analytics-hub
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

### Running the Application

Start the development server:
```bash
ng serve
```

Navigate to `http://localhost:4200/` in your browser. The application will automatically reload if you change any of the source files.

## Project Structure

```
src/
├── app/
│   ├── app.component.html    # Main template with dashboard layout
│   ├── app.component.ts      # Component logic with Chart.js integration
│   ├── app.component.css     # Component-specific styles
│   └── app.config.ts         # App configuration
├── styles.css                # Global styles
└── index.html               # Main HTML file
```

## Features Implemented

### Dashboard Layout
- Header with "UES Analytics Hub" title
- Navigation tabs with color-coded departments
- Strategic section with icon and description
- Search bar with placeholder functionality

### Revenue Chart
- Interactive pie chart using Chart.js
- Service line breakdown:
  - Construction Inspection (25%)
  - Environmental (20%)
  - Geotechnical (20%)
  - Materials (20%)
  - Special Inspection (15%)

### Responsive Design
- Mobile-friendly navigation
- Flexible chart sizing
- Adaptive layout for different screen sizes

## Customization

### Adding New Tabs
Edit the navigation section in `app.component.html` and add corresponding CSS classes in `app.component.css`.

### Modifying Chart Data
Update the chart data in the `createPieChart()` method in `app.component.ts`.

### Styling Changes
Modify the CSS files to match your brand colors and design preferences.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.

## Further Development

This is a sample implementation. For a production application, consider:
- Adding routing for different tabs
- Implementing real data services
- Adding more interactive charts and widgets
- User authentication and authorization
- Backend API integration

## Original Angular CLI Information

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 19.2.19.

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.

## Webhook Integration

### n8n Webhook Service
The application now includes a webhook service that connects to n8n for real-time data processing.

**Webhook URL:** `http://localhost:5678/webhook-test/my-webhook`

### Features:
- **Search Integration**: Send search queries to n8n webhook
- **Chart Data Requests**: Request dynamic chart data
- **Connection Testing**: Automatic webhook connectivity testing
- **Error Handling**: Graceful handling of network errors and CORS issues

### Usage:
1. Start n8n server on `localhost:5678`
2. Create a webhook node with path `/webhook-test/my-webhook`
3. Use the search box in the application to send queries
4. View responses in the browser console and UI

### Service Methods:
```typescript
// Send search query
webhookService.sendSearchQuery("show revenue data")

// Request chart data
webhookService.requestChartData("revenue-by-service-line")

// Test connection
webhookService.testConnection()
```

For detailed webhook setup and testing instructions, see `webhook-test.md`.