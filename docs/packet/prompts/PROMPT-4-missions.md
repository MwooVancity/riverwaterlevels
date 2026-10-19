# PASS 4: judge the missions, then run the best three (new chat)

The project's own assistant wrote a long audit prompt with twelve "missions" (`appendix/missions-A-to-L.md`: A reader pages, B attack the gates, C launch readiness, D data and APIs, E information gain, F the pipeline to every river, G operations, H product and the road to number one, I unknown unknowns, J the process itself, K the release queue and keywords, L verify what we say we fixed). The owner worries those missions are narrow, anchored on the assistant's own beliefs, and too many to answer in one go. Read `README-FIRST.md`, `00-CONTEXT.md`, `MANIFEST.md` and `appendix/missions-A-to-L.md`. Then:

1. For each mission, a verdict: KEEP, REWRITE (give the rewritten question in one or two sentences), MERGE (into which), or DROP, with the reason. Say which missions ask for work a chat model cannot do (live browsing, screenshots, running tests) and what to ask instead.
2. What is missing. The five or six most important questions about this project that none of the twelve missions asks (think strategy, demand, defensibility, distribution, unit economics, legal and safety exposure, whether the unit of the product is right, and the cost and yield of the review process itself). Write each as a mission of the same length as the originals.
3. The best three. Choose the three missions (original, rewritten or new) that would most change the owner's decisions, and run them now using the packet (`site/`, `code/`, `evidence/`). Use the labels [SEEN IN PACKET], [MY KNOWLEDGE, UNVERIFIED], [GUESS], say what you could not verify, and lead with the single most important finding.
4. A better single prompt. Rewrite the whole mission list as one prompt of at most 600 words that a model can finish in one answer, that does not state the project's conclusions, and that lets the model say the premise is wrong.

At most 3,000 words. Put your top three recommendations for the owner first.
