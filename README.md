# 🐲 Solana Tools

A comprehensive collection of Python tools for analyzing Solana blockchain tokens, wallets, and trading activity using the GMGN.ai API. These tools help traders identify profitable wallets, track early buyers, analyze token holders, and discover copy-trading opportunities on the Solana network.

## 📋 Table of Contents

- [Features](#features)
- [Tools Overview](#tools-overview)
- [Installation](#installation)
- [Usage](#usage)
- [Tool Details](#tool-details)
- [Output](#output)
- [Requirements](#requirements)

## ✨ Features

- **Multi-threaded Processing**: Fast, concurrent data fetching with configurable thread counts
- **Smart Wallet Analysis**: Identify profitable traders and early buyers across multiple tokens
- **Copy Trading Detection**: Find wallets that bought tokens shortly after target addresses
- **Token Analytics**: Analyze top pumping tokens with detailed metrics
- **Comprehensive Data Export**: Save results in JSON, CSV, and TXT formats

## 🛠️ Tools Overview

### 1. **Bulk Wallet Checker** (`bulkwallet-checker/`)
Analyzes multiple Solana wallets in bulk, fetching comprehensive trading statistics including:
- 7-day and 30-day profit/loss
- Win rates
- Token distribution across profit ranges
- SOL balance and trading activity

### 2. **Token Analyzer** (`clean-analyzer/`)
A full-featured CLI tool for analyzing Solana tokens and wallets:
- Real-time SOL price tracking
- Token holder analysis
- Wallet transaction history
- Favorites management for tokens and wallets
- Integration with Solscan API

### 3. **Copy Wallet Finder** (`copywallet-finder/`)
Discovers potential copy-trading wallets by identifying addresses that bought a token immediately after a target wallet:
- Paginates through complete trade history
- Finds the 10 wallets that bought before a specified target
- Useful for identifying smart money followers

### 4. **Early Buyer Finder** (`earlybuyer-finder/`)
Identifies the earliest buyers of tokens and aggregates their data:
- Fetches first buyers (excluding token creators)
- Tracks repeated early buyers across multiple tokens
- Exports realized/unrealized profits
- Finds wallets that consistently buy tokens early

### 5. **Early Wallet Finder** (`earlywallet-finder/`)
Advanced tool that combines early buyer analysis with copy wallet detection:
- Finds top 5 early buyers by realized profit
- For each top buyer, identifies potential copy wallets
- Perfect for discovering successful trading networks

### 6. **GMGN Analyzer** (`gmgn-analyzer/`)
Fetches and displays top pumping tokens from GMGN.ai:
- Customizable display modes (simple/detailed)
- Real-time token metrics
- Market cap, volume, holder count
- Direct links to GMGN token pages

### 7. **Top Holders Analyzer** (`top-holders/`)
Analyzes the top holders of specified tokens:
- Holder profit/loss tracking
- Buy/sell transaction counts
- Profit multipliers
- Identifies whales and repeated holders across tokens

### 8. **Top Traders Analyzer** (`top-traders/`)
Finds the most profitable traders for given tokens:
- Sorts traders by realized profit
- Multi-token analysis
- Tracks trader frequency across tokens
- Exports comprehensive trading statistics

### 9. **Solana Tabulator** (`solana-tabulater/`)
Utility module for interacting with GMGN API and processing wallet data.

### 10. **Timestamp Wallet Finder** (`timestampwallet-finder/`)
Finds wallets that traded specific tokens within custom time ranges.

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/z0d1a/solana-tools.git
cd solana-tools
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies for each tool you want to use:

**For most tools:**
```bash
pip install tls-client fake-useragent requests
```

**For the clean-analyzer:**
```bash
pip install requests rich pyperclip solana
```

## 📖 Usage

### General Pattern

Most tools follow this pattern:

1. Navigate to the tool directory:
```bash
cd [tool-name]
```

2. Run the Python script:
```bash
python [script-name].py
```

3. Follow the interactive prompts

### Example Workflows

#### Find Early Buyers
```bash
cd earlybuyer-finder
python earlybuyer.py
# Enter contract address(es): GZpmXr...
# Enter number of early buyers: 10
# Enter threads: 5
```

#### Analyze Wallet Performance
```bash
cd bulkwallet-checker
python bulkwallet.py
# Choose mode: bulk
# Enter addresses: wallet1,wallet2,wallet3
# Enter threads: 3
# Skip wallets? no
```

#### Discover Copy Wallets
```bash
cd copywallet-finder
python copyfinder.py
# Enter contract address: ABC123...
# Enter target wallet: DEF456...
# Enter threads: 4
```

#### View Top Pumping Tokens
```bash
cd gmgn-analyzer
python analyzer.py
# Display mode: detailed
# Number of tokens: 20
```

## 📊 Tool Details

### Bulk Wallet Checker
**Input:**
- Wallet address(es) - single or comma-separated
- Number of threads
- Skip inactive wallets option

**Output:**
- CSV file in `Dragon/data/Solana/BulkWallet/`
- Columns: Wallet ID, total profit %, 7d/30d USD profit, win rates, SOL balance, token distribution

### Token Analyzer (Clean Analyzer)
**Features:**
- Interactive menu system
- Token and wallet analysis modes
- Favorites management
- Transaction history viewer

**APIs Used:**
- Solscan for token metadata and holder info
- CoinGecko for SOL price

### Copy Wallet Finder
**Process:**
1. Fetches all buy transactions for a token
2. Locates target wallet in transaction history
3. Returns 10 wallets that bought immediately before target

**Output:** Text file with wallet addresses

### Early Buyer Finder
**Input:** Multiple token contract addresses

**Output:**
- `allTopAddresses_[id].txt` - All unique early buyers
- `repeatedEarlyBuyers_[id].txt` - Wallets that bought multiple tokens early
- `EarlyBuyers_[id].json` - Detailed profit data

### GMGN Analyzer
**Display Modes:**
- **Simple:** Symbol, market cap, 5m price change, volume, holders
- **Detailed:** All fields plus created time, last trade, website links, GMGN link

### Top Holders & Top Traders
Both tools:
- Support multi-token analysis
- Export JSON with detailed metrics
- Identify repeated addresses across tokens
- Save unique and repeated addresses separately

## 📁 Output

### Directory Structure
```
data/Solana/
├── BulkWallet/
│   └── wallets_[id].csv
├── CopyWallets/
│   └── wallets_after_[id].txt
├── EarlyBuyers/
│   ├── allTopAddresses_[id].txt
│   ├── repeatedEarlyBuyers_[id].txt
│   └── EarlyBuyers_[id].json
├── TopHolders/
│   ├── allTopAddresses_[id].txt
│   ├── repeatedTopHolders_[id].txt
│   └── TopHolders_[id].json
└── TopTraders/
    ├── allTopAddresses_[id].txt
    ├── repeatedTopTraders_[id].txt
    └── topTraders_[id].json
```

## 🔧 Requirements

### Core Dependencies
```
tls-client>=0.2.0
fake-useragent>=1.4.0
requests>=2.31.0
```

### Additional (for specific tools)
```
rich>=13.0.0          # clean-analyzer
pyperclip>=1.8.2      # clean-analyzer
solana>=0.30.0        # clean-analyzer
```

## ⚙️ Configuration

### Thread Count
- Recommended: 3-5 threads for most tools
- Higher thread counts may trigger rate limits
- Tools implement randomized user agents and TLS fingerprints to avoid detection

### API Rate Limiting
All tools implement:
- Retry logic (typically 3-5 attempts)
- Sleep delays between requests
- Randomized headers and user agents
- TLS client fingerprint randomization

## 🎯 Use Cases

1. **Smart Money Tracking**: Identify consistently profitable early buyers
2. **Copy Trading**: Find wallets that follow successful traders
3. **Whale Watching**: Track large holders across multiple tokens
4. **Token Research**: Analyze holder distribution and top trader profitability
5. **Market Sentiment**: Monitor top pumping tokens in real-time

## ⚠️ Disclaimer

These tools are for educational and research purposes only. Always conduct your own research before making trading decisions. The Solana blockchain and DeFi markets are highly volatile and risky.

## 📝 License

MIT License - Feel free to use and modify these tools for your own purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📧 Contact

Created by [@z0d1a](https://github.com/z0d1a)

---

**Happy Trading! 🚀**
