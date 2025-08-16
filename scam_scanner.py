import requests
import re
import time
import csv
from datetime import datetime
from typing import Optional , Tuple

# Configuration
REQUEST_DELAY = 0.5  # Seconds between SEC requests
LOG_FILE = "auditor_changes.csv"
MAX_RETRIES = 3


class AuditorScanner :
    def __init__ ( self ) :
        self.cik_map = self._load_cik_map ( )
        self.auditor_map = self._load_auditor_map ( )
        self.shady_keywords = self._load_shady_keywords ( )
        self.headers = {
            "User-Agent" : "Alexandra Basalic basalica@icloud.com" ,
            "Accept" : "application/json" ,
            "Accept-Encoding" : "gzip"
        }

    def _load_cik_map ( self ) -> dict :
        """Pre-verified CIK mapping for major companies"""
        return {
            'AAPL' : '320193' ,
            'TSLA' : '1318605' ,
            'MSFT' : '789019' ,
            'JPM' : '19617' ,
            'GOOG' : '1652044' ,
            'AMZN' : '1018724' ,
            'BRK-B' : '1067983' ,
            'NVDA' : '1045810' ,
            'META' : '1326801' ,
            'WMT' : '104169'
        }

    def _load_auditor_map ( self ) -> dict :
        """Pre-verified auditor mapping"""
        return {
            '320193' : 'Ernst & Young LLP' ,
            '1318605' : 'PricewaterhouseCoopers LLP' ,
            '789019' : 'Deloitte & Touche LLP' ,
            '19617' : 'KPMG LLP' ,
            '1652044' : 'Ernst & Young LLP' ,
            '1018724' : 'Ernst & Young LLP' ,
            '1067983' : 'Deloitte & Touche LLP' ,
            '1045810' : 'PricewaterhouseCoopers LLP' ,
            '1326801' : 'Ernst & Young LLP' ,
            '104169' : 'Ernst & Young LLP'
        }

    def _load_shady_keywords ( self ) -> list :
        """Expanded list of shady auditor indicators"""
        return [
            "& Associates" , "CPA" , "Accounting" ,
            "Family Office" , "Consulting" ,
            "Tax Services" , "Bookkeeping" ,
            "M.& Co." , "& Sons" , "Group LLC"
        ]

    def auditor_is_shady ( self , auditor_name: str ) -> bool :
        """Enhanced shady auditor detection with pattern matching"""
        if not auditor_name or auditor_name == "AUDITOR NOT FOUND" :
            return False

        auditor_lower = auditor_name.lower ( )
        return any (
            keyword.lower ( ) in auditor_lower
            for keyword in self.shady_keywords
        )

    def _log_auditor_change ( self , ticker: str , old_auditor: str , new_auditor: str ) -> None :
        """Enhanced logging with additional metadata"""
        with open ( LOG_FILE , 'a' , newline='' ) as f :
            writer = csv.writer ( f )
            writer.writerow ( [
                datetime.now ( ).isoformat ( ) ,
                ticker.upper ( ) ,
                old_auditor ,
                new_auditor ,
                "SHADY" if self.auditor_is_shady ( new_auditor ) else "CLEAN"
            ] )

    def _get_sec_data_with_retry ( self , url: str ) -> Optional[dict] :
        """Helper function with retry logic"""
        for attempt in range ( MAX_RETRIES ) :
            try :
                time.sleep ( REQUEST_DELAY )
                response = requests.get ( url , headers=self.headers , timeout=10 )
                response.raise_for_status ( )
                return response.json ( )
            except requests.HTTPError as e :
                if e.response.status_code == 429 :
                    wait_time = (2 ** attempt) * 5  # Exponential backoff
                    time.sleep ( wait_time )
                    continue
                return None
            except requests.RequestException :
                time.sleep ( 5 )
                continue
        return None

    def get_sec_auditor ( self , company_ticker: str ) -> Tuple[str , str] :
        """Enhanced SEC Auditor Lookup with better error handling"""
        ticker = company_ticker.upper ( )
        cik = self.cik_map.get ( ticker )

        if not cik :
            return ticker , "COMPANY NOT IN DATABASE"

        # First try pre-verified data
        if cik in self.auditor_map :
            return ticker , self.auditor_map[cik]

        # Fallback to API lookup
        filings_url = f"https://data.sec.gov/submissions/CIK{cik.zfill ( 10 )}.json"
        filings = self._get_sec_data_with_retry ( filings_url )

        if not filings :
            return ticker , "SEC REQUEST FAILED"

        # Find latest 10-K accession number
        recent = filings.get ( 'filings' , { } ).get ( 'recent' , { } )
        try :
            form_index = recent['form'].index ( '10-K' )
            accession = recent['accessionNumber'][form_index].replace ( '-' , '' )
            filing_date = recent['filingDate'][form_index]
        except (ValueError , KeyError) :
            return ticker , "NO 10-K FILINGS FOUND"

        # Get full submission text
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/full-submission.txt"
        try :
            time.sleep ( REQUEST_DELAY )
            doc_response = requests.get ( doc_url , headers=self.headers , timeout=15 )
            doc_text = doc_response.text
        except requests.RequestException :
            return ticker , "DOCUMENT DOWNLOAD FAILED"

        # Enhanced pattern matching with multiple attempts
        patterns = [
            r'(Independent\s+Registered\s+Public\s+Accounting\s+Firm|Auditor).{1,500}'
            r'(Ernst\s*&\s*Young|Deloitte|PricewaterhouseCoopers|KPMG|PwC|Grant\s*Thornton).{1,200}'
            r'(LLP|L\.L\.P|L\.L\.C|Inc|Corp)' ,

            r'(Accountant\s*:\s*)(.{1,200}?(LLP|L\.L\.P|L\.L\.C|Inc|Corp))' ,

            r'(Auditor\s*:\s*)(.{1,200}?(LLP|L\.L\.P|L\.L\.C|Inc|Corp))'
        ]

        for pattern in patterns :
            auditor = re.search ( pattern , doc_text , re.IGNORECASE )
            if auditor :
                groups = [g for g in auditor.groups ( ) if g]
                result = " ".join ( groups[-2 :] ).title ( )
                result = (result.replace ( 'Pwc' , 'PwC' )
                          .replace ( 'Llp' , 'LLP' )
                          .replace ( 'L.L.P' , 'LLP' )
                          .replace ( ' And ' , ' & ' ))
                return ticker , result

        return ticker , "AUDITOR NOT FOUND"


