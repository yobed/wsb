
import re
from time import sleep
import pandas as pd
import json
import os
import openai

try:
    client = openai.OpenAI() 
except openai.OpenAIError as e:
    print(f"ERROR: OpenAI API key issue or client initialization failed: {e}")
    print("Ensure OPENAI_API_KEY environment variable is set correctly.")
    exit()

OPENAI_MODEL_NAME = "gpt-4o-mini" # Cost-effective and capable OpenAI model

TITLE_COLUMN = 'title'
SELFTEXT_COLUMN = 'selftext'
CHECK_ONLY_FIRST_CHUNK = False # Set to True to process only the first chunk

# Configurations
file_path = 'wsb_sub_sentiment.csv'
output_path = 'wsb_sub_processed.csv'
ticker_file = 'ticker_list.txt'
chunk_size = CHUNK_SIZE = 500


DELAY_BETWEEN_API_CALLS_SECONDS = 0.02
CHUNKS_ALREADY_PROCESSED_COUNT = 217
ROWS_TO_SKIP_IN_INPUT = CHUNKS_ALREADY_PROCESSED_COUNT * CHUNK_SIZE



def chunkify_batch(file_path, output_path, chunk_size, tickers, chunks_already_processed):
    try:
        write_header_to_output = True
        output_exists = os.path.exists(output_path)
        for i,chunk in enumerate(pd.read_csv(file_path, chunksize=chunk_size)):
            # Process each chunk here
            current_index = i
            # For example, you can print the first few rows of each chunk
            if current_index < chunks_already_processed:
                print(f"Skipping chunk {current_index + 1} as it has already been processed.")
                continue
            print(f'--- Processing chunk {i + 1} ---')
            processed_chunk = extraction(chunk, tickers)
            print("Head of processed chunk:")
            print(processed_chunk.head(10))
            print("\nValue counts for 'sentiment' column in this chunk:")
            print(processed_chunk['sentiment'].value_counts().head(10))

            print("\nValue counts for 'ai_reason' column in this chunk:")
            print(processed_chunk['ai_reason'].value_counts().head(10))

            # Ticker check
            if 'tickers' in processed_chunk.columns:
                print("\nValue counts for 'tickers' column in this chunk:")
                print(processed_chunk['tickers'].value_counts().head(10)) # Show top 10 for brevity
            else:
                print("'tickers' column not found in chunk.")

            
            # save the processed chunk to a new CSV file
            if write_header_to_output and not output_exists:
                processed_chunk.to_csv(output_path, mode='w', header=True, index=False)
                write_header_to_output = False # Headers are now written, subsequent appends
                print(f"Chunk {i + 1} saved to '{output_path}' with headers.")
            else:
                processed_chunk.to_csv(output_path, mode='a', header=False, index=False)
                print(f"Chunk {i + 1} appended to '{output_path}'.")

            if i == 0 and CHECK_ONLY_FIRST_CHUNK:
                print("\nProcessed only the first chunk as requested. Stopping.")
                break # Stop after processing the first chunk
            

            # You can also save each chunk to a new file if needed
            # chunk.to_csv(f'chunk_{i}.csv', index=False)
    except Exception as e:
        print(f"An error occurred while processing the file: {e}")
        exit(1)

        
