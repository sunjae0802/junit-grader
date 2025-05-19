#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from collections import OrderedDict
import json
import csv
from typing import NamedTuple, List

class TestResult(NamedTuple):
    classname: str
    name: str
    success: bool
    output: str

TIMEOUT = 10

def process_junit(xml_filename: str) -> List[TestResult]:
    """Process a JUnit XML file and return a list of TestResults"""
    test_results = []

    root = ET.parse(xml_filename).getroot()
    for testcase in root.findall(".//testcase"):
        result = process_junit_testcase(testcase)
        test_results.append(result)

    return test_results

def process_junit_testcase(testcase: ET.Element) -> TestResult:
    """Process a JUnit XML testcase tag and return a TestResult"""
    classname = testcase.attrib["classname"]
    testname = testcase.attrib["name"]
    success = False
    output = None

    # Some Testcases have an explicit "failure" tag
    if (failure_tag := testcase.find("failure")) is not None:
        success = False
        if failure_tag.text is not None:
            output = failure_tag.text
        if output is None:
            if (sout_tag := testcase.find("system-out")) is not None:
                output = sout_tag.text
        if output is None:
            runtime = float(testcase.attrib["time"])
            if runtime > TIMEOUT:
                output = "TIMEOUT (infinite loop?)"

    # Other Testcases have a "status" tag instead
    elif 'status' in testcase.attrib:
        status = testcase.attrib['status']
        if status == "run":
            success = True
        elif status == "fail":
            success = False
            if (sout_tag := testcase.find("system-out")) is not None and sout_tag.text is not None:
                output = sout_tag.text
            else:
                runtime = float(testcase.attrib["time"])
                if runtime > TIMEOUT:
                    output = "TIMEOUT (infinite loop?)"

    # We treat all other Testcases as success
    else:
        success = True

    if output is None:
        output = ""

    return TestResult(classname, testname, success, output)

def generate_score(score_filename:str, xml_files: List[str], max_score: int):
    fieldnames = ['classname', 'testname', 'max_score']

    with open(score_filename, 'w') as score_file:
        writer = csv.DictWriter(score_file, fieldnames=fieldnames)

        rows = []
        writer.writeheader()
        for f in xml_files:
            test_results = process_junit(f)
            for test in test_results:
                r = {}
                r['classname'] = test.classname
                r['testname'] = test.name

                rows.append(r)

        num_rows = len(rows)
        for r in rows:
            r['max_score'] = int(max_score / num_rows)
            writer.writerow(r)

def grade_txt(score_filename:str, xml_files: List):
    total_max = 0
    all_results = OrderedDict()
    with open(score_filename, 'r') as score_file:
        reader = csv.DictReader(score_file)

        for row in reader:
            full_name = row["classname"] + ":" + row["testname"]
            all_results[full_name] = { "name": full_name, "max_score": row["max_score"] }
            total_max += int(row['max_score'])
            all_results[full_name]['score'] = 0

    total = 0
    for f in xml_files:
        test_results = process_junit(f)
        for test in test_results:
            full_name = test.classname + ":" + test.name
            score = all_results[full_name]["max_score"]
            if not test.success:
                score = 0
            all_results[full_name]['score'] = score
            total += int(score)

            if test.output:
                if len(test.output) > 0:
                    all_results[full_name]['output'] = test.output

    for n in all_results.keys():
        result = all_results[n]
        print(f"{result['name']}: {result['score']}/{result['max_score']}")

    print("--------------------------")
    print(f"{total} / {total_max}")

def gradescope_json(score_filename:str, xml_files: List):
    all_results = OrderedDict()
    with open(score_filename, 'r') as score_file:
        reader = csv.DictReader(score_file)

        for row in reader:
            full_name = (row["classname"], row["testname"])
            full_name_str = row["classname"] + ":" + row["testname"]
            all_results[full_name] = { "name": full_name_str, "max_score": row["max_score"] }
            all_results[full_name]['score'] = 0

    for f in xml_files:
        test_results = process_junit(f)
        for test in test_results:
            full_name = (test.classname, test.name)
            score = all_results[full_name]["max_score"]
            if not test.success:
                score = 0
            all_results[full_name]['score'] = score

            if test.output:
                if len(test.output) > 0:
                    all_results[full_name]['output'] = test.output

    test_results_json = []
    for n in all_results.keys():
        test_results_json.append(json.dumps(all_results[n]))

    print("""{
"tests":
[
"""
    )

    print(",\n".join(test_results_json))

    print("""    ]
}
"""
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Convert junit test results to score")
    parser.add_argument("-s", "--scores_csv_file", default='scores.csv')
    parser.add_argument("-m", "--max_score", default=100)
    parser.add_argument("-t", "--timeout", default=10, type=float)
    parser.add_argument("operation", choices=['generate', 'grade-txt', 'gradescope'])
    parser.add_argument("xml_files", nargs="+")
    args = parser.parse_args()

    if args:
        TIMEOUT = args.timeout

        if args.operation == 'generate':
            generate_score(args.scores_csv_file, args.xml_files, args.max_score)
        elif args.operation == 'grade-txt':
            grade_txt(args.scores_csv_file, args.xml_files)
        elif args.operation == 'gradescope':
            gradescope_json(args.scores_csv_file, args.xml_files)
