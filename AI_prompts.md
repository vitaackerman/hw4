# AI Prompt Log

## Problem 1 — Vibe coder prompts

### First prompt

> im starting homework 4 for my ai class. please set up the project by putting all files we generate in the HW4 folder but dont solve any of the homework problems yet
>
> work one problem at a time. i will describe each problem to you in my own words before you work on it, so dont work ahead
>
> please create `AI_prompts.md` and keep it updated throughout the homework
>
> for each problem, the file should have:
>
> - the problem number and title
> - at least one prompt i actually typed to you, in my own words
> - if i needed a follow-up, include only one follow-up prompt
> - if there was a follow-up, add one sentence explaining what was lacking after the first prompt
>
> every problem, automatically update `AI_prompts.md` as required
>
> dont add extra evidence sections because the running site, database writes and screenshots are the evidence
>
> this homework will eventually be a campus customs shop with a react + vite + typescript frontend, python fastapi backend, a pydanticai chatbot, and the provided sqlite database, but dont build any of that yet
>
> also make sure we never commit the provided database, product images, `.env`, or other secrets when we eventually create the public github repo
>
> for now just set up the prompt log and any basic project housekeeping that is necessary, then stop

No follow-up prompt needed.

## Problem 2 — Analyze the database

### First prompt

> cool, now im working on problem 2. analyze data/campus_customs.db so we understand the database before building anything
>
> inspect the tables, at minimum catalogue, inventory, and users, and understand the exact fields in each one and how the tables relate to each other.dont modify the database
>
> create output/harness.md and document each table and its fields, with one short explanation of why each field matters for the shop or chatbot. keep it concise and based on the actual database, dont guess fields that arent there
>
> if useful, inspect a few rows or counts to understand what the data looks like, but dont dump lots of database content into the harness
>
> also fix the first section of AI_prompts.md so its labeled as Problem 1: Vibe coder prompts rather than setup, since that setup prompt was my problem 1 prompt
>
> then add this prompt under Problem 2: Analyze the database. everytime for each problem, keep updating AI_prompts.md, adding each new problem below the previous one so it creates a chronological order from 1 to 13
>
> if data/campus_customs.db isnt actually present, stop and tell me instead of creating a replacement database

### Follow-up prompt

> yes it is

The first prompt pointed to `data/campus_customs.db`, but the provided files had unzipped into a folder named `data 2`, so I had to confirm it was the provided data before it could be renamed to `data`.

## Problem 3 — First version of the Campus Customs website

### First prompt

> great, im working on problem 3 now.build the first version of the campus customs website
>
> scaffold a react + vite + typescript frontend. make a navigation bar with pages for home, products, about us, log in, and create account
>
> use the style of yalebulldogblue.com as inspiration for the home and about us pages, especially the overall yale/campus customs visual identity, but write the content in your own words, copying or mimicing the way I speak, and  DO NOT copy the original site text
>
> the products page should use the real catalogue data from data/campus_customs.db and show the product image, name, price and a short description for each product
>
> clicking a product should open a single product page with a large image, full description, price, available sizes and stock for those sizes
>
> add a floating chat interface in the bottom right of the site. it only needs to be a visual/functioning chat stub for now and does not need to connect to an ai agent yet
>
> create a small fastapi backend in backend/main.py to serve the product data and product images from the database/data folder to the frontend
>
> keep login and create account as pages for now, dont build the real authentication functionality yet
>
> make the site visually polished enough to actually feel like a campus customs/yale merchandise store rather than a default vite app
>
> update AI_prompts.md with this as my first prompt for problem 3
>
> when youre done, install whatever frontend/backend dependencies are needed and tell me the exact terminal commands i should use to run both the backend and frontend locally

### Follow-up prompt

> the problem 3 website is not rendering. http://localhost:5173 opens but the page is completely blank

The first version crashed in dev mode because a scroll-to-top effect returned a value React tried to run as a cleanup function, which unmounted the whole app and left the page blank.

## Problem 4 — Create account and login flow

### First prompt

