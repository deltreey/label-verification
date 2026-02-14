- Good. You’re thinking correctly. Before writing code, extract requirements.
  
  Below is a clean, structured requirements list derived from the document — broken into:
  
  * Functional Requirements
  * Non-Functional Requirements
  * UX Requirements
  * Performance Requirements
  * Batch / Workflow Requirements
  * AI / Edge Case Requirements
  * Technical Constraints
  * Deliverables
  * Explicit Evaluation Signals (what they’re really testing)
  
  ---
- # 1️⃣ Core Functional Requirements
  
  The app must:
  
  1. Accept a label image upload (single label).
  2. Extract text from the label (OCR or equivalent).
  3. Extract and identify required fields from the label:
  
   * Brand name
   * Class/type designation
   * Alcohol content
   * Net contents
   * Name and address of bottler/producer
   * Country of origin (if applicable)
   * Government Health Warning Statement
  4. Compare extracted label data against structured application data.
  
   * Field-by-field matching.
   * Detect mismatches.
  5. Validate Government Warning Statement:
  
   * Exact wording.
   * “GOVERNMENT WARNING:” in ALL CAPS.
   * Formatting enforcement (at least detect caps).
  6. Provide a clear pass/fail summary.
  7. Highlight discrepancies clearly.
  8. Allow judgment override or tolerance for “nuanced” matches:
  
   * Case differences (“STONE’S THROW” vs “Stone’s Throw”)
   * Minor formatting differences.
  9. Handle imperfect images:
  
   * Tilted
   * Glare
   * Poor lighting
     (Doesn’t have to be perfect, but attempt reasonable robustness.)
  
  ---
- # 2️⃣ Batch / Workflow Requirements
  
  1. Support batch upload of multiple labels.
  2. Process labels in parallel or queue.
  3. Provide status per label.
  4. Return aggregated results.
  
  ---
- # 3️⃣ Performance Requirements
  
  Critical:
  
  * Processing time per label ≤ 5 seconds.
  
  * This is explicitly a usage blocker.
  * Must feel faster than manual review.
  * No 30–40 second processing delays.
  
  ---
- # 4️⃣ User Experience Requirements
  
  Target users:
  
  * Mixed tech literacy.
  * Some 50+ years old.
  * Must be extremely intuitive.
  
  UX constraints:
  
  * Clean interface.
  * No hidden controls.
  * No hunting for buttons.
  * Minimal steps.
  * Clear visual feedback.
  * Clear error messages.
  * “My mother could use it” benchmark.
  
  ---
- # 5️⃣ AI / Intelligence Requirements
  
  Not just pattern matching.
  
  Must demonstrate:
  
  * OCR capability.
  * Text normalization.
  * Fuzzy matching for reasonable human judgment.
  * Exact match for legally strict items (warning statement).
  
  Nice-to-have (but not mandatory):
  
  * Basic image pre-processing (rotation correction, contrast).
  * Handling angled labels.
  * Handling glare partially.
  
  ---
- # 6️⃣ Technical Constraints
  
  * Standalone prototype.
  * No integration with COLA.
  * Azure-friendly.
  * Avoid heavy outbound API reliance (firewall restrictions).
  * Avoid fragile external ML endpoints.
  * Keep deployment simple.
  
  Security:
  
  * No PII storage.
  * No reckless cloud usage.
  * Production compliance not required for prototype.
  
  ---
- # 7️⃣ Deliverables
  
  Must provide:
  
  1. Source code repository:
  
   * All source code.
   * README with setup instructions.
   * Explanation of:
  
     * Architecture
     * Tools used
     * Tradeoffs
     * Assumptions.
  2. Deployed working URL.
  
  ---
- # 8️⃣ Evaluation Criteria (Explicit)
  
  They will score:
  
  * Correctness.
  * Completeness.
  * Code organization.
  * Technical choices.
  * UX clarity.
  * Error handling.
  * Attention to details.
  * Thoughtful tradeoffs.
  
  They explicitly prefer:
  
  > Working core over ambitious incomplete.
  
  ---
- # 9️⃣ Hidden Evaluation Signals (This Is Important)
  
  What they are actually testing:
  
  1. Do you over-engineer?
  2. Do you understand operational constraints?
  3. Do you prioritize performance?
  4. Do you understand human workflow?
  5. Do you design for federal environments?
  6. Do you respect nuance (Dave’s comment)?
  7. Do you handle legal strictness (Jenny’s warning requirement)?
  8. Do you consider network/firewall constraints?
  9. Do you communicate tradeoffs clearly?
  
  This is not a Kaggle AI challenge.
  
  This is:
  
  > “Can you build a practical internal tool that real agents would adopt?”
  
  ---
- # � Critical Priorities (If You Do Nothing Else)
  
  If time gets tight, make sure:
  
  * It works reliably.
  * It processes in <5 seconds.
  * Government warning validation is strict.
  * UI is extremely simple.
  * Code is clean and well documented.
  * README explains tradeoffs clearly.
  * You show awareness of nuance (case-insensitive matching, etc.)
  
  ---
  
  If you want, next we can:
  
  * Reduce this to a “minimum viable impressive” version.
  * Decide architecture direction.
  * Decide whether to use:
  
  * local OCR (Tesseract)
  * Azure Vision
  * hybrid
  * Or outline a one-week execution plan.
  
  Now we move from philosophy to disciplined engineering.