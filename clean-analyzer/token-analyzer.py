import requests
import json
import os
import sys
import time
import pyperclip
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress
from datetime import datetime
import asyncio
from solana.rpc.async_api import AsyncClient  # In case you want to use async calls

console = Console()

# -------------------------------
# Global Variables & File Names
# -------------------------------
SOLSCAN_API = "https://public-api.solscan.io"
FAVORITES_FILE = "favorite_tokens.json"
WALLET_FAVORITES_FILE = "favorite_wallets.json"

# -------------------------------
# Utility Functions
# -------------------------------

def clear_screen():
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')

def display_ascii_art():
    ascii_art = """
[bold cyan]
  ____       _            _           
 / ___|  ___| | ___   ___| | _____ _ __ 
 \___ \ / _ \ |/ _ \ / __| |/ / _ \ '__|
  ___) |  __/ | (_) | (__|   <  __/ |   
 |____/ \___|_|\___/ \___|_|\_\___|_|   v.1.0
 
          Solana Analyzer
          by IbnHindi
[/bold cyan]
    """
    print(ascii_art)

def truncate_address(address):
    # Truncate long Solana addresses for display purposes
    if len(address) <= 12:
        return address
    return f"{address[:6]}...{address[-6:]}"

# -------------------------------
# Solana Price & Token Data
# -------------------------------

def fetch_sol_price():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
        response.raise_for_status()
        data = response.json()
        return data['solana']['usd']
    except Exception as e:
        console.print(f"[bold red]Error fetching SOL price: {e}[/bold red]")
        return None

def get_token_info(token_address):
    """
    Fetch basic token metadata from Solscan.
    (This endpoint returns JSON data such as token name, symbol, decimals, etc.)
    """
    url = f"{SOLSCAN_API}/token/meta?tokenAddress={token_address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "name": data.get("name", "Unknown Token"),
            "symbol": data.get("symbol", "UNKNOWN"),
            "decimals": data.get("decimals", 0)
        }
    except Exception as e:
        console.print(f"[bold yellow]Warning: Could not fetch token info: {e}[/bold yellow]")
        return {"name": "Unknown Token", "symbol": "UNKNOWN", "decimals": 0}

def fetch_top_token_holders(token_address):
    """
    Attempt to fetch top token holders via Solscan.
    (Endpoint and returned data structure may vary; adjust as needed.)
    """
    url = f"{SOLSCAN_API}/token/holders?tokenAddress={token_address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Assume the returned JSON has a key "data" with a list of holder records.
        top_holders = data.get("data", [])[:10]
        result = []
        for holder in top_holders:
            # Here we assume each holder dict contains an 'owner' field and (optionally) a 'share'
            result.append({
                'address': holder.get("owner", "Unknown"),
                'share': holder.get("share", "N/A")
            })
        return result
    except Exception as e:
        console.print(f"[bold red]Error fetching top token holders: {e}[/bold red]")
        return None

# -------------------------------
# Wallet Data & Transaction Analysis
# -------------------------------

def get_wallet_balance(address):
    """
    Fetch the wallet SOL balance from Solscan.
    (This example assumes the endpoint returns a JSON with a "lamports" field.)
    """
    url = f"{SOLSCAN_API}/account/{address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        lamports = data.get("lamports", 0)
        sol_balance = lamports / 1e9  # Convert lamports to SOL
        return sol_balance
    except Exception as e:
        console.print(f"[bold red]Error fetching wallet balance: {e}[/bold red]")
        return None

def fetch_token_transfers(address, start=0, limit=30):
    """
    Fetch recent transactions (which may include token transfers) for the given wallet address using Solscan.
    (Adjust the query parameters as needed based on API documentation.)
    """
    url = f"{SOLSCAN_API}/account/transactions?account={address}&limit={limit}&offset={start}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Assume the response is a list of transaction objects
        transactions = response.json()
        return transactions
    except Exception as e:
        console.print(f"[bold red]Error fetching transactions: {e}[/bold red]")
        return None

