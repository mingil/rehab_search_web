import requests
import pandas as pd
from collections import Counter
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from modules.logger_setup import logger
from modules.config import OPENALEX_EMAIL, CURRENT_YEAR
from modules.ml_utils import perform_topic_clustering
import fitz

def get_retry_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def extract_text_from_pdf(file_bytes):
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            return "".join([page.get_text() for page in doc])[:100000]
    except Exception as e:
        logger.error(f"PDF Parsing Error: {e}")
        return ""

def extract_abstract(abs_idx):
    if not abs_idx: return ""
    try:
        positions = [max(pos) for pos in abs_idx.values() if pos]
        words = [""] * (max(positions) + 1)
        for w, p_list in abs_idx.items():
            for p in p_list: words[p] = w
        return " ".join(words).strip()
    except: return ""

def parse_journal_data(r):
    stats = r.get("summary_stats")
    if not isinstance(stats, dict): stats = {}
    return {"name": r.get("display_name") or "Unknown Journal", "issn": r.get("issn_l") or "", "pub": r.get("host_organization_name") or "Unknown Publisher", "h_index": stats.get("h_index") or 0, "if_2yr": round(float(stats.get("2yr_mean_citedness") or 0.0), 2), "works": r.get("works_count") or 0}

def fetch_journal_info(issn):
    try:
        headers = {"User-Agent": f"mailto:{OPENALEX_EMAIL}"} if OPENALEX_EMAIL else {}
        session = get_retry_session()
        res = session.get(f"https://api.openalex.org/sources/issn:{issn}", headers=headers, timeout=10)
        if res.status_code == 200 and res.json().get("id"): return parse_journal_data(res.json())
    except Exception as e: logger.error(f"Journal Reverse Lookup Error: {e}")
    return None

def parse_work_metadata(w, count=None):
    title = w.get("title") or "No Title"
    loc = w.get("primary_location") or {}
    source = loc.get("source") or {} if isinstance(loc, dict) else {}
    journal = source.get("display_name") if isinstance(source, dict) else "Unknown"
    year = w.get("publication_year") or CURRENT_YEAR
    cites = count if count is not None else (w.get("cited_by_count") or 0)
    doi = w.get("doi") or ""
    abstract = extract_abstract(w.get("abstract_inverted_index") or {})
    authors_list = [a.get("author", {}).get("display_name", "") for a in w.get("authorships") or [] if isinstance(a, dict)]
    authors = ", ".join([a for a in authors_list[:5] if a]) + (" et al." if len(authors_list) > 5 else "")
    oa = w.get("open_access") or {}
    oa_url = oa.get("oa_url") if isinstance(oa, dict) and oa.get("is_oa") else None
    try: velocity = round(cites / max((CURRENT_YEAR - int(year) + 1), 1), 1)
    except: velocity = 0.0
    return {"Title": title, "Authors": authors, "Journal": journal, "Year": year, "Citations": cites, "Velocity (Cites/Yr)": velocity, "OA_Link": oa_url, "DOI": doi, "Abstract": abstract}

def run_data_pipeline(issns, start_yr, end_yr, top_n, mode, kw, prog_bar):
    headers = {"User-Agent": f"mailto:{OPENALEX_EMAIL}"} if OPENALEX_EMAIL else {}
    issn_str = "|".join(issns)
    results = []
    session = get_retry_session()

    logger.info(f"Data Pipeline Started (Mode:{mode}, Target:{top_n}, Keyword:{kw})")

    if "Ultra-fast" in mode:
        cursor = "*"
        while len(results) < top_n and cursor:
            per_page = min(200, top_n - len(results))
            if per_page <= 0: break
            params = {"filter": f"primary_location.source.issn:{issn_str},publication_year:{start_yr}-{end_yr}", "sort": "cited_by_count:desc", "per-page": per_page, "cursor": cursor}
            if kw.strip(): params["search"] = kw.strip()

            prog_bar.progress(min(int((len(results)/top_n)*100), 95), text=f"Ultra-fast scanning... ({len(results)}/{top_n} papers)")
            try:
                res = session.get("https://api.openalex.org/works", params=params, headers=headers, timeout=20)
                res.raise_for_status()
                data = res.json()
                if not data.get("results"): break
                for w in data["results"]:
                    if len(results) >= top_n: break
                    results.append(parse_work_metadata(w))
                cursor = data.get("meta", {}).get("next_cursor")
            except Exception as e:
                logger.error(f"Ultra-fast scan error: {e}")
                break
    else:
        cursor, page, all_refs = "*", 0, []
        while cursor and page < 40:
            try:
                params = {"filter": f"primary_location.source.issn:{issn_str},publication_year:{start_yr}-{end_yr}", "select": "referenced_works", "per-page": 200, "cursor": cursor}
                if kw.strip(): params["search"] = kw.strip()
                res = session.get("https://api.openalex.org/works", params=params, headers=headers, timeout=20)
                res.raise_for_status()
                data = res.json()
                if not data.get("results"): break
                for w in data["results"]: all_refs.extend(w.get("referenced_works", []))
                cursor = data.get("meta", {}).get("next_cursor")
                page += 1
                prog_bar.progress(min(page * 2, 40), text=f"Network back-tracing... (Page {page})")
            except Exception as e:
                logger.error(f"Deep scan error: {e}")
                break

        if not all_refs: return pd.DataFrame()
        top_refs = Counter(all_refs).most_common(top_n * 3)
        ref_dict = {ref_id.split('/')[-1]: count for ref_id, count in top_refs}
        ref_ids = list(ref_dict.keys())

        chunk_size = 50
        for i in range(0, len(ref_ids), chunk_size):
            if len(results) >= top_n: break
            chunk_str = "|".join(ref_ids[i:i+chunk_size])
            params = {"filter": f"openalex:{chunk_str}", "per-page": chunk_size}
            prog_bar.progress(40 + int(((i/len(ref_ids))*60)), text=f"Restoring metadata... ({min(i+chunk_size, len(ref_ids))}/{len(ref_ids)})")
            try:
                res = session.get("https://api.openalex.org/works", params=params, headers=headers, timeout=20)
                res.raise_for_status()
                for w in res.json().get("results", []):
                    w_id = w.get("id", "").split('/')[-1]
                    results.append(parse_work_metadata(w, count=ref_dict.get(w_id, 0)))
            except Exception as e:
                logger.error(f"Metadata restoration error: {e}")

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(by="Citations", ascending=False).head(top_n).reset_index(drop=True)
        df.insert(0, "Rank", range(1, len(df) + 1))
        prog_bar.progress(98, text="🤖 Running Machine Learning (K-Means) clustering...")
        df = perform_topic_clustering(df)

    prog_bar.progress(100, text="Data extraction and processing complete!")
    return df
