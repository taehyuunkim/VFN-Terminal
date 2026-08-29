#!/usr/bin/env python3
"""
VFN Terminal v2 updater.

Purpose
-------
1) Gather a broad public-source universe.
2) Build a daily headline candidate set.
3) Screen SEC / regulatory / press-release sources for event-driven situations.
4) Optionally use OpenAI to rank + summarize candidates into investor-ready JSON.
5) Never bypass paywalls/authentication and never republish full articles.

Secrets
-------
SEC_USER_AGENT  Required for polite SEC access. Example: "Tae Kim tae@example.com"
OPENAI_API_KEY  Optional but strongly recommended for high-quality ranking/summaries.
OPENAI_MODEL    Optional, defaults to gpt-5.6-luna.

The frontend reads only /data/*.json.
"""

from __future__ import annotations
import json, os, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, quote_plus
import requests, feedparser
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
UA=os.getenv("SEC_USER_AGENT","VFN Terminal public research contact@example.com")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-5.6-luna")
HEADERS={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

# Known public RSS endpoints. If one changes, failure is isolated to that feed.
RSS_SOURCES=[
 ("The Guardian — Business","https://www.theguardian.com/business/rss","news"),
 ("The Guardian — Technology","https://www.theguardian.com/technology/rss","news"),
 ("The Guardian — World","https://www.theguardian.com/world/rss","news"),
 ("BBC — Business","https://feeds.bbci.co.uk/news/business/rss.xml","news"),
 ("BBC — World","https://feeds.bbci.co.uk/news/world/rss.xml","news"),
 ("CNBC — Top News","https://www.cnbc.com/id/100003114/device/rss/rss.html","news"),
 ("CNBC — Finance","https://www.cnbc.com/id/10000664/device/rss/rss.html","news"),
 ("CNBC — Technology","https://www.cnbc.com/id/19854910/device/rss/rss.html","news"),
 ("CNBC — Investing","https://www.cnbc.com/id/15839069/device/rss/rss.html","news"),
 ("NYT — Business","https://rss.nytimes.com/services/xml/rss/nyt/Business.xml","news"),
 ("NYT — Technology","https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml","news"),
 ("NPR — Business","https://feeds.npr.org/1006/rss.xml","news"),
 ("Federal Reserve","https://www.federalreserve.gov/feeds/press_all.xml","macro"),
 ("PR Newswire — General Business","https://www.prnewswire.com/rss/news-releases-list.rss","press"),
]

# Public pages that are useful but may not expose a stable RSS URL.
HTML_SOURCES=[
 ("Apollo — The Daily Spark","https://www.apollo.com/wealth/insights-news/insights/daily-spark","news"),
 ("Axios — Newsletters","https://www.axios.com/newsletters","news"),
 ("MarketWatch — Markets","https://www.marketwatch.com/markets","news"),
 ("Yahoo Finance","https://finance.yahoo.com/topic/stock-market-news/","news"),
 ("Fortune — Finance","https://fortune.com/finance/","news"),
 ("Financial Times — Markets","https://www.ft.com/markets","news"),
 ("Financial Times — Companies","https://www.ft.com/companies","news"),
 ("U.S. Treasury","https://home.treasury.gov/news/press-releases","macro"),
 ("BLS — Latest Releases","https://www.bls.gov/bls/newsrels.htm","macro"),
 ("BEA — News Releases","https://www.bea.gov/news","macro"),
 ("EIA — Press Releases","https://www.eia.gov/pressroom/","macro"),
 ("ECB — Press Releases","https://www.ecb.europa.eu/press/pr/html/index.en.html","macro"),
 ("ECB — Speeches","https://www.ecb.europa.eu/press/key/html/index.en.html","macro"),
 ("Bank of England","https://www.bankofengland.co.uk/news","macro"),
 ("Bank of Japan","https://www.boj.or.jp/en/announcements/release_2026/index.htm","macro"),
 ("Bank of Canada","https://www.bankofcanada.ca/press/","macro"),
 ("RBA","https://www.rba.gov.au/media-releases/","macro"),
 ("BIS","https://www.bis.org/press/index.htm","macro"),
 ("IMF","https://www.imf.org/en/News","macro"),
 ("World Bank","https://www.worldbank.org/en/news","macro"),
 ("OECD","https://www.oecd.org/en/about/news.html","macro"),
 ("SEC — Press Releases","https://www.sec.gov/newsroom/press-releases","event"),
 ("SEC — Litigation Releases","https://www.sec.gov/enforcement-litigation/litigation-releases","event"),
 ("PR Newswire — M&A","https://www.prnewswire.com/news-releases/financial-services-latest-news/acquisitions-mergers-and-takeovers-list/","event"),
 ("PR Newswire — Earnings","https://www.prnewswire.com/news-releases/financial-services-latest-news/earnings-list/","press"),
 ("GlobeNewswire","https://www.globenewswire.com/","press"),
 ("Business Wire","https://www.businesswire.com/portal/site/home/news/","press"),
 ("Accesswire","https://www.accesswire.com/newsroom","press"),
 ("FTC — Competition","https://www.ftc.gov/news-events/news/press-releases?type=All&field_mission%5B29%5D=29","event"),
 ("DOJ Antitrust","https://www.justice.gov/atr/press-releases","event"),
 ("DOJ Antitrust — Case Filings","https://www.justice.gov/atr/antitrust-case-filings","event"),
 ("CFTC","https://www.cftc.gov/PressRoom/PressReleases","event"),
 ("FINRA","https://www.finra.org/media-center/newsreleases","event"),
 ("FDIC","https://www.fdic.gov/news/press-releases/","event"),
 ("OCC","https://www.occ.treas.gov/news-issuances/news-releases/index-news-releases.html","event"),
 ("CFPB","https://www.consumerfinance.gov/about-us/newsroom/","event"),
 ("FCC","https://www.fcc.gov/news-events/headlines","event"),
 ("FERC","https://www.ferc.gov/news-events/news/news-releases","event"),
 ("UK CMA — Mergers","https://www.gov.uk/cma-cases?case_type=mergers","event"),
 ("UK CMA — Open Cases","https://www.gov.uk/cma-cases?case_state=open","event"),
 ("European Commission — Mergers","https://competition-policy.ec.europa.eu/mergers/latest-news_en","event"),
 ("European Commission — Antitrust","https://competition-policy.ec.europa.eu/antitrust-and-cartels/latest-news_en","event"),
 ("Competition Bureau Canada","https://competition-bureau.canada.ca/how-we-foster-competition/education-and-outreach/news-releases","event"),
 ("ACCC Australia","https://www.accc.gov.au/media-release","event"),
 ("Bundeskartellamt Germany","https://www.bundeskartellamt.de/SharedDocs/Meldung/EN/Pressemitteilungen/pressemitteilungen_node.html","event"),
 ("Autorité de la concurrence France","https://www.autoritedelaconcurrence.fr/en/press-releases","event"),
]

EDGAR_FORMS=[
"8-K","6-K","425","S-4","F-4","DEFM14A","PREM14A","SC 13D","SC 13D/A","SC 13G",
"SC TO-T","SC TO-I","SC TO-C","13E-3","14D-9","10-Q","10-K","20-F","40-F",
"NT 10-Q","NT 10-K","8-A12B","4","3","5"
]

EVENT_TERMS=[
 "merger","acquisition","acquire","strategic review","strategic alternatives",
 "sale process","explore a sale","divest","spin-off","spinoff","split-off",
 "tender offer","go-private","takeover","asset sale","business combination",
 "merger agreement","definitive agreement","restructuring","chapter 11",
 "exchange offer","recapitalization","activist","proxy contest","consent solicitation"
]
MARKET_TERMS=[
 "inflation","jobs","payroll","federal reserve","fed ","treasury","yield","rates",
 "tariff","oil","natural gas","credit","default","spread","ai ","semiconductor",
 "earnings","guidance","recession","gdp","consumer","housing","bank"
]

def get(url, timeout=25):
    r=requests.get(url,headers=HEADERS,timeout=timeout)
    r.raise_for_status()
    return r

def clean(s):
    return re.sub(r"\s+"," ",BeautifulSoup(s or "","html.parser").get_text(" ",strip=True)).strip()

def parse_time(entry):
    for key in ("published_parsed","updated_parsed"):
        t=getattr(entry,key,None)
        if t:
            return datetime(*t[:6],tzinfo=timezone.utc).isoformat()
    return ""

def rss_items(source,url,kind,limit=30):
    out=[]
    try:
        raw=get(url).content
        feed=feedparser.parse(raw)
        for e in feed.entries[:limit]:
            title=clean(getattr(e,"title",""))
            if len(title)<20: continue
            out.append({
              "source":source,"headline":title,
              "summary_raw":clean(getattr(e,"summary",""))[:1200],
              "url":getattr(e,"link",url),"published":parse_time(e),"kind":kind
            })
    except Exception as exc:
        print(f"[warn:rss] {source}: {exc}",file=sys.stderr)
    return out

def html_items(source,url,kind,limit=30):
    out=[]
    try:
        soup=BeautifulSoup(get(url).text,"html.parser")
        seen=set()
        for a in soup.find_all("a",href=True):
            title=clean(a.get_text(" ",strip=True))
            href=urljoin(url,a["href"])
            if len(title)<28 or title in seen or not href.startswith("http"): continue
            # Avoid nav boilerplate.
            if title.lower() in {"read more","learn more","view all","subscribe","sign up"}: continue
            seen.add(title)
            out.append({"source":source,"headline":title,"summary_raw":"","url":href,"published":"","kind":kind})
            if len(out)>=limit: break
    except Exception as exc:
        print(f"[warn:html] {source}: {exc}",file=sys.stderr)
    return out

def edgar_atom(form,limit=35):
    # SEC's browse-edgar Atom endpoint; form is URL-encoded.
    url=("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent"
         f"&type={quote_plus(form)}&company=&dateb=&owner=include&start=0&count={limit}&output=atom")
    out=[]
    try:
        feed=feedparser.parse(get(url).content)
        for e in feed.entries[:limit]:
            title=clean(getattr(e,"title",""))
            summary=clean(getattr(e,"summary",""))
            out.append({
              "source":f"SEC / {form}","headline":title,"summary_raw":summary,
              "url":getattr(e,"link","https://www.sec.gov/edgar/search/"),
              "published":parse_time(e),"kind":"filing","form":form
            })
    except Exception as exc:
        print(f"[warn:edgar] {form}: {exc}",file=sys.stderr)
    time.sleep(.12)
    return out

def dedupe(items):
    seen=set();out=[]
    for x in items:
        k=re.sub(r"[^a-z0-9]","",x["headline"].lower())[:150]
        if not k or k in seen: continue
        seen.add(k);out.append(x)
    return out

def relevance(x):
    text=(x.get("headline","")+" "+x.get("summary_raw","")).lower()
    score=0
    score+=sum(3 for t in EVENT_TERMS if t in text)
    score+=sum(1 for t in MARKET_TERMS if t in text)
    if x.get("kind")=="filing": score+=2
    if x.get("kind")=="event": score+=2
    if x.get("source","").startswith("Apollo"): score+=2
    return score

def ticker_from_sec_title(title):
    # EDGAR titles often contain form - company (CIK...). We deliberately avoid guessing ticker.
    return ""

def heuristic_event_type(text,form=""):
    t=text.lower()
    if "chapter 11" in t or "restructur" in t or "exchange offer" in t: return "Restructuring"
    if "strategic review" in t or "strategic alternatives" in t or "sale process" in t: return "Strategic Review"
    if "spin-off" in t or "spinoff" in t or "split-off" in t: return "Spin-off"
    if "divest" in t or "asset sale" in t: return "Divestiture"
    if form.startswith("SC 13D") or "activist" in t or "proxy contest" in t: return "Activism"
    if any(k in t for k in ["merger","acquisition","acquire","takeover","tender offer","go-private","business combination"]): return "M&A"
    return "Filing"

def heuristic_assets(text):
    t=text.lower();a=[]
    if any(k in t for k in ["fed ","federal reserve","inflation","jobs","payroll","treasury","gdp","recession","tariff","oil"]): a.append("Macro")
    if any(k in t for k in ["credit","bond","debt","yield","default","spread","loan","refinanc"]): a.append("Credit")
    if any(k in t for k in ["stock","equity","earnings","guidance","company","merger","acquisition","ai ","semiconductor"]) or not a: a.append("Equity")
    if len(a)>=2: a.append("Cross-Asset")
    return list(dict.fromkeys(a))

def ai_json(prompt):
    if not OPENAI_API_KEY: return None
    try:
        from openai import OpenAI
        client=OpenAI(api_key=OPENAI_API_KEY)
        r=client.responses.create(model=OPENAI_MODEL,input=prompt)
        txt=r.output_text.strip()
        txt=re.sub(r"^```(?:json)?|```$","",txt,flags=re.M).strip()
        return json.loads(txt)
    except Exception as exc:
        print(f"[warn:ai] {exc}",file=sys.stderr)
        return None


def fallback_takeaway(x):
    text=(x.get("headline","")+" "+x.get("summary_raw","")).lower()
    if any(k in text for k in ["merger","acquisition","takeover","tender offer","business combination"]):
        return "Event-driven read: verify consideration, financing, vote requirements, regulatory conditions, termination rights and the next dated closing milestone."
    if any(k in text for k in ["strategic alternatives","strategic review","explore a sale","sale process"]):
        return "Strategic-review read: separate announced process from actual buyer interest; track adviser engagement, asset perimeter, balance-sheet urgency and any explicit timetable."
    if any(k in text for k in ["chapter 11","restructur","exchange offer","covenant","default"]):
        return "Credit read: map liquidity, maturity wall, covenant headroom, collateral and recovery waterfall; determine whether the event changes the fulcrum security."
    if any(k in text for k in ["fed ","federal reserve","inflation","payroll","jobs","treasury","yield","rates"]):
        return "Macro read: translate the release into the growth/inflation/discount-rate path, then identify sectors or capital structures most sensitive to the change."
    if any(k in text for k in ["earnings","guidance","revenue","margin"]):
        return "Equity read: distinguish one-quarter noise from a change in normalized earnings power, estimate revisions and identify what consensus now has to move."
    if any(k in text for k in ["antitrust","ftc","doj","cma","competition commission","merger review"]):
        return "Deal-risk read: determine whether this changes closing probability or duration; focus on remedy scope, second-request/phase timing and contractual risk allocation."
    return "Investor read: identify the first-order change to earnings, balance-sheet risk, industry structure, catalyst timing or discount rate before assessing the market reaction."

def build_digest(candidates):
    cand=sorted(candidates,key=relevance,reverse=True)[:220]
    compact=[{"id":i,"source":x["source"],"headline":x["headline"],"snippet":x.get("summary_raw","")[:550],"url":x["url"]} for i,x in enumerate(cand)]
    prompt=f"""You are editing a concise daily research terminal for a fundamental equity/credit investor.
From the candidate headlines below, select at least 50 and no more than 60 items that most change underwriting, catalysts,
discount rates, balance-sheet risk, industry structure, regulation, or positioning.

Return JSON ONLY as:
{{"items":[{{"id":0,"summary":"2-3 sentence factual summary","investment_takeaway":"1-2 sentences explaining the actual equity/credit underwriting implication","asset_classes":["Equity"],"importance":"high"}}]}}
Allowed asset classes: Equity, Credit, Macro, Cross-Asset. Importance: high, medium, low.
Do not invent facts beyond the candidate snippet/headline. Drop low-value lifestyle/politics headlines unless market-relevant.

CANDIDATES:
{json.dumps(compact,ensure_ascii=False)}
"""
    ai=ai_json(prompt)
    if ai and ai.get("items"):
        rows=[]
        for y in ai["items"]:
            try:x=cand[int(y["id"])]
            except:continue
            rows.append({
              "time":"","source":x["source"],"headline":x["headline"],
              "summary":clean(y.get("summary","")),"investment_takeaway":clean(y.get("investment_takeaway","")),
              "asset_classes":y.get("asset_classes") or heuristic_assets(x["headline"]),
              "importance":y.get("importance","medium"),"url":x["url"]
            })
        if rows:return rows
    # Safe fallback: lower quality but fully automatic.
    rows=[]
    for x in cand[:55]:
        rows.append({
          "time":"","source":x["source"],"headline":x["headline"],
          "summary":x.get("summary_raw")[:650] or "Open the linked source for the full report.",
          "investment_takeaway":fallback_takeaway(x),
          "asset_classes":heuristic_assets(x["headline"]+" "+x.get("summary_raw","")),
          "importance":"high" if relevance(x)>=5 else "medium","url":x["url"]
        })
    return rows

def build_events(candidates):
    event_cands=[]
    for x in candidates:
        blob=(x["headline"]+" "+x.get("summary_raw","")).lower()
        form=x.get("form","")
        if x.get("kind") in ("filing","event") and (any(t in blob for t in EVENT_TERMS) or form in {"425","S-4","DEFM14A","PREM14A","SC 13D","SC 13D/A","SC TO-T","SC TO-I","13E-3"}):
            event_cands.append(x)
    event_cands=sorted(event_cands,key=relevance,reverse=True)[:180]
    compact=[{"id":i,"source":x["source"],"headline":x["headline"],"snippet":x.get("summary_raw","")[:650],"form":x.get("form",""),"url":x["url"]} for i,x in enumerate(event_cands)]
    prompt=f"""You are maintaining a special-situations event tape for an event-driven equity/credit investor.
Use ONLY the candidates. Select 15-20 material corporate events, transaction updates, strategic reviews,
spin/divestiture signals, activist 13D signals, restructurings, regulatory deal milestones, or surprising filing disclosures.

Return JSON ONLY:
{{"items":[{{"id":0,"ticker":"","company":"","event_type":"M&A","status":"Live","signal":"NEW","why_it_matters":"...","next_step":"..."}}]}}
event_type must be one of M&A, Strategic Review, Spin-off, Divestiture, Activism, Restructuring, Filing.
Do not guess ticker/company if not supported. 'why_it_matters' should explain event economics/risk.
'next_step' should identify the next thing a special-situations investor should verify or monitor.

CANDIDATES:
{json.dumps(compact,ensure_ascii=False)}
"""
    ai=ai_json(prompt)
    rows=[]
    if ai and ai.get("items"):
        for y in ai["items"]:
            try:x=event_cands[int(y["id"])]
            except:continue
            rows.append({
              "time":"","ticker":y.get("ticker",""),"company":y.get("company","") or x["headline"][:100],
              "event_type":y.get("event_type","Filing"),"status":y.get("status","Live"),"signal":y.get("signal","NEW"),
              "why_it_matters":clean(y.get("why_it_matters","")),"next_step":clean(y.get("next_step","")),
              "source":x["source"],"url":x["url"]
            })
        if rows:return rows
    for x in event_cands[:18]:
        text=x["headline"]+" "+x.get("summary_raw","")
        rows.append({
          "time":"","ticker":"","company":x["headline"][:100],"event_type":heuristic_event_type(text,x.get("form","")),
          "status":"Live","signal":"NEW",
          "why_it_matters":"Potential special-situations signal detected. Verify terms, consideration, financing, approvals and whether this changes standalone or deal-case value.",
          "next_step":"Open the primary source and identify the next dated catalyst or gating condition.",
          "source":x["source"],"url":x["url"]
        })
    return rows

def write(name,items):
    now=datetime.now(timezone.utc)
    (DATA/name).write_text(json.dumps({"date":now.date().isoformat(),"updated_at":now.isoformat(),"items":items},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def main():
    all_items=[]
    for source,url,kind in RSS_SOURCES: all_items+=rss_items(source,url,kind)
    for source,url,kind in HTML_SOURCES: all_items+=html_items(source,url,kind)
    for form in EDGAR_FORMS: all_items+=edgar_atom(form)
    all_items=dedupe(all_items)
    print(f"raw_candidates={len(all_items)}")
    digest=build_digest([x for x in all_items if x.get("kind")!="filing"] + [x for x in all_items if relevance(x)>=5])
    events=build_events(all_items)
    if digest: write("digest.json",digest)
    if events: write("special_situations.json",events)
    print(f"digest={len(digest)} events={len(events)} ai={'on' if OPENAI_API_KEY else 'off'}")

if __name__=="__main__":
    main()
