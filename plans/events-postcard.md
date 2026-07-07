Yes — programmatic postcards are very much a real thing, and it's cheap enough to be exactly the kind of cursed/wholesome gem sink you're describing.

## Postcard / mail APIs
- **Lob** — the most developer-friendly one in the US. Postcards via REST API, you upload a front/back design (HTML templates or PDF), pass an address, they print + mail it. Roughly a couple bucks a card depending on size/volume. Great docs, sandbox mode for testing. This is the one I'd reach for first if you're all US-based.
- **PostGrid** — very similar to Lob (US + Canada), postcards/letters/cheques, address verification built in.
- **Stannp** — UK/Europe-based, known for being *cheap* and having a clean API. Worth it if any of the three of you are outside the US.
- **Handwrytten** — sends *actual handwritten* notes/cards via robot pens. More expensive, but the "a real card in real handwriting showed up because you hit a collective goal" payoff is absurd in the best way.
- **Click2Mail / Mailform** — more old-school, less slick APIs, but they exist.

The fun version for your app: a gem item (or a collective-goal **event**) that fires a Lob call to mail one of the others a deliberately stupid postcard — "Certified by the Sweat Council: your friend did 100 pushups and thought of you." Verify current pricing before you commit, but mentally budget ~$1–3/card.

## On events as a first-class citizen
This is the right instinct, and it ties your three loose threads (Forbidden Button, curses, collective goals) into *one primitive*. An **Event** is basically:

- **a trigger** — admin-fired, user-purchased (Forbidden Button / curse), or collective-goal-reached
- **a target** — everyone, one user, or the caster
- **an effect** — a payload the client renders on next load

If you model it that way, "Double Gem Weekend," "You are now the Gains Goblin," "confetti on all phones," and "we collectively hit 1,000 miles so a postcard ships" are all *the same feature* with different rows. The Gains Goblin one is great precisely because the effect is pure client theater: green theme tint + a goblin sprite wandering the background + a dismiss banner. No real-world stakes, all vibes.

A couple of design notes that make events sing:
- **Effects should be data, not code** — `{type: "theme_curse", variant: "goblin", expires_at: ...}` so you can add new curses without shipping a release each time.
- **Curses want a reveal moment** — the "greeted on next page load" banner is the whole joke. Make that interstitial a real, dismissible thing, not a passive style change they might not notice.
- **Keep a log** — an event feed ("Tuesday: Dan was cursed. Wednesday: collective goal hit, postcard mailed to Maxwell") becomes its own source of group-chat comedy.
- **Cheap Forbidden Button** — agreed, keep it low-cost so it gets *spammed*. The comedy is in frequency, not scarcity.

Want me to keep riffing on event ideas, or do a quick read of your codebase to see how gems/achievements are currently modeled so the "Event" primitive would slot in cleanly when you're ready to build it?

---

Lob vs PostGrid: I'd have to try them both. The pricing's close enough that the tiebreaker won't be the per-card cost, it'll be the stuff you only feel once you're elbow-deep:

- **Template ergonomics** — how painful is it to design the front/back? HTML templating vs. uploading a PDF, merge variables for names/stats, etc. This is where you'll spend the most time, so whichever has the nicer authoring flow wins.
- **Sandbox/test mode** — can you fire fake sends and see a proof image without spending real money or mailing real cards? Both should have this; check how good the preview render is.
- **Address verification** — you've only got two friends' addresses, so this barely matters for you, but it's nice if it catches a typo before mailing into the void.
- **The proof image** — both return a rendered preview URL of the actual card. Pipe *that* into your event feed so the group chat sees the dumb postcard the moment it's triggered, days before it physically lands.

Since you've got free tiers on both, the cheap experiment is: make one genuinely cursed test postcard in each, eyeball the proof, and see which API made you swear less. Whichever one you finish first is your answer.
