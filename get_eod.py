#!/usr/bin/env python3
import sys
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime, timedelta, timezone

with open("config.json", "r") as config_file:
    config = json.load(config_file)
    base_url = config["base_url"]
    jira_url = f"{base_url}/rest/api/3/"
    email = config["email"]
    token = config["token"]
    jira_issues_base_url = f"{base_url}/browse/"

auth = HTTPBasicAuth(email, token)
headers = {"Accept": "application/json"}

# get all issues updated today
date = (datetime.now() - timedelta(days=int(sys.argv[1]))).strftime("%Y-%m-%d")

response = requests.request(
    "GET",
    jira_url + "search",
    headers=headers,
    params={
        "jql": f'(reporter was currentUser() OR assignee was currentUser()) AND updatedDate >= "{date}"',
        "fields": "key, summary",
    },
    auth=auth,
)

number_of_days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
datetime_cutoff = datetime.now(timezone.utc) - timedelta(hours=18 * number_of_days)

issues = json.loads(response.text)["issues"]


def parse_content(content):
    text = ""
    for elem in content:
        if "type" in elem and elem["type"] == "hardBreak":
            text += "  \n"
        elif "type" in elem and elem["type"] == "mention":
            text += elem["attrs"]["text"].replace("@", "") + " "
        elif "type" in elem and elem["type"] == "text":
            if "marks" in elem and any(
                mark["type"] == "link" for mark in elem["marks"]
            ):
                link = next(mark for mark in elem["marks"] if mark["type"] == "link")
                text += f"[{elem['text']}]({link['attrs']['href']})".strip() + " "
            else:
                text += elem["text"].strip() + " "
        elif "type" in elem and elem["type"] == "inlineCard":
            text += f"[{elem['attrs']['url']}]({elem['attrs']['url']}) "
        elif "type" in elem and elem["type"] == "code":
            text += f"`{elem['text']}`"
    return text


def parse_block(block):
    text = ""
    if "type" in block and block["type"] == "codeBlock":
        text += "```\n" + block["content"][0]["text"] + "\n```\n"
    elif "type" in block and block["type"] == "paragraph":
        text += parse_content(block["content"])
    elif "type" in block and block["type"] == "bulletList":
        for item in block["content"]:
            text += "  - " + parse_content(item["content"][0]["content"]) + "\n"
    elif "type" in block and block["type"] == "heading":
        level = block.get("attrs", {}).get("level", 1)
        heading_text = parse_content(block.get("content", [])).strip()
        text += f"{'#' * level} {heading_text}\n"
    return text


# get last comment from all these issues
for issue in issues:
    response = requests.request(
        "GET",
        jira_url + "issue/" + issue["key"] + "/comment",
        headers=headers,
        auth=auth,
    )

    issue_title = issue.get("fields", {}).get("summary", issue["key"])
    comments = json.loads(response.text)["comments"]

    comments_text = []
    for comment in comments:
        comment_text = ""
        comment_datetime = datetime.strptime(
            comment["updated"], "%Y-%m-%dT%H:%M:%S.%f%z"
        )
        if (
            comment_datetime >= datetime_cutoff
            and "emailAddress" in comment["author"]
            and comment["author"]["emailAddress"] == email
        ):
            content = comment["body"]["content"]
            for block in content:
                comment_text += parse_block(block)
            comments_text.append(comment_text)

    if comments_text:
        print(f"**[{issue_title}]({jira_issues_base_url + issue['key']})**")
        for comment in comments_text:
            print(f"* {comment}")
        print("\n")
