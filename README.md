<picture><source media="(prefers-color-scheme: dark)" srcset="assets/header-dark.svg"><img alt="Evan Alferez. I build the software Japanese businesses run on." src="assets/header-light.svg" width="100%"></picture>

<br>

I'm Evan. I build commercial software in Japan and see it all the way through: schema, code, deployment, and the client meeting in between. Most of what I ship is deliberately unglamorous. Accounting integrations that pass Shopify's App Store review, a booking system that can't double-book, an app parents open every morning before school.

Most of that work is closed-source product and client code, so the public repos here are only part of the picture. The rest is below.

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/sections/work-dark.svg"><img alt="Work" src="assets/sections/work-light.svg" width="100%"></picture>

<a href="https://choubalab.com"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/chouba-lab-dark.svg"><img alt="Chouba Lab: Orders, refunds and payout fees become itemised, tax-correct journal entries in freee." src="assets/cards/chouba-lab-light.svg" width="50%"></picture></a><a href="https://sabizu.com"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/sabizu-dark.svg"><img alt="Sabizu: Booking for one-person shops. Overlapping slots are rejected by Postgres itself." src="assets/cards/sabizu-light.svg" width="50%"></picture></a>
<a href="https://apps.apple.com/jp/app/happy-island/id6760802460?l=en-US"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/happy-island-dark.svg"><img alt="Happy Island: School messaging for primary-school families, on iOS, Android and the web." src="assets/cards/happy-island-light.svg" width="50%"></picture></a><a href="https://github.com/evanclan/OpenJLPT"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/openjlpt-dark.svg"><img alt="OpenJLPT: 7,811 words, 2,383 kanji and 526 grammar points, on npm, PyPI and SQLite." src="assets/cards/openjlpt-light.svg" width="50%"></picture></a>
<a href="https://www.raja-r.com"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/raja-r-dark.svg"><img alt="raja-r.com: A study-abroad agency moved off Jimdo without losing the rankings it had earned." src="assets/cards/raja-r-light.svg" width="50%"></picture></a><a href="https://github.com/evanclan/natsuki-attendance"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/attendance-dark.svg"><img alt="Attendance: RFID and QR check-in, payroll, and LINE alerts to guardians for schools." src="assets/cards/attendance-light.svg" width="50%"></picture></a>
<a href="https://www.facebook.com/mgakaguro.page/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/guro-ako-dark.svg"><img alt="Guro Ako: A community, a video channel and a web platform for Filipino teachers." src="assets/cards/guro-ako-light.svg" width="50%"></picture></a><picture><source media="(prefers-color-scheme: dark)" srcset="assets/cards/ryuugaku-quest-dark.svg"><img alt="Ryuugaku Quest: Right answers are attacks. Missed words respawn through spaced repetition." src="assets/cards/ryuugaku-quest-light.svg" width="50%"></picture>

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/sections/progress-dark.svg"><img alt="In progress" src="assets/sections/progress-light.svg" width="100%"></picture>

- **Chouba Lab for Money Forward.** The same journal engine, pointed at Money Forward. The first live webhook posted a real entry to a production ledger, and it now handles Money Forward's refresh-token rotation race.
- **RaJA Global Academy.** A bilingual Japanese/English rebuild of a school's website on Next.js, replacing Jimdo.
- **Perception.** A research build that captures four screen streams in parallel and compresses each frame to 30–128 KB, so an agent can learn what someone is actually doing at a desktop.

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/sections/method-dark.svg"><img alt="How I work" src="assets/sections/method-light.svg" width="100%"></picture>

- **Put invariants in the database.** If two bookings must never overlap, Postgres enforces it with an exclusion constraint, not an `if` in a request handler.
- **A migration should never cost the client their search traffic.** Redirects, canonicals and the sitemap are verified against the live domain before anyone calls it launched.
- **Keep secrets out of git.** I keep one registry of which account owns which project across my three machines, so neither I nor a coding agent deploys to the wrong one. It stores IDs and variable names only, and a check scans for keys before every commit.
- **Make the type system enforce translation.** On [evanserv.com](https://www.evanserv.com), a project without both English and Japanese copy fails to compile.
- **Treat Japanese business rules as the product.** Consumption tax, freee, Money Forward and LINE are where the real work is, not edge cases.

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/sections/stack-dark.svg"><img alt="Stack" src="assets/sections/stack-light.svg" width="100%"></picture>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/stack-dark.svg"><img alt="Stack: TypeScript, React, Next.js, React Native, Remix, PostgreSQL, Supabase, Prisma, Vercel, Fly.io, Cloudflare Workers, Shopify apps, freee, Money Forward, Stripe, LINE, Claude, OpenAI, Gemini, MCP, n8n, Godot and Adobe tools." src="assets/stack-light.svg" width="100%"></picture>

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/sections/activity-dark.svg"><img alt="Activity" src="assets/sections/activity-light.svg" width="100%"></picture>

<picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/evanclan/evanclan/output/activity-dark.svg"><img alt="Contribution activity over the last twelve months" src="https://raw.githubusercontent.com/evanclan/evanclan/output/activity-light.svg" width="100%"></picture>

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/sections/contact-dark.svg"><img alt="Elsewhere" src="assets/sections/contact-light.svg" width="100%"></picture>

[evanserv.com](https://www.evanserv.com) &ensp;·&ensp; [LinkedIn](https://www.linkedin.com/in/evanalferez) &ensp;·&ensp; Happy Island on [App Store](https://apps.apple.com/jp/app/happy-island/id6760802460?l=en-US) and [Google Play](https://play.google.com/store/apps/details?id=com.happyisland.app)

I work in English, 日本語, Cebuano and Tagalog. ご相談は日本語でも英語でもお気軽にどうぞ。

<br>

<sub>Every graphic on this page is drawn by <a href="scripts/draw.py"><code>scripts/draw.py</code></a>. The activity panel is redrawn every morning by GitHub Actions.</sub>
