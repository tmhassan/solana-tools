import json
import time
import random
import os
import tls_client

from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

class EarlyBuyers:
    def __init__(self):
        # Initialize a TLS client session.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s
        self.allData = {}
        self.allAddresses = set()
        self.addressFrequency = defaultdict(int)
        self.totalBuyers = 0

    def randomise(self):
        # Randomize the client identifier and refresh the session and headers.
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

        # Generate a random user agent (the 'os' parameter is omitted for compatibility).
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

    def fetchEarlyBuyers(self, contractAddress: str, buyers: int):
        """
        Fetch the early buyers for a given contract address.
        The endpoint is called with the parameter 'revert=true', and the function
        returns the first list of history entries containing "buy" events where the maker
        does not have "creator" in its token tags.
        Retries up to 3 times.
        """
        url = f"https://gmgn.ai/defi/quotation/v1/trades/sol/{contractAddress}?revert=true"
        retries = 3

        for attempt in range(retries):
            try:
                self.randomise()
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
                # Extract the list of historical trades.
                data = response.json().get('data', {}).get('history', [])
                if isinstance(data, list):
                    # Return the first entry that is a "buy" event and does not include "creator" in maker_token_tags.
                    for item in data:
                        if item.get('event') == "buy" and "creator" not in item.get('maker_token_tags', []):
                            return data
            except Exception as e:
                print(f"[🐲] Error fetching data on attempt {attempt+1}: {e}")
            time.sleep(1)

        print(f"[🐲] Failed to fetch data after {retries} attempts for contract: {contractAddress}")
        return []

    def earlyBuyersdata(self, contractAddresses, threads, buyers: int):
        """
        For each contract address in the list, fetch the early buyer trade history,
        limit the results to the specified number of buyers per contract, and then aggregate the data.
        The function then saves the aggregated early buyer data and a list of unique addresses.
        """
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.fetchEarlyBuyers, address, buyers): address for address in contractAddresses}

            for future in as_completed(futures):
                contract_address = futures[future]
                response = future.result()
                # Limit the response to the desired number of early buyers.
                limited_response = response[:buyers] if len(response) >= buyers else response

                if contract_address not in self.allData:
                    self.allData[contract_address] = []

                self.totalBuyers += len(limited_response)

                # Print each early buyer with its realized profit.
                for earlyBuyer in limited_response:
                    address = earlyBuyer.get('maker')
                    pnl = earlyBuyer.get('realized_profit')
                    # Print in the format: Maker: <address>, Realized Profit: <pnl>
                    if address:
                        print(f"Maker: {address}, Realized Profit: {pnl}")
                        self.addressFrequency[address] += 1
                        self.allAddresses.add(address)
                        bought_usd = (f"${earlyBuyer.get('amount_usd'):,.2f}"
                                      if earlyBuyer.get('amount_usd') is not None else "?")
                        total_profit = (f"${earlyBuyer.get('realized_profit'):,.2f}"
                                        if earlyBuyer.get('realized_profit') is not None else "?")
                        unrealized_profit = (f"${earlyBuyer.get('unrealized_profit'):,.2f}"
                                             if earlyBuyer.get('unrealized_profit') is not None else "?")
                        trades = f"{earlyBuyer.get('total_trade')}" if earlyBuyer.get('total_trade') is not None else "?"
                        buyer_data = {
                            "boughtUsd": bought_usd,
                            "totalProfit": total_profit,
                            "unrealizedProfit": unrealized_profit,
                            "trades": trades,
                        }
                        self.allData[contract_address].append({address: buyer_data})

        repeatedAddresses = [address for address, count in self.addressFrequency.items() if count > 1]
        identifier = self.shorten(list(self.allAddresses)[0]) if self.allAddresses else "no_addresses"

        output_dir = 'data/Solana/EarlyBuyers'
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, f'allTopAddresses_{identifier}.txt'), 'w') as av:
            for address in self.allAddresses:
                av.write(f"{address}\n")

        if repeatedAddresses:
            with open(os.path.join(output_dir, f'repeatedEarlyBuyers_{identifier}.txt'), 'w') as ra:
                for address in repeatedAddresses:
                    ra.write(f"{address}\n")
            print(f"[🐲] Saved {len(repeatedAddresses)} repeated addresses to repeatedEarlyBuyers_{identifier}.txt")

        with open(os.path.join(output_dir, f'EarlyBuyers_{identifier}.json'), 'w') as tt:
            json.dump(self.allData, tt, indent=4)

        print(f"[🐲] Saved {self.totalBuyers} early buyers for {len(contractAddresses)} contract(s) to allTopAddresses_{identifier}.txt")
        print(f"[🐲] Saved {len(self.allAddresses)} unique early buyer addresses to EarlyBuyers_{identifier}.json")
        return

if __name__ == '__main__':
    # Prompt for contract addresses (you can enter multiple addresses separated by commas)
    tokens_input = input("Enter the contract addresses separated by commas: ").strip()
    contract_addresses = [token.strip() for token in tokens_input.split(',') if token.strip()]
    if not contract_addresses:
        print("No contract addresses provided. Exiting.")
        exit(1)

    try:
        buyers = int(input("Enter the number of early buyers you'd like to scrape per contract: "))
    except ValueError:
        print("Invalid number for early buyers. Please enter an integer.")
        exit(1)

    try:
        threads = int(input("Enter the number of threads you'd like to use: "))
    except ValueError:
        print("Invalid number for threads. Please enter an integer.")
        exit(1)

    start_time = time.time()
    scraper = EarlyBuyers()
    scraper.earlyBuyersdata(contract_addresses, threads, buyers)
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