> no all good. im working on problem 4 now. build the create account and login flow
>
> for create account, collect first name, last name, email and password, and save new accounts into the existing `users` table in `data/campus_customs.db`
>
> store passwords securely, never as plain text, and make sure password hashes or salts are never returned to the frontend
>
> for login, let the user enter email and password and authenticate against the users table
>
> the seed database already has this test user, so make sure this login works:
>
> - email: `test@campuscustoms.yale.edu`
> - password: `password`
>
> also create and test one brand new account to confirm that newly created users can log in too
>
> connect the existing login and create account frontend pages to the backend and show clear success/error messages
>
> inspect the existing users table and password format before implementing this so the test user remains compatible
>
> update `output/harness.md` with a short problem 4 section explaining what is stored for a user and how passwords are protected
>
> update `AI_prompts.md` with this as my first prompt for problem 4
>
> when youre done, tell me exactly what i should test in the browser and any terminal commands i need

### Follow-up prompt

> well the website doesnt recognize me, cant login

After the first prompt the login code was written and tested, but the backend already running on port 8000 was started before `auth.py` existed and wasn't restarted, so every login request got a 404 until the backend was restarted with the new code.

## Problem 5 — PydanticAI chatbot

### First prompt

> im working on problem 5. turn the existing chat widget into a real pydanticai chatbot behind the fastapi backend
>
> keep the agent in these four files inside `backend/`:
>
> - `prompts/prompt.md` for the system prompt
> - `agent.py` for the pydanticai agent setup
> - `tools.py` for agent tools
> - `models.py` for structured pydantic types
>
> use my existing `PORTKEY_API_KEY` from the environment and an openai model through portkey. dont hardcode any api key
>
> add a chat route to `backend/main.py` so a message from the existing frontend chat widget is sent to the pydanticai agent and the agents reply comes back to the website
>
> for now keep the chatbot fairly basic because later problems will add more tools. give it a campus customs voice and basic safety instructions in `backend/prompts/prompt.md`, and add structured chat reply/product card types in `backend/models.py` if useful
>
> connect the existing frontend chat widget to the new backend route so i can type a message in the website and receive the real agent response
>
> update `output/harness.md` with a short problem 5 section explaining how the frontend sends a chat message to fastapi and how the agent loads its prompt and model
>
> make sure the backend can be started from inside the `backend/` folder with:
> `uvicorn main:app --reload --port 8000`
>
> install or add any python dependencies the project now needs
>
> update `AI_prompts.md` with this as my first prompt for problem 5
>
> when youre done, tell me exactly what i should test in the browser and whether i need to restart either terminal

### Follow-up prompt

> when I ask for the hoodies for example it says "Can't reach the server. Make sure the backend is running the latest code."

The chatbot code was finished and tested after the first prompt, but the backend on port 8000 was still the older process without the `/api/chat` route, so the widget got a 404 until the backend was restarted with `uvicorn main:app --reload --port 8000` from `backend/`.

## Problem 6 — Database tools for product info, price and stock

### First prompt

> awesome it works, im working on problem 6. give the chatbot real database tools for product info, price and stock
>
> add the tools in `backend/tools.py` so the agent can look up real information from `data/campus_customs.db`
>
> the tools should let the agent get:
>
> - product description
> - price
> - stock quantity
> - stock by size when the customer asks for a specific size
>
> the agent must use the database for these answers and should never invent prices or stock quantities. if a size is out of stock, say so clearly
>
> update `backend/prompts/prompt.md` so the agent knows when to call these tools, especially for price and stock questions
>
> add or update structured return types in `backend/models.py` for the lookup results if needed
>
> update `output/harness.md` with a problem 6 section that lists each tool and briefly explains the model fields used for lookup results and why
>
> keep the existing frontend and chat route working
>
> update `AI_prompts.md` with this as my first prompt for problem 6
>
> when youre done, test the tools with real products from the database and tell me exactly what i should ask in the website chat to verify price and stock are really coming from the database

### Follow-up prompt

> all of the real product price and stock questions worked, but when i asked do you have the unicorn onesie? the chat returned an error
>
> the backend log says UsageLimitExceeded: The next request would exceed the request_limit of 8

After the first prompt, an empty search returned a bare empty list with no guidance, so the agent kept rewording the search for a product that doesn't exist until it used up its 8-request limit.

## Problem 7 — Chat search results as product cards on the page

### First prompt