def display_transactions(transactions, wallet_address, start=0):
    """
    Display a table of token transfer–related transactions.
    (This example assumes each transaction includes a 'txHash', 'blockTime', and optionally a list
     'tokenTransfers' with details about transfers.)
    """
    table = Table(title=f"Token Transfer Events (SOLANA) - Showing {start+1} to {start+len(transactions)}")
    table.add_column("#", style="cyan")
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Source", style="yellow")
    table.add_column("Destination", style="yellow")
    table.add_column("Token", style="green")
    table.add_column("Amount", style="blue", justify="right")
    table.add_column("Tx Hash", style="dim blue")

    for index, tx in enumerate(transactions, start=start+1):
        # Convert blockTime (assumed to be in seconds) to a date string
        block_time = tx.get('blockTime', 0)
        date = datetime.fromtimestamp(block_time) if block_time else "Unknown"

        # For demonstration, we assume the transaction dict may include a key 'tokenTransfers'
        # which is a list. We display the first transfer (if available).
        token_transfer = (tx.get('tokenTransfers') or [{}])[0]
        source = token_transfer.get('source', 'Unknown')
        destination = token_transfer.get('destination', 'Unknown')
        token_symbol = token_transfer.get('tokenSymbol', 'N/A')
        amount = token_transfer.get('tokenAmount', "N/A")

        # Determine type based on whether the wallet is the receiver or sender.
        tx_type = "[green]IN[/green]" if destination == wallet_address else "[red]OUT[/red]"
        table.add_row(
            str(index),
            date if isinstance(date, str) else date.strftime("%b %d %H:%M"),
            tx_type,
            truncate_address(source),
            truncate_address(destination),
            token_symbol,
            str(amount),
            truncate_address(tx.get('txHash', 'Unknown'))
        )
    console.print(table)
    return transactions

def display_transaction_details(tx, wallet_address):
    """
    Fetch and display detailed transaction information for a given transaction hash using Solscan.
    (This example calls an endpoint that returns transaction details.
     Adjust the endpoint and fields based on available documentation.)
    """
    tx_hash = tx.get("txHash", "Unknown")
    url = f"{SOLSCAN_API}/transaction/{tx_hash}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        tx_data = response.json()

        table = Table(title=f"Transaction Details for {tx_hash}")
        table.add_column("Field", style="cyan", width=30)
        table.add_column("Value", style="yellow")

        table.add_row("Slot", str(tx_data.get("slot", "Unknown")))
        block_time = tx_data.get("blockTime")
        if block_time:
            table.add_row("Block Time", datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Fee", str(tx_data.get("fee", "Unknown")))
        explorer_link = f"https://solscan.io/tx/{tx_hash}"
        table.add_row("Explorer Link", explorer_link)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error fetching transaction details: {e}[/bold red]")

def display_wallet_balance(address):
    balance = get_wallet_balance(address)
    if balance is not None:
        console.print(f"\n[bold green]Current Wallet Balance:[/bold green] {balance:.4f} SOL")
    else:
        console.print("\n[bold red]Failed to fetch wallet balance.[/bold red]")

def wallet_transaction_analysis():
    address = Prompt.ask("\nEnter the Solana wallet address")
    start = 0
    limit = 30
    all_transactions = []

    while True:
        with console.status("[bold green]Fetching token transfer events..."):
            transactions = fetch_token_transfers(address, start, limit)

        if transactions:
            all_transactions.extend(transactions)
            display_transactions(transactions, address, start)
            display_wallet_balance(address)

            while True:
                action = Prompt.ask("\nEnter a transaction number to view details, 'm' for more transactions, or 'c' to continue")
                if action.lower() == 'c':
                    return
                elif action.lower() == 'm':
                    start += limit
                    break
                elif action.isdigit():
                    tx_index = int(action) - 1
                    if 0 <= tx_index < len(all_transactions):
                        tx = all_transactions[tx_index]
                        display_transaction_details(tx, address)
                    else:
                        console.print("[bold red]Invalid transaction number.[/bold red]")
                else:
                    console.print("[bold red]Invalid input. Please enter a number, 'm', or 'c'.[/bold red]")
        else:
            if start == 0:
                console.print("[bold red]No token transfer events found or error occurred.[/bold red]")
            else:
                console.print("[bold yellow]No more transactions to display.[/bold yellow]")
            break

# -------------------------------
# Favorites Management (Tokens)
# -------------------------------

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_favorites(favorites):
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favorites, f, indent=2)

