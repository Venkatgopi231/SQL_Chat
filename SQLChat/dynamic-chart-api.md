# Dynamic Pie Chart API Integration

## Overview
The `createPieChart` method has been updated to dynamically create pie charts from API response data. The chart can now handle multiple data formats and automatically update based on webhook responses.

## Supported API Data Formats

### Format 1: Simple Number Array
```json
{
  "success": true,
  "data": {
    "chartData": [25, 20, 20, 20, 15],
    "labels": ["Construction", "Environmental", "Geotechnical", "Materials", "Special"],
    "title": "Revenue Distribution"
  }
}
```

### Format 2: Object Array
```json
{
  "success": true,
  "data": {
    "chartData": [
      { "label": "Construction Inspection", "value": 25, "color": "#E91E63" },
      { "label": "Environmental", "value": 20, "color": "#2196F3" },
      { "label": "Geotechnical", "value": 20, "color": "#9C27B0" },
      { "label": "Materials", "value": 20, "color": "#FF9800" },
      { "label": "Special Inspection", "value": 15, "color": "#795548" }
    ],
    "title": "Service Line Revenue"
  }
}
```

### Format 3: Structured Chart Object
```json
{
  "success": true,
  "data": {
    "chart": {
      "title": "Revenue by Service Line",
      "type": "pie",
      "data": [
        { "label": "Construction", "value": 25 },
        { "label": "Environmental", "value": 20 }
      ],
      "colors": ["#E91E63", "#2196F3", "#9C27B0"]
    }
  }
}
```

### Format 4: Alternative Property Names
The parser supports various property names for flexibility:
- **Labels**: `label`, `name`, `category`
- **Values**: `value`, `amount`, `percentage`
- **Chart Data**: `chartData`, `chart`, `pieChart`

## Key Features

### 1. **Dynamic Chart Creation**
- Automatically destroys existing chart before creating new one
- Supports unlimited number of data points
- Auto-generates colors if not provided

### 2. **Flexible Data Parsing**
- Handles multiple API response formats
- Graceful fallback to default data on parsing errors
- Comprehensive error logging

### 3. **Enhanced Chart Options**
- **Legend**: Displayed on the right side with point styles
- **Tooltips**: Show value and percentage
- **Animation**: Smooth rotate and scale animations
- **Responsive**: Adapts to container size

### 4. **Color Management**
- Default color palette with 15 predefined colors
- Supports custom colors from API response
- Automatic color cycling for large datasets

## Method Documentation

### `createPieChart(apiData: ApiChartData)`
Main method that creates the pie chart from structured data.

**Parameters:**
- `apiData`: Structured chart data object

**Features:**
- Destroys existing chart instance
- Validates canvas context
- Creates Chart.js configuration
- Updates chart title dynamically

### `handleWebhookChartData(data: any)`
Processes raw webhook response and converts to chart format.

**Supported Response Properties:**
- `data.chartData` - Primary chart data
- `data.chart` - Alternative chart data
- `data.pieChart` - Pie-specific chart data
- `data.title` - Chart title override
- `data.labels` - Labels for number arrays

### `parseNumberArray(values: number[], labels?: string[])`
Converts simple number arrays to structured format.

**Example Input:**
```javascript
parseNumberArray([25, 20, 15], ["A", "B", "C"])
```

**Output:**
```javascript
{
  title: "Revenue by Service Line",
  type: "pie",
  data: [
    { label: "A", value: 25, color: "#E91E63" },
    { label: "B", value: 20, color: "#2196F3" },
    { label: "C", value: 15, color: "#9C27B0" }
  ]
}
```

### `parseObjectArray(items: any[])`
Converts object arrays to structured format.

**Supported Object Properties:**
- `label` / `name` / `category` - Item label
- `value` / `amount` / `percentage` - Item value
- `color` - Custom color (optional)

### `parseChartObject(chartObj: any)`
Handles pre-structured chart objects.

