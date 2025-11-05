import json
import time
import random
import os
import tls_client
import base64

from fake_useragent import UserAgent
from collections import defaultdict

class EarlyBuyerCopyFinder:
    def __init__(self):
        # Initialize a tls_client session.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s
        self.allData = {}         # Aggregated early buyer data per contract
        self.allAddresses = set() # Unique early buyer addresses across contracts
        self.addressFrequency = defaultdict(int)
        self.totalBuyers = 0

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
        # Generate a random user agent (omit the 'os' parameter for compatibility).
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

    def fetchEarlyBuyers(self, contractAddress: str):
        """
        Fetches early buyer trade history from the token endpoint.
        Uses the 'revert=true' parameter to get the earliest trades.
        Returns a list of trade entries filtered to "buy" events (excluding entries with "creator" in maker_token_tags).
        """
        url = f"https://gmgn.ai/defi/quotation/v1/trades/sol/{contractAddress}?revert=true"
        retries = 3
        for attempt in range(retries):
            try:
                self.randomise()
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                if response.status_code == 200:
                    data = response.json().get('data', {}).get('history', [])
                    if isinstance(data, list):
                        filtered = [
                            entry for entry in data
                            if entry.get('event') == "buy" and "creator" not in entry.get('maker_token_tags', [])
                        ]
                        return filtered
            except Exception as e:
                print(f"[🐲] Error fetching early buyers on attempt {attempt+1}: {e}")
            time.sleep(1)
        print(f"[🐲] Failed to fetch early buyer data for contract: {contractAddress}")
        return []

    def findCopyWallets(self, contractAddress: str, targetMaker: str):
        """
        Sequentially fetch pages of trade history for the given contract.
        For each page, collect makers until the target maker is encountered.
        Return the last 10 unique maker addresses encountered (the potential copy wallets).
        """
        base_url = f"https://gmgn.ai/defi/quotation/v1/trades/sol/{contractAddress}?limit=100&event=buy"
        paginator = None
        encountered_makers = []
        found_target = False

        while True:
            self.randomise()
            url = f"{base_url}&cursor={paginator}" if paginator else base_url
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                if response.status_code != 200:
                    print(f"[🐲] Error fetching trade page: Non-200 status ({response.status_code}).")
                    break
            except Exception as e:
                print(f"[🐲] Error fetching trade page: {e}")
                break

            data = response.json().get('data', {})
            history = data.get('history', [])
            for trade in history:
                maker = trade.get('maker')
                if maker == targetMaker:
                    found_target = True
                    break
                if maker not in encountered_makers:
                    encountered_makers.append(maker)
            if found_target:
                break
            paginator = data.get('next')
            if not paginator:
                print("[🐲] No further pages.")
                break
            # Optionally, display the decoded paginator:
            try:
                decoded = base64.b64decode(paginator).decode('utf-8')
                print(f"[🐲] Page cursor: {decoded}", end="\r")
            except Exception:
                pass
            time.sleep(1)

        # Return the last 10 makers (those immediately preceding the target maker).
        return encountered_makers[-10:]

    def run(self, contractAddress: str):
        """
        Main routine:
         1. Fetch early buyers from the given contract.
         2. Sort them by realized profit (PnL) and select the top 5.
         3. For each top early buyer (target maker), run the copy wallet finder separately.
         4. Print and save the results.
        """
        print(f"\n[🐲] Fetching early buyers for contract: {contractAddress}\n")
        early_buyers = self.fetchEarlyBuyers(contractAddress)
        if not early_buyers:
            print("[🐲] No early buyer data found. Exiting.")
            return

        # Sort early buyers by realized_profit (if missing, assume 0) in descending order.
        early_buyers.sort(key=lambda b: b.get('realized_profit') or 0, reverse=True)
        top5_buyers = early_buyers[:5]

        print("\n[🐲] Top 5 Early Buyers (by realized profit):")
        for idx, buyer in enumerate(top5_buyers, 1):
            maker = buyer.get('maker')
            pnl = buyer.get('realized_profit') or 0
            print(f"{idx}. Maker: {maker}, Realized Profit: {pnl}")

        results = {}
        print("\n[🐲] Searching for copy wallets for each top early buyer...\n")
        # Process each target maker one by one.
        for buyer in top5_buyers:
            target_maker = buyer.get('maker')
            print(f"\n[🐲] Processing target maker: {target_maker}")
            copy_wallets = self.findCopyWallets(contractAddress, target_maker)
            results[target_maker] = copy_wallets
            if copy_wallets:
                print(f"[🐲] Found copy wallets for {target_maker}:")
                for idx, wallet in enumerate(copy_wallets, 1):
                    print(f"  {idx}. {wallet}")
            else:
                print(f"[🐲] No copy wallets found for {target_maker}.")

        # Save the results to a JSON file.
        output_dir = "Dragon/data/Solana/EarlyBuyerCopyWallets"
        os.makedirs(output_dir, exist_ok=True)
        identifier = self.shorten(list(self.allAddresses)[0]) if self.allAddresses else "no_addresses"
        filename = f"EarlyBuyerCopyWallets_{identifier}_{random.randint(1111,9999)}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as file:
            json.dump(results, file, indent=4)
        print(f"\n[🐲] Saved copy wallet results to {filepath}")

if __name__ == '__main__':
    contract_address = input("Enter the contract address: ").strip()
    if not contract_address:
        print("No contract address provided. Exiting.")
        exit(1)
    start_time = time.time()
    finder = EarlyBuyerCopyFinder()
    finder.run(contract_address)
    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