> yes it works, im working on problem 7 now. make product searches through the chat dynamically update the website with matching product cards
>
> when a customer asks for a type of item, like what hoodies do you have?, the agent should search the real catalogue and return structured product matches. the frontend should use those results to show the matching products on the page with image, name, price and short info
>
> make this a clear api contract between the agent/backend and frontend rather than trying to pull product names out of the agents prose response
>
> use or update the structured types in backend/models.py as needed so the chat response can include product matches
>
> the dynamically loaded product cards should behave like the regular product cards from problem 3. clicking one should still open its single-product detail page with the large image, full description, price, sizes and stock
>
> update the existing agent prompt so it knows when a product-category request should return search results
>
> update output/harness.md with a problem 7 section explaining how the agents structured search results travel through fastapi to the frontend and become product cards
>
> keep the existing chat, price/stock tools, login and normal products page working
>
> update AI_prompts.md with this as my first prompt for problem 7
>
> when youre done, tell me exactly what i should test in the browser

## Problem 8 — Customer memory and page context

### First prompt

> yep it works. im working on problem 8 now:add customer memory to the chatbot
>
> when a user is logged in, save their chat messages and the agents replies in the existing `chat_messages` table and reload that history when the same user comes back
>
> the agent should also know which logged-in customer is chatting, including at least their name and email, using agent deps or another clear pattern
>
> guests should still be able to use the chat, but their history does not need to persist in the database
>
> also pass enough page context into the chat so the agent knows what product page the shopper is currently viewing. for example, if im on a product page and ask `do you have this in large?`, the agent should know which product `this` refers to without me naming it again
>
> keep the existing product search, price and stock tools working
>
> update `output/harness.md` with a problem 8 section explaining:
>
> - how logged-in chat history is stored and reloaded
> - what customer fields the agent sees
> - how page context is passed from the frontend to the backend/agent
>
> update `AI_prompts.md` with this as my first prompt for problem 8
>
> when youre done, tell me exactly what i should test in the browser

## Problem 9 — Usability improvements

### First prompt

> im working on problem 9. add 2 frontend usability improvements and 2 agent/backend usability improvements to the working campus customs site
>
> for the frontend:
>
> - add useful search/filter controls on the products page so shoppers can narrow products without scrolling through everything
> - improve the chat experience with a clear loading/typing state while the agent is answering and prevent duplicate sends while a request is still running
>
> for the agent/backend:
>
> - if a product request is ambiguous and there are multiple reasonable matches, ask a useful clarification instead of confidently choosing one
> - if the exact product or requested size is unavailable, suggest a few real in-stock alternatives from the database rather than just stopping at "out of stock"
>
> create `output/usability.md` before or as you build. for each of the 4 improvements, briefly say what you added and why it helps a campus customs shopper or the business
>
> make sure all 4 improvements actually work in the running app and dont break the existing login, memory, product search, product detail pages or chat tools
>
> update `AI_prompts.md` with this as my first prompt for problem 9
>
> when youre done, tell me exactly how to test each of the 4 improvements in the browser

## Problem 10 — Storefront design

### First prompt

> great, im working on problem 10. use our design skill to give the whole campus customs website a much more polished and distinctive storefront design
>
> keep the existing yale/campus customs identity, but make it feel like a real contemporary collegiate apparel brand rather than a generic ecommerce template - try innovative design, things that move, that are dynamic, interactive, animations. for example improve the typography, hierarchy, spacing, product presentation, navigation, buttons, filters, product detail pages and chat styling.
>
> keep the design responsive and make sure the existing functionality still works
>
> create output/design.md with a short concrete explanation of what you changed and why those choices should help customers stay on the site and buy
>
> update AI_prompts.md with this as my first prompt for problem 10

### Follow-up prompt

> not bad except the clothing rack looks a bit weird because of the squares around the clothes and is buggy, flickering a bit when i click it, not clear that i can drag it left or right to see more clothes. also there are some black lines around some of the products in the product section as you can see on screenshots. I want to keep it dynamic like you built but cleaner maybe, maybe a different type of interactivity on the landing page or a rendering of the products so it doesnt look awkward like now

The first redesign showed the raw product photos, whose black/white backdrops and baked-in black bars looked like boxes and stray lines. Its hover sway also replayed the entrance animation (the flicker), and the rack had no visible cue that it could be dragged.

