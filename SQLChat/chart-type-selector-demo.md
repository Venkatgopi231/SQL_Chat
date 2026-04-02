# Chart Type Selector Demo

## Overview
The UES Analytics Hub now includes interactive chart type selector buttons in the top-right corner of the chart section, matching the screenshot design.

## Features

### Chart Type Buttons
- **Pie** - Traditional pie chart with segments
- **Donut** - Doughnut chart (pie with center hole)  
- **Bar** - Vertical bar chart for comparisons
- **Line** - Line chart for trends over time

### Interactive Functionality
- Click any button to instantly change the chart type
- Active button is highlighted in blue
- Chart data is preserved when switching types
- Smooth animations between chart types

## How It Works

### 1. **Button States**
- **Active**: Blue background with white text
- **Inactive**: Gray background with dark text
- **Hover**: Light gray background

### 2. **Chart Type Switching**
```typescript
// User clicks "Bar" button
changeChartType('bar')
// → Chart instantly converts to bar chart with same data
```

### 3. **Data Preservation**
- Current chart data is stored in `currentChartData`
- When switching types, data is reused with new visualization
- Chart title and colors are maintained

## Usage Examples

### Manual Chart Type Change
```typescript
// Change to bar chart
component.changeChartType('bar');

// Change to line chart  
component.changeChartType('line');

// Change to doughnut chart
component.changeChartType('doughnut');
```

### API Response with Chart Type
```json
{
  "success": true,
  "data": {
    "chartData": [1200, 950, 500, 450, 200, 150, 100, 50, 25, 10],
    "labels": ["Admin", "Supervisor", "Operator", "Staff", "Manager", "Trainee", "Intern", "Guest", "Contractor", "Visitor"],
    "title": "Number of Users per Role (Bar)",
    "type": "bar"
  }
}
```

### Webhook Integration
When webhook returns chart data, the appropriate button is automatically selected:
- API returns `"type": "bar"` → Bar button becomes active
- API returns `"type": "line"` → Line button becomes active
- No type specified → Pie button remains active (default)

## Visual Design

### Button Layout
```
[Chart Title]                    [Pie] [Donut] [Bar] [Line]
```

### Styling Features
- Rounded button group container
- 2px gap between buttons
- Smooth hover transitions
- Focus indicators for accessibility
- Responsive design for mobile devices

## Responsive Behavior

### Desktop (768px+)
- Buttons displayed horizontally in top-right
- Full button labels visible
- Hover effects enabled

### Tablet (768px and below)
- Buttons stack below chart title
- Full width button group
- Larger touch targets

### Mobile (480px and below)
- Buttons stack vertically
- Full width individual buttons
- Optimized for touch interaction

## Testing the Feature

### Browser Testing
1. Open the application at `http://localhost:4200/`
2. Look for the chart type buttons in the top-right of the chart section
3. Click different buttons to see chart type changes
4. Notice the active button highlighting

### Console Testing
```javascript
// Test programmatic chart type changes
component.changeChartType('bar');
component.changeChartType('line');
component.changeChartType('doughnut');
component.changeChartType('pie');
```

### Webhook Testing
Send webhook data with different chart types:
```json
// Test bar chart
{"chartData": [10, 20, 30], "type": "bar", "title": "Bar Chart Test"}

// Test line chart  
{"chartData": [5, 15, 25], "type": "line", "title": "Line Chart Test"}
```

## Integration with Existing Features

### Webhook Responses
- Chart type from API automatically selects correct button
- Manual button clicks override API chart type
- Button state reflects current chart type

### Search Functionality
- Search results can specify chart type
- Chart type selector remains functional after webhook updates
- User can manually change type after API response

### Error Handling
- Invalid chart types default to 'pie' with Pie button active
- Missing chart data shows default chart with Pie button active
- Button states always reflect actual chart type

## Accessibility Features

### Keyboard Navigation
- Buttons are focusable with Tab key
- Enter/Space keys activate buttons
- Focus indicators visible

### Screen Readers
- Button labels clearly indicate chart type
- Active state announced to screen readers
- Chart type changes announced

### Color Contrast
- High contrast between active/inactive states
- Meets WCAG accessibility guidelines
- Clear visual hierarchy

## Performance Considerations

### Efficient Rendering
- Chart destruction and recreation optimized
- Minimal DOM manipulation
- Smooth transitions without performance impact

### Memory Management
- Previous chart instances properly destroyed
- No memory leaks from chart type switching
- Efficient data structure reuse

## Future Enhancements

### Potential Additions
- More chart types (scatter, radar, polar area)
- Chart type icons in addition to text
- Keyboard shortcuts for chart type switching
- Chart type preferences saving
- Animation customization per chart type