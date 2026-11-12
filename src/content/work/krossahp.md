---
title: KrossaHP
summary: Daily practice for Högskoleprovet, the Swedish university admissions test. Each session is built from your own mistakes and the subtests where you have the most points to gain.
year: 2026
role: Founder, design & development
tags: [TypeScript, Next.js, PostgreSQL, Education]
link: https://krossahp.se
order: 2
cover: ../../assets/work/krossahp.png
coverDark: ../../assets/work/krossahp-dark.png
---

KrossaHP is a web app for practising Högskoleprovet, the standardized test used for admission to Swedish universities. It is in Swedish and live at [krossahp.se](https://krossahp.se), where you can start without an account.

## The problem

The usual way to prepare is to sit old exams. An old exam shows what the test looks like, but it gives you 160 questions in the test's own order and one score at the end. It doesn't say what to practise tomorrow, and a question you missed shows up once, in the answer key.

## A daily session

KrossaHP gives you one short session a day, about 12 questions. The session is put together from questions you got wrong earlier, the subtests where you have the most points to gain, and a few mixed questions from the rest. Each question says why it was picked. A question you miss comes back after roughly 1, 3, 7, 16 and 35 days.

With every answer you also say whether you were sure or guessing. A lucky guess doesn't count as knowledge, so guessed questions are repeated too. After answering you see why the option you picked was tempting, how the question is solved and a strategy to take to the next one.

The app covers all eight subtests, four verbal and four quantitative.

## The score forecast

Each half of the test is normalized to a scale from 0.0 to 2.0. KrossaHP forecasts where you stand on that scale as an interval, which narrows as you train, and shows how many more correct answers your goal needs. The site promises no score increase.

The design follows three well-supported principles from learning research: retrieving knowledge from memory, spacing repetition over time and mixing question types.

## How it is built

The app is written in TypeScript with Next.js and React, and stores progress in PostgreSQL through Drizzle. Paid plans go through Stripe. Guests train without signing in, and an account (Google or an emailed link) carries progress across devices. Unit tests for the domain logic and the question bank run on Bun, and Playwright covers the user journey at phone and desktop sizes.