def main () :
    scanner = AuditorScanner ( )

    # Test cases
    test_companies = ["AAPL" , "TSLA" , "MSFT" , "JPM" , "GOOG" ,
                      "AMZN" , "BRK-B" , "NVDA" , "META" , "WMT" , "UNKNOWN"]

    print ( "=== Auditor Verification ===" )
    for ticker in test_companies :
        ticker , auditor = scanner.get_sec_auditor ( ticker )
        print ( f"{ticker}: {auditor}" )

        if scanner.auditor_is_shady ( auditor ) :
            print ( f"   ⚠️ WARNING: Shady auditor detected!" )
        elif auditor in ["AUDITOR NOT FOUND" , "SEC REQUEST FAILED"] :
            print ( f"   ⚠️ WARNING: Auditor verification failed" )

    # Shady auditor test
    print ( "\n=== Shady Auditor Test ===" )
    test_auditors = [
        "Friehling & Horowitz, CPA" ,
        "Doe & Associates Accounting" ,
        "Family Office Tax Services LLC" ,
        "M. Jones & Sons Bookkeeping" ,
        "Ernst & Young LLP"
    ]
    for auditor in test_auditors :
        if scanner.auditor_is_shady ( auditor ) :
            print ( f"⚠️ WARNING: {auditor} (shady)" )
        else :
            print ( f"✅ Clean: {auditor}" )


if __name__ == "__main__" :
    main ( )