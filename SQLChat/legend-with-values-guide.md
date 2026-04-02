# Legend with Values Guide

## Overview
All chart types now display legends with values, providing detailed information about each data point directly in the legend area.

## Legend Display by Chart Type

### Pie & Doughnut Charts
- **Position**: Right side of the chart
- **Format**: `Label: Value (Percentage%)`
- **Example**: `Construction: 25 (25.0%)`
- **Features**:
  - Shows actual values and calculated percentages
  - Click legend items to hide/show segments
  - Point-style indicators (circles)

### Bar Charts
- **Position**: Top of the chart
- **Format**: `Label: Value`
- **Example**: `Q1: 45`, `Q2: 35`, `Q3: 25`
- **Features**:
  - Shows individual bar values
  - Click legend items to hide/show bars
  - Color-coded indicators

### Line Charts
- **Position**: Top of the chart
- **Format**: `Label: Value`
- **Example**: `Jan: 100`, `Feb: 120`, `Mar: 140`
- **Features**:
  - Shows data point values
  - Click legend items to hide/show points
  - Line color indicators

## Legend Features

### Interactive Functionality
- **Click to Toggle**: Click any legend item to hide/show that data
- **Visual Feedback**: Hidden items appear grayed out
- **Real-time Updates**: Chart updates immediately when toggling

### Custom Label Generation
```typescript
generateLegendLabelsWithValues(chart: any) {
  // For pie/doughnut: "Label: Value (Percentage%)"
  // For bar/line: "Label: Value"
  return customLabels;
}
```

### Styling Features
- **Point Style**: Circular indicators for all chart types
- **Font Size**: 12px for optimal readability
- **Padding**: 20px spacing between legend items
- **Colors**: Match chart segment/bar/line colors

## API Response Examples

### Pie Chart with Legend Values
```json
{
  "success": true,
  "data": {
    "chartData": [25, 20, 20, 20, 15],
    "labels": ["Construction", "Environmental", "Geotechnical", "Materials", "Special"],
    "title": "Revenue Distribution",
    "type": "pie"
  }
}
```
**Legend Display:**
- Construction: 25 (25.0%)
- Environmental: 20 (20.0%)
- Geotechnical: 20 (20.0%)
- Materials: 20 (20.0%)
- Special: 15 (15.0%)

### Bar Chart with Legend Values
```json
{
  "success": true,
  "data": {
    "chartData": [1200, 950, 500, 450, 200],
    "labels": ["Admin", "Supervisor", "Operator", "Staff", "Manager"],
    "title": "Users per Role",
    "type": "bar"
  }
}
```
**Legend Display:**
- Admin: 1200
- Supervisor: 950
- Operator: 500
- Staff: 450
- Manager: 200

### Line Chart with Legend Values
```json
{
  "success": true,
  "data": {
    "chartData": [100, 120, 140, 180, 200],
    "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
    "title": "Monthly Growth",
    "type": "line"
  }
}
```
**Legend Display:**
- Jan: 100
- Feb: 120
- Mar: 140
- Apr: 180
- May: 200

## Responsive Design

### Desktop (768px+)
- **Pie/Doughnut**: Legend on right side
- **Bar/Line**: Legend on top
- Full legend text visible
- Optimal spacing and padding

### Tablet & Mobile (768px and below)
- **All Charts**: Legend positioned for best fit
- Responsive font sizing
- Touch-friendly legend items
- Optimized spacing for smaller screens

## Legend Positioning

### Chart Type Specific Positioning
```typescript
const chartTypeConfigs = {
  pie: { legend: { position: 'right' } },
  doughnut: { legend: { position: 'right' } },
  bar: { legend: { position: 'top' } },
  line: { legend: { position: 'top' } }
};
```

### Benefits of Positioning
- **Right (Pie/Doughnut)**: Maximizes chart size while showing detailed legends
- **Top (Bar/Line)**: Doesn't interfere with axis labels and scales
- **Responsive**: Automatically adjusts for mobile devices

## Interactive Legend Behavior

### Click Functionality
```typescript
onClick: (event, legendItem, legend) => {
  const chart = legend.chart;
  const index = legendItem.index;
  
  // Toggle data visibility
  if (chartType === 'pie' || chartType === 'doughnut') {
    // Hide/show pie segments
    const meta = chart.getDatasetMeta(0);
    meta.data[index].hidden = !meta.data[index].hidden;
  } else {
    // Hide/show bar/line data points
    const meta = chart.getDatasetMeta(0);
    meta.data[index].hidden = !meta.data[index].hidden;
  }
  
  chart.update();
}
```

### Visual States
- **Active**: Full color, normal text
- **Hidden**: Grayed out, strikethrough text
- **Hover**: Slight highlight effect

## Tooltip Integration

### Consistent Information
- **Tooltips**: Show same information as legends
- **Pie/Doughnut**: Value and percentage on hover
- **Bar/Line**: Value only on hover
- **Synchronized**: Legend and tooltip data always match

## Testing the Legend Feature

### Browser Testing
1. Open application at `http://localhost:4200/`
2. Observe legend with values for default pie chart
3. Click chart type buttons to see different legend formats
4. Click legend items to hide/show data
5. Verify values match chart segments/bars/points

### Console Testing
```javascript
// Test different chart types with legend values
const testData = {
  pie: {
    chartData: [30, 25, 20, 15, 10],
    labels: ["A", "B", "C", "D", "E"],
    type: "pie",
    title: "Pie Chart with Legend Values"
  },
  bar: {
    chartData: [45, 35, 25, 15],
    labels: ["Q1", "Q2", "Q3", "Q4"],
    type: "bar", 
    title: "Bar Chart with Legend Values"
  }
};

// Test each type
component.handleWebhookChartData(testData.pie);
component.handleWebhookChartData(testData.bar);
```

### Webhook Testing
Send different chart types and verify legend displays:
```bash
# Test with curl
curl -X POST http://localhost:5678/webhook-test/my-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "chartData": [40, 30, 20, 10],
    "labels": ["Service A", "Service B", "Service C", "Service D"],
    "type": "doughnut",
    "title": "Services with Legend Values"
  }'
```

## Performance Considerations

### Efficient Legend Generation
- **Cached Calculations**: Percentages calculated once per render
- **Minimal DOM Updates**: Only legend items that change are updated
- **Memory Efficient**: No memory leaks from legend event handlers

### Responsive Performance
- **Optimized Rendering**: Legend positioning adapts without performance impact
- **Touch Optimization**: Legend interactions optimized for mobile devices
- **Smooth Animations**: Legend updates with smooth transitions

## Accessibility Features

### Screen Reader Support
- **Descriptive Labels**: Legend items include full value information
- **Keyboard Navigation**: Legend items are keyboard accessible
- **ARIA Labels**: Proper ARIA attributes for screen readers

### Visual Accessibility
- **High Contrast**: Legend text meets WCAG contrast requirements
- **Clear Typography**: Readable font sizes and weights
- **Color Independence**: Information conveyed through text, not just color

## Customization Options

### Legend Text Format
```typescript
// Customize legend text format
generateLegendLabelsWithValues(chart: any) {
  // Current format: "Label: Value (Percentage%)"
  // Can be customized to: "Label - Value", "Label: Value only", etc.
}
```

### Styling Customization
```css
/* Custom legend styling */
.chart-container {
  font-family: 'Custom Font', sans-serif;
  color: #custom-color;
}
```

### Position Customization
```typescript
// Change legend positions
const customConfig = {
  pie: { legend: { position: 'bottom' } },
  bar: { legend: { position: 'right' } }
};
```