def add_to_favorites_token(favorites, token_address, token_name):
    favorites[token_address] = {
        'name': token_name,
        'added_time': datetime.now().isoformat()
    }
    save_favorites(favorites)
    console.print(f"[bold green]Added token {token_name} to favorites![/bold green]")

def remove_from_favorites_token(favorites, token_address):
    if token_address in favorites:
        token_name = favorites.pop(token_address)['name']
        save_favorites(favorites)
        console.print(f"[bold yellow]Removed token {token_name} from favorites.[/bold yellow]")
    else:
        console.print("[bold red]Token not found in favorites.[/bold red]")

def display_favorite_tokens(favorites):
    if not favorites:
        console.print("[yellow]No favorite tokens saved yet.[/yellow]")
        return
    table = Table(title="Favorite Tokens")
    table.add_column("#", style="cyan")
    table.add_column("Address", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Added Time", style="green")
    for i, (address, data) in enumerate(favorites.items(), 1):
        added_time = datetime.fromisoformat(data['added_time']).strftime("%Y-%m-%d %H:%M")
        table.add_row(str(i), address, data['name'], added_time)
    console.print(table)

def analyze_token():
    token_address = Prompt.ask("\n[bold cyan]Enter the Solana token address[/bold cyan]")
    with Progress() as progress:
        task = progress.add_task("[green]Fetching token data...", total=100)
        # For demonstration, we call get_token_info (which uses Solscan)
        token_info = get_token_info(token_address)
        progress.update(task, completed=100)

    if token_info:
        table = Table(title="Token Information")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_row("Name", token_info.get("name", "Unknown Token"))
        table.add_row("Symbol", token_info.get("symbol", "UNKNOWN"))
        table.add_row("Decimals", str(token_info.get("decimals", "N/A")))
        table.add_row("Address", token_address)
        console.print(table)

        # Fetch and display top token holders if available
        top_holders = fetch_top_token_holders(token_address)
        if top_holders:
            holders_table = Table(title="Top 10 Token Holders")
            holders_table.add_column("Rank", style="cyan", justify="right")
            holders_table.add_column("Address", style="green")
            holders_table.add_column("Share", style="magenta", justify="right")
            for i, holder in enumerate(top_holders, 1):
                holders_table.add_row(str(i), holder['address'], str(holder['share']))
            console.print(holders_table)
        else:
            console.print("[yellow]No token holder information available.[/yellow]")

        # Ask user to add token to favorites if not already saved
        favorites = load_favorites()
        if token_address not in favorites:
            if Prompt.ask("[bold cyan]Add this token to favorites?[/bold cyan]", choices=["y", "n"], default="n") == "y":
                add_to_favorites_token(favorites, token_address, token_info.get("name", "Unknown Token"))
    else:
        console.print("[bold red]Failed to fetch token data.[/bold red]")

# -------------------------------
# Favorites Management (Wallets)
# -------------------------------

def load_favorite_wallets():
    if os.path.exists(WALLET_FAVORITES_FILE):
        with open(WALLET_FAVORITES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_favorite_wallets(favorites):
    with open(WALLET_FAVORITES_FILE, 'w') as f:
        json.dump(favorites, f)

def add_to_favorite_wallets(favorites, address):
    nickname = Prompt.ask("Enter a nickname for this wallet (optional)", default="")
    favorites[address] = {'nickname': nickname}
    save_favorite_wallets(favorites)
    console.print(f"[bold green]Added {address} to favorite wallets with nickname: {nickname or 'N/A'}![/bold green]")

def remove_from_favorite_wallets(favorites, address):
    if address in favorites:
        data = favorites.pop(address)
        save_favorite_wallets(favorites)
        console.print(f"[bold yellow]Removed {address} from favorite wallets.[/bold yellow]")
    else:
        console.print("[bold red]Wallet address not found in favorites.[/bold red]")

def display_favorite_wallets(favorites):
    if not favorites:
        console.print("[yellow]No favorite wallets saved yet.[/yellow]")
        return
    table = Table(title="Favorite Wallets")
    table.add_column("#", style="cyan")
    table.add_column("Address", style="cyan")
    table.add_column("Nickname", style="green")
    for i, (address, data) in enumerate(favorites.items(), 1):
        nickname = data.get('nickname', 'N/A')
        table.add_row(str(i), address, nickname)
    console.print(table)

# -------------------------------
# Main Menu
# -------------------------------

def main():
    clear_screen()
    display_ascii_art()

    # Fetch and display SOL price
    sol_price = fetch_sol_price()
    if sol_price:
        console.print(f"\n[bold yellow]SOL Price: ${sol_price:,.2f} USD[/bold yellow]\n")
    else:
        console.print("\n[bold red]Unable to fetch SOL price.[/bold red]\n")

    favorites_tokens = load_favorites()
    favorites_wallets = load_favorite_wallets()

    while True:
        console.print("\n[bold cyan]Main Menu:[/bold cyan]")
        console.print("[bold white]1.[/bold white] [yellow]Analyze Token[/yellow]")
        console.print("[bold white]2.[/bold white] [yellow]Analyze Wallet[/yellow]")
        console.print("[bold white]3.[/bold white] [yellow]Favorite Tokens Management[/yellow]")
        console.print("[bold white]4.[/bold white] [yellow]Favorite Wallets Management[/yellow]")
        console.print("[bold white]5.[/bold white] [yellow]Exit[/yellow]")

        choice = Prompt.ask("[bold cyan]Enter your choice[/bold cyan]")

        if choice == "1":
            clear_screen()
            analyze_token()
            input("\nPress Enter to return to the main menu...")
            clear_screen()
        elif choice == "2":
            clear_screen()
            wallet_transaction_analysis()
            input("\nPress Enter to return to the main menu...")
            clear_screen()
        elif choice == "3":
            clear_screen()
            display_favorite_tokens(favorites_tokens)
            console.print("\n[bold cyan]Favorite Token Options:[/bold cyan]")
            console.print("[bold white]1.[/bold white] [yellow]Analyze a favorite token[/yellow]")
            console.print("[bold white]2.[/bold white] [yellow]Remove a favorite token[/yellow]")
            console.print("[bold white]3.[/bold white] [yellow]Return to main menu[/yellow]")
            fav_choice = Prompt.ask("[bold cyan]Enter your choice[/bold cyan]")
            if fav_choice == "1":
                token_number = Prompt.ask("[bold cyan]Enter the number of the favorite token to analyze[/bold cyan]")
                if token_number.isdigit():
                    index = int(token_number) - 1
                    if 0 <= index < len(favorites_tokens):
                        address = list(favorites_tokens.keys())[index]
                        # For analysis, we reuse our analyze_token function (or simply display info)
                        token_info = get_token_info(address)
                        table = Table(title="Token Information")
                        table.add_column("Field", style="cyan")
                        table.add_column("Value", style="yellow")
                        table.add_row("Name", token_info.get("name", "Unknown Token"))
                        table.add_row("Symbol", token_info.get("symbol", "UNKNOWN"))
                        table.add_row("Decimals", str(token_info.get("decimals", "N/A")))
                        table.add_row("Address", address)
                        console.print(table)
                        input("\nPress Enter to return to the favorite menu...")
                    else:
                        console.print("[bold red]Invalid token number.[/bold red]")
                else:
                    console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
            elif fav_choice == "2":
                token_number = Prompt.ask("[bold cyan]Enter the number of the favorite token to remove[/bold cyan]")
                if token_number.isdigit():
                    index = int(token_number) - 1
                    if 0 <= index < len(favorites_tokens):
                        address = list(favorites_tokens.keys())[index]
                        remove_from_favorites_token(favorites_tokens, address)
                    else:
                        console.print("[bold red]Invalid token number.[/bold red]")
                else:
                    console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
            elif fav_choice == "3":
                pass
            else:
                console.print("[bold red]Invalid choice.[/bold red]")
            clear_screen()
        elif choice == "4":
            clear_screen()
            display_favorite_wallets(favorites_wallets)
            console.print("\n[bold cyan]Favorite Wallet Options:[/bold cyan]")
            console.print("[bold white]1.[/bold white] [yellow]Analyze a favorite wallet[/yellow]")
            console.print("[bold white]2.[/bold white] [yellow]Remove a favorite wallet[/yellow]")
            console.print("[bold white]3.[/bold white] [yellow]Return to main menu[/yellow]")
            fav_choice = Prompt.ask("[bold cyan]Enter your choice[/bold cyan]")
            if fav_choice == "1":
                wallet_number = Prompt.ask("[bold cyan]Enter the number of the favorite wallet to analyze[/bold cyan]")
                if wallet_number.isdigit():
                    index = int(wallet_number) - 1
                    if 0 <= index < len(favorites_wallets):
                        address = list(favorites_wallets.keys())[index]
                        wallet_transaction_analysis_for_fav(address)
                    else:
                        console.print("[bold red]Invalid wallet number.[/bold red]")
                else:
                    console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
            elif fav_choice == "2":
                wallet_number = Prompt.ask("[bold cyan]Enter the number of the favorite wallet to remove[/bold cyan]")
                if wallet_number.isdigit():
                    index = int(wallet_number) - 1
                    if 0 <= index < len(favorites_wallets):
                        address = list(favorites_wallets.keys())[index]
                        remove_from_favorite_wallets(favorites_wallets, address)
                    else:
                        console.print("[bold red]Invalid wallet number.[/bold red]")
                else:
                    console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
            elif fav_choice == "3":
                pass
            else:
                console.print("[bold red]Invalid choice.[/bold red]")
            clear_screen()
        elif choice == "5":
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")

    console.print("[bold green]Thank you for using the Solana Analyzer![/bold green]")

def wallet_transaction_analysis_for_fav(address):
    """
    A helper function to analyze a favorite wallet (without prompting for address).
    """
    start = 0
    limit = 30
    all_transactions = []

    while True:
        with console.status("[bold green]Fetching token transfer events..."):
            transactions = fetch_token_transfers(address, start, limit)

        if transactions:
            all_transactions.extend(transactions)
            display_transactions(transactions, address, start)
            display_wallet_balance(address)

            while True:
                action = Prompt.ask("\nEnter a transaction number to view details, 'm' for more transactions, or 'c' to continue")
                if action.lower() == 'c':
                    return
                elif action.lower() == 'm':
                    start += limit
                    break
                elif action.isdigit():
                    tx_index = int(action) - 1
                    if 0 <= tx_index < len(all_transactions):
                        tx = all_transactions[tx_index]
                        display_transaction_details(tx, address)
                    else:
                        console.print("[bold red]Invalid transaction number.[/bold red]")
                else:
                    console.print("[bold red]Invalid input. Please enter a number, 'm', or 'c'.[/bold red]")
        else:
            if start == 0:
                console.print("[bold red]No token transfer events found or error occurred.[/bold red]")
            else:
                console.print("[bold yellow]No more transactions to display.[/bold yellow]")
            break

if __name__ == "__main__":
    main()
