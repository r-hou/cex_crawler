# Exchange Scrapers Refactoring Project

## Background
A cryptocurrency exchange scraper project with multiple exchange classes in the `exchange/` folder. Each exchange scraper has many duplicated functions and patterns that need to be refactored into a base class for better maintainability.

## Current Issues Identified

### 1. Code Duplication
- **Duplicate browser initialization code** - Almost identical `init_browser()` methods across multiple scrapers (BingxScraper, MexcScraper, WeexScraper, BlofinScraper, BitunixScraper, etc.)
- **Repeated HTTP headers setup** - Similar header configurations in multiple classes
- **Duplicate file saving logic** - Same pattern for saving JSON and text files across scrapers
- **Common utility methods** - Methods like `random_delay()`, `simulate_human_behavior()`, browser cleanup, etc.
- **Similar constructor patterns** - Most classes take a `DeepSeekAnalyzer` instance and set up similar instance variables

### 2. File Structure Issues
Currently, JSON and text files are saved directly to `announcements_json/` and `announcements_text/` folders. 

**Current Structure:**
```
project/
├── announcements_json/
│   ├── binance_*.json
│   ├── bingx_*.json
│   └── ...
└── announcements_text/
    ├── binance_*.txt
    ├── bingx_*.txt
    └── ...
```

**Target Structure:**
```
project/
└── output/
    ├── binance/
    │   ├── binance_*.json
    │   └── binance_*.txt
    ├── bingx/
    │   ├── bingx_*.json
    │   └── bingx_*.txt
    └── [other_exchanges]/
        ├── *.json files
        └── *.txt files
```

## Refactoring Requirements

### 1. Create Base Exchange Scraper Class


### 2. Update File Management System
Implement the new directory structure:
- Create `output/` folder if it doesn't exist
- Create exchange-specific subfolders (e.g., `output/binance/`, `output/bingx/`)
- Update all file saving logic to use the new structure
- Ensure both JSON and text files for the same announcement go to the same exchange folder

### 3. Refactor Existing Exchange Classes
For each exchange scraper:
- Inherit from Base Exchange Scraper Class
- Remove duplicated code (browser init, common utilities, file saving)
- Keep only exchange-specific logic (URL patterns, parsing methods, API calls)
- Update file paths to use the new directory structure

### 4. Update Main Integration
Modify `main.py` to:
- Update the CSV generation function to work with the new directory structure
- Ensure the `save_accoucements_to_csv()` function searches in `output/*/` folders
- Maintain backward compatibility where possible


### File Naming Convention:
- JSON files: `{exchange_name}_{file_id}.json`
- Text files: `{exchange_name}_{file_id}.txt`
- Save both files in `output/{exchange_name}/` folder

## Current Exchange Support

### Spot Trading Exchanges:
- Binance
- BingX
- Bitget
- Bybit
- Gate.io
- MEXC
- LBank
- Upbit
- Bithumb
- CoinEx

### Futures Trading Exchanges:
- Binance
- BingX
- Bitunix
- Blofin
- Bitget
- BTCC
- Bybit
- Gate.io
- MEXC
- OKX
- LBank
- WEEX


You also need to add a debug switch, if it's on, only scrap MAX_SIZE announcements for each exchange

