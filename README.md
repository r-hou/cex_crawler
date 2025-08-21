# Cryptocurrency Exchange Announcements Scraper

A comprehensive cryptocurrency exchange announcement scraper that automatically collects and analyzes listing/delisting announcements from 15+ major exchanges using AI-powered content analysis.

## 🚀 Features

- **Multi-Exchange Support**: Scrapes announcements from 15+ major exchanges including Binance, Bybit, OKX, Gate.io, etc.
- **AI-Powered Analysis**: Uses DeepSeek AI to extract listing/delisting information from announcements
- **Organized Output**: Saves results in organized directory structure (`output/{exchange_name}/`)
- **Debug Mode**: Configurable processing limits for development and testing
- **Browser Automation**: Uses Playwright for dynamic content scraping
- **CSV Export**: Generates consolidated CSV reports of all announcements

## 📋 Supported Exchanges

### Spot Trading Exchanges
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

### Futures Trading Exchanges
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

## 🛠 Installation & Setup

### Prerequisites
- macOS (tested on macOS 10.15+)
- Python 3.8 or higher
- Git

### Step 1: Install Python and Dependencies

#### Option A: Using Homebrew (Recommended for Mac)
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python

# Verify installation
python3 --version
```

#### Option B: Using Conda
```bash
# Install Miniconda
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh

# Create and activate environment
conda create -n exchange-scraper python=3.10
conda activate exchange-scraper
```

### Step 2: Clone and Setup Project

```bash
# Navigate to your preferred directory
cd ~/Downloads

# If you don't have the project yet, create the directory structure
# (Skip this if you already have the project)
mkdir exchange-scraper
cd exchange-scraper

# Install required packages
pip install -r requirements.txt

# Install Playwright browsers (required for web scraping)
playwright install
```

### Step 3: Configure API Keys

You need a DeepSeek AI API key for announcement analysis.

#### Option A: Environment Variable (Recommended)
```bash
# Add to your shell profile (~/.zshrc or ~/.bash_profile)
echo 'export OPENAI_API_KEY="your-deepseek-api-key-here"' >> ~/.zshrc

# Reload your shell configuration
source ~/.zshrc
```

#### Option B: Direct Configuration
Edit the individual exchange files and add your API key directly:
```python
analyzer = DeepSeekAnalyzer(api_key="your-deepseek-api-key-here")
```

### Step 4: Verify Installation

```bash
# Test if all dependencies are installed
python3 -c "import requests, playwright, beautifulsoup4, openai; print('All dependencies installed successfully!')"

