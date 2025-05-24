# For analysis on data, WSB data via ticker list, sentiment analysis
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns

PROCESSED_FILE_PATH = 'wsb_sub_processed.csv'
def load_processed_data(file_path):
    """Load the processed data from a CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Processed file not found: {file_path}")
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])

    return df

def analyze_sentiment_distribution(df):
    """Analyze the distribution of sentiment in the DataFrame."""
    sentiment_counts = df['sentiment'].value_counts()
    print("Sentiment Distribution:")
    print(sentiment_counts)

    # sentiment distribution bar plot
    plt.figure(figsize=(10, 6))
    sns.barplot(x=sentiment_counts.index, y=sentiment_counts.values)
    plt.title('Sentiment Distribution')
    plt.xlabel('Sentiment')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def analyze_sentiment_by_period(df, period='W'):

    df['date'] = pd.to_datetime(df['date'])
    
    # Set 'date' as index for resampling
    df_resampled = df.set_index('date')
    
    # Resample and count sentiments
    sentiment_by_period = df_resampled.groupby(pd.Grouper(freq=period))['sentiment'] \
                                      .value_counts() \
                                      .unstack(fill_value=0)
    
    print(f"Sentiment Distribution by {period}:")
    print(sentiment_by_period.head())


    sentiment_by_period.plot(kind='bar', stacked=True, figsize=(15, 7))
    
    period_name = {"W": "Week", "M": "Month", "ME": "Month", "Q": "Quarter", "QE":"Quarter"}.get(period, period)
    plt.title(f'Sentiment Distribution by {period_name}')
    plt.xlabel(period_name)
    plt.ylabel('Count')
    
    if period in ['M', 'ME', 'Q', 'QE']:
        plt.xticks(rotation=45, ha='right')
    else: 
        plt.xticks(rotation=70, ha='right')

    plt.tight_layout()
    plt.show()

    return sentiment_by_period

def analyze_fully(df):
    valid_sentiments = ['Positive', 'Negative', 'Neutral']
    df_clean_sentiment = df[df['sentiment'].isin(valid_sentiments)].copy()
    sentiment_map = {'Positive': 1, 'Neutral': 0, 'Negative': -1}
    df_clean_sentiment['sentiment_score'] = df_clean_sentiment['sentiment'].map(sentiment_map)
    # Parse the JSON string into actual lists
    df_clean_sentiment['tickers_list'] = df_clean_sentiment['tickers'].apply(lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else [])

    df_exploded_tickers = df_clean_sentiment.explode('tickers_list')
    df_exploded_tickers.rename(columns={'tickers_list': 'ticker_symbol'}, inplace=True)
    df_ticker_analysis = df_exploded_tickers[df_exploded_tickers['ticker_symbol'].notna()].copy()
    return df_ticker_analysis, df_clean_sentiment

def analyze_ticker_sentiment(df_ticker_analysis):
    top_n = 20
    most_mentioned_tickers = df_ticker_analysis['ticker_symbol'].value_counts().nlargest(top_n)
    print(f"\nTop {top_n} Most Mentioned Tickers:")
    print(most_mentioned_tickers)

    plt.figure(figsize=(12, 8))
    most_mentioned_tickers.sort_values().plot(kind='barh') # sort_values for better visual
    plt.title(f'Top {top_n} Most Mentioned Tickers')
    plt.xlabel('Number of Mentions')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    try:
        # Load the processed data
        df = load_processed_data(PROCESSED_FILE_PATH)
        
        print("First few rows of the DataFrame:")
        print(df.head())
        
        df_ticker_analysis, df_clean_sentiment = analyze_fully(df)
        analyze_ticker_sentiment(df_ticker_analysis)
        
    except Exception as e:
        print(f"An error occurred: {e}")

