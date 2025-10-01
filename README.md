# GA4 Week-over-Week Analyzer

A Python tool for analyzing Google Analytics 4 (GA4) data on a week-over-week basis. This analyzer processes GA4 export data and generates comprehensive reports showing traffic trends, engagement patterns, and conversion insights across different channels, sources, and landing pages.

## Features

- **Week-over-Week Comparison**: Automatically groups data by week and calculates changes between consecutive weeks
- **Multi-Dimensional Analysis**: 
  - Channel performance
  - Source/Medium combinations
  - Landing page traffic
  - Landing page + Source/Medium combinations
  - Landing page + Channel combinations
- **Data Quality Checks**: Identifies missing dates within each week's data range
- **Executive Summary**: Auto-generated Markdown summary with key insights and trends
- **Detailed CSV Reports**: Exports granular data for further analysis

## Requirements

- Python 3.7+
- pandas
- numpy

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Input Data Format

The script expects a CSV file exported from GA4 with the following structure:

- **Rows 1-6**: Comment/metadata rows (automatically skipped)
- **Row 7**: Header row with column names
- **Row 8**: Grand total row (automatically skipped)
- **Row 9+**: Daily data rows

### Required Columns

- `Date`: Date in YYYYMMDD format (e.g., 20240101)
- `Session Payscale Custom Channels`: Channel classification
- `Session source / medium`: Traffic source and medium
- `Page path and screen class`: Landing page URL
- `Total users`: Number of users
- `Engagement rate`: Engagement rate (decimal or percentage)
- `Key events`: Number of key events (conversions)
- `User key event rate`: Conversion rate per user

## Usage

### Basic Usage

1. Place your GA4 CSV export in the same directory as the script
2. Update the filename in the script:

```python
analyzer = GA4WeekOverWeekAnalyzer(
    csv_path='your_ga4_data.csv',  # Update this
    output_dir='output'
)
analyzer.run_analysis()
```

3. Run the script:
```bash
python ga4_analyzer.py
```

### Custom Configuration

```python
analyzer = GA4WeekOverWeekAnalyzer(
    csv_path='path/to/your/data.csv',
    output_dir='custom_output_directory'
)
analyzer.run_analysis()
```

## Output Files

All output files are saved to the `output/` directory (or your custom output directory):

### CSV Reports

1. **channels_week_over_week.csv**: Week-over-week changes by channel
2. **source_medium_week_over_week.csv**: Week-over-week changes by source/medium
3. **landing_pages_week_over_week.csv**: Week-over-week changes by landing page
4. **landing_page_source_week_over_week.csv**: Combined landing page + source/medium analysis
5. **landing_page_channel_week_over_week.csv**: Combined landing page + channel analysis

### Executive Summary

**executive_summary.md**: A comprehensive Markdown report including:
- Analysis period and data completeness status
- Top channel changes for each week comparison
- Source/medium performance highlights
- Landing page traffic trends
- Top-performing combinations
- Key insights on traffic trends, engagement patterns, and conversions

## Understanding the Reports

### Week Numbering

Weeks are numbered sequentially starting from Week 1. Weeks start on Monday and end on Sunday.

### Metrics Explained

- **Users_Change**: Absolute change in number of users
- **Users_Change_Pct**: Percentage change in users
- **Key_Events_Change**: Absolute change in conversions
- **Key_Events_Change_Pct**: Percentage change in conversions
- **Engagement_Change**: Change in engagement rate

### Data Completeness Warnings

The tool checks for missing dates within each week. If any dates are missing, warnings will appear in:
- Console output
- Executive summary report

Comparisons involving incomplete weeks should be interpreted with caution.

## Example Console Output

```
============================================================
GA4 Week-over-Week Analysis
============================================================
Loading data...
Initial shape: (245, 7)
Columns: ['Date', 'Session Payscale Custom Channels', ...]

Loaded 245 rows of data
Date range: 2024-01-01 to 2024-02-28

Found 8 weeks:
  Week 1: 2024-01-01 to 2024-01-07
  Week 2: 2024-01-08 to 2024-01-14
  ...

Checking for missing dates...
  Week 1: Complete (all 7 days present)
  Week 2: Missing 1 date(s) - 2024-01-10
  ...

Generating channel analysis...
Saved: output/channels_week_over_week.csv
...
============================================================
Analysis complete!
All reports saved to: /path/to/output
============================================================
```

## Troubleshooting

### "No valid data rows loaded!"

- Check that your CSV has the correct format
- Verify that Row 7 contains column headers
- Ensure date values are in YYYYMMDD format

### Date Parsing Errors

- Dates should be numeric (e.g., 20240101) or string format (e.g., "20240101")
- Check for any non-standard date formats in your export

### Missing Columns Error

Ensure your GA4 export includes all required columns listed in the "Required Columns" section above.

## License

This tool is provided as-is for analytics purposes.

## Contributing

Feel free to submit issues or pull requests for improvements.