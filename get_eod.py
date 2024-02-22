#!/usr/bin/env python3
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
date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

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

datetime_cutoff = datetime.now(timezone.utc) - timedelta(hours=18)

issues = json.loads(response.text)["issues"]

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

    comment_text = ""
    for comment in comments:
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
                if "type" in block and block["type"] == "codeBlock":
                    # Assuming the text is directly inside, adjust if nested
                    comment_text += "```\n" + block["content"][0]["text"] + "\n```\n"
                    continue
                for elem in block["content"]:
                    if "type" in elem and elem["type"] == "hardBreak":
                        comment_text += "  \n"
                        continue
                    if "type" in elem and elem["type"] == "mention":
                        comment_text += elem["attrs"]["text"].replace("@", "") + " "
                        continue
                    # if 'type' in elem and elem['type'] == 'code':
                    #   comment_text += "`" + elem['text'] + "`"
                    if "text" in elem:
                        if "marks" in elem and any(
                            mark["type"] == "link" for mark in elem["marks"]
                        ):
                            link = next(
                                mark for mark in elem["marks"] if mark["type"] == "link"
                            )
                            comment_text += (
                                f"[{elem['text']}]({link['attrs']['href']})".strip()
                                + " "
                            )
                        else:
                            comment_text += elem["text"].strip() + " "
                    elif "attrs" in elem and "url" in elem["attrs"]:
                        link_text = (
                            elem["attrs"]["url"]
                            if "url" in elem["attrs"]
                            else elem["attrs"]["url"]
                        )
                        comment_text += (
                            f"[{link_text}]({elem['attrs']['url']})".strip() + " "
                        )
                comment_text += "\n"

    if comments and comment_text:
        print(f"#### [{issue_title}]({jira_issues_base_url + issue['key']})")
        print(f"{comment_text}")
