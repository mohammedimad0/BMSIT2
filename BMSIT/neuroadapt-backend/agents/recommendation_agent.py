"""
Recommendation Agent: Generate personalized learning recommendations.

Uses Gemini to dynamically generate truly personalised recommendations
based on student profile, metrics, subject, and class level.

Falls back to curated static database if Gemini unavailable.
"""

import logging
import os
import json
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ─── Static curated resource database (fallback) ──────────────────────────────

RESOURCE_DATABASE = {
    "science": {
        6: {
            "youtube": [
                {"title": "Basic Biology Explained Simply", "channel": "Kurzgesagt – In a Nutshell", "url": "https://www.youtube.com/results?search_query=class+6+science+biology+explained"},
                {"title": "Simple Chemistry for Beginners", "channel": "TED-Ed", "url": "https://www.youtube.com/results?search_query=class+6+chemistry+basics+NCERT"},
                {"title": "Physics for Kids – Forces & Motion", "channel": "SciShow Kids", "url": "https://www.youtube.com/results?search_query=class+6+physics+forces+motion+NCERT"},
            ],
            "nptel": [
                {"title": "Introductory Biology (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/102106068"},
                {"title": "Basic Chemistry Concepts (IIT Kharagpur)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/104105080"},
            ],
            "khan": [
                {"title": "Biology – All About Life", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/biology"},
                {"title": "Chemistry Basics", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/chemistry"},
            ]
        },
        7: {
            "youtube": [
                {"title": "Photosynthesis Explained", "channel": "Amoeba Sisters", "url": "https://www.youtube.com/results?search_query=photosynthesis+class+7+NCERT"},
                {"title": "The Solar System", "channel": "Crash Course Kids", "url": "https://www.youtube.com/results?search_query=solar+system+class+7+NCERT"},
                {"title": "Weather and Climate", "channel": "National Geographic", "url": "https://www.youtube.com/results?search_query=weather+climate+class+7+science"},
            ],
            "nptel": [
                {"title": "General Biology – I (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/102106068"},
                {"title": "Physics Part I (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/115101117"},
            ],
            "khan": [
                {"title": "Life Sciences", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science"},
                {"title": "Physical Science", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/physics"},
            ]
        },
        8: {
            "youtube": [
                {"title": "Cell Biology Deep Dive", "channel": "Amoeba Sisters", "url": "https://www.youtube.com/results?search_query=cell+biology+class+8+NCERT"},
                {"title": "Force and Pressure", "channel": "Khan Academy India", "url": "https://www.youtube.com/results?search_query=force+pressure+class+8+NCERT"},
                {"title": "Microorganisms: Friend and Foe", "channel": "Crash Course", "url": "https://www.youtube.com/results?search_query=microorganisms+class+8+NCERT"},
            ],
            "nptel": [
                {"title": "General Biology – II (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/102106068"},
                {"title": "Physics – II (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/115101117"},
            ],
            "khan": [
                {"title": "Biology", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/biology"},
                {"title": "Chemistry", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/chemistry"},
            ]
        },
        9: {
            "youtube": [
                {"title": "Matter in Our Surroundings", "channel": "Physics Wallah", "url": "https://www.youtube.com/results?search_query=matter+in+our+surroundings+class+9+NCERT"},
                {"title": "Tissues – Biology Class 9", "channel": "Unacademy", "url": "https://www.youtube.com/results?search_query=tissues+class+9+NCERT+biology"},
                {"title": "Motion – Class 9 Physics", "channel": "NCERT Official", "url": "https://www.youtube.com/results?search_query=motion+class+9+NCERT+physics"},
            ],
            "nptel": [
                {"title": "Biology – Advanced (IIT Delhi)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/102101047"},
                {"title": "Physics – Advanced Applications (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/115106093"},
            ],
            "khan": [
                {"title": "Advanced Biology", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/biology"},
                {"title": "Advanced Chemistry", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/chemistry"},
            ]
        },
        10: {
            "youtube": [
                {"title": "Chemical Reactions and Equations", "channel": "Physics Wallah", "url": "https://www.youtube.com/results?search_query=chemical+reactions+equations+class+10+NCERT"},
                {"title": "Life Processes – Class 10", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=life+processes+class+10+NCERT"},
                {"title": "Electricity – Class 10 Physics", "channel": "NCERT Official", "url": "https://www.youtube.com/results?search_query=electricity+class+10+NCERT+physics"},
            ],
            "nptel": [
                {"title": "General Biology – III (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/102106068"},
                {"title": "Physics – Advanced (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/115101117"},
            ],
            "khan": [
                {"title": "AP Biology", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/ap-biology"},
                {"title": "AP Chemistry", "platform": "Khan Academy", "url": "https://www.khanacademy.org/science/ap-chemistry"},
            ]
        }
    },
    "maths": {
        6: {
            "youtube": [
                {"title": "Number Systems – Class 6", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=number+system+class+6+NCERT+maths"},
                {"title": "Basic Geometry Made Easy", "channel": "Math Antics", "url": "https://www.youtube.com/results?search_query=geometry+class+6+NCERT"},
                {"title": "Fractions Simplified", "channel": "Khan Academy", "url": "https://www.youtube.com/results?search_query=fractions+class+6+NCERT"},
            ],
            "nptel": [
                {"title": "Mathematics – Basics (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/111104137"},
            ],
            "khan": [
                {"title": "Arithmetic and Pre-Algebra", "platform": "Khan Academy", "url": "https://www.khanacademy.org/math/arithmetic"},
            ]
        },
        7: {
            "youtube": [
                {"title": "Simple Equations – Class 7", "channel": "Physics Wallah", "url": "https://www.youtube.com/results?search_query=simple+equations+class+7+NCERT+maths"},
                {"title": "Triangles and Its Properties", "channel": "Unacademy", "url": "https://www.youtube.com/results?search_query=triangles+class+7+NCERT"},
                {"title": "Data Handling – Statistics Basics", "channel": "Math Antics", "url": "https://www.youtube.com/results?search_query=data+handling+class+7+NCERT"},
            ],
            "nptel": [
                {"title": "Mathematics – Algebra (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/111104137"},
            ],
            "khan": [
                {"title": "Pre-Algebra", "platform": "Khan Academy", "url": "https://www.khanacademy.org/math/pre-algebra"},
            ]
        },
        8: {
            "youtube": [
                {"title": "Linear Equations in Two Variables", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=linear+equations+class+8+NCERT+maths"},
                {"title": "Introduction to Trigonometry", "channel": "Math Antics", "url": "https://www.youtube.com/results?search_query=introduction+trigonometry+class+8+NCERT"},
                {"title": "Mensuration – Area and Volume", "channel": "Khan Academy India", "url": "https://www.youtube.com/results?search_query=mensuration+class+8+NCERT"},
            ],
            "nptel": [
                {"title": "Mathematics – Algebra & Geometry (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/111104137"},
            ],
            "khan": [
                {"title": "Algebra 1", "platform": "Khan Academy", "url": "https://www.khanacademy.org/math/algebra"},
            ]
        },
        9: {
            "youtube": [
                {"title": "Number Systems – Class 9", "channel": "NCERT Official", "url": "https://www.youtube.com/results?search_query=number+systems+class+9+NCERT+maths"},
                {"title": "Polynomials – Class 9", "channel": "Physics Wallah", "url": "https://www.youtube.com/results?search_query=polynomials+class+9+NCERT"},
                {"title": "Coordinate Geometry", "channel": "3Blue1Brown", "url": "https://www.youtube.com/results?search_query=coordinate+geometry+class+9+NCERT"},
            ],
            "nptel": [
                {"title": "Mathematics – Advanced (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/111104137"},
            ],
            "khan": [
                {"title": "Algebra 2", "platform": "Khan Academy", "url": "https://www.khanacademy.org/math/algebra2"},
            ]
        },
        10: {
            "youtube": [
                {"title": "Quadratic Equations – Class 10", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=quadratic+equations+class+10+NCERT+maths"},
                {"title": "Trigonometry – Class 10", "channel": "Physics Wallah", "url": "https://www.youtube.com/results?search_query=trigonometry+class+10+NCERT"},
                {"title": "Statistics and Probability", "channel": "3Blue1Brown", "url": "https://www.youtube.com/results?search_query=statistics+probability+class+10+NCERT"},
            ],
            "nptel": [
                {"title": "Mathematics – Calculus (IIT Delhi)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/111102064"},
            ],
            "khan": [
                {"title": "Precalculus", "platform": "Khan Academy", "url": "https://www.khanacademy.org/math/precalculus"},
            ]
        }
    },
    "english": {
        6: {
            "youtube": [
                {"title": "Reading Comprehension Skills", "channel": "English Speeches", "url": "https://www.youtube.com/results?search_query=reading+comprehension+class+6+english"},
                {"title": "Grammar Fundamentals for Beginners", "channel": "BBC Learning English", "url": "https://www.youtube.com/results?search_query=english+grammar+class+6+NCERT"},
            ],
            "nptel": [
                {"title": "English Communication – Basics (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109104117"},
            ],
            "khan": [
                {"title": "Reading and Language Arts", "platform": "Khan Academy", "url": "https://www.khanacademy.org/ela"},
            ]
        },
        7: {"youtube": [{"title": "Literary Analysis Made Simple", "channel": "Mr. Bruff", "url": "https://www.youtube.com/results?search_query=literary+analysis+class+7+english"}, {"title": "Advanced Grammar – Tenses and Voice", "channel": "BBC Learning English", "url": "https://www.youtube.com/results?search_query=advanced+grammar+class+7+english"}], "nptel": [{"title": "English Communication – Intermediate (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109104117"}], "khan": [{"title": "Literature and Composition", "platform": "Khan Academy", "url": "https://www.khanacademy.org/ela"}]},
        8: {"youtube": [{"title": "Shakespeare for Class 8", "channel": "Mr. Bruff", "url": "https://www.youtube.com/results?search_query=shakespeare+class+8+english"}, {"title": "Critical Thinking in English", "channel": "TED-Ed", "url": "https://www.youtube.com/results?search_query=critical+thinking+english+class+8"}], "nptel": [{"title": "English Communication – Advanced (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109104117"}], "khan": [{"title": "AP English Language", "platform": "Khan Academy", "url": "https://www.khanacademy.org/ela"}]},
        9: {"youtube": [{"title": "Essay Writing Mastery", "channel": "The Strive Studies", "url": "https://www.youtube.com/results?search_query=essay+writing+class+9+english"}, {"title": "Beehive – Class 9 English", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=beehive+class+9+english+NCERT"}], "nptel": [{"title": "Advanced English Communication (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109104117"}], "khan": [{"title": "English Literature", "platform": "Khan Academy", "url": "https://www.khanacademy.org/ela"}]},
        10: {"youtube": [{"title": "First Flight – Class 10 English", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=first+flight+class+10+english+NCERT"}, {"title": "Advanced Essay Writing", "channel": "The Strive Studies", "url": "https://www.youtube.com/results?search_query=advanced+essay+writing+class+10+english"}], "nptel": [{"title": "English Literature and Culture (IIT Bombay)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109104117"}], "khan": [{"title": "AP English Literature", "platform": "Khan Academy", "url": "https://www.khanacademy.org/ela"}]},
    },
    "social-science": {
        6: {"youtube": [{"title": "History – Our Past Class 6", "channel": "History Class", "url": "https://www.youtube.com/results?search_query=our+past+class+6+history+NCERT"}, {"title": "The Earth Our Habitat", "channel": "Geography Now", "url": "https://www.youtube.com/results?search_query=earth+our+habitat+class+6+geography+NCERT"}], "nptel": [{"title": "Introduction to Social Sciences (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109106104"}], "khan": [{"title": "World History", "platform": "Khan Academy", "url": "https://www.khanacademy.org/humanities/world-history"}]},
        7: {"youtube": [{"title": "Our Pasts II – Class 7 History", "channel": "Historyman", "url": "https://www.youtube.com/results?search_query=our+pasts+class+7+history+NCERT"}, {"title": "Environment – Class 7 Geography", "channel": "Geography Now", "url": "https://www.youtube.com/results?search_query=environment+class+7+geography+NCERT"}], "nptel": [{"title": "Indian History (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109106104"}], "khan": [{"title": "AP World History", "platform": "Khan Academy", "url": "https://www.khanacademy.org/humanities/ap-world-history"}]},
        8: {"youtube": [{"title": "Resources and Development – Class 8", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=resources+development+class+8+social+science"}, {"title": "The Indian Constitution", "channel": "LawSikho", "url": "https://www.youtube.com/results?search_query=indian+constitution+class+8+civics+NCERT"}], "nptel": [{"title": "Democracy and Governance (IIT Delhi)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109102047"}], "khan": [{"title": "Civics and Government", "platform": "Khan Academy", "url": "https://www.khanacademy.org/humanities/us-government-and-civics"}]},
        9: {"youtube": [{"title": "Contemporary India – Class 9", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=contemporary+india+class+9+geography+NCERT"}, {"title": "India and Contemporary World – Class 9", "channel": "History Class", "url": "https://www.youtube.com/results?search_query=india+contemporary+world+class+9+history+NCERT"}], "nptel": [{"title": "Indian History (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109106104"}], "khan": [{"title": "World History", "platform": "Khan Academy", "url": "https://www.khanacademy.org/humanities/world-history"}]},
        10: {"youtube": [{"title": "Power Sharing – Class 10 Civics", "channel": "Vedantu", "url": "https://www.youtube.com/results?search_query=power+sharing+class+10+civics+NCERT"}, {"title": "Resources and Development – Class 10", "channel": "Unacademy", "url": "https://www.youtube.com/results?search_query=resources+development+class+10+geography+NCERT"}], "nptel": [{"title": "Indian Polity (IIT Madras)", "platform": "NPTEL", "url": "https://nptel.ac.in/courses/109106104"}], "khan": [{"title": "AP World History", "platform": "Khan Academy", "url": "https://www.khanacademy.org/humanities/ap-world-history"}]},
    }
}


# ─── Gemini-powered AI recommendation generator ───────────────────────────────

def _call_gemini(prompt: str) -> Optional[str]:
    """Call Gemini API and return the text response."""
    if not GEMINI_API_KEY:
        logger.warning("[recommendation_agent] GEMINI_API_KEY not set — skipping AI call")
        return None

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            },
            timeout=30
        )
        if response.status_code != 200:
            logger.warning(f"[recommendation_agent] Gemini error: {response.status_code}")
            return None
        data = response.json()
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", None)
    except Exception as e:
        logger.error(f"[recommendation_agent] Gemini call failed: {e}")
        return None


def generate_ai_recommendations(
    subject: str,
    class_level: int,
    student_metrics: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Use Gemini to generate truly personalised recommendations.
    Returns structured JSON or None if Gemini unavailable.
    """
    metrics = student_metrics or {}
    profile = metrics.get("profile", "general learner")
    reading_wpm = metrics.get("readingWpm", 150)
    mistakes = metrics.get("mistakesPerQuiz", 0)
    stress = metrics.get("recentStress", 0.1)
    completed = metrics.get("completedLessons", 0)

    prompt = f"""You are an expert educational psychologist and curriculum advisor specialising in neurodivergent learning.

A student with the following profile needs personalised learning recommendations:
- Subject: {subject} (Class {class_level}, NCERT/CBSE curriculum)
- Learning Profile: {profile}
- Reading Speed: {reading_wpm} WPM
- Quiz Mistakes Per Session: {mistakes}
- Stress Level (0-1): {stress}
- Completed Lessons: {completed}

Generate a comprehensive personalised recommendation plan as a JSON object with EXACTLY this structure:
{{
  "difficulty": "easy" | "intermediate" | "advanced",
  "tips": ["tip 1", "tip 2", "tip 3", "tip 4", "tip 5"],
  "adaptations": ["adaptation_key_1", "adaptation_key_2"],
  "youtube_searches": [
    {{"title": "descriptive video title", "search_query": "exact YouTube search query for Class {class_level} {subject} NCERT", "reason": "why this helps this student's profile"}},
    {{"title": "descriptive video title", "search_query": "exact YouTube search query", "reason": "why this helps"}},
    {{"title": "descriptive video title", "search_query": "exact YouTube search query", "reason": "why this helps"}}
  ],
  "activities": [
    {{"name": "Activity name", "type": "visual|auditory|kinesthetic|structured", "description": "How to do it", "duration_minutes": 15}},
    {{"name": "Activity name", "type": "visual|auditory|kinesthetic|structured", "description": "How to do it", "duration_minutes": 20}},
    {{"name": "Activity name", "type": "visual|auditory|kinesthetic|structured", "description": "How to do it", "duration_minutes": 10}}
  ],
  "study_timeline": {{
    "total_days": 14,
    "daily_minutes": 30,
    "weekly_schedule": [
      {{"day": "Monday", "focus": "topic focus", "activity": "specific activity", "duration_minutes": 30}},
      {{"day": "Tuesday", "focus": "topic focus", "activity": "specific activity", "duration_minutes": 30}},
      {{"day": "Wednesday", "focus": "topic focus", "activity": "specific activity", "duration_minutes": 30}},
      {{"day": "Thursday", "focus": "topic focus", "activity": "specific activity", "duration_minutes": 30}},
      {{"day": "Friday", "focus": "topic focus", "activity": "specific activity", "duration_minutes": 30}},
      {{"day": "Saturday", "focus": "Review and consolidation", "activity": "quiz or flashcard review", "duration_minutes": 45}},
      {{"day": "Sunday", "focus": "Rest and light exploration", "activity": "watch one recommended video", "duration_minutes": 20}}
    ],
    "checkpoints": [
      {{"day": 7, "task": "Mid-week self-assessment description"}},
      {{"day": 14, "task": "Final review task description"}}
    ]
  }},
  "profile_insight": "2-3 sentence personalised insight about this student's learning style and how the recommendations address their specific needs"
}}

Tailor everything specifically to the student's profile ({profile}) and make the YouTube search queries very specific to Class {class_level} {subject} NCERT content.
Return ONLY the JSON object, no other text."""

    raw = _call_gemini(prompt)
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"[recommendation_agent] JSON parse error: {e}")
        return None


# ─── Static-database fallback ────────────────────────────────────────────────

def generate_recommendations(
    subject: str,
    class_level: int,
    student_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate personalised recommendations.

    Tries Gemini first; falls back to static DB + rule-based adaptations.
    """
    metrics = student_metrics or {}

    # ── Try Gemini AI first ──
    ai_result = generate_ai_recommendations(subject, class_level, student_metrics)
    if ai_result:
        logger.info("[recommendation_agent] Using Gemini AI recommendations")

        # Convert youtube_searches to the standard resources format
        youtube_resources = []
        for ys in ai_result.get("youtube_searches", []):
            query = ys.get("search_query", "")
            youtube_resources.append({
                "title": ys.get("title", "YouTube Resource"),
                "channel": "YouTube Search",
                "url": f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
            })

        # Get static NPTEL and Khan resources as base
        base = RESOURCE_DATABASE.get(subject.lower(), {}).get(class_level, {})

        return {
            "resources": {
                "youtube": youtube_resources,
                "nptel": base.get("nptel", []),
                "khan": base.get("khan", []),
            },
            "tips": ai_result.get("tips", []),
            "difficulty": ai_result.get("difficulty", "intermediate"),
            "adaptations": ai_result.get("adaptations", []),
            "activities": ai_result.get("activities", []),
            "study_timeline": ai_result.get("study_timeline", {}),
            "profile_insight": ai_result.get("profile_insight", ""),
            "ai_powered": True,
        }

    # ── Fallback: static DB + rule-based ──
    logger.info("[recommendation_agent] Using static DB recommendations (Gemini unavailable)")
    base_resources = RESOURCE_DATABASE.get(subject.lower(), {}).get(class_level, {})

    if not base_resources:
        return {
            "resources": {"youtube": [], "nptel": [], "khan": []},
            "tips": ["Subject or class level not found in recommendation database."],
            "difficulty": "intermediate",
            "adaptations": [],
            "activities": [],
            "study_timeline": {},
            "profile_insight": "",
            "ai_powered": False,
        }

    recommendations: Dict[str, Any] = {
        "resources": base_resources,
        "tips": [],
        "difficulty": "intermediate",
        "adaptations": [],
        "activities": [],
        "study_timeline": {},
        "profile_insight": "",
        "ai_powered": False,
    }

    reading_wpm = metrics.get("readingWpm", 150)
    if reading_wpm < 100:
        recommendations["difficulty"] = "easy"
        recommendations["tips"].append("📖 Slow reading pace: Focus on visual resources and shorter videos (under 10 min)")
        recommendations["adaptations"].append("visual_heavy")
    elif reading_wpm > 200:
        recommendations["difficulty"] = "advanced"
        recommendations["tips"].append("⚡ Fast reading pace: Try challenging resources and detailed articles")
        recommendations["adaptations"].append("text_heavy")

    profile = metrics.get("profile", "").lower()
    if "dyslexia" in profile or "dyslexic" in profile:
        recommendations["tips"].append("📚 Dyslexia-friendly: Choose resources with clear typography and audio support")
        recommendations["tips"].append("🎧 Try listening to the chapter text using TTS before reading it")
        recommendations["adaptations"].append("dyslexia_friendly")
        recommendations["activities"].append({"name": "Audio-first learning", "type": "auditory", "description": "Listen to the chapter narration before reading. Pause and repeat difficult sections.", "duration_minutes": 15})
    elif "adhd" in profile:
        recommendations["tips"].append("⏱️ Short attention span: Prefer videos under 8 minutes and use the Pomodoro technique")
        recommendations["tips"].append("🎮 Use interactive quizzes and gamified learning to maintain focus")
        recommendations["adaptations"].append("short_format")
        recommendations["activities"].append({"name": "Pomodoro Study Burst", "type": "structured", "description": "Study for 15 minutes, then take a 5-minute movement break. Repeat 3 times.", "duration_minutes": 20})
    elif "autism" in profile or "autistic" in profile:
        recommendations["tips"].append("🧠 Structured learning: Follow step-by-step tutorials in logical, predictable order")
        recommendations["tips"].append("📋 Create a visual checklist of topics covered before moving to the next")
        recommendations["adaptations"].append("structured_format")
        recommendations["activities"].append({"name": "Topic checklist mapping", "type": "structured", "description": "Create a visual checklist of all chapter objectives. Tick each one as you understand it.", "duration_minutes": 10})

    stress = metrics.get("recentStress", 0.1)
    if stress > 0.7:
        recommendations["tips"].append("😌 High stress detected: Take breaks and try relaxing, gamified learning content")
        recommendations["adaptations"].append("stress_relief")

    mistakes = metrics.get("mistakesPerQuiz", 0)
    if mistakes > 5:
        recommendations["tips"].append("🎯 Review basics: Start with foundational concepts before advanced topics")
        recommendations["adaptations"].append("review_focus")

    completed = metrics.get("completedLessons", 0)
    if completed > 10:
        recommendations["tips"].append("🌟 Consistent progress! Challenge yourself with advanced or supplementary materials")
        recommendations["adaptations"].append("challenge_focus")

    return recommendations


def generate_personalized_study_plan(
    subject: str,
    class_level: int,
    student_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a personalised 14-day study plan based on student profile.
    """
    metrics = student_metrics or {}
    recommendations = generate_recommendations(subject, class_level, student_metrics)

    # If AI gave us a study_timeline already, use it
    if recommendations.get("ai_powered") and recommendations.get("study_timeline"):
        plan = recommendations["study_timeline"]
        plan["recommendations"] = recommendations
        return plan

    reading_wpm = metrics.get("readingWpm", 150)
    profile = metrics.get("profile", "").lower()

    if reading_wpm < 100:
        session_duration = 20
    elif reading_wpm < 150:
        session_duration = 30
    else:
        session_duration = 45

    # ADHD: shorter sessions
    if "adhd" in profile:
        session_duration = min(session_duration, 25)

    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    topic_focuses = [
        f"Introduction to {subject} concepts",
        "Core vocabulary and key terms",
        "Reading and comprehension practice",
        "Visual/diagram study",
        "Practice problems and exercises",
        "Review and self-quiz",
        "Light exploration and video",
        "Deep reading – first half",
        "Deep reading – second half",
        "Concept mapping",
        "Error analysis and correction",
        "Revision of weak areas",
        "Full chapter mock test",
        "Final review and celebration",
    ]

    weekly_schedule = []
    for i, day in enumerate(days_of_week):
        focus_idx = i % len(topic_focuses)
        weekly_schedule.append({
            "day": day,
            "focus": topic_focuses[focus_idx],
            "activity": "Read → Summarise → Test" if i % 2 == 0 else "Watch video → Take notes → Review glossary",
            "duration_minutes": session_duration if day not in ["Saturday"] else session_duration + 15,
        })

    plan = {
        "total_days": 14,
        "daily_minutes": session_duration,
        "weekly_schedule": weekly_schedule,
        "checkpoints": [
            {"day": 7, "task": f"Complete a self-quiz on the first half of {subject} topics"},
            {"day": 14, "task": f"Full chapter assessment and study plan review"},
        ],
        "recommendations": recommendations,
        "total_study_hours": round((session_duration * 14) / 60, 1),
    }

    return plan
