"""Expose deterministic CI-test failure details as readable GitHub annotations."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def escape(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    path = Path(sys.argv[1])
    if not path.is_file():
        print("::error title=Windows tests::Pytest did not produce its test result file.")
        return
    for case in ET.parse(path).getroot().iter("testcase"):
        for failure in list(case.findall("failure")) + list(case.findall("error")):
            name = case.get("classname", "") + "." + case.get("name", "")
            print(
                "::error title="
                + escape(name)
                + "::"
                + escape((failure.text or failure.get("message", ""))[:18000])
            )


if __name__ == "__main__":
    main()
