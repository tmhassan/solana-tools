import json
import time
import random
import os
import tls_client

from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

class TopHolders:
    def __init__(self):
        # Create a tls_client session with a default identifier.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s
        self.allData = {}
        self.allAddresses = set()
        self.addressFrequency = defaultdict(int)
        self.totalTraders = 0

    def randomise(self):
        # Randomly choose a client identifier and refresh session and headers.
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

        # Generate a random user agent based on the identifier.
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

    def getBondingCurve(self, contractAddress: str):
        """
        Retrieve the bonding curve (pool address) for the given token.
        Retries up to 3 times.
        Note: This function now uses the top-level 'biggest_pool_address' key.
        """
        retries = 3
        url = f"https://gmgn.ai/defi/quotation/v1/tokens/sol/{contractAddress}"

        for attempt in range(retries):
            self.randomise()
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                data = response.json()  # No 'data' wrapper in the JSON response.
                if data:
                    bondingCurve = data.get('biggest_pool_address', "")
                    return bondingCurve
            except Exception as e:
                print(f"[🐲] Error fetching bonding curve for token {contractAddress} on attempt {attempt+1}: {e}")
            time.sleep(1)
        print(f"[🐲] Failed to fetch bonding curve for token {contractAddress} after {retries} attempts.")
        return ""

    def fetchTopHolders(self, contractAddress: str):
        """
        Fetch the top holders for a given token.
        Retries up to 3 times before returning an empty list.
        """
        url = f"https://gmgn.ai/defi/quotation/v1/tokens/top_holders/sol/{contractAddress}?orderby=amount_percentage&direction=desc"
        retries = 3

        for attempt in range(retries):
            self.randomise()
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                data = response.json().get('data', None)  # Assuming the top holders response is wrapped in 'data'
                if data:
                    return data
            except Exception as e:
                print(f"[🐲] Error fetching top holders for token {contractAddress} on attempt {attempt+1}: {e}")
            time.sleep(1)
        print(f"[🐲] Failed to fetch top holders for token {contractAddress} after {retries} attempts.")
        return []

    def topHolderData(self, contractAddresses, threads):
        """
        Process a list of token addresses using a ThreadPoolExecutor.
        Aggregates the top holders data and saves the results to files.
        """
        # Exclusion list (only add if needed)
        excludeAddress = [
            "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
            "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
        ]

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.fetchTopHolders, address): address for address in contractAddresses}

            for future in as_completed(futures):
                contract_address = futures[future]
                response = future.result()

                bondingCurve = self.getBondingCurve(contract_address)
                if bondingCurve:
                    excludeAddress.append(bondingCurve)

                self.allData[contract_address] = {}
                self.totalTraders += len(response)

                for top_holder in response:
                    # Uncomment the following lines if you want to apply specific filters.
                    # if top_holder['address'] in excludeAddress or top_holder['cost_cur'] < 50:
                    #     continue

                    multiplier_value = top_holder.get('profit_change')
                    if multiplier_value is None:
                        multiplier_value = 0

                    address = top_holder.get('address')
                    self.addressFrequency[address] += 1 
                    self.allAddresses.add(address)
                    
                    bought_usd = f"${top_holder.get('total_cost', 0):,.2f}"
                    total_profit = f"${top_holder.get('realized_profit', 0):,.2f}"
                    unrealized_profit = f"${top_holder.get('unrealized_profit', 0):,.2f}"
                    multiplier = f"{multiplier_value:.2f}x"
                    buys = f"{top_holder.get('buy_tx_count_cur', 0)}"
                    sells = f"{top_holder.get('sell_tx_count_cur', 0)}"
                    
                    self.allData[address] = {
                        "boughtUsd": bought_usd,
                        "totalProfit": total_profit,
                        "unrealizedProfit": unrealized_profit,
                        "multiplier": multiplier,
                        "buys": buys,
                        "sells": sells
                    }
        
        repeatedAddresses = [address for address, count in self.addressFrequency.items() if count > 1]
        identifier = self.shorten(list(self.allAddresses)[0]) if self.allAddresses else "no_addresses"
        
        output_dir = 'data/Solana/TopHolders'
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, f'allTopAddresses_{identifier}.txt'), 'w') as av:
            for address in self.allAddresses:
                av.write(f"{address}\n")

        if repeatedAddresses:
            with open(os.path.join(output_dir, f'repeatedTopHolders_{identifier}.txt'), 'w') as ra:
                for address in repeatedAddresses:
                    ra.write(f"{address}\n")
            print(f"[🐲] Saved {len(repeatedAddresses)} repeated addresses to repeatedTopHolders_{identifier}.txt")

        with open(os.path.join(output_dir, f'TopHolders_{identifier}.json'), 'w') as tt:
            json.dump(self.allData, tt, indent=4)

        print(f"[🐲] Saved data for {self.totalTraders} top holders for {len(contractAddresses)} tokens to allTopAddresses_{identifier}.txt")
        print(f"[🐲] Saved {len(self.allAddresses)} unique top holder addresses to TopHolders_{identifier}.json")

        return

if __name__ == '__main__':
    # Prompt the user to enter token addresses.
    tokens_input = input("Enter the contract addresses separated by commas: ").strip()
    contract_addresses = [token.strip() for token in tokens_input.split(',') if token.strip()]

    if not contract_addresses:
        print("No contract addresses provided. Exiting.")
        exit(1)

    try:
        threads = int(input("Enter the number of threads you'd like to use: "))
    except ValueError:
        print("Invalid number of threads. Please enter an integer.")
        exit(1)

    start_time = time.time()

    scraper = TopHolders()
    scraper.topHolderData(contract_addresses, threads)

    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
