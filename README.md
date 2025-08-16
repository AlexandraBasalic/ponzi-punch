# 🔥 AUDITOR RADAR  
*"Because nobody audits the auditors"*  

**What this does**:  
- Scrapes SEC filings to find out who's signing off on corporate financials  
- Flags shady accounting firms (the kind that "miss" $10B "accidentally")  
- Spits out everything in CSV format so you can embarrass the right people  

**Why I built this**:  
After seeing the same Big Four rubber-stamp every financial disaster since 2008, I wanted a way to:  
1. Catch auditor switches *before* the bankruptcy filing  
2. Spot the next Friehling & Horowitz (Madoff's "auditors")  
3. Automate what the SEC should’ve done decades ago  

---


### 🚀 QUICK START  
1. **Run the scanner** (requires Python 3.10+):  
   ```bash
   git clone https://github.com/[YOUR_USERNAME]/auditor-radar.git
   cd auditor-radar
   pip install -r requirements.txt
   python scam_scanner.py