**Expected Structure:**
```javascript
{
  title: "Chart Title",
  type: "pie",
  data: [...],
  colors: [...]
}
```

## Integration Examples

### Example 1: Search-Triggered Chart Update
```typescript
// User searches for "revenue data"
// Webhook returns:
{
  "success": true,
  "data": {
    "chartData": [30, 25, 20, 15, 10],
    "labels": ["Service A", "Service B", "Service C", "Service D", "Service E"],
    "title": "Updated Revenue Distribution"
  }
}
// Chart automatically updates with new data
```

### Example 2: Manual Chart Refresh
```typescript
// Programmatically update chart
const newData: ApiChartData = {
  title: "Custom Chart",
  data: [
    { label: "Category 1", value: 40, color: "#FF6B6B" },
    { label: "Category 2", value: 35, color: "#4ECDC4" },
    { label: "Category 3", value: 25, color: "#45B7D1" }
  ]
};

this.refreshChart(newData);
```

## Error Handling

### Graceful Degradation
- Invalid data formats fall back to default chart
- Missing properties use sensible defaults
- Comprehensive console logging for debugging

### Common Error Scenarios
1. **Invalid JSON**: Falls back to default data
2. **Missing Properties**: Uses default values
3. **Empty Arrays**: Shows "No Data" message
4. **Network Errors**: Maintains existing chart

## n8n Webhook Configuration

### Sample n8n Workflow Response
```javascript
// In n8n, return this structure:
return {
  success: true,
  data: {
    chartData: [
      { label: "Construction", value: {{ $json.construction }} },
      { label: "Environmental", value: {{ $json.environmental }} },
      { label: "Materials", value: {{ $json.materials }} }
    ],
    title: "Real-time Revenue Data",
    timestamp: new Date().toISOString()
  }
};
```

### Dynamic Data Processing
```javascript
// Process dynamic data in n8n
const processedData = items.map(item => ({
  label: item.json.serviceName,
  value: item.json.revenue,
  color: item.json.color || null
}));

return {
  success: true,
  data: {
    chartData: processedData,
    title: "Dynamic Service Revenue",
    generatedAt: new Date().toISOString()
  }
};
```

## Testing

### Test Data Examples
```javascript
// Test with different formats
const testFormats = [
  // Format 1: Numbers only
  { chartData: [25, 20, 20, 20, 15] },
  
  // Format 2: Objects
  { 
    chartData: [
      { label: "Test A", value: 30 },
      { label: "Test B", value: 70 }
    ]
  },
  
  // Format 3: Full structure
  {
    chart: {
      title: "Test Chart",
      data: [{ label: "Item", value: 100 }]
    }
  }
];
```

### Browser Console Testing
```javascript
// Test in browser console
const testData = {
  title: "Test Chart",
  data: [
    { label: "A", value: 50, color: "#FF0000" },
    { label: "B", value: 30, color: "#00FF00" },
    { label: "C", value: 20, color: "#0000FF" }
  ]
};

// Assuming component instance is available
component.createPieChart(testData);
```

## Performance Considerations

### Chart Instance Management
- Always destroys previous chart to prevent memory leaks
- Efficient canvas context reuse
- Minimal DOM manipulation

### Data Processing
- Lightweight parsing algorithms
- Early validation and error handling
- Optimized color assignment

### Animation Performance
- Smooth 1-second animations
- Hardware-accelerated rendering
- Responsive design considerations

## Multi-Chart Type Support (Updated)

### Supported Chart Types
The application now supports multiple chart types based on the `type` property in the API response:

- **pie** - Traditional pie chart with segments
- **bar** - Vertical bar chart for comparisons  
- **line** - Line chart for trends over time
- **doughnut** - Doughnut chart (pie with center hole)
- **donut** - Alias for doughnut chart (converted to 'doughnut')

### Chart Type Configuration

Each chart type has optimized settings:

