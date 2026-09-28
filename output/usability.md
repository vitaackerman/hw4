# Usability improvements (Problem 9)

Two frontend and two agent/backend improvements to the Campus Customs site. For each: what was added, and why it helps a shopper or the business.

## Frontend 1 — Products page filters

**Added:** A filter bar on the Products page with:
- keyword search (name, colors, tags, description)
- category chips
- **size in stock** (only products with at least 1 unit left in that size)
- **price** (Under $40 / $60 / $80)
- **color family** (navy, gray, white, red, blue, black, yellow, green, gold; groups like "navy blue" and "heather gray" folded in)
- **sort** (Featured, price low→high and high→low, name, most in stock)

Filters combine, show a live "N of 102 products" count, can be removed one at a time as chips or all at once with "Clear all", and are saved in the URL (`/products?size=L&max=60&color=Navy`). With a size selected, each card leads with how many are left in that size ("8 left in L · …"). Home-page category tiles and the back button keep working. For example, Size L + Under $60 + Navy narrows 102 products to 33, and every one really has L in stock.

**Why it helps:** 102 products is a lot to scroll on a phone. The most common real question is "what do you have in *my* size, in *my* budget?". The size filter answers it directly, so shoppers never click into a product only to find their size sold out. For the business, fewer dead-end clicks means fewer abandoned visits, and shareable filter URLs work for posts like "all navy crewnecks under $60".

## Frontend 2 — Clear chat loading state and no duplicate sends

**Added:**
- While the agent is answering, the chat shows a status line under the typing dots that changes over time ("Checking the catalogue…" → "Still looking, almost there…"), and the header status switches to "Typing…".
- The text box, send button and suggestion chips are disabled, and the send button shows a spinner.
- A synchronous lock (a ref, not React state) blocks a second send even from a fast double-press of Enter or a double-click, before React has re-rendered.

**Why it helps:** Agent replies take 1–5 seconds while it calls database tools. Without clear feedback, shoppers assume it's broken and send the question again. That produced duplicate questions and answers in the chat, duplicate saved rows in `chat_messages` for logged-in users, and extra paid model calls on the Portkey budget.

## Agent/backend 1 — Ask a clarifying question when a request is ambiguous

**Added:**
- When a price, stock or size question could mean several real products, the lookup tools return `needs_clarification` with 2–4 real candidates instead of picking one. For example, "how much is the Benjamin Franklin one?" matches a $32 tee, a $72 quarter-zip and a $98 fleece, and "is the Yale hoodie in large?" matches 27 hoodies. A name is treated as clear only when exactly one product's name contains every word the shopper used, so "Branford quarter zip" or a full product name still gets a direct answer.
- The agent returns them in a structured `clarification_options` field, and the API sends them as `clarification: {options: [...]}`.
- The chat shows each option as a tappable button (image, name, price). Tapping one sends "I mean the …" and the agent answers for that exact product.
- The prompt tells the agent to ask a short, specific question rather than guessing.

**Why it helps:** Confidently answering for the wrong hoodie gives the shopper a wrong price or stock number, which is worse than asking. Tappable options turn clarification into a single tap rather than retyping a long product name, and they only ever list real products from the database.

## Agent/backend 2 — Real in-stock alternatives when something is unavailable

**Added:** When a requested size is sold out, `check_size_stock` now returns `alternatives`: up to 3 similar products (same category, ranked by shared colors and tags) that do have that size in stock, with their real price and quantity for that size. It still returns the product's own `other_available_sizes`. When a product isn't in the catalogue at all (e.g. "unicorn hoodie"), the tools return real in-stock suggestions of the same kind of item, here hoodies. The prompt tells the agent to offer both, and the alternatives appear as clickable product cards. Real example: *"Large is sold out in the Boola Boola T Shirt. It's available in XS, S, M, XL and XXL. For a similar navy tee, the District Tri Blend T Shirt Vintage Shield is $32 with 8 left in L, or the Football Left Chest T Shirt is $32 with 2 left in L."* Both numbers match the database. Every alternative's price and stock also goes through the Problem 6 check that numbers must come from a tool.

**Why it helps:** "Sold out" is a dead end, and the shopper leaves. Offering a similar item in *their* size keeps the sale, and the alternatives are real, in stock and priced, so the shopper can act on them immediately.
