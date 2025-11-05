import json
import time
import random
import os
import tls_client

from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Optionally, you can remove or ignore this top-level instantiation if it causes issues:
# ua = UserAgent(os='linux', browsers=['firefox'])

class TopTraders:
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
        # Removed the 'os' parameter here.
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

    def fetchTopTraders(self, contractAddress: str):
        """
        Fetch top traders data for a given contract address.
        Retries up to 3 times before returning an empty list.
        """
        url = f"https://gmgn.ai/defi/quotation/v1/tokens/top_traders/sol/{contractAddress}?orderby=profit&direction=desc"
        retries = 3

        for attempt in range(retries):
            try:
                self.randomise()
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                data = response.json().get('data', None)
                if data:
                    return data
            except Exception as e:
                print(f"[🐲] Error fetching data for token {contractAddress} on attempt {attempt+1}: {e}")
                time.sleep(1)  # Wait before retrying

        print(f"[🐲] Failed to fetch data for token {contractAddress} after {retries} attempts.")
        return []

    def topTraderData(self, contractAddresses, threads):
        """
        Process a list of contract addresses using a ThreadPoolExecutor.
        Saves aggregated data into files.
        """
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Submit fetch tasks for each contract address.
            futures = {executor.submit(self.fetchTopTraders, address): address for address in contractAddresses}
            
            for future in as_completed(futures):
                contract_address = futures[future]
                response = future.result()

                # Store data per contract address (even if empty)
                self.allData[contract_address] = {}
                self.totalTraders += len(response)

                for top_trader in response:
                    multiplier_value = top_trader.get('profit_change')
                    
                    if multiplier_value is not None:
                        address = top_trader.get('address')
                        self.addressFrequency[address] += 1 
                        self.allAddresses.add(address)
                        
                        bought_usd = f"${top_trader.get('total_cost', 0):,.2f}"
                        total_profit = f"${top_trader.get('realized_profit', 0):,.2f}"
                        unrealized_profit = f"${top_trader.get('unrealized_profit', 0):,.2f}"
                        multiplier = f"{multiplier_value:.2f}x"
                        buys = f"{top_trader.get('buy_tx_count_cur', 0)}"
                        sells = f"{top_trader.get('sell_tx_count_cur', 0)}"
                        
                        # Use the trader's address as the key in the aggregated data.
                        self.allData[address] = {
                            "boughtUsd": bought_usd,
                            "totalProfit": total_profit,
                            "unrealizedProfit": unrealized_profit,
                            "multiplier": multiplier,
                            "buys": buys,
                            "sells": sells
                        }
        
        # Identify addresses that appear more than once across tokens.
        repeatedAddresses = [address for address, count in self.addressFrequency.items() if count > 1]
        
        # Create an identifier based on one of the addresses (or any other scheme).
        identifier = self.shorten(list(self.allAddresses)[0]) if self.allAddresses else "no_addresses"
        
        # Save all top trader addresses.
        output_dir = 'data/Solana/TopTraders'
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, f'allTopAddresses_{identifier}.txt'), 'w') as av:
            for address in self.allAddresses:
                av.write(f"{address}\n")

        # Save repeated addresses if any.
        if repeatedAddresses:
            with open(os.path.join(output_dir, f'repeatedTopTraders_{identifier}.txt'), 'w') as ra:
                for address in repeatedAddresses:
                    ra.write(f"{address}\n")
            print(f"[🐲] Saved {len(repeatedAddresses)} repeated addresses to repeatedTopTraders_{identifier}.txt")

        # Save the complete top traders data as JSON.
        with open(os.path.join(output_dir, f'topTraders_{identifier}.json'), 'w') as tt:
            json.dump(self.allData, tt, indent=4)

        print(f"[🐲] Saved data for {self.totalTraders} top traders from {len(contractAddresses)} tokens.")
        print(f"[🐲] Saved {len(self.allAddresses)} unique top trader addresses to topTraders_{identifier}.json")

        return

if __name__ == '__main__':
    # Prompt the user to enter contract addresses.
    tokens_input = input("Enter the contract addresses separated by commas: ").strip()
    # Split the input by comma and remove any extra whitespace.
    contract_addresses = [token.strip() for token in tokens_input.split(',') if token.strip()]

    if not contract_addresses:
        print("No contract addresses provided. Exiting.")
        exit(1)

    # Ask the user how many threads to use.
    try:
        threads = int(input("Enter the number of threads you'd like to use: "))
    except ValueError:
        print("Invalid number of threads. Please enter an integer.")
        exit(1)

    # Optionally, you can time the execution.
    start_time = time.time()
    
    scraper = TopTraders()
    scraper.topTraderData(contract_addresses, threads)
    
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
