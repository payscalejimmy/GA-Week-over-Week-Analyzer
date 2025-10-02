import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class GA4WeekOverWeekAnalyzer:
    def __init__(self, csv_path, output_dir='output'):
        """Initialize the analyzer with CSV path and output directory."""
        self.csv_path = csv_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.df = None
        self.weekly_data = {}
        
    def load_data(self):
        """Load CSV data starting from row 7 (header) and skip row 8 (grand total)."""
        print("Loading data...")
        
        # Skip comment rows (0-5) AND the grand total row (7)
        # This uses row 6 (row 7 in 1-indexed, the header row) as the header
        # and starts reading data from row 8 (row 9 in 1-indexed)
        rows_to_skip = list(range(6)) + [7]  # Skip rows 0-5 and row 7 (grand total)
        self.df = pd.read_csv(self.csv_path, skiprows=rows_to_skip, header=0)
        
        # Debug: Check what we loaded
        print(f"Initial shape: {self.df.shape}")
        print(f"Columns: {self.df.columns.tolist()}")
        
        # Clean column names
        self.df.columns = self.df.columns.str.strip()
        
        # Reset index
        self.df = self.df.reset_index(drop=True)
        
        # Debug: Check Date column values before conversion
        print(f"\nDate column dtype: {self.df['Date'].dtype}")
        print(f"First 5 date values: {self.df['Date'].head().tolist()}")
        
        # Convert date column - handle both string and numeric formats
        if self.df['Date'].dtype == 'object':
            # It's already a string
            self.df['Date'] = pd.to_datetime(self.df['Date'], format='%Y%m%d', errors='coerce')
        else:
            # It's numeric, convert to string first
            self.df['Date'] = self.df['Date'].astype(int).astype(str)
            self.df['Date'] = pd.to_datetime(self.df['Date'], format='%Y%m%d', errors='coerce')
        
        print(f"Dates after conversion - valid: {self.df['Date'].notna().sum()}, invalid: {self.df['Date'].isna().sum()}")
        
        # Remove any rows with invalid dates
        initial_rows = len(self.df)
        self.df = self.df.dropna(subset=['Date']).copy()
        print(f"Removed {initial_rows - len(self.df)} rows with invalid dates")
        
        # Convert numeric columns
        numeric_cols = ['Total users', 'Engagement rate', 'Key events', 'User key event rate']
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        print(f"\nLoaded {len(self.df)} rows of data")
        if len(self.df) > 0:
            print(f"Date range: {self.df['Date'].min()} to {self.df['Date'].max()}")
            print(f"\nSample of loaded data:")
            print(self.df[['Session Payscale Custom Channels', 'Date', 'Total users', 'Key events']].head(3))
        else:
            print("ERROR: No valid data rows loaded!")
        
    def create_weekly_groups(self):
        """Group data by week."""
        print("\nGrouping data by week...")
        
        # Add week number (Monday as start of week)
        self.df['Week'] = self.df['Date'].dt.to_period('W-SUN')
        self.df['Week_Start'] = self.df['Week'].apply(lambda x: x.start_time)
        
        # Get unique weeks sorted
        weeks = sorted(self.df['Week_Start'].unique())
        
        print(f"Found {len(weeks)} weeks:")
        for i, week in enumerate(weeks, 1):
            week_end = week + timedelta(days=6)
            print(f"  Week {i}: {week.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
        
        return weeks
    
    def check_missing_dates(self, weeks):
        """Check for missing dates within each week's range."""
        print("\nChecking for missing dates...")
        
        missing_dates_by_week = {}
        
        for i, week in enumerate(weeks, 1):
            week_end = week + timedelta(days=6)
            
            # Get all dates that should be in this week
            expected_dates = pd.date_range(start=week, end=week_end, freq='D')
            
            # Get actual dates in the data for this week
            actual_dates = self.df[self.df['Week_Start'] == week]['Date'].dt.date.unique()
            actual_dates = pd.to_datetime(actual_dates)
            
            # Find missing dates
            missing = [d for d in expected_dates if d not in actual_dates]
            
            if missing:
                missing_dates_by_week[i] = {
                    'week_start': week,
                    'week_end': week_end,
                    'missing_dates': missing
                }
                print(f"  Week {i}: Missing {len(missing)} date(s) - {', '.join([d.strftime('%Y-%m-%d') for d in missing])}")
            else:
                print(f"  Week {i}: Complete (all 7 days present)")
        
        return missing_dates_by_week
    
    def aggregate_weekly_data(self, group_by_col, weeks):
        """Aggregate data by week for a specific grouping column."""
        weekly_agg = []
        
        for week in weeks:
            week_data = self.df[self.df['Week_Start'] == week].copy()
            
            if len(week_data) == 0:
                continue
            
            grouped = week_data.groupby(group_by_col).agg({
                'Total users': 'sum',
                'Key events': 'sum',
                'Engagement rate': 'mean',
                'User key event rate': 'mean'
            }).reset_index()
            
            grouped['Week_Start'] = week
            weekly_agg.append(grouped)
        
        if weekly_agg:
            return pd.concat(weekly_agg, ignore_index=True)
        return pd.DataFrame()
    
    def calculate_week_over_week(self, df, weeks, group_col):
        """Calculate week-over-week changes."""
        comparisons = []
        
        for i in range(len(weeks) - 1):
            current_week = weeks[i + 1]
            previous_week = weeks[i]
            
            current_data = df[df['Week_Start'] == current_week].copy()
            previous_data = df[df['Week_Start'] == previous_week].copy()
            
            # Merge on the grouping column
            merged = current_data.merge(
                previous_data,
                on=group_col,
                suffixes=('_current', '_previous'),
                how='outer'
            )
            
            # Fill NaN values with 0 for calculations
            merged = merged.fillna(0)
            
            # Calculate changes
            merged['Users_Change'] = merged['Total users_current'] - merged['Total users_previous']
            merged['Users_Change_Pct'] = np.where(
                merged['Total users_previous'] > 0,
                ((merged['Total users_current'] - merged['Total users_previous']) / 
                 merged['Total users_previous'] * 100),
                np.where(merged['Total users_current'] > 0, 100, 0)
            )
            
            merged['Key_Events_Change'] = merged['Key events_current'] - merged['Key events_previous']
            merged['Key_Events_Change_Pct'] = np.where(
                merged['Key events_previous'] > 0,
                ((merged['Key events_current'] - merged['Key events_previous']) / 
                 merged['Key events_previous'] * 100),
                np.where(merged['Key events_current'] > 0, 100, 0)
            )
            
            merged['Engagement_Change'] = (merged['Engagement rate_current'] - 
                                          merged['Engagement rate_previous'])
            
            merged['Week_Comparison'] = f"Week {i+2} vs Week {i+1}"
            merged['Current_Week'] = current_week
            merged['Previous_Week'] = previous_week
            
            comparisons.append(merged)
        
        if comparisons:
            return pd.concat(comparisons, ignore_index=True)
        return pd.DataFrame()
    
    def generate_channel_report(self, weeks):
        """Generate channel analysis report."""
        print("\nGenerating channel analysis...")
        
        channel_weekly = self.aggregate_weekly_data('Session Payscale Custom Channels', weeks)
        channel_wow = self.calculate_week_over_week(
            channel_weekly, weeks, 'Session Payscale Custom Channels'
        )
        
        # Save detailed CSV
        output_file = self.output_dir / 'channels_week_over_week.csv'
        channel_wow.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")
        
        return channel_wow
    
    def generate_source_medium_report(self, weeks):
        """Generate source/medium analysis report."""
        print("Generating source/medium analysis...")
        
        sm_weekly = self.aggregate_weekly_data('Session source / medium', weeks)
        sm_wow = self.calculate_week_over_week(
            sm_weekly, weeks, 'Session source / medium'
        )
        
        # Save detailed CSV
        output_file = self.output_dir / 'source_medium_week_over_week.csv'
        sm_wow.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")
        
        return sm_wow
    
    def generate_landing_page_report(self, weeks):
        """Generate landing page analysis report."""
        print("Generating landing page analysis...")
        
        lp_weekly = self.aggregate_weekly_data('Page path and screen class', weeks)
        lp_wow = self.calculate_week_over_week(
            lp_weekly, weeks, 'Page path and screen class'
        )
        
        # Save detailed CSV
        output_file = self.output_dir / 'landing_pages_week_over_week.csv'
        lp_wow.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")
        
        return lp_wow
    
    def generate_landing_page_source_report(self, weeks):
        """Generate landing page + source/medium combination analysis."""
        print("Generating landing page + source/medium analysis...")
        
        # Create combined grouping column
        self.df['LP_Source'] = self.df['Page path and screen class'] + ' | ' + self.df['Session source / medium']
        
        lp_source_weekly = self.aggregate_weekly_data('LP_Source', weeks)
        lp_source_wow = self.calculate_week_over_week(
            lp_source_weekly, weeks, 'LP_Source'
        )
        
        # Save detailed CSV
        output_file = self.output_dir / 'landing_page_source_week_over_week.csv'
        lp_source_wow.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")
        
        return lp_source_wow
    
    def generate_landing_page_channel_report(self, weeks):
        """Generate landing page + channel combination analysis."""
        print("Generating landing page + channel analysis...")
        
        # Create combined grouping column
        self.df['LP_Channel'] = self.df['Page path and screen class'] + ' | ' + self.df['Session Payscale Custom Channels']
        
        lp_channel_weekly = self.aggregate_weekly_data('LP_Channel', weeks)
        lp_channel_wow = self.calculate_week_over_week(
            lp_channel_weekly, weeks, 'LP_Channel'
        )
        
        # Save detailed CSV
        output_file = self.output_dir / 'landing_page_channel_week_over_week.csv'
        lp_channel_wow.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")
        
        return lp_channel_wow
    
    def generate_executive_summary(self, channel_wow, sm_wow, lp_wow, lp_source_wow, lp_channel_wow, weeks, missing_dates_info):
        """Generate executive summary in Markdown format."""
        print("\nGenerating executive summary...")
        
        md_content = []
        md_content.append("# GA4 Week-over-Week Executive Summary")
        md_content.append(f"\n**Analysis Period:** {self.df['Date'].min().strftime('%B %d, %Y')} - {self.df['Date'].max().strftime('%B %d, %Y')}")
        md_content.append(f"\n**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add data completeness warning if there are missing dates
        if missing_dates_info:
            md_content.append("\n\n⚠️ **Data Completeness Notice:**\n")
            for week_num, info in missing_dates_info.items():
                missing_date_strs = [d.strftime('%b %d') for d in info['missing_dates']]
                md_content.append(f"- **Week {week_num}** ({info['week_start'].strftime('%b %d')} - {info['week_end'].strftime('%b %d')}): "
                                f"Missing data for {len(info['missing_dates'])} day(s) - {', '.join(missing_date_strs)}\n")
            md_content.append("\n*Note: Comparisons involving incomplete weeks should be interpreted with caution.*\n")
        
        md_content.append("\n---\n")
        
        # Overall metrics
        md_content.append("## Overall Performance\n")
        
        for i in range(len(weeks) - 1):
            week_comp = f"Week {i+2} vs Week {i+1}"
            md_content.append(f"### {week_comp}\n")
            md_content.append(f"**Period:** {weeks[i+1].strftime('%b %d')} - {(weeks[i+1] + timedelta(days=6)).strftime('%b %d')} vs {weeks[i].strftime('%b %d')} - {(weeks[i] + timedelta(days=6)).strftime('%b %d')}\n")
            
            # Add warning if either week in comparison has missing dates
            comparison_has_missing = False
            if (i+1) in missing_dates_info or (i+2) in missing_dates_info:
                comparison_has_missing = True
                md_content.append("\n⚠️ *This comparison includes incomplete week(s) - see Data Completeness Notice above.*\n")
            
            # Channel performance
            channel_data = channel_wow[channel_wow['Week_Comparison'] == week_comp]
            if not channel_data.empty:
                md_content.append("\n#### Top Channel Changes\n")
                
                # Top gainers
                top_gainers = channel_data.nlargest(3, 'Users_Change')
                md_content.append("**Biggest User Increases:**\n")
                for _, row in top_gainers.iterrows():
                    md_content.append(f"- **{row['Session Payscale Custom Channels']}**: "
                                    f"{row['Users_Change']:+,.0f} users "
                                    f"({row['Users_Change_Pct']:+.1f}%)\n")
                
                # Top decliners
                top_decliners = channel_data.nsmallest(3, 'Users_Change')
                md_content.append("\n**Biggest User Decreases:**\n")
                for _, row in top_decliners.iterrows():
                    md_content.append(f"- **{row['Session Payscale Custom Channels']}**: "
                                    f"{row['Users_Change']:+,.0f} users "
                                    f"({row['Users_Change_Pct']:+.1f}%)\n")
            
            # Source/Medium insights
            sm_data = sm_wow[sm_wow['Week_Comparison'] == week_comp]
            if not sm_data.empty:
                md_content.append("\n#### Top Source/Medium Changes\n")
                
                # Filter out rows with minimal activity
                sm_data_significant = sm_data[sm_data['Total users_current'] > 100]
                
                if not sm_data_significant.empty:
                    top_sm_gainers = sm_data_significant.nlargest(5, 'Users_Change')
                    md_content.append("**Biggest Traffic Increases:**\n")
                    for _, row in top_sm_gainers.iterrows():
                        md_content.append(f"- **{row['Session source / medium']}**: "
                                        f"{row['Users_Change']:+,.0f} users "
                                        f"({row['Users_Change_Pct']:+.1f}%) | "
                                        f"{row['Key events_current']:.0f} key events\n")
            
            # Landing page insights
            lp_data = lp_wow[lp_wow['Week_Comparison'] == week_comp]
            if not lp_data.empty:
                md_content.append("\n#### Top Landing Page Changes\n")
                
                # Filter out rows with minimal activity
                lp_data_significant = lp_data[lp_data['Total users_current'] > 50]
                
                if not lp_data_significant.empty:
                    top_lp_gainers = lp_data_significant.nlargest(5, 'Users_Change')
                    md_content.append("**Highest Traffic Growth Pages:**\n")
                    for _, row in top_lp_gainers.iterrows():
                        md_content.append(f"- `{row['Page path and screen class']}`: "
                                        f"{row['Users_Change']:+,.0f} users "
                                        f"({row['Users_Change_Pct']:+.1f}%)\n")
            
            # Landing Page + Source/Medium combinations
            lp_source_data = lp_source_wow[lp_source_wow['Week_Comparison'] == week_comp]
            if not lp_source_data.empty:
                md_content.append("\n#### Top Landing Page + Source/Medium Combinations\n")
                
                # Filter for significant traffic
                lp_source_significant = lp_source_data[lp_source_data['Total users_current'] > 50]
                
                if not lp_source_significant.empty:
                    top_combos = lp_source_significant.nlargest(5, 'Users_Change')
                    md_content.append("**Highest Growth Combinations:**\n")
                    for _, row in top_combos.iterrows():
                        parts = row['LP_Source'].split(' | ')
                        md_content.append(f"- **{parts[1]}** → `{parts[0]}`: "
                                        f"{row['Users_Change']:+,.0f} users "
                                        f"({row['Users_Change_Pct']:+.1f}%) | "
                                        f"{row['Key events_current']:.0f} conversions\n")
            
            # Landing Page + Channel combinations
            lp_channel_data = lp_channel_wow[lp_channel_wow['Week_Comparison'] == week_comp]
            if not lp_channel_data.empty:
                md_content.append("\n#### Top Landing Page + Channel Combinations\n")
                
                # Filter for significant traffic
                lp_channel_significant = lp_channel_data[lp_channel_data['Total users_current'] > 50]
                
                if not lp_channel_significant.empty:
                    top_channel_combos = lp_channel_significant.nlargest(5, 'Users_Change')
                    md_content.append("**Highest Growth Channel Combinations:**\n")
                    for _, row in top_channel_combos.iterrows():
                        parts = row['LP_Channel'].split(' | ')
                        md_content.append(f"- **{parts[1]}** → `{parts[0]}`: "
                                        f"{row['Users_Change']:+,.0f} users "
                                        f"({row['Users_Change_Pct']:+.1f}%)\n")
            
            md_content.append("\n---\n")
        
        # Key insights section
        md_content.append("## Key Insights\n")
        md_content.append(self._generate_key_insights(channel_wow, sm_wow, lp_wow))
        
        # Save markdown file
        output_file = self.output_dir / 'executive_summary.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(''.join(md_content))
        print(f"Saved: {output_file}")

    def _generate_key_insights(self, channel_wow, sm_wow, lp_wow):
        """Generate key insights section."""
        insights = []
        insights.append("\n### Traffic Trends\n")
        
        # Analyze overall channel trends
        channel_totals = channel_wow.groupby('Session Payscale Custom Channels').agg({
            'Users_Change': 'sum',
            'Key_Events_Change': 'sum'
        }).reset_index()
        
        # Top performing channels overall
        top_channels = channel_totals.nlargest(3, 'Users_Change')
        insights.append("**Strongest Performing Channels (Overall):**\n")
        for _, row in top_channels.iterrows():
            insights.append(f"- {row['Session Payscale Custom Channels']}: "
                          f"+{row['Users_Change']:,.0f} users, "
                          f"+{row['Key_Events_Change']:.0f} key events\n")
        
        # Engagement insights
        insights.append("\n### Engagement Patterns\n")
        
        # Find sources with best engagement improvements
        sm_engagement = sm_wow[sm_wow['Total users_current'] > 100].copy()
        if not sm_engagement.empty:
            top_engagement = sm_engagement.nlargest(3, 'Engagement_Change')
            insights.append("**Biggest Engagement Rate Improvements:**\n")
            for _, row in top_engagement.iterrows():
                insights.append(f"- {row['Session source / medium']}: "
                              f"{row['Engagement_Change']:+.2%} change in engagement\n")
        
        # Conversion insights
        insights.append("\n### Conversion Highlights\n")
        sm_conversions = sm_wow[sm_wow['Key events_current'] > 10].copy()
        if not sm_conversions.empty:
            top_conversions = sm_conversions.nlargest(3, 'Key_Events_Change')
            insights.append("**Top Key Event Increases:**\n")
            for _, row in top_conversions.iterrows():
                insights.append(f"- {row['Session source / medium']}: "
                              f"+{row['Key_Events_Change']:.0f} key events "
                              f"({row['Key_Events_Change_Pct']:+.1f}%)\n")
        
        return ''.join(insights)
    
    def run_analysis(self):
        """Run the complete analysis."""
        print("=" * 60)
        print("GA4 Week-over-Week Analysis")
        print("=" * 60)
        
        # Load and process data
        self.load_data()
        weeks = self.create_weekly_groups()
        
        if len(weeks) < 2:
            print("\nError: Need at least 2 weeks of data for comparison")
            return
        
        # Check for missing dates
        missing_dates_info = self.check_missing_dates(weeks)
        
        # Generate reports
        channel_wow = self.generate_channel_report(weeks)
        sm_wow = self.generate_source_medium_report(weeks)
        lp_wow = self.generate_landing_page_report(weeks)
        lp_source_wow = self.generate_landing_page_source_report(weeks)
        lp_channel_wow = self.generate_landing_page_channel_report(weeks)
        
        # Generate executive summary
        self.generate_executive_summary(channel_wow, sm_wow, lp_wow, lp_source_wow, lp_channel_wow, weeks, missing_dates_info)
        
        print("\n" + "=" * 60)
        print("Analysis complete!")
        print(f"All reports saved to: {self.output_dir.absolute()}")
        print("=" * 60)


if __name__ == "__main__":
    # Usage
    analyzer = GA4WeekOverWeekAnalyzer(
        csv_path='ga4_data.csv',  # Update with your CSV filename
        output_dir='output'
    )
    analyzer.run_analysis()