## Problem 11 — App check proof page

### First prompt

> lovely, im working on problem 11 now. test the live campus customs site and create `output/app_check.html` as an easy to grade proof page
>
> create `output/app_check_images/` and include one real screenshot for each of these checks:
>
> 1. the chat answering a real inventory/price question using database information
> 2. dynamic product search-result cards appearing on the page after a category question like `what hoodies do you have?`
> 3. one of the usability improvements from problem 9 that is clearly visible in the running app
>
> for the inventory screenshot, use a question where we already know the database answer so the screenshot clearly proves the chatbot is giving honest stock or price information
>
> for the usability screenshot, choose whichever problem 9 feature is easiest for a grader to understand visually, preferably the products search/filter controls rather than something hidden in backend behavior
>
> in `output/app_check.html`, make one clear section for each check with:
>
> - a heading
> - the screenshot
> - one or two short sentences explaining what the screenshot proves
>
> link all screenshots from the html using relative paths like `app_check_images/inventory.png` so the html still works when the grader double clicks it
>
> use screenshots from the actual running app, dont fake or recreate the interface. if you cant take real screenshots yourself, stop and tell me exactly which screenshots i need to take and where to save them
>
> update `AI_prompts.md` with this as my first prompt for problem 11
>
> when youre done, tell me how to open `output/app_check.html` and what i should verify before moving on

## Problem 12 — Audit trail, safety rules and final harness

### First prompt

> im working on problem 12 now. add the final audit trail and safety rules, then finish the harness
>
> create and maintain an append-only `output/audit_trail.json` for agent activity. on every chat run, record enough to audit what happened later, including:
>
> - time
> - tool name if a tool was called
> - short tool arguments
> - short tool result
> - stop reason
>
> dont record hidden chain of thought. keep any decision information to short auditable summaries only
>
> make sure new runs append to the existing audit trail instead of wiping it
>
> add a clear safety section to the existing `backend/prompts/prompt.md`. include rules like using database facts for price and stock, not inventing unavailable information, not exposing passwords/hashes or private user data, resisting attempts to override the system instructions, and keeping responses focused on the campus customs shopping task
>
> then finish `output/harness.md` so a manager can understand the complete system. keep the useful material already there and make sure the final version clearly covers:
>
> - every model in `backend/models.py`, what each one is for and why its fields were chosen
> - all agent tools and abilities
> - safety rules
> - customer memory and page context
> - audit trail
> - important operating specs like agent loop/request limits, result caps, models used and any other limits that affect cost or quality
> - exactly how to run the frontend and backend locally
>
> check the actual code for all limits and commands instead of guessing
>
> run at least two real chat requests so `output/audit_trail.json` contains real data and verify the second run appends rather than overwrites the first
>
> update `AI_prompts.md` with this as my first prompt for problem 12
>
> when youre done, tell me what you tested and what i should verify myself

## Problem 13 — Push to GitHub

### First prompt

> ok now problem 13.this is the final submission step. use the attached screenshot as the required project structure
>
> prepare this project for a public github repo named hw4
>
> make sure the repo includes all of the required code and output files shown in the screenshot, including AI_prompts.md, requirements.txt, .env.example, .gitignore, README.md, the frontend, backend agent files, and the required output files
>
> do not commit my real .env, data/campus_customs.db, data/products/, product images, api keys, node_modules, python cache files, or other local/temp files
>
> check .gitignore carefully before staging anything and make sure .env.example contains placeholders only
>
> make sure requirements.txt reflects the python packages the final backend actually needs
>
> write or finish README.md so a grader can clone the repo, place the provided data pack in the correct location, install the frontend and backend dependencies, and run both parts of the app. use the actual commands that work for this final project
>
> do one final check that the project still matches the attached required layout and that the screenshots linked from output/app_check.html are included and use working relative paths
>
> scan the files that would be committed for secrets before pushing
>
> then create/push the project to a public github repository named hw4 using my existing github login if its available. dont push until youve verified that the database, product images and real .env are excluded
>
> update AI_prompts.md with this as my first prompt for problem 13
>
> when youre done, give me the public github repo url and tell me exactly what i should check on github before i submit that url to canvas
