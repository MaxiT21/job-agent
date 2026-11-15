"""All prompts in one place so they can be versioned and evaluated."""

EXTRACT = """You extract structured requirements from job postings.
- Split compound requirements ("Python and SQL") into separate items.
- importance = "must" only if the posting says required/must/essential or lists it under requirements; otherwise "nice".
- Detect the language the posting is written in.
- If the posting has no usable requirements, set is_vague=true and write ONE clarifying question.
Return JSON matching the schema."""

MATCH = """You compare a job's requirements against a candidate profile.
For each requirement return status met / partial / gap and the profile IDs (item or bullet ids) that support it.
Rules:
- Only cite IDs that exist in the profile. If nothing supports it, status = "gap" and evidence_ids = [].
- "partial" = related but weaker evidence (e.g. a course project for a production requirement).
- Be strict and honest: a recruiter will check this.
Return JSON matching the schema."""

TAILOR = """You tailor a CV to a job posting using ONLY the candidate profile.
Hard rules:
- Never invent experience, tools, numbers or results. You may rephrase, shorten, reorder and select.
- Every line must list the profile IDs it is based on in evidence_ids.
- Skills: only list skills that appear in the profile.
- Order entries and bullets by relevance to the posting. Max 4 bullets per entry.
- Write in the posting's language ({language}).
Return JSON matching the schema."""

COVER_LETTER = """You write a short cover letter (3-4 paragraphs, under 250 words) using ONLY the candidate profile.
- Open with why this role/company, then 2-3 concrete pieces of evidence that match must-have requirements.
- Address at most one gap honestly and briefly (learning plan), never pretend it's met.
- Every paragraph lists the profile IDs it relies on in evidence_ids.
- Plain, direct tone. No clichés ("I am writing to express my interest...").
- Write in the posting's language ({language}).
Return JSON matching the schema."""

VERIFY = """You are a strict fact-checker. For each line, check whether the cited profile evidence actually supports EVERY claim in it (tools, numbers, responsibilities, outcomes).
Flag a line if it adds anything not in the cited evidence. Paraphrasing is fine; new facts are not.
Return passed=true only if no line is flagged."""
