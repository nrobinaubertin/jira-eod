jira-eod
========

1. Get a token from jira: https://id.atlassian.com/manage-profile/security/api-tokens
2. Create a `config.json` file following this template:
```
{
  "base_url": "https://<SOMETHING>.atlassian.net",
  "email": "<EMAIL>",
  "token": "<TOKEN>"
}
```
3. `python3 ./get_eod.py`
