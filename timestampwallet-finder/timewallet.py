import random
import tls_client
from fake_useragent import UserAgent
import concurrent.futures
import time
import os
import base64

class TimestampTransactions:
    def __init__(self):
        # Create a tls_client session with a default identifier.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s

    def randomise(self):
        # Randomize the client identifier and refresh session and headers.
        self.identifier = random.choice(
            [browser for browser in tls_client.settings.ClientIdentifiers.__args__
             if browser.startswith(('chrome', 'safari', 'firefox', 'opera'))]
        )
        self.sendRequest = tls_client.Session(random_tls_extension_order=True, client_identifier=self.identifier)
        
        parts = self.identifier.split('_')
        identifier, version, *rest = parts
        os_type = 'windows'
        if identifier == 'opera':
            identifier = 'chrome'
        elif version == 'ios':
            os_type = 'ios'
        else:
            os_type = 'windows'
        
        # Omit the 'os' parameter for compatibility.
        self.user_agent = UserAgent(browsers=[identifier]).random
        
        self.headers = {
            'Host': 'gmgn.ai',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'dnt': '1',
            'priority': 'u=1, i',
            'referer': 'https://gmgn.ai/?chain=sol',
            'user-agent': self.user_agent
        }

    def fetch_url(self, url: str):
        """
        Attempts to fetch a URL (without proxies) and returns the JSON response.
        Retries up to 3 times before returning an empty dictionary.
        """
        retries = 3
        for attempt in range(retries):
            self.randomise()
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"[🐲] Error fetching data (attempt {attempt+1}): {e}")
            time.sleep(1)
        print(f"[🐲] Failed to fetch data after {retries} attempts.")
        return {}

    def getTxByTimestamp(self, contractAddress: str, threads: int, start: str, end: str):
        """
        Fetches all trade history pages for the given contract address and collects all trades
        whose timestamp falls between start and end.
        Saves every maker address from these trades into a text file.
        
        Note: Provide the timestamps in Unix time (seconds since epoch), for example: 1690000000
        """
        base_url = f"https://gmgn.ai/defi/quotation/v1/trades/sol/{contractAddress}?limit=100"
        paginator = None
        urls = []
        all_trades = []
        
        print(f"[🐲] Starting... please wait.")
        
        # Convert the provided timestamps to integers.
        start = int(start)
        end = int(end)
        
        # Paginate until we reach trades older than our start timestamp.
        while True:
            self.randomise()
            url = f"{base_url}&cursor={paginator}" if paginator else base_url
            urls.append(url)
            response = self.fetch_url(url)
            data = response.get('data', {})
            trades = data.get('history', [])
            
            # If no trades returned or the oldest trade is older than start, stop paginating.
            if not trades or trades[-1].get('timestamp', 0) < start:
                break
            
            paginator = data.get('next')
            if not paginator:
                break
            time.sleep(1)
        
        # Use a thread pool to fetch all pages concurrently.
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.fetch_url, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                response = future.result()
                trades = response.get('data', {}).get('history', [])
                # Filter trades by timestamp
                filtered_trades = [trade for trade in trades if start <= trade.get('timestamp', 0) <= end]
                all_trades.extend(filtered_trades)
        
        # Extract maker addresses from the filtered trades.
        wallets = [trade.get("maker") for trade in all_trades if trade.get("maker")]
        
        # Create the output directory if it doesn't exist.
        output_dir = "Dragon/data/Solana/TimestampTxns"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"txns_{self.shorten(contractAddress)}_{random.randint(1111, 9999)}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            for wallet in wallets:
                f.write(f"{wallet}\n")
        
        print(f"[🐲] {len(wallets)} trades successfully saved to {filepath}")

if __name__ == '__main__':
    # Prompt the user for input.
    contract_address = input("Enter the contract address: ").strip()
    if not contract_address:
        print("No contract address provided. Exiting.")
        exit(1)
    
    try:
        threads = int(input("Enter the number of threads you'd like to use: "))
    except ValueError:
        print("Invalid number of threads. Please enter an integer.")
        exit(1)
    
    # Display a note about the timestamp format.
    print("Note: Timestamps must be provided as Unix time (seconds since epoch), e.g., 1690000000")
    
    start_timestamp = input("Enter the start timestamp: ").strip()
    end_timestamp = input("Enter the end timestamp: ").strip()
    
    if not start_timestamp or not end_timestamp:
        print("Both start and end timestamps must be provided. Exiting.")
        exit(1)
    
    start_time = time.time()
    txnFinder = TimestampTransactions()
    txnFinder.getTxByTimestamp(contract_address, threads, start_timestamp, end_timestamp)
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
