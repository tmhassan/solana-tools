import random
import tls_client
import concurrent.futures
from threading import Lock
import time
import base64
import os

class CopyTradeWalletFinder:
    def __init__(self):
        # Create a tls_client session with a default identifier.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s
        self.lock = Lock()

    def randomise(self):
        # Predefined list of modern user agents for different browsers
        user_agents = [
            # Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/113.0",
            "Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/113.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58"
        ]
        
        # Randomly choose a client identifier and refresh session and headers
        self.identifier = random.choice(
            [browser for browser in tls_client.settings.ClientIdentifiers.__args__
             if browser.startswith(('chrome', 'safari', 'firefox', 'opera'))]
        )
        self.sendRequest = tls_client.Session(random_tls_extension_order=True, client_identifier=self.identifier)
        
        # Randomly select a user agent from our predefined list
        self.user_agent = random.choice(user_agents)

        self.headers = {
            'Host': 'gmgn.ai',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'dnt': '1',
            'priority': 'u=1, i',
            'referer': 'https://gmgn.ai/?chain=sol',
            'user-agent': self.user_agent
        }

    def request(self, url: str):
        """
        Makes a GET request to the provided URL.
        Retries up to 3 times before returning empty data.
        Returns a tuple: (history data, next cursor/paginator)
        """
        retries = 3

        for attempt in range(retries):
            self.randomise()
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                if response.status_code == 200:
                    json_data = response.json()
                    data = json_data['data']['history']
                    paginator = json_data['data'].get('next')
                    return data, paginator
            except Exception as e:
                print(f"[🐲] Error fetching data, trying backup... {e}")

            time.sleep(1)

        print(f"[🐲] Failed to fetch data after {retries} attempts for URL: {url}")
        return [], None

    def findWallets(self, contractAddress: str, targetMaker: str, threads: int):
        """
        For the given contract address, paginates through the trade history (buy events)
        to grab all pages. Then, using a thread pool, it scans all fetched pages and looks
        for the target wallet address. It then returns the 10 makers immediately preceding the target.
        """
        base_url = f"https://gmgn.ai/defi/quotation/v1/trades/sol/{contractAddress}?limit=100&event=buy"
        paginator = None
        urls = []

        print("\n[🐲] Starting... please wait.\n")

        # First, paginate through history until no further page is available.
        while True:
            self.randomise()
            url = f"{base_url}&cursor={paginator}" if paginator else base_url
            urls.append(url)
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                if response.status_code != 200:
                    raise Exception("Error in initial request")
            except Exception as e:
                print(f"[🐲] Error fetching data, trying backup... {e}")
                time.sleep(1)
                continue

            paginator = response.json()['data'].get('next')
            # Show progress by decoding the paginator (if available)
            if paginator:
                try:
                    decoded = base64.b64decode(paginator).decode('utf-8')
                    print(f"[🐲] Page cursor: {decoded}", end="\r")
                except Exception:
                    pass

            if not paginator:
                print("\n[🐲] No further pages.")
                break

            time.sleep(1)

        # Use a thread pool to request all URLs concurrently.
        found_target = False
        temp_makers = []  # All makers (from each page)

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.request, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                history, _ = future.result()

                with self.lock:
                    for maker_entry in history:
                        event = maker_entry['event']
                        txns = maker_entry.get('total_trade', 0)
                        # Consider only "buy" events with fewer than 200 transactions.
                        if event == "buy" and txns < 200:
                            if maker_entry['maker'] == targetMaker:
                                found_target = True
                                break
                            if maker_entry['maker'] not in temp_makers:
                                temp_makers.append(maker_entry['maker'])
                if found_target:
                    break

        # Grab the last 10 makers in the list (i.e. those immediately preceding the target).
        makers = temp_makers[-10:]

        if found_target:
            print(f"\n[🐲] Found target maker: {targetMaker}")
            print(f"[🐲] The 10 makers immediately preceding the target maker:")
            for idx, maker in enumerate(makers, 1):
                print(f"{idx}. {maker}")
        else:
            print(f"\n[🐲] Target maker {targetMaker} not found.")

        # Save results to file
        output_dir = "Dragon/data/Solana/CopyWallets"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"wallets_after_{self.shorten(targetMaker)}_{random.randint(1111, 9999)}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as file:
            for maker in makers:
                file.write(f"{maker}\n")
        print(f"[🐲] Saved the 10 makers after {targetMaker} to {filename}")

if __name__ == '__main__':
    # Prompt the user for input
    contract_address = input("Enter the contract address: ").strip()
    if not contract_address:
        print("No contract address provided. Exiting.")
        exit(1)

    target_maker = input("Enter the wallet (maker) address you'd like to check: ").strip()
    if not target_maker:
        print("No wallet address provided. Exiting.")
        exit(1)

    try:
        threads = int(input("Enter the number of threads you'd like to use: "))
    except ValueError:
        print("Invalid number of threads. Please enter an integer.")
        exit(1)

    start_time = time.time()

    finder = CopyTradeWalletFinder()
    finder.findWallets(contract_address, target_maker, threads)

    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
