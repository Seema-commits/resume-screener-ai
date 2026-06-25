import json
import re

from app.services.ai_service import call_ai
from app.prompts.screening_prompts import SCREENING_PROMPT
from app.prompts.parsing_prompts import PARSE_PROMPT
from app.utils.json_parser import extract_json
from app.utils.date_utils import run_integrity_checks
from app.utils.weight_rules import derive_criteria_weights
from app.utils.location_rules import (
    parse_jd_location,
    check_location_mismatch
)
from app.models.screening_models import (
    CandidateScoringResponse,
    ParsedProfilesResponse
)
from app.services.logging_service import log_event


# Candidates per batch, for BOTH parsing and scoring calls. Kept
# small so a batch's JSON response never gets close to the model's
# max_tokens limit, regardless of how many resumes are uploaded in
# total (this is what fixes the truncation/JSON-decode-error issue
# at scale).
BATCH_SIZE = 5

PARSE_MAX_TOKENS_PER_BATCH = 3000
SCORING_MAX_TOKENS_PER_BATCH = 4000


def _split_into_candidate_chunks(candidate_text):
    """
    parser_service.py formats combined_text with
    "--- Candidate N: name ---" markers before each resume's text.
    Split back into one chunk per candidate so parsing can be
    batched instead of sent as one giant request.
    """

    parts = re.split(r"(?=--- Candidate \d+:)", candidate_text)
    return [p.strip() for p in parts if p.strip()]


