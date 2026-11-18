"""Download the MineThatData e-mail experiment file."""

from __future__ import annotations

import urllib.request
from pathlib import Path

URL = "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
DESTINATION = Path("data/hillstrom.csv")


def main() -> None:
    if DESTINATION.exists():
        print(f"Using existing {DESTINATION}")
        return
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    partial = DESTINATION.with_suffix(".part")
    request = urllib.request.Request(URL, headers={"User-Agent": "email-campaign-analysis"})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    partial.replace(DESTINATION)
    print(f"Downloaded {DESTINATION}")


if __name__ == "__main__":
    main()