#### Pie & Doughnut Charts
- Legend displayed on the right side
- Tooltips show value and percentage
- No axis scales

#### Bar Charts  
- Legend hidden (labels on X-axis)
- Y-axis starts at zero with grid lines
- Transparent background colors with solid borders
- Hover effects

#### Line Charts
- Legend hidden (labels on X-axis) 
- Y-axis starts at zero with grid lines
- Filled area under the line
- Smooth curve tension (0.4)
- Point markers with hover effects

### API Response Examples

#### Bar Chart Request
```json
{
  "success": true,
  "data": {
    "chartData": [45, 35, 25, 20],
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "title": "Quarterly Performance",
    "type": "bar"
  }
}
```

#### Line Chart Request  
```json
{
  "success": true,
  "data": {
    "chartData": [
      { "label": "Jan", "value": 100 },
      { "label": "Feb", "value": 120 },
      { "label": "Mar", "value": 140 }
    ],
    "title": "Monthly Growth",
    "type": "line"
  }
}
```

#### Doughnut Chart Request
```json
{
  "success": true,
  "data": {
    "chart": {
      "title": "Market Share",
      "type": "doughnut",
      "data": [
        { "label": "Company A", "value": 40, "color": "#4CAF50" },
        { "label": "Company B", "value": 35, "color": "#FF9800" },
        { "label": "Others", "value": 25, "color": "#9E9E9E" }
      ]
    }
  }
}
```

### Dynamic Chart Creation Process

1. **Type Detection**: Reads `type`, `chartType` from API response
2. **Data Parsing**: Handles arrays or objects based on chart type
3. **Configuration**: Applies type-specific settings (scales, legend, etc.)
4. **Dataset Creation**: Creates appropriate dataset for chart type
5. **Rendering**: Destroys old chart and creates new one

### Chart Type Specific Features

#### Color Handling
- **Pie/Doughnut**: Full opacity colors for segments
- **Bar**: Semi-transparent backgrounds (80% opacity) with solid borders
- **Line**: Single color with 20% opacity fill, solid line and points

#### Tooltip Behavior
- **Pie/Doughnut**: Shows value and calculated percentage
- **Bar/Line**: Shows label and value only

#### Animation
- All chart types have 1-second smooth animations
- Type-specific animations (rotate for pie, scale for bars, etc.)

### Testing Different Chart Types

#### Browser Console Testing
```javascript
// Test different chart types
const testData = {
  bar: { chartData: [10, 20, 30], labels: ["A", "B", "C"], type: "bar", title: "Bar Test" },
  line: { chartData: [5, 15, 25], labels: ["X", "Y", "Z"], type: "line", title: "Line Test" },
  doughnut: { chartData: [40, 60], labels: ["Part 1", "Part 2"], type: "doughnut", title: "Donut Test" }
};

// Test each type
component.handleWebhookChartData(testData.bar);
component.handleWebhookChartData(testData.line);  
component.handleWebhookChartData(testData.doughnut);
```

#### n8n Webhook Examples
```javascript
// Dynamic chart type based on user input
const chartType = $json.requestedChartType || 'pie';
const data = $json.chartData || [25, 20, 20, 20, 15];

return {
  success: true,
  data: {
    chartData: data,
    labels: $json.labels || ["A", "B", "C", "D", "E"],
    title: `${chartType.toUpperCase()} Chart - ${new Date().toLocaleDateString()}`,
    type: chartType
  }
};
```

### Error Handling & Fallbacks

- **Invalid Chart Type**: Falls back to 'pie' chart
- **Missing Data**: Uses default sample data
- **Parsing Errors**: Logs error and shows default chart
- **Type Normalization**: 'donut' automatically converts to 'doughnut'

### Performance Considerations

- **Chart Destruction**: Always destroys previous chart to prevent memory leaks
- **Efficient Rendering**: Optimized dataset creation per chart type
- **Color Caching**: Reuses color palette across chart types
- **Responsive Design**: All chart types adapt to container size