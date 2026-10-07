---
title: A missing cookie is not proof that cookies are disabled
summary: How a false “cookies disabled” error on my own thesis page became a small, bounded fix in Anubis.
date: 2026-10-07
tags: [Go, Open source, Web security, Anubis]
---

I ran into this bug while trying to open my own master's thesis. Uppsala University's DiVA portal sits behind [Anubis](https://github.com/TecharoHQ/anubis), the proof-of-work challenge that many sites now put in front of their pages to slow down scrapers. My browser solved the challenge, and Anubis then told me I had cookies disabled. I didn't.

## The challenge flow

When Anubis challenges a visitor, it also sets a verification cookie. The browser solves the proof-of-work and submits the result, and the server checks two things: that the solution is valid, and that the verification cookie came back with it.

If the cookie was missing, Anubis took that as proof that the browser doesn't keep cookies, cleared its cookies and showed the "cookies disabled" error. There's a reason for stopping there: a client that can't store cookies can never hold the pass Anubis gives it, so sending it through another challenge would loop forever.

## Where the assumption breaks

A missing cookie has two explanations. Either the browser refuses cookies, or it accepted the cookie and lost it this one time. The code only allowed for the first.

The second is real. [Issue #1916](https://github.com/TecharoHQ/anubis/issues/1916) already had reports of browsers that accept cookies but drop the verification cookie in edge cases, such as Safari on a first navigation that was upgraded from HTTP to HTTPS. Starting a fresh challenge, for example with the error page's "Go home" link, worked for those users. The cookie loss was transient, but the error treated it as permanent.

## The fix

When the verification cookie is missing, send the client back once to the redirect target it was already heading for, so it gets a fresh challenge and a fresh cookie. The hard part is "once". The natural place to remember that a client has already retried is a cookie, and cookies are exactly what can't be trusted here. So the limit lives on the server:

- A retry is only granted when the submission refers to a live, unspent challenge, so arbitrary requests can't create retry state.
- It's recorded in Anubis's store under a hash of the client's IP address and User-Agent, and granted at most once per client per challenge lifetime (30 minutes).

```go
func (s *Server) shouldRetryMissingTestCookie(r *http.Request) bool {
	chall, err := s.getChallenge(r)
	if err != nil || chall.Spent {
		return false
	}

	key := "cookie-retry:" + internal.SHA256sum(
		r.Header.Get("X-Real-IP")+":"+r.Header.Get("User-Agent"))
	if _, err := s.store.Get(r.Context(), key); err == nil {
		return false
	}

	// Same lifetime as an issued challenge.
	return s.store.Set(r.Context(), key, []byte("1"),
		30*time.Minute) == nil
}
```

A browser that lost the cookie once gets a new challenge and passes. A browser that really has cookies disabled gets the same error as before, after one extra challenge instead of an endless loop. The warning that Anubis logs for operators is unchanged, so they see the same signal as before.

## Tests

The regression tests submit solved challenges with and without the verification cookie and check the outcome of each step:

- With the cookie, the client passes.
- After a first miss, the client is retried and then passes.
- Repeated misses end in the error.
- The retry is per client: a different User-Agent gets its own.
- An unknown challenge isn't retried.
- A spent challenge isn't retried.

The last four matter as much as the first two. They pin down that the retry can't be turned into a loop or created out of nothing.

## Upstream

I submitted the change as [TecharoHQ/anubis#2004](https://github.com/TecharoHQ/anubis/pull/2004), with a changelog entry. The maintainer, Xe Iaso, changed the separator in the store key so it also works with S3-style storage backends, and merged it on 6 October 2026.

The mistake in the original code is a common one: treating a single missing signal as proof of its most likely cause. The fix keeps the same conclusion but only draws it after seeing the cookie missing twice, and it keeps the record of the first miss somewhere the failure can't erase it.
