import os
import glob
import datetime
import subprocess
import re
import argparse
import csv

def ocr_text(path):
    for lang in ("ita", "eng"):
        try:
            out = subprocess.run(["tesseract", path, "stdout", "--psm", "6", "-l", lang], capture_output=True, text=True, check=True).stdout
            if out.strip():
                return out
        except Exception:
            continue
    return ""

def find_time_near(text, keywords):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        ll = line.lower()
        if any(k in ll for k in keywords):
            m = re.search(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", line)
            if m:
                return m.group(1)
            if i + 1 < len(lines):
                m2 = re.search(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", lines[i + 1])
                if m2:
                    return m2.group(1)
    low = text.lower()
    for k in keywords:
        for mt in re.finditer(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", text):
            idx = mt.start()
            seg = low[max(0, idx - 60): idx + 60]
            if k in seg:
                return mt.group(1)
    return ""

def find_total_time(text):
    lines = text.splitlines()
    low = text.lower()
    idx_tt = -1
    for i, line in enumerate(lines):
        ll = line.lower()
        if ("tempo totale" in ll) or ("durata totale" in ll):
            idx_tt = i
            break
    cand_tt = ""
    if idx_tt != -1:
        for j in range(idx_tt - 1, max(-1, idx_tt - 6), -1):
            if j < 0:
                break
            m = re.search(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", lines[j])
            if m:
                cand_tt = m.group(1)
                break
        if not cand_tt:
            before = "\n".join(lines[:idx_tt])
            mts = list(re.finditer(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", before))
            if mts:
                cand_tt = mts[-1].group(1)
    idx_ta = low.find("tempo di allenamento")
    if idx_ta == -1:
        idx_ta = low.find("allenamento")
    cand_before_ta = ""
    if idx_ta != -1:
        pre = text[:idx_ta]
        mts = list(re.finditer(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", pre))
        if mts:
            cand_before_ta = mts[-1].group(1)
    s_tt = to_seconds_duration(cand_tt)
    s_bt = to_seconds_duration(cand_before_ta)
    if s_tt is not None and s_bt is not None:
        return cand_tt if s_tt >= s_bt else cand_before_ta
    if s_tt is not None:
        return cand_tt
    if s_bt is not None:
        return cand_before_ta
    return find_time_near(text, ["tempo totale"]) or ""

def to_seconds_duration(s):
    if not s:
        return None
    parts = s.split(":")
    if len(parts) == 3:
        h, m, ss = map(int, parts)
        return h * 3600 + m * 60 + ss
    if len(parts) == 2:
        a, b = map(int, parts)
        return a * 60 + b
    return None

def format_duration(sec):
    if sec is None:
        return ""
    if sec >= 3600:
        return f"{sec // 3600}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"
    return f"{sec // 60}:{sec % 60:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="images")
    ap.add_argument("--output", default="output.csv")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.input, "*.jpg")))
    rows = []
    for f in files:
        fn = os.path.basename(f)
        if " - " not in fn:
            continue
        name = fn[:-4]
        left, route = name.split(" - ", 1)
        left_parts = left.split()
        date = left_parts[0].split(".")[0]
        mezzo = " ".join(left_parts[1:]) if len(left_parts) > 1 else ""
        print(f"Elaboro: {fn}")
        route = route.split(" (")[0]
        parts = route.split()
        start = parts[0]
        arr = parts[-1]
        st = os.stat(f)
        ts = datetime.datetime.fromtimestamp(getattr(st, "st_birthtime", st.st_mtime))
        text = ocr_text(f)
        low = text.lower()
        km = ""
        mkm = re.search(r"(\d{1,3}(?:[\.,]\d{1,2})?)\s*km\b", low)
        if mkm:
            km = mkm.group(1).replace(",", ".")
        kcal = ""
        mkcal = re.search(r"\b(\d{2,5})\s*(kcal|cal)\b", low)
        if mkcal:
            kcal = mkcal.group(1)
        tt_str = find_total_time(text)
        ta_str = find_time_near(text, ["tempo di allenamento", "allenamento", "tempo in movimento", "movimento"])
        all_times = re.findall(r"(\d{1,3}\s*:\s*[0-5]\d(?:\s*:\s*[0-5]\d)?)", text)
        def is_near_keywords(t):
            i = text.find(t)
            w = text[max(0, i - 50): i + 50].lower()
            return any(k in w for k in ["tempo", "durata", "totale", "allenamento"])
        candidates = [t for t in all_times if not is_near_keywords(t)]
        ora = ""
        for t in candidates:
            if t.count(":") == 1:
                h, m = map(int, t.split(":"))
                if 0 <= h <= 23:
                    ora = f"{h:02d}:{m:02d}"
                    break
        if not ora:
            ora = ts.strftime("%H:%M:%S")
        tt = to_seconds_duration(tt_str)
        ta = to_seconds_duration(ta_str)
        pausa = ""
        if tt is not None and ta is not None and tt >= ta:
            pausa = format_duration(tt - ta)
        tempo_totale = format_duration(tt) if tt is not None else ""
        print(f"  mezzo={mezzo}, percorso={start}->{arr}, tempo_totale={tempo_totale}, tempo_allenamento={format_duration(ta) if ta is not None else ''}")
        rows.append([date, ora, mezzo, start, arr, tempo_totale, km, pausa, kcal])
    with open(args.output, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["data", "ora", "mezzo", "luogo_partenza", "luogo_arrivo", "tempo_totale", "km_percorsi", "pausa", "kcal_consumate"])
        for r in rows:
            w.writerow(r)

if __name__ == "__main__":
    main()
