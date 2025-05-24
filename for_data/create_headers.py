# Simple file to help me create headers
import pandas as pd


# File Path to your CSV file of data
file_path = 'wsb_sub.csv'

# If you know the headers
column_names = ['score', 'date', 'title', 'author', 'permalink', 'selftext']
# if you are unsure, check the first line of the CSV file 
in_place = False  # Set to True if you want to overwrite the original file * with caution




# Let's first open the CSV file, and create headers for the columns:
def create_headers(file_path):
    # Known headers, you can change them as per your CSV file
    df = pd.DataFrame()
    column_names = ['score', 'date', 'title', 'author', 'permalink', 'selftext']
    try:
        # If you are SURE there's no header row in the CSV file itself:
        df = pd.read_csv(file_path, header=None, names=column_names)
        print("DataFrame with assigned headers:")
        print(df.head())
        print("\nHeaders:", df.columns.tolist())

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: The file '{file_path}' is empty.")
    except Exception as e:
        print(f"An error occurred: {e}")
    # Check if the DataFrame is empty
    if df.empty:
        print("The DataFrame is empty. No data to process.")
    else:
        print("DataFrame created successfully with headers.")
        # Display the first few rows of the DataFrame
        print(df.head())
        # Display the column names
        print("Column names:", df.columns.tolist())
    return df

if __name__ == "__main__":
    # File path, (not included but check out Pushshift data dumps for .zst files).
    # Create headers for the CSV file
    df = create_headers(file_path)
    # Check if the DataFrame is not empty
    if not df.empty:
        # Create a new column for sentiment
        df['sentiment'] = None
        # Create a df for what the AI thinks:
        df['ai_reason'] = None
        # Create a col for tickers mentioned
        df['tickers'] = None
        # Save the DataFrame to a new CSV file
    
        if in_place:
            output_file_path = file_path
        else:
            # Create a new file name for the output
            file_path = file_path.split('.csv')[0]
            output_file_path = f'{file_path}_sentiment.csv'
        df.to_csv(output_file_path, index=False)
        print(f"DataFrame with sentiment column saved to '{output_file_path}'")
    else:
        print("The DataFrame is empty. No data to process.")
    