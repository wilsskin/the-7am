# Setting up The 7AM

The steps only Wilson can do (BUILD_PLAN.md §12), in plain words, in the order we need them. Each one takes a few minutes. Claude walks through each one live when it's time.

## What an API key is, and where keys go

An API key is a long password that lets a program use a service for you. Finnhub's key lets the script ask for earnings data; Resend's key lets it send email from your account.

Keys never go in this repo (anything in the repo is copied to GitHub). They live in two places:
- **On your Mac**, for testing: a line in `~/.zshrc`, your shell's settings file, which programs read when they start. In Claude Code, type the line with a `!` in front so it runs right there:
  `! echo 'export NAME=value' >> ~/.zshrc` then `! source ~/.zshrc`
  Don't paste the key into the chat itself; chat history is stored.
- **In the scheduled task**, as "network secrets" (step 6). Those are stored by Anthropic and only sent to the one website they belong to.

## 1. Finnhub (earnings): ~2 minutes

1. Go to finnhub.io and click **Get free API key**. Sign up with any email. No card.
2. Copy the key from the dashboard.
3. `! echo 'export FINNHUB_API_KEY=your_key' >> ~/.zshrc`

Unlocks: the Earnings section.

## 2. Resend (sending the email): ~5 minutes

1. Go to resend.com and sign up **with w0skinner@gmail.com**. Without your own domain, Resend can only send to the address on the account, which is exactly what we want.
2. In the dashboard, **API Keys → Create API Key**. Name it "the-7am", permission **Sending access**. Copy it (it's shown once).
3. `! echo 'export RESEND_API_KEY=your_key' >> ~/.zshrc`
4. In Gmail, make a filter so the issue never lands in spam: search `from:onboarding@resend.dev`, click the filter icon, **Create filter**, tick **Never send it to Spam** and **Always mark it as important**.

Unlocks: Milestone 4, a real email in your inbox. Free plan: 100 emails a day, we send one.

## 3. Reddit (memes): ~5 minutes, then a wait

Reddit reviews new API apps by hand now, so this can take days or weeks. If it's never approved, The 7AM ships without the Meme roundup (decided Nov 22).

1. Log in to Reddit, go to reddit.com/prefs/apps, click **create another app**.
2. Name "the-7am", type **script**, redirect URI `http://localhost:8080`. Fill in the access request form if asked: personal, read-only, one request a day.
3. Once approved, the **client ID** is the short string under the app name; the **secret** is labeled.
4. `! echo 'export REDDIT_CLIENT_ID=...' >> ~/.zshrc` and the same for `REDDIT_CLIENT_SECRET`.

## 4. GitHub + Claude Code on the web: ~5 minutes

The repo already exists: github.com/wilsskin/the-7am (private).

1. Go to claude.ai/code and sign in.
2. When asked, connect GitHub and give access to **the-7am** only. This lets Claude's cloud computers copy the repo each morning and push `feedback/FEEDBACK.md`.

## 5. Gmail connector: ~2 minutes

Needed for the feedback loop (replies to the issue get filed in the repo).

1. In claude.ai, **Settings → Connectors → Gmail → Connect**, and approve.
2. Google Calendar is already connected; leave it on.

The morning task only searches `to:w0skinner+7am-feedback@gmail.com from:me` and never opens anything else.

## 6. The scheduled task (Milestone 5, Claude sets this up with you)

A scheduled task is a Claude session that starts by itself on a timer, in Anthropic's cloud, so your Mac can be off.

- **Schedule:** every day at 6:22am New York time. Off the hour on purpose: on-the-hour jobs can start late.
- **Prompt:** the contents of `prompts/TASK.md`.
- **Repo:** wilsskin/the-7am.
- **Connectors:** Google Calendar and Gmail only. Remove every other one.
- **Network:** a custom allowlist (the only websites the task may reach): query1.finance.yahoo.com, query2.finance.yahoo.com, fc.yahoo.com, guce.yahoo.com, finnhub.io, api.open-meteo.com, api-endpoint.mta.info, site.api.espn.com, www.reddit.com, oauth.reddit.com, i.redd.it, api.resend.com, plus the default package list. If news research fails under the allowlist, switch network access to Full.
- **Network secrets:** FINNHUB_API_KEY, RESEND_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET.

Then: **Run now**, check the email, reply to it once, and confirm the reply shows up in `feedback/FEEDBACK.md` the next morning (`git pull` in ~/code/the-7am to see it).

## Monthly: refresh the S&P 500 list

Market caps in `data/sp500.csv` drive the standout stock and the earnings filter. Once a month, in ~/code/the-7am:
`! .venv/bin/python -m brief.sp500` then commit and push the CSV (or ask Claude to).
