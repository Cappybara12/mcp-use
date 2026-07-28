"""
Real article format patterns learned from Wayzyy's published articles.
Used to guide the planner when building outlines.
"""

BEACH_GUIDE_FORMAT = """
H2 pattern for beach guides (use as inspiration, adapt to topic):
1. [Beach Name] at a Glance
2. Should I Stay in [Beach Name]? (or: What [Beach] Is Actually Like)
3. Which Part of [Beach] Should You Stay In?
   H3: The Northern End — Best for [type]
   H3: The Central Stretch — Best for [type]
   H3: The Southern End — Best for [type]
   H3: Beach Hut vs Villa vs Hotel — What Should You Book?
4. Best Time to Visit [Beach Name]
   H3: November to February — The Best Time
   H3: March to May — Warm but Less Crowded
   H3: June to September — The Monsoon Season
   H3: October — The Hidden Sweet Spot
   H3: Month-by-Month Quick Guide (table format)
5. Things to Do in [Beach] Without Feeling Rushed
6. Where to Eat in [Beach]: Cafés and Restaurants Worth Visiting
7. [Beach] Nightlife: What It's Really Like in 2026
8. Practical Things Nobody Tells You About [Beach]
   H3: Is Mobile Network Good?
   H3: Are There ATMs Nearby?
   H3: Is Parking Easy?
   H3: Is [Beach] Expensive?
   H3: How Many Days Should You Spend Here?
   H3: Is It Good for Families?
   H3: Is It Good for a Workation?
   H3: What Should You Pack?
9. [Beach] vs [Alt1] vs [Alt2]: Which Should You Choose?
   H3: Choose [Beach] if you want [X]
   H3: Choose [Alt1] if you want [Y]
   H3: Choose [Alt2] if you want [Z]
   H3: The Verdict
10. Local Tips Before You Book
11. Common Mistakes Visitors Make at [Beach]
12. Final Thoughts: Is [Beach] Worth Staying In?
13. Frequently Asked Questions About [Beach]
"""

DESTINATION_GUIDE_FORMAT = """
H2 pattern for destination/travel guides:
1. [Destination] at a Glance
2. Is [Destination] Worth Visiting? (set honest expectations)
3. What [Destination] Is Actually Like
4. How to Reach [Destination]
   H3: By Road (with distances + time from key towns)
   H3: By Train/Bus (if applicable)
   H3: Parking at [Destination]
5. Best Time to Visit
6. What to See and Do (specific, not generic)
7. [Destination] vs [Alternatives]: Which Should You Choose?
8. Where to Stay Near [Destination]
9. Practical Information
   H3: Entry fees / timings
   H3: Photography rules
   H3: Facilities (washrooms, ATMs, food stalls)
   H3: Mobile network
   H3: How long to spend
10. Local Tips and What Most Guides Won't Tell You
11. Common Mistakes Visitors Make
12. Is [Destination] Good for Families / Couples / Solo?
13. Final Thoughts
14. Frequently Asked Questions
"""

ACCOMMODATION_GUIDE_FORMAT = """
H2 pattern for villa/stay/accommodation guides:
1. Why [Area] Has Become the Most Popular Stay in Goa
2. What Makes [Area] Different from Other Parts of Goa
3. Types of Stays Available in [Area]
   H3: Villas (with private pools)
   H3: Homestays
   H3: Boutique guesthouses
4. Best Areas / Neighbourhoods to Stay In
5. What to Expect from a [Area] Villa Stay
6. Price Range: What ₹X–₹Y Gets You in [Area]
7. Best Time to Book (and When Prices Spike)
8. [Area] vs [Alternative]: Which is Better for Your Trip?
9. Practical Staying Tips
10. What Guests Often Get Wrong When Booking
11. Final Thoughts
12. Frequently Asked Questions
"""

TITLE_PATTERNS = [
    "{Place} (2026): The Honest Guide to {Subtopic}",
    "{Place} Guide (2026): {Subtopic}",
    "{Place} (2026): Is It Really Worth Visiting? The Honest Guide",
    "{Place} (2026): Why {Audience} Keep Recommending It",
    "Best Time to Visit {Place} — The Complete Guide for Every Vibe",
    "{Place} vs {Place2}: Which One Is Right for You?",
    "Where to Stay in {Place} (2026): The Honest {Type} Guide",
    "How to {Action} in {Place} (2026): Everything Nobody Tells You",
]

INTRO_PATTERNS = """
Strong intro approaches used in Wayzyy articles:

1. Acknowledge what people search/expect, then subvert:
   "If you've ever searched for [X], you've probably come across [Y].
   Almost every guide recommends it. Travel blogs describe it as [generic praise].
   Here's what it's actually like."

2. Direct scene-setting (no fluff):
   "Agonda Beach is one of South Goa's best-kept secrets. Spanning three kilometres
   of pristine sand lined with coconut palms, it offers a stark contrast to the
   commercial hubs of the north."

3. The honest question opener:
   "Planning to stay in Vagator? Read our honest guide to [specific practical things]."

NEVER start with:
- "Goa is one of India's most popular..."  (obvious)
- "Nestled along the..."  (AI cliché)
- "Welcome to our comprehensive guide..."  (generic)
- "Are you planning a trip to..."  (lazy)
"""

FAQ_GUIDELINES = """
FAQ section guidelines:
- 8-12 questions minimum
- Source from: Reddit threads, People Also Ask, travel forums
- Each answer: 2-4 sentences, practical and direct
- Cover: practical logistics + opinion questions + comparison questions
- Example good FAQ questions:
  "Is [X] worth visiting?"
  "How many days should I spend in [X]?"
  "Is [X] safe for solo travellers?"
  "Is [X] good for families?"
  "Which is better: [X] or [Y]?"
  "What is the best time to visit [X]?"
  "Can you swim at [X]?"
  "Is [X] expensive?"
  "Do I need a scooter in [X]?"
  "Is mobile network good in [X]?"
"""
