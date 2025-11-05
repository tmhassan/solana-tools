import csv
import random
import tls_client
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os

class BulkWalletChecker:
    def __init__(self):
        # Initialize a TLS client session.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s
        self.skippedWallets = 0
        self.totalGrabbed = 0
        self.totalFailed = 0
        self.results = []

    def randomise(self):
        # Randomize the client identifier and refresh the session and headers.
        self.identifier = random.choice(
            [browser for browser in tls_client.settings.ClientIdentifiers.__args__
             if browser.startswith(('chrome', 'safari', 'firefox', 'opera'))]
        )
        self.sendRequest = tls_client.Session(random_tls_extension_order=True, client_identifier=self.identifier)
        self.sendRequest.timeout_seconds = 60

        parts = self.identifier.split('_')
        identifier, version, *rest = parts
        os_type = 'windows'
        if identifier == 'opera':
            identifier = 'chrome'
        elif version == 'ios':
            os_type = 'ios'
        else:
            os_type = 'windows'

        # Note: We omit the 'os' parameter for compatibility.
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

    def getTokenDistro(self, wallet: str, useProxies=False):
        # Since we're not using proxies, use direct connection.
        url = f"https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/{wallet}/unique_token_7d?interval=30d"
        retries = 3
        tokenDistro = []

        for attempt in range(retries):
            self.randomise()
            try:
                response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True).json()
                tokenDistro = response['data']['tokens']
                if tokenDistro:
                    break
            except Exception:
                time.sleep(1)
        if not tokenDistro:
            return {"No Token Distribution Data": None}

        FiftyPercentOrMore = 0
        ZeroToFifty = 0
        FiftyTo100 = 0
        TwoToFour = 0
        FiveToSix = 0
        SixPlus = 0
        NegativeToFifty = 0 

        for profit in tokenDistro:
            total_profit_pnl = profit.get('total_profit_pnl')
            if total_profit_pnl is not None:
                profitMultiplier = total_profit_pnl * 100

                if profitMultiplier <= -50:
                    FiftyPercentOrMore += 1
                elif -50 < profitMultiplier < 0:
                    NegativeToFifty += 1
                elif 0 <= profitMultiplier < 50:
                    ZeroToFifty += 1
                elif 50 <= profitMultiplier < 199:
                    FiftyTo100 += 1
                elif 200 <= profitMultiplier < 499:
                    TwoToFour += 1
                elif 500 <= profitMultiplier < 600:
                    FiveToSix += 1
                elif profitMultiplier >= 600:
                    SixPlus += 1

        return {
            "-50% +": FiftyPercentOrMore,
            "0% - -50%": NegativeToFifty,
            "0 - 50%": ZeroToFifty,
            "50% - 199%": FiftyTo100,
            "200% - 499%": TwoToFour,
            "500% - 600%": FiveToSix,
            "600% +": SixPlus
        }

    def getWalletData(self, wallet: str, skipWallets: bool, useProxies=False):
        url = f"https://gmgn.ai/defi/quotation/v1/smartmoney/sol/walletNew/{wallet}?period=7d"
        retries = 5
        
        for attempt in range(retries):
            try:
                self.randomise()
                response = self.sendRequest.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data['msg'] == "success":
                        data = data['data']
                        
                        if skipWallets:
                            if 'buy_30d' in data and isinstance(data['buy_30d'], (int, float)) and data['buy_30d'] > 0:
                                self.totalGrabbed += 1
                                print(f"[🐲] Successfully grabbed data for {wallet} ({self.totalGrabbed})")
                                return self.processWalletData(wallet, data, self.headers, useProxies)
                            else:
                                self.skippedWallets += 1
                                print(f"[🐲] Skipped {self.skippedWallets} wallets", end="\r")
                                return None
                        else:
                            return self.processWalletData(wallet, data, self.headers, useProxies)
            except Exception as e:
                self.totalFailed += 1
                print(f"[🐲] Failed to grab data for {wallet} ({self.totalFailed})")
            time.sleep(1)
        
        if "realized_profit" not in response.text:
            print(f"[🐲] Failed to grab data for {wallet} after {retries} attempts.")
        else:
            print(f"[🐲] Successfully grabbed data for {wallet}")
        return None

    def processWalletData(self, wallet, data, headers, useProxies=False):
        direct_link = f"https://gmgn.ai/sol/address/{wallet}"
        total_profit_percent = f"{data['total_profit_pnl'] * 100:.2f}%" if data['total_profit_pnl'] is not None else "error"
        realized_profit_7d_usd = f"${data['realized_profit_7d']:,.2f}" if data['realized_profit_7d'] is not None else "error"
        realized_profit_30d_usd = f"${data['realized_profit_30d']:,.2f}" if data['realized_profit_30d'] is not None else "error"
        winrate_7d = f"{data['winrate'] * 100:.2f}%" if data['winrate'] is not None else "?"
        sol_balance = f"{float(data['sol_balance']):.2f}" if data['sol_balance'] is not None else "?"
        buy_7d = f"{data['buy_7d']}" if data['buy_7d'] is not None else "?"

        self.randomise()
        winrate_30data = self.sendRequest.get(
            f"https://gmgn.ai/defi/quotation/v1/smartmoney/sol/walletNew/{wallet}?period=30d", 
            headers=self.headers,
            allow_redirects=True
        ).json()['data']
        winrate_30d = f"{winrate_30data['winrate'] * 100:.2f}%" if winrate_30data['winrate'] is not None else "?"

        if "Skipped" in data.get("tags", []):
            return {
                "wallet": wallet,
                "tags": ["Skipped"],
                "directLink": direct_link
            }

        tokenDistro = self.getTokenDistro(wallet, useProxies)

        try:
            tags = data['tags']
        except Exception:
            tags = "?"

        return {
            "wallet": wallet,
            "totalProfitPercent": total_profit_percent,
            "7dUSDProfit": realized_profit_7d_usd,
            "30dUSDProfit": realized_profit_30d_usd,
            "winrate_7d": winrate_7d,
            "winrate_30d": winrate_30d,
            "tags": tags,
            "sol_balance": sol_balance,
            "token_distribution": tokenDistro if tokenDistro else {},
            "directLink": direct_link,
            "buy_7d": buy_7d
        }
    
    def fetchWalletData(self, wallets, threads, skipWallets, useProxies=False):
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.getWalletData, wallet.strip(), skipWallets, useProxies): wallet for wallet in wallets}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    self.results.append(result)

        result_dict = {}
        for result in self.results:
            wallet = result.get('wallet')
            if wallet:
                result_dict[wallet] = result
                result.pop('wallet', None)  
            else:
                print(f"[🐲] Missing 'wallet' key in result: {result}")

        if self.results and 'token_distribution' in self.results[0]:
            token_dist_keys = self.results[0]['token_distribution'].keys()
        else:
            token_dist_keys = []

        identifier = self.shorten(list(result_dict)[0])
        filename = f"{identifier}_{random.randint(1111, 9999)}.csv"

        output_dir = "Dragon/data/Solana/BulkWallet"
        os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist.
        path = os.path.join(output_dir, f"wallets_{filename}")

        with open(path, 'w', newline='') as outfile:
            writer = csv.writer(outfile)

            header = ['Identifier'] + list(next(iter(result_dict.values())).keys())

            if 'token_distribution' in header:
                header.remove('token_distribution')

            header.extend(token_dist_keys)

            writer.writerow(header)

            for key, value in result_dict.items():
                row = [key]
                for h in header[1:]:
                    if h in value:
                        row.append(value[h])
                    elif 'token_distribution' in value and h in value['token_distribution']:
                        row.append(value['token_distribution'][h])
                    else:
                        row.append(None)
                writer.writerow(row)

        print(f"[🐲] Saved data for {len(result_dict)} wallets to {filename}")

if __name__ == '__main__':
    mode = input("Do you want to input one wallet address or multiple (bulk)? (enter 'one' or 'bulk'): ").strip().lower()
    if mode == 'one':
        wallet_input = input("Enter the wallet address: ").strip()
        wallets = [wallet_input]
    elif mode == 'bulk':
        wallet_input = input("Enter multiple wallet addresses separated by commas: ").strip()
        wallets = [w.strip() for w in wallet_input.split(',') if w.strip()]
    else:
        print("Invalid mode. Exiting.")
        exit(1)

    try:
        threads = int(input("Enter the number of threads you'd like to use: "))
    except ValueError:
        print("Invalid number for threads. Please enter an integer.")
        exit(1)

    skip_input = input("Do you want to skip certain wallets? (yes/no): ").strip().lower()
    skipWallets = True if skip_input == "yes" else False

    start_time = time.time()
    checker = BulkWalletChecker()
    checker.fetchWalletData(wallets, threads, skipWallets, useProxies=False)
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
