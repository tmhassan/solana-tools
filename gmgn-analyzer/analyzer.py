import json
import time
import random
import os
import tls_client
from datetime import datetime
from fake_useragent import UserAgent

class SolanaCoinAnalyzer:
    def __init__(self):
        # Create a tls_client session with a default identifier.
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s

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
        # Generate a random user agent (omitting the 'os' parameter for compatibility).
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

    def get_top_pumping_tokens(self, limit):
        """
        Fetches the top pumping tokens on Solana using the GMGN API.
        The limit is clamped between 1 and 50.
        """
        limit = min(50, max(1, limit))
        url = f"https://gmgn.ai/defi/quotation/v1/rank/sol/pump?limit={limit}&orderby=progress&direction=desc&pump=true"
        self.randomise()
        try:
            response = self.sendRequest.get(url, headers=self.headers, allow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'data' in data:
                    if isinstance(data['data'], dict):
                        # Look for the first list in the data dict.
                        for key, value in data['data'].items():
                            if isinstance(value, list):
                                return value
                        print("🐲 No list found in the 'data' dictionary")
                    else:
                        print(f"🐲 'data' value is not a dict, it's a {type(data['data'])}")
                else:
                    print("🐲 Unexpected data format in the API response")
            else:
                print(f"🐲 API request failed with status code: {response.status_code}")
        except Exception as e:
            print(f"🐲 An error occurred while fetching data: {e}")
        return []

    def format_token_info(self, token, mode="detailed"):
        """
        Formats the token information for display.
        For detailed mode, shows all available details including a GMGN link.
        For simple mode, shows a subset of details.
        """
        try:
            created_time = datetime.fromtimestamp(token.get('created_timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            created_time = "N/A"
        try:
            last_trade_time = datetime.fromtimestamp(token.get('last_trade_timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            last_trade_time = "N/A"
        
        symbol = token.get('symbol', 'N/A')
        name = token.get('name', 'N/A')
        
        price = token.get('price', None)
        price_str = f"${price:.8f}" if isinstance(price, (int, float)) else "N/A"
        
        # Try several keys for market cap.
        market_cap = token.get('usd_market_cap') or token.get('market_cap') or token.get('cap')
        try:
            market_cap = float(market_cap)
            market_cap_str = f"${market_cap:,.2f}"
        except Exception:
            market_cap_str = "N/A"
        
        # Try several keys for volume (1h).
        volume = token.get('volume_1h') or token.get('volume')
        try:
            volume = float(volume)
            volume_str = f"${volume:,.2f}"
        except Exception:
            volume_str = "N/A"
            
        progress = token.get('progress', None)
        progress_str = f"{progress:.2%}" if isinstance(progress, (int, float)) else "N/A"
        
        holder_count = token.get('holder_count', 'N/A')
        price_change_percent5m = token.get('price_change_percent5m', 'N/A')
        website = token.get('website', 'N/A')
        twitter = token.get('twitter', 'N/A')
        telegram = token.get('telegram', 'N/A')
        
        # First try to get the gmgn link from the token.
        gmgn_link = token.get('link', {}).get('gmgn')
        if not gmgn_link:
            # If not present, try to construct it from the token's address.
            token_address = token.get('address')
            if token_address:
                gmgn_link = f"https://gmgn.ai/sol/token/{token_address}"
            else:
                gmgn_link = "N/A"
        
        if mode.lower() == "simple":
            # Simple mode shows a subset of fields.
            return (f"Symbol: {symbol}\n"
                    f"Market Cap: {market_cap_str}\n"
                    f"Price Change (5m): {price_change_percent5m}%\n"
                    f"Volume (1h): {volume_str}\n"
                    f"Holder Count: {holder_count}\n")
        else:
            # Detailed mode shows all fields plus the GMGN link.
            return (f"Symbol: {symbol}\n"
                    f"Name: {name}\n"
                    f"Price: {price_str}\n"
                    f"Market Cap: {market_cap_str}\n"
                    f"Created: {created_time}\n"
                    f"Last Trade: {last_trade_time}\n"
                    f"Holder Count: {holder_count}\n"
                    f"Volume (1h): {volume_str}\n"
                    f"Price Change (5m): {price_change_percent5m}%\n"
                    f"Website: {website}\n"
                    f"GMGN Link: {gmgn_link}\n"
                    f"--------------------")
    
def main():
    print("🐲 GMGN Solana Coin Analyzer")
    display_mode = input("How do you want the information displayed (simple or detailed)? ").strip().lower()
    try:
        limit = int(input("Enter the number of top pumping tokens to retrieve (max 50): "))
    except ValueError:
        print("🐲 Invalid input. Using default limit of 10.")
        limit = 10

    analyzer = SolanaCoinAnalyzer()
    tokens = analyzer.get_top_pumping_tokens(limit)
    if tokens:
        print("🐲 Top Pumping Tokens:")
        for idx, token in enumerate(tokens, 1):
            formatted = analyzer.format_token_info(token, mode=display_mode)
            print(f"{idx}.")
            print(formatted)
    else:
        print("🐲 No token data retrieved.")

if __name__ == '__main__':
    main()