# Test Playwright installation
playwright --version
```

## 🚀 Usage

### Basic Usage

#### Run All Exchanges
```bash
# Run the main scraper (processes all exchanges)
python3 main.py
```

#### Run Individual Exchange
```bash
# Run specific exchange scraper
python3 -m exchange.binance
python3 -m exchange.bybit
python3 -m exchange.mexc
# ... etc for other exchanges
```

### Debug Mode Configuration

The scraper includes a debug mode that limits processing to a specified number of announcements per exchange:

```python
# In main.py - modify these settings:
DEBUG_MODE = True        # Enable/disable debug mode
MAX_DEBUG_SIZE = 3      # Maximum announcements to process per exchange in debug mode
```

### Advanced Usage Examples

#### 1. Run with Custom Debug Settings
```bash
# Edit main.py to change debug settings, then run
python3 main.py
```

#### 2. Process Specific Exchange Types
```bash
# Process only spot exchanges (modify main.py to comment out futures exchanges)
python3 main.py
```

#### 3. Generate CSV Report Only
```python
# Run this in Python to generate CSV from existing data
from main import save_accoucements_to_csv
save_accoucements_to_csv()
```

## 📁 Output Structure

The scraper creates the following directory structure:

```
project/
├── output/
│   ├── binance/
│   │   ├── binance_12345.txt    # Raw announcement text
│   │   ├── binance_12345.json   # AI analysis results
│   │   └── ...
│   ├── bybit/
│   │   ├── bybit_67890.txt
│   │   ├── bybit_67890.json
│   │   └── ...
│   └── [other_exchanges]/
│       ├── *.txt files          # Raw announcement content
│       └── *.json files         # AI analysis with extracted data
├── announcements.csv            # Consolidated CSV report
└── ...
```

### Output File Formats

#### Text Files (.txt)
Contains the raw announcement content scraped from the exchange.

#### JSON Files (.json)
Contains AI analysis results with extracted information:
```json
[
  {
    "type": "listing",
    "symbol": "PEPE",
    "time": "2024-01-15 10:00:00",
    "exchange": "binance",
    "file": "path/to/source/file.txt"
  }
]
```

## 🔧 Configuration

### Debug Mode Settings
```python
# In main.py
DEBUG_MODE = True          # Enable debug mode
MAX_DEBUG_SIZE = 3        # Process only 3 announcements per exchange
```

### Exchange Selection
```python
# In main.py - comment/uncomment exchanges as needed
SPOT_CEX = ["binance", "bingx", "bitget", ...]
FUTURES_CEX = ["binance", "bingx", "bitunix", ...]
```

### Individual Exchange Settings
Each exchange scraper can be configured with:
```python
scraper = ExchangeScraper(
    analyzer=analyzer,
    debug=True,          # Enable debug mode for this scraper
    max_size=5          # Maximum announcements to process
)
```

## 🔍 Monitoring and Logs

### Check Processing Status
The scraper provides detailed console output:
```
=== Processing Binance ===
✓ Found 25 announcements
✓ Processing announcement 1/25: "New Listing: PEPE/USDT"
✓ Successfully analyzed and saved
Debug mode: Reached max_size limit (3), stopping...
=== Binance scraping completed: 3 announcements processed ===
```

### Debug Output Files
- Check `output/{exchange}/` for individual results
- Review `announcements.csv` for consolidated data
- Monitor console output for errors or completion status

## ❗ Troubleshooting

### Common Issues on Mac

#### 1. Python Command Not Found
```bash
# Try using python3 instead of python
python3 --version

# If still not found, install via Homebrew
brew install python
```

#### 2. Playwright Installation Issues
```bash
# Install Playwright browsers
playwright install

# If permission issues:
sudo playwright install
```

#### 3. SSL Certificate Errors
```bash
# Update certificates
/Applications/Python\ 3.x/Install\ Certificates.command
```

#### 4. Permission Denied Errors
```bash
# Make sure you have write permissions
chmod +w ~/Downloads/major
```

#### 5. API Key Issues
```bash
# Verify your API key is set
echo $OPENAI_API_KEY

# Test API connectivity
python3 -c "from deepseek_analyzer import DeepSeekAnalyzer; print('API key working')"
```

### Debug Mode Not Working
- Ensure `DEBUG_MODE = True` in main.py
- Check that `max_size` parameter is set correctly in individual scrapers
- Verify console output shows "Debug mode: Reached max_size limit" messages

### No Output Files Generated
1. Check console output for error messages
2. Verify API key is correctly configured
3. Ensure output directory has write permissions
4. Test individual exchange scrapers first

### Playwright Browser Issues
```bash
# Reinstall browsers
playwright install --force

# Check browser installation
playwright list
```

## 📝 Development

### Adding New Exchanges
1. Create new scraper class inheriting from `BaseScraper`
2. Implement exchange-specific methods
3. Add to main.py import statements and exchange lists
4. Test with debug mode enabled

### Modifying AI Analysis
Edit the analysis prompt in `deepseek_analyzer.py` to customize extraction logic.

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Ensure all dependencies are correctly installed
3. Test individual components (API key, Playwright, etc.)
4. Review console output for specific error messages

## 🔄 Updates

The scraper is designed to be easily maintainable:
- Exchange-specific logic is isolated in individual files
- Common functionality is shared through `BaseScraper`
- Configuration is centralized in `main.py`
- Debug mode allows for safe testing of changes