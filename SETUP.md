# Setting up The 7AM

The steps only Wilson can do, in plain words. Everything here is already done; this is how to redo or change it.

## What an API key is, and where keys go

An API key is a long password that lets a program use a service for you. Finnhub's key lets the script ask for earnings data; Resend's key lets it send email from your account.

Keys never go in this repo (anything in the repo is copied to GitHub). They live in two places:
- **On your Mac**, for testing: a line in `~/.zshrc`, your shell's settings file, which programs read when they start. In Claude Code, type the line with a `!` in front so it runs right there:
  `! echo 'export NAME=value' >> ~/.zshrc` then `! source ~/.zshrc`
- **In the cloud environment** the scheduled task runs in, as environment variables (step 6).

## 1. Finnhub (earnings)

1. Go to finnhub.io and click **Get free API key**. Sign up with any email. No card.
2. Copy the key from the dashboard.
3. `! echo 'export FINNHUB_API_KEY=your_key' >> ~/.zshrc`, and add it to the cloud environment (step 6).

## 2. Resend (sending the email)

1. The account is **w0skinner@gmail.com**. Free plan: 100 emails a day, we send one.
2. **API Keys → Create API Key**, permission **Sending access**. Copy it (it's shown once).
3. `! echo 'export RESEND_API_KEY=your_key' >> ~/.zshrc`, and add it to the cloud environment (step 6).
4. **Domains:** wilsonskinner.com is verified, so the issue comes from `7am@wilsonskinner.com`. Its DNS records (DKIM `resend._domainkey`, CNAMEs `send` and `rsend`, `_dmarc`) live at Porkbun; don't delete them. Open and click tracking stay off.

## 3. Reddit (memes): only if you want Reddit back

Memes come from Short Squeez, Exec Sum and Lemmy (free, no keys). Reddit reviews new API apps by hand and never approved ours. If it ever does:

1. Log in to Reddit, go to reddit.com/prefs/apps, click **create another app**: name "the-7am", type **script**, redirect URI `http://localhost:8080`.
2. Once approved, the **client ID** is the short string under the app name; the **secret** is labeled.
3. Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` to `~/.zshrc` and the cloud environment, and add `"reddit"` to `memes.sources` in `config.yaml`.

## 4. GitHub + Claude Code on the web

The repo is github.com/wilsskin/the-7am (private). In claude.ai/code, GitHub is connected with access to **the-7am** only, so Claude's cloud computers can copy the repo each morning and push `feedback/FEEDBACK.md`.

## 5. Connectors

In claude.ai, **Settings → Connectors**: Gmail and Google Calendar stay connected. The morning task only searches Gmail for your feedback replies and the last two issues, and never opens anything else.

## 6. The scheduled task

A scheduled task is a Claude session that starts by itself on a timer, in Anthropic's cloud, so your Mac can be off.

- **Schedule:** 6:28am New York time. The cron is in UTC with no time zone: `28 11 * * *` in winter (EST), `28 10 * * *` in summer (EDT). Ask Claude to switch it when the footer reminder shows up (next: Mar 14 and Nov 7, 2027).
- **Prompt:** a short wrapper that tells Claude to follow `prompts/TASK.md`.
- **Repo:** wilsskin/the-7am.
- **Connectors:** Google Calendar and Gmail only.
- **Cloud environment "the-7am":** network access **Full**. Environment variables: `FINNHUB_API_KEY`, `RESEND_API_KEY`. Only you can change these, in claude.ai.

To test: **Run now** sends that day's issue right away (and uses up the day's one send).

## Monthly: the S&P 500 list

Market caps in `data/sp500.csv` drive the big movers and the earnings filter. The scheduled task refreshes it on the 1st of each month and pushes it. To do it by hand in ~/code/the-7am: `! .venv/bin/python -m brief.sp500`.