def extraction(chunk, tickers, title_col='title', selftext_col='selftext'):
    # This function should contain the logic to extract tickers from the chunk
    # tickers will be located in either the title or selftext column
    # You can use regex or any other method to find the tickers
    found_tickers = []
    sentiments = []
    reasons = []
    for index, row in chunk.iterrows():
        title_text = str(row.get(title_col, '')).lower() if pd.notna(row.get(title_col)) else ""
        self_text = str(row.get(selftext_col, '')).lower() if pd.notna(row.get(selftext_col)) else ""
        # We want to combine the title and selftext into one string
        combined_text_to_search = title_text + " " + self_text
        # Store tickers uniquely
        # ------------ TICKER EXTRACTION ------------- 
        tickers_in_this_row = set()
        if combined_text_to_search.strip(): # if combined_text is not empty otherwise skip
            for ticker_symbol in tickers:
                # Using regex to escape other characters:
                pattern = r'(?:[\s\(\[\"\']|^)(\$|#)?(' + re.escape(ticker_symbol) + r')\b'
                if re.search(pattern, combined_text_to_search): # regex is fast
                    tickers_in_this_row.add(ticker_symbol.upper())
        found_tickers.append(json.dumps(sorted(list(tickers_in_this_row))))
        # --------- END TICKER EXTRACTION ------------- 
        sentiment = None
        reason = None
        if len(tickers_in_this_row) > 0:
            if combined_text_to_search.strip(): # if combined_text is not empty otherwise skip
                sentiment, reason = sentiment_analysis(combined_text_to_search)
                if sentiment and reason:
                    if sentiment == "Rate Limited":
                        sentiment, reason = sentiment_analysis(combined_text_to_search)
                sleep(DELAY_BETWEEN_API_CALLS_SECONDS)
        sentiments.append(sentiment)
        reasons.append(reason)

    chunk['sentiment'] = sentiments
    chunk['ai_reason'] = reasons
    chunk['tickers'] = found_tickers
    return chunk

def sentiment_analysis(text,):
    # Reddit has a 40_000 character limit for body section!
    max_chars = 1500
    processed_text = str(text)
    if len(processed_text) > max_chars:
        processed_text = processed_text[:max_chars]  # Truncate to max_chars
    try: 
        messages = [
            {"role": "system", "content": "You are an AI expert in financial and meme sentiment analysis. Analyze the sentiment of the provided Reddit post text. "
                                         "Respond with a JSON object containing two keys: "
                                         "'sentiment' (string: 'Positive', 'Negative', or 'Neutral') and "
                                         "'ai_reason' (string: a brief, one-sentence explanation for the sentiment)."},
            {"role": "user", "content": f"Analyze the following text: \"{processed_text}\""}
        ]
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME, messages=messages, temperature=0.2,
            max_tokens=150, response_format={"type": "json_object"}
        )
        api_response_content = response.choices[0].message.content
        if api_response_content:
            result = json.loads(api_response_content)
            sentiment_val = result.get('sentiment', 'Parse Error')
            reason_val = result.get('ai_reason', 'Parse Error')
            return sentiment_val, reason_val
        else:
            return "API Error", "Empty API response content"
    except openai.RateLimitError as e: # Specific error for rate limits
        print(f"OpenAI Rate Limit Error hit: {e}. Sleeping for 60 seconds...")
        sleep(60) # Reactive sleep
        return "Rate Limited", "Retrying after delay"
    except openai.APIError as e: # Other API errors
        print(f"OpenAI API Error for text '{processed_text[:50]}...': {e}")
        return None, None
    except json.JSONDecodeError as e:
        error_response_content = api_response_content if 'api_response_content' in locals() else "Response content not available"
        print(f"JSON Decode Error for text '{processed_text[:50]}...': {e}. Response: {error_response_content}")
        return None, None
    except Exception as e:
        print(f"An unexpected error during OpenAI call for text '{processed_text[:50]}...': {e}")
        exit(1) # Exit on unexpected errors
    


    

def read_ticker_file(ticker_file):
    try:
        with open(ticker_file, 'r') as f:
            tickers = [line.strip().lower() for line in f if line.strip()]
        return tickers
    except FileNotFoundError:
        print(f"Error: The file '{ticker_file}' was not found.")
        exit(1)

if __name__ == "__main__":
    # Read the ticker file
    tickers = read_ticker_file(ticker_file)
    print("Tickers read from file:", tickers)
    sleep(1)
    # Process the CSV file in chunks
    chunkify_batch(file_path, output_path, chunk_size, tickers, CHUNKS_ALREADY_PROCESSED_COUNT)
    print("Chunkified batch processing completed.")
    