class ScreeningAgent:

    # -----------------------------------------------
    # STAGE 1: parse raw resume text into structured
    # entities (roles with dates, education, skills).
    # Facts only - no scoring/judgment happens here.
    # Done in batches so large resume counts can't
    # truncate the response.
    # -----------------------------------------------

    def parse_resumes(self, session_id, candidate_text, api_key=None):

        chunks = _split_into_candidate_chunks(candidate_text)

        if not chunks:
            return []

        all_profiles = []

        for i in range(0, len(chunks), BATCH_SIZE):

            batch_chunks = chunks[i:i + BATCH_SIZE]
            batch_text = "\n\n".join(batch_chunks)

            response = call_ai(
                batch_text,
                system_prompt=PARSE_PROMPT,
                max_tokens=PARSE_MAX_TOKENS_PER_BATCH,
                api_key=api_key
            )

            try:

                parsed = extract_json(response)
                validated = ParsedProfilesResponse(**parsed)
                all_profiles.extend(validated.profiles)

            except Exception as e:

                print("\n===== PARSE BATCH ERROR =====\n")
                print(f"Batch {i // BATCH_SIZE + 1}: {str(e)}")
                print("\n==============================\n")

                log_event(
                    session_id=session_id,
                    agent_name="ScreeningAgent",
                    event_type="parse_batch_error",
                    data={
                        "batch_index": i // BATCH_SIZE,
                        "error": str(e),
                        "raw_response": response
                    }
                )

                # one failed parse batch shouldn't sink the whole
                # run - those candidates just won't get flags/
                # scored against structured facts, skip and continue
                continue

        log_event(
            session_id=session_id,
            agent_name="ScreeningAgent",
            event_type="parsed_profiles",
            data={
                "profile_count": len(all_profiles),
                # Full roles/dates per candidate - this is what
                # lets you compare what Stage 1 actually extracted
                # between two runs if a flag (e.g. date overlap)
                # unexpectedly appears or disappears.
                "profiles": [p.model_dump() for p in all_profiles]
            }
        )

        return all_profiles

    # -----------------------------------------------
    # STAGE 2: deterministic integrity checks. Pure
    # Python, NO LLM call - this is what makes these
    # flags defensible/explainable in the demo.
    # -----------------------------------------------

    def detect_flags(self, profiles, job_description):

        jd_location_info = parse_jd_location(job_description)

        flags_by_candidate = {}

        for profile in profiles:

            flags = run_integrity_checks(profile)

            flags += check_location_mismatch(
                profile.location,
                jd_location_info
            )

            if flags:
                flags_by_candidate[profile.candidate_name] = flags

        return flags_by_candidate

    # -----------------------------------------------
    # STAGE 3: score against the JD using the
    # structured profiles + deterministic flags as
    # input. Per-criterion breakdown, never a single
    # opaque number. Done in small BATCHES so the
    # response never gets large enough to be truncated,
    # no matter how many resumes are uploaded.
    # -----------------------------------------------

    def score_batch(
        self,
        session_id,
        job_description,
        profiles_batch,
        deterministic_flags,
        criteria_weights,
        api_key=None
    ):

        profiles_json = json.dumps(
            [p.model_dump() for p in profiles_batch],
            indent=2
        )

        batch_flags = {
            p.candidate_name: deterministic_flags[p.candidate_name]
            for p in profiles_batch
            if p.candidate_name in deterministic_flags
        }

        flags_json = json.dumps(batch_flags, indent=2)

        criteria_json = json.dumps(criteria_weights, indent=2)

        prompt = f"""
        Job Description:
        {job_description}

        Use EXACTLY these 4 criteria and point caps for every
        candidate in this batch (derived deterministically from
        the job description above - do not change them):
        {criteria_json}

        Structured Candidate Profiles in this batch (already
        parsed - facts, trust these, do not re-parse from scratch):
        {profiles_json}

        Integrity flags already detected by deterministic code for
        these candidates, keyed by candidate_name (copy these into
        each candidate's flags list exactly as given, then add your
        own if you find contradictions or unverifiable skills):
        {flags_json}
        """

        response = call_ai(
            prompt,
            system_prompt=SCREENING_PROMPT,
            max_tokens=SCORING_MAX_TOKENS_PER_BATCH,
            api_key=api_key
        )

        try:

            parsed_response = extract_json(response)

            validated_response = CandidateScoringResponse(
                **parsed_response
            )

            return validated_response.candidates

        except Exception as e:

            raise RuntimeError(
                f"{str(e)} | RAW RESPONSE: {response[:500]}"
            )

    # -----------------------------------------------
    # Deterministic classification: shortlist/reject
    # is decided here, in code, not by the LLM. This
    # also scales correctly to any number of resumes.
    # -----------------------------------------------

    def classify_candidates(self, candidates, top_n, score_threshold_100):

        qualified = [
            c for c in candidates
            if c.score >= score_threshold_100
        ]

        qualified.sort(key=lambda c: c.score, reverse=True)

        if top_n == "All qualified":
            shortlisted = qualified
        else:
            shortlisted = qualified[:int(top_n)]

        shortlisted_names = {
            c.candidate_name for c in shortlisted
        }

        rejected = [
            c for c in candidates
            if c.candidate_name not in shortlisted_names
        ]

        rejected.sort(key=lambda c: c.score, reverse=True)

        return shortlisted, rejected

    # -----------------------------------------------
    # MAIN ENTRY POINT
    # -----------------------------------------------

    def screen_candidates(
        self,
        session_id,
        job_description,
        candidate_text,
        top_n,
        score_threshold,
        api_key=None
    ):

        # ---------------------------------------
        # Stage 1
        # ---------------------------------------

        try:

            profiles = self.parse_resumes(
                session_id,
                candidate_text,
                api_key=api_key
            )

        except Exception as e:

            log_event(
                session_id=session_id,
                agent_name="ScreeningAgent",
                event_type="parse_error",
                data={"error": str(e)}
            )

            return {
                "error": "Resume parsing failed",
                "details": str(e)
            }

        # ---------------------------------------
        # Stage 2
        # ---------------------------------------

        deterministic_flags = self.detect_flags(
            profiles,
            job_description
        )

        # Derived ONCE per run (per job description), reused
        # identically across every candidate/batch - this is what
        # keeps the ranking apples-to-apples within a single run,
        # even though different JDs can produce different weights.
        weight_result = derive_criteria_weights(job_description)
        criteria_weights = weight_result["weights"]

        log_event(
            session_id=session_id,
            agent_name="ScreeningAgent",
            event_type="request",
            data={
                "job_description": job_description,
                "top_n": top_n,
                "score_threshold": score_threshold,
                "deterministic_flags": deterministic_flags,
                "candidate_count": len(profiles),
                "criteria_weights": criteria_weights,
                "matched_weight_signals": weight_result[
                    "matched_signals"
                ]
            }
        )

        # ---------------------------------------
        # Stage 3 - score in batches
        # ---------------------------------------

        all_candidates = []
        last_error = None

        for i in range(0, len(profiles), BATCH_SIZE):

            batch = profiles[i:i + BATCH_SIZE]

            try:

                batch_candidates = self.score_batch(
                    session_id,
                    job_description,
                    batch,
                    deterministic_flags,
                    criteria_weights,
                    api_key=api_key
                )

                all_candidates.extend(batch_candidates)

            except Exception as e:

                last_error = str(e)

                print("\n===== BATCH SCORING ERROR =====\n")
                print(f"Batch {i // BATCH_SIZE + 1}: {last_error}")
                print("\n================================\n")

                log_event(
                    session_id=session_id,
                    agent_name="ScreeningAgent",
                    event_type="batch_error",
                    data={
                        "batch_index": i // BATCH_SIZE,
                        "error": last_error
                    }
                )

                # one failed batch shouldn't sink the whole run -
                # skip it and keep going with the rest
                continue

        if not all_candidates:

            return {
                "error": "Validation failed",
                "details": (
                    "No candidates could be scored - "
                    "all batches failed"
                ),
                "raw_response": (
                    last_error or "No error details captured"
                )
            }

        # ---------------------------------------
        # Classify (deterministic, in code)
        # ---------------------------------------

        score_threshold_100 = score_threshold * 10

        shortlisted, rejected = self.classify_candidates(
            all_candidates,
            top_n,
            score_threshold_100
        )

        output = {
            "shortlisted_candidates": [
                c.model_dump() for c in shortlisted
            ],
            "rejected_candidates": [
                c.model_dump() for c in rejected
            ],
            "parsed_profiles": [
                p.model_dump() for p in profiles
            ],
            "criteria_weights": criteria_weights,
            "matched_weight_signals": weight_result[
                "matched_signals"
            ]
        }

        log_event(
            session_id=session_id,
            agent_name="ScreeningAgent",
            event_type="response",
            data=output
        )

        return output