import pandas as pd
import json
import os
import yfinance as yf

PROCESSED_FILE_PATH = 'wsb_sub_processed.csv'
TARGET_TICKER = 'TSLA' 

def analyze_ticker(processed_file_path, target_ticker):
    # check if the processed data file exists
    if not os.path.exists(processed_file_path):
        print(f"error: processed file not found at {processed_file_path}")
        # raise FileNotFoundError(f"Processed file not found: {processed_file_path}") # Alternative
        return pd.DataFrame() # return empty dataframe if file not found

    try:
        df = pd.read_csv(processed_file_path)
        print(f"loaded {len(df)} rows from {processed_file_path}")

        df['date'] = pd.to_datetime(df['date'])

        def parse_ticker_json_string(ticker_json_str):
            try:
                # check if it's a string and looks like a json list before parsing
                if isinstance(ticker_json_str, str) and ticker_json_str.startswith('['):
                    return json.loads(ticker_json_str)
                return []
            except json.JSONDecodeError:
                return [] # return empty list if json parsing fails
        # parse tickers
        df['tickers_list'] = df['tickers'].apply(parse_ticker_json_string)

        # filter the dataframe for rows where 'tickers_list' contains the target_ticker
        df_target_ticker = df[df['tickers_list'].apply(lambda tl: isinstance(tl, list) and target_ticker in tl)].copy()
        
        # if no posts are found for the target ticker, print a message and return an empty dataframe
        if df_target_ticker.empty:
            print(f"no posts found mentioning the target ticker: {target_ticker}")
            exit(0) # exit the script if no posts found

        # SENTIMENT

        # map sentiment
        sentiment_to_score_map = {'Positive': 1, 'Neutral': 0, 'Negative': -1}
        # valid sentiment ( we know data is good, so to be sure )
        valid_sentiment_values = ['Positive', 'Negative', 'Neutral']
        
        # filter out rows that don't have a valid sentiment value
        df_target_ticker_cleaned = df_target_ticker[df_target_ticker['sentiment'].isin(valid_sentiment_values)].copy()
        # create a new 'sentiment_score' column using the map
        df_target_ticker_cleaned['sentiment_score'] = df_target_ticker_cleaned['sentiment'].map(sentiment_to_score_map)
        

        if df_target_ticker_cleaned.empty:
            print(f"No sentiments found for {target_ticker}")
            return pd.DataFrame()

        # AGGREGATION
        
        # date needed as index for resampling
        df_indexed_by_date = df_target_ticker_cleaned.set_index('date')

        # calculate the average daily sentiment score
        # 'W' stands for daily frequency
        # .fillna(0) replaces any days with no data (NaN) with a neutral score of 0 -- this won't be hit, as we filter out empty posts above
        daily_avg_sentiment_score = df_indexed_by_date['sentiment_score'].resample('W').mean().fillna(0)
        
        # count the number of posts per day for the target ticker
        daily_post_counts = df_indexed_by_date.resample('W').size() 
        # rename the series for clarity when merging
        daily_post_counts.name = 'post_count'


        # calculate the daily proportion of each sentiment type
        # normalize=True gives proportions instead of raw counts
        # .unstack(fill_value=0) pivots sentiment types into columns, filling missing ones with 0
        daily_sentiment_proportions = df_indexed_by_date.groupby(pd.Grouper(freq='D'))['sentiment'] \
                                                        .value_counts(normalize=True) \
                                                        .unstack(fill_value=0)
        #print(daily_sentiment_proportions.head()) # debug print to check proportions
        
        # aggregate all into one df
        
        # start with average sentiment and post counts
        analysis_df = pd.DataFrame({
            'avg_sentiment_score': daily_avg_sentiment_score,
            'post_count': daily_post_counts
        })
        #print(analysis_df.head()) # debug print to check initial aggregation
        
        # add proportion columns for 'Positive', 'Negative', 'Neutral' sentiments
        for sentiment_category in valid_sentiment_values: # iterate through defined valid sentiments
            if sentiment_category in daily_sentiment_proportions.columns:
                analysis_df[f'{sentiment_category}_proportion'] = daily_sentiment_proportions[sentiment_category]
            else:
                # if a sentiment category never appeared, add a column of zeros for it
                analysis_df[f'{sentiment_category}_proportion'] = 0 
        
        # fill any remaining NaN values in the final dataframe with 0
        # this can happen if a date exists in one aggregated series but not others before merging
        analysis_df = analysis_df.fillna(0)

        return analysis_df

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 
        exit(1)


if __name__ == "__main__":

    target_daily_analysis = analyze_ticker(PROCESSED_FILE_PATH, TARGET_TICKER)
    
    if not target_daily_analysis.empty:
        print(f"\n--- Daily Analysis for {TARGET_TICKER} (first 5 days) ---")
        print(target_daily_analysis.head())
    
    # Now we'll get into fetching stock price data for the same date range
    start_date = target_daily_analysis.index.min()
    end_date = target_daily_analysis.index.max()
    print(f"\nFetching stock price data for {TARGET_TICKER} from {start_date} to {end_date}...")
    try:
        tsla_stock_data = yf.download(TARGET_TICKER, start=start_date, end=end_date, interval='1d')
        combined_df = target_daily_analysis.copy()
        all_days_index = pd.date_range(start=combined_df.index.min(), end=combined_df.index.max(), freq='D')
        tsla_stock_data_resampled = tsla_stock_data.reindex(all_days_index).ffill() # Forward fill prices for non-trading days
        combined_df['TSLA_Close'] = tsla_stock_data_resampled['Close']
        combined_df['TSLA_Volume'] = tsla_stock_data_resampled['Volume']
        combined_df['TSLA_Price_Change'] = combined_df['TSLA_Close'].diff()
        # remove NaN rows in the beginning
        combined_df = combined_df.dropna()
        print(combined_df.head())

        # Lets PLOT
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        sentiment_metric_to_plot = 'avg_sentiment_score' 
        
    
        fig, ax1 = plt.subplots(figsize=(18, 9)) 
    
        # Sentiment Metric on the first y-axis (ax1)
        color = 'tab:blue'
        ax1.set_xlabel('Date')
        ax1.set_ylabel(sentiment_metric_to_plot, color=color)
        ax1.plot(combined_df.index, combined_df[sentiment_metric_to_plot], color=color, linestyle='-', marker='.', markersize=3, label=f'TSLA {sentiment_metric_to_plot}')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle=':', alpha=0.7)
    
        # (ax2) for the TSLA Close Price, sharing the same x-axis
        ax2 = ax1.twinx()  
        color = 'tab:red'
        ax2.set_ylabel('TSLA Close Price ($)', color=color)
        ax2.plot(combined_df.index, combined_df['TSLA_Close'], color=color, linestyle='-', marker='.', markersize=3, label='TSLA Close Price')
        ax2.tick_params(axis='y', labelcolor=color)
    
        # title layout
        plt.title('TSLA Sentiment vs. Stock Price Over Time', fontsize=16)
        fig.tight_layout() # otherwise the right y-label is slightly clipped
        
        # legends
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='upper left')
    
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=8, maxticks=15)) 
        fig.autofmt_xdate() 
    
        plt.show()

        # VOLUME & PRICE
        fig, ax1 = plt.subplots(figsize=(18, 9))
        color = 'tab:green'
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Post Count (TSLA mentions)', color=color)
        ax1.bar(combined_df.index, combined_df['post_count'], color=color, alpha=0.6, width=0.9, label='TSLA Post Count')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle=':', alpha=0.7)

        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('TSLA Close Price ($)', color=color)
        ax2.plot(combined_df.index, combined_df['TSLA_Close'], color=color, label='TSLA Close Price')
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title('TSLA Mention Volume vs. Stock Price Over Time', fontsize=16)
        fig.tight_layout()
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='upper left')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=8, maxticks=15))
        fig.autofmt_xdate()
        plt.show()

    except Exception as e:
        print(f"Error fetching stock data: {e}")
        exit(1)
    

    
# --- Example of how you might call this function ---
# if __name__ == "__main__":
#     PROCESSED_FILE_PATH = 'wsb_sub_processed.csv' # Make sure this file exists and is populated
#     TARGET_TICKER = 'TSLA'
# 
#     tsla_daily_analysis = analyze_ticker(PROCESSED_FILE_PATH, TARGET_TICKER)
# 
#     if not tsla_daily_analysis.empty:
#         print(f"\n--- Daily Analysis for {TARGET_TICKER} (first 5 days) ---")
#         print(tsla_daily_analysis.head())
# 
#         # From here, you would proceed to fetch stock price data for TSLA
#         # for the same date range and then combine and plot them.
#     else:
#         print(f"No analysis data generated for {TARGET_TICKER